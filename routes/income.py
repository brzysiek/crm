import json
from datetime import date

from dateutil.relativedelta import relativedelta
from flask import (Blueprint, flash, redirect, render_template,
                   request, session, url_for)

from models.dictionary import get_income_categories
from models.income import (create_income, delete_income, get_all_incomes,
                           get_income_by_id, update_income)
from models.user_settings import get_user_setting

bp = Blueprint('income', __name__, url_prefix='/income')

INCOME_COLUMNS = [
    {'key': 'client',           'label': 'Klient'},
    {'key': 'description',      'label': 'Opis'},
    {'key': 'category',         'label': 'Kategoria'},
    {'key': 'payment_status',   'label': 'Status płatności'},
    {'key': 'invoice',          'label': 'Faktura'},
    {'key': 'payment_method',   'label': 'Forma'},
    {'key': 'source',           'label': 'Skąd'},
    {'key': 'responsible',      'label': 'Odpowiedzialny'},
]
INCOME_COLUMNS_SETTING_KEY = 'income_columns'


def _visible_income_columns():
    all_keys = [c['key'] for c in INCOME_COLUMNS]
    saved = get_user_setting(session['user_id'], INCOME_COLUMNS_SETTING_KEY)
    if not saved:
        return all_keys
    try:
        cols = [c for c in json.loads(saved) if c in all_keys]
        return cols or all_keys
    except (ValueError, TypeError):
        return all_keys

MONTHS_PL = {
    1: 'styczeń', 2: 'luty', 3: 'marzec', 4: 'kwiecień',
    5: 'maj', 6: 'czerwiec', 7: 'lipiec', 8: 'sierpień',
    9: 'wrzesień', 10: 'październik', 11: 'listopad', 12: 'grudzień',
}


def _last_months(n=18):
    months = []
    today = date.today()
    for i in range(n):
        d = today - relativedelta(months=i)
        months.append({
            'value': d.strftime('%Y-%m'),
            'label': f"{MONTHS_PL[d.month]} {d.year}",
        })
    return months


def _parse_form(form):
    category = form.get('category', '').strip()
    if category == '__new__':
        category = form.get('category_new', '').strip()

    try:
        vat_rate = float(form.get('vat_rate', 23))
    except ValueError:
        vat_rate = 23.0

    try:
        amount_gross = float(form.get('amount_gross', 0))
    except ValueError:
        amount_gross = 0.0

    if vat_rate < 0:
        amount_net = amount_gross
    else:
        amount_net = round(amount_gross / (1 + vat_rate / 100), 2)

    try:
        amount_net_form = float(form.get('amount_net') or amount_net)
    except ValueError:
        amount_net_form = amount_net

    try:
        orig_amount = float(form.get('orig_amount') or 0) or None
    except (ValueError, TypeError):
        orig_amount = None
    orig_currency = form.get('orig_currency', '').strip() or None
    if orig_currency == 'PLN':
        orig_currency = None
        orig_amount   = None

    income_date = form.get('date', date.today().isoformat())
    accounting_month = form.get('accounting_month', '').strip() or income_date[:7]

    return {
        'payment_due_date':  form.get('payment_due_date', '').strip() or None,
        'date':            income_date,
        'accounting_month': accounting_month,
        'client_name':     form.get('client_name', '').strip() or None,
        'client_nip':      form.get('client_nip', '').strip() or None,
        'description':     form.get('description', '').strip(),
        'invoice_number':  form.get('invoice_number', '').strip() or None,
        'amount_gross':    amount_gross,
        'vat_rate':        vat_rate,
        'amount_net':      amount_net_form,
        'orig_amount':     orig_amount,
        'orig_currency':   orig_currency,
        'invoice_status':  form.get('invoice_status', 'none'),
        'invoice_ref':     form.get('invoice_ref', '').strip() or None,
        'payment_method':  form.get('payment_method') or None,
        'payment_status':  form.get('payment_status', 'unpaid'),
        'category':        category or None,
        'notes':           form.get('notes', '').strip() or None,
        'paid_by':         form.get('paid_by', '').strip() or None,
        'source':          form.get('source', '').strip() or None,
    }


def _validate(data):
    errors = []
    if not data.get('date'):
        errors.append('Data jest wymagana.')
    if not data.get('description'):
        errors.append('Opis jest wymagany.')
    if not data.get('amount_gross') or float(data.get('amount_gross', 0)) <= 0:
        errors.append('Kwota brutto musi być większa od zera.')
    return errors


@bp.route('/')
def list_incomes():
    month = request.args.get('month', '')
    category = request.args.get('category', '')
    payment_status = request.args.get('payment_status', '')
    search = request.args.get('search', '')

    from models.income import get_monthly_income_kpi
    incomes = get_all_incomes(
        month=month or None,
        category=category or None,
        payment_status=payment_status or None,
        search=search or None,
    )
    kpi = get_monthly_income_kpi(month) if month else None
    categories = get_income_categories()
    visible_columns = _visible_income_columns()

    return render_template('income/list.html',
        incomes=incomes,
        kpi=kpi,
        categories=categories,
        months=_last_months(),
        filters={
            'month': month, 'category': category,
            'payment_status': payment_status, 'search': search,
        },
        columns=INCOME_COLUMNS,
        visible_columns=visible_columns,
        columns_setting_key=INCOME_COLUMNS_SETTING_KEY,
    )


@bp.route('/new', methods=['GET', 'POST'])
def new_income():
    categories = get_income_categories()
    today = date.today().isoformat()

    if request.method == 'POST':
        data = _parse_form(request.form)
        errors = _validate(data)
        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('income/form.html',
                income=request.form, categories=categories,
                action=url_for('income.new_income'),
                title='Nowy przychód', today=today)

        income_id = create_income(data)

        fi_id = request.form.get('fakturownia_id', '').strip()
        if fi_id:
            try:
                from database import get_db
                db = get_db()
                with db.cursor() as cur:
                    cur.execute(
                        "UPDATE fakturownia_invoices "
                        "SET status='assigned', assigned_expense_id=%s "
                        "WHERE fakturownia_id=%s",
                        (income_id, fi_id)
                    )
                db.commit()
            except Exception:
                pass

        txn_ids = request.form.getlist('bank_txn_ids[]')
        if txn_ids:
            from models.income import link_income_transaction
            for tid in txn_ids:
                try:
                    link_income_transaction(income_id, int(tid))
                except Exception:
                    pass

            if not data.get('source') or not data.get('payment_method'):
                try:
                    from models.bank_transaction import get_bank_transaction_by_id
                    first_txn = get_bank_transaction_by_id(int(txn_ids[0]))
                    if first_txn:
                        from database import get_db as _get_db
                        _db = _get_db()
                        _upd = {}
                        if not data.get('source'):
                            _upd['source'] = first_txn.get('bank')
                        if not data.get('payment_method'):
                            _upd['payment_method'] = 'transfer'
                        if _upd:
                            _sets = ', '.join(f"{k}=%s" for k in _upd)
                            with _db.cursor() as _cur:
                                _cur.execute(
                                    f"UPDATE incomes SET {_sets} WHERE id=%s",
                                    list(_upd.values()) + [income_id]
                                )
                            _db.commit()
                except Exception:
                    pass

        invoice_links = request.form.getlist('invoice_links[]')
        for link in invoice_links:
            try:
                src, inv_id_str = link.split(':', 1)
                if src == 'fakturownia':
                    from models.invoice import assign_invoice
                    assign_invoice(int(inv_id_str), income_id)
                elif src == 'gdrive':
                    from models.gdrive_invoice import assign_gdrive_invoice
                    assign_gdrive_invoice(int(inv_id_str), income_id)
            except Exception:
                pass

        flash('Przychód został zapisany.', 'success')
        return redirect(url_for('income.list_incomes'))

    # Prefill z transakcji bankowej
    bank_txn_id = request.args.get('bank_txn')
    if bank_txn_id:
        try:
            from models.bank_transaction import get_bank_transaction_by_id
            txn = get_bank_transaction_by_id(int(bank_txn_id))
            if txn:
                amount = abs(float(txn['amount'] or 0))
                txn_date = str(txn['date'])[:10] if txn.get('date') else today
                prefill = {
                    'date':          txn_date,
                    'accounting_month': txn_date[:7],
                    'amount_gross':  amount,
                    'vat_rate':      '23',
                    'client_name':   txn.get('counterparty') or '',
                    'description':   '',
                    'invoice_status': 'none',
                    'bank_txn_id':   txn['id'],
                    'orig_amount':   txn.get('orig_amount') or '',
                    'orig_currency': txn.get('orig_currency') or '',
                    'paid_by':       session.get('full_name', ''),
                }
                return render_template('income/form.html',
                    income=prefill, categories=categories,
                    action=url_for('income.new_income'),
                    title='Nowy przychód', today=today)
        except Exception:
            pass

    inv_id = request.args.get('inv')
    prefill = {'paid_by': session.get('full_name', '')}
    prefill_invoice = None
    if inv_id:
        try:
            from models.invoice import get_invoice_by_id
            inv = get_invoice_by_id(int(inv_id))
            if inv:
                import json as _json
                raw = _json.loads(inv['raw_json']) if inv.get('raw_json') else {}
                ksef = (inv.get('ksef_number') or '').strip() \
                    or (raw.get('ksef_number') or '').strip() \
                    or (raw.get('ksef_id') or '').strip() \
                    or (raw.get('gov_id') or '').strip()
                client_name = (raw.get('buyer_name') or inv.get('vendor_name') or '').strip()
                client_nip  = (raw.get('buyer_tax_no') or inv.get('vendor_nip') or '').strip()
                raw_payment_to = inv.get('payment_to') or ''
                if not raw_payment_to and inv.get('raw_json'):
                    import json as _json2
                    _raw = _json.loads(inv['raw_json']) if isinstance(inv['raw_json'], str) else {}
                    raw_payment_to = _raw.get('payment_to') or ''
                inv_date = str(inv.get('issue_date') or '')[:10] or today
                prefill = {
                    'date':             inv_date,
                    'accounting_month': inv_date[:7],
                    'payment_due_date': str(raw_payment_to)[:10] if raw_payment_to else '',
                    'amount_gross':     inv.get('amount_gross', ''),
                    'vat_rate':         '23',
                    'invoice_number':   inv.get('invoice_number', ''),
                    'client_name':      client_name,
                    'client_nip':       client_nip,
                    'description':      '',
                    'invoice_status':   'ksef' if ksef else 'none',
                    'invoice_ref':      ksef,
                    'fakturownia_id':   inv['fakturownia_id'],
                    'paid_by':          session.get('full_name', ''),
                }
                prefill_invoice = {
                    'source':         'fakturownia',
                    'id':             inv['id'],
                    'invoice_number': inv.get('invoice_number') or '',
                    'vendor_name':    client_name,
                    'issue_date':     str(inv.get('issue_date') or '')[:10],
                    'amount_gross':   float(inv.get('amount_gross') or 0) or None,
                }
        except Exception:
            pass

    return render_template('income/form.html',
        income=prefill, categories=categories,
        action=url_for('income.new_income'),
        title='Nowy przychód', today=today,
        prefill_invoice=prefill_invoice)


@bp.route('/<int:income_id>/edit', methods=['GET', 'POST'])
def edit_income(income_id):
    income = get_income_by_id(income_id)
    if not income:
        flash('Przychód nie istnieje.', 'error')
        return redirect(url_for('income.list_incomes'))

    categories = get_income_categories()
    today = date.today().isoformat()

    if request.method == 'POST':
        data = _parse_form(request.form)
        errors = _validate(data)
        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('income/form.html',
                income=request.form, categories=categories,
                action=url_for('income.edit_income', income_id=income_id),
                title='Edytuj przychód', today=today)

        update_income(income_id, data)
        flash('Przychód został zaktualizowany.', 'success')
        return redirect(url_for('income.list_incomes'))

    return render_template('income/form.html',
        income=income, categories=categories,
        action=url_for('income.edit_income', income_id=income_id),
        title='Edytuj przychód', today=today,
        income_id=income_id)


@bp.route('/<int:income_id>/delete', methods=['POST'])
def delete_income_view(income_id):
    delete_income(income_id)
    flash('Przychód został usunięty.', 'success')
    return redirect(url_for('income.list_incomes'))
