import json
from datetime import date

from dateutil.relativedelta import relativedelta
from flask import (Blueprint, flash, redirect, render_template,
                   request, session, url_for)

from models.dictionary import get_expense_categories as get_categories
from models.expense import (create_expense, delete_expense,
                             get_all_expenses, get_expense_by_id, update_expense)
from models.user import get_active_users
from models.user_settings import get_user_setting

EXPENSE_COLUMNS = [
    {'key': 'contractor',       'label': 'Kontrahent'},
    {'key': 'description',      'label': 'Opis'},
    {'key': 'category',         'label': 'Kategoria'},
    {'key': 'paid_pct',         'label': 'Opłacone'},
    {'key': 'invoice',          'label': 'Faktura'},
    {'key': 'payment_method',   'label': 'Forma'},
    {'key': 'source',           'label': 'Skąd'},
    {'key': 'responsible',      'label': 'Odpowiedzialny'},
]
EXPENSE_COLUMNS_SETTING_KEY = 'expenses_columns'


def _visible_expense_columns():
    all_keys = [c['key'] for c in EXPENSE_COLUMNS]
    saved = get_user_setting(session['user_id'], EXPENSE_COLUMNS_SETTING_KEY)
    if not saved:
        return all_keys
    try:
        cols = [c for c in json.loads(saved) if c in all_keys]
        return cols or all_keys
    except (ValueError, TypeError):
        return all_keys


def _fix_vendor_from_raw(raw: dict) -> str:
    """Zwraca nazwę dostawcy z raw_json (buyer_name = dostawca dla faktur kosztowych)."""
    return (raw.get('buyer_name') or '').strip()

bp = Blueprint('expenses', __name__, url_prefix='/expenses')

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
    person = form.get('responsible_person', '').strip()
    if person == '__other__':
        person = form.get('responsible_person_other', '').strip()

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

    expense_date = form.get('date', date.today().isoformat())
    accounting_month = form.get('accounting_month', '').strip() or expense_date[:7]

    return {
        'payment_due_date':   form.get('payment_due_date', '').strip() or None,
        'date':               expense_date,
        'accounting_month':   accounting_month,
        'responsible_person': person,
        'contractor_name':    form.get('contractor_name', '').strip() or None,
        'contractor_nip':     form.get('contractor_nip', '').strip() or None,
        'invoice_number':     form.get('invoice_number', '').strip() or None,
        'description':        form.get('description', '').strip(),
        'amount_gross':       amount_gross,
        'vat_rate':           vat_rate,
        'amount_net':         amount_net_form,
        'orig_amount':        orig_amount,
        'orig_currency':      orig_currency,
        'payment_percent':    float(form.get('payment_percent', 0) or 0),
        'invoice_status':     form.get('invoice_status', 'none'),
        'invoice_ref':        form.get('invoice_ref', '').strip() or None,
        'paid_by':            person or None,
        'payment_method':     form.get('payment_method') or None,
        'is_recurring':       form.get('is_recurring', '0') == '1',
        'category':           category or None,
        'notes':              form.get('notes', '').strip() or None,
        'source':             form.get('source', '').strip() or None,
    }


def _validate(data):
    errors = []
    if not data.get('date'):
        errors.append('Data jest wymagana.')
    if not data.get('responsible_person'):
        errors.append('Osoba odpowiedzialna jest wymagana.')
    if not data.get('description'):
        errors.append('Opis jest wymagany.')
    if not data.get('amount_gross') or float(data.get('amount_gross', 0)) <= 0:
        errors.append('Kwota brutto musi być większa od zera.')
    return errors


@bp.route('/')
def list_expenses():
    month = request.args.get('month', '')
    category = request.args.get('category', '')
    invoice_status = request.args.get('invoice_status', '')
    payment_filter = request.args.get('payment_filter', '')
    search = request.args.get('search', '')

    expenses = get_all_expenses(
        month=month or None,
        category=category or None,
        invoice_status=invoice_status or None,
        payment_filter=payment_filter or None,
        search=search or None,
    )
    categories = get_categories()
    users = get_active_users()

    from models.expense import get_monthly_kpi
    kpi = get_monthly_kpi(month) if month else None

    visible_columns = _visible_expense_columns()

    return render_template('expenses/list.html',
        expenses=expenses,
        categories=categories,
        users=users,
        months=_last_months(),
        kpi=kpi,
        filters={
            'month': month, 'category': category,
            'invoice_status': invoice_status,
            'payment_filter': payment_filter, 'search': search,
        },
        columns=EXPENSE_COLUMNS,
        visible_columns=visible_columns,
        columns_setting_key=EXPENSE_COLUMNS_SETTING_KEY,
    )


@bp.route('/new', methods=['GET', 'POST'])
def new_expense():
    users = get_active_users()
    categories = get_categories()
    today = date.today().isoformat()

    if request.method == 'POST':
        data = _parse_form(request.form)
        errors = _validate(data)
        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('expenses/form.html',
                expense=request.form, users=users, categories=categories,
                action=url_for('expenses.new_expense'),
                title='Nowy wydatek', today=today)

        expense_id = create_expense(data)

        # Oznacz fakturę jako przypisaną jeśli formularz pochodzi z Fakturowni
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
                        (expense_id, fi_id)
                    )
                db.commit()
            except Exception:
                pass

        txn_ids = request.form.getlist('bank_txn_ids[]')
        if txn_ids:
            from models.expense import link_transaction
            for tid in txn_ids:
                try:
                    link_transaction(expense_id, int(tid))
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
                                    f"UPDATE expenses SET {_sets} WHERE id=%s",
                                    list(_upd.values()) + [expense_id]
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
                    assign_invoice(int(inv_id_str), expense_id)
                elif src == 'gdrive':
                    from models.gdrive_invoice import assign_gdrive_invoice
                    assign_gdrive_invoice(int(inv_id_str), expense_id)
            except Exception:
                pass

        flash('Wydatek został zapisany.', 'success')
        return redirect(url_for('expenses.list_expenses'))

    # Prefill z transakcji bankowej
    bank_txn_id = request.args.get('bank_txn')
    if bank_txn_id:
        try:
            from models.bank_transaction import get_bank_transaction_by_id
            txn = get_bank_transaction_by_id(int(bank_txn_id))
            if txn:
                amount = abs(float(txn['amount'] or 0))
                prefill = {
                    'amount_gross':    amount,
                    'vat_rate':        '23',
                    'contractor_name': txn.get('counterparty') or '',
                    'description':     '',
                    'invoice_status':  'none',
                    'bank_txn_id':     txn['id'],
                    'orig_amount':     txn.get('orig_amount') or '',
                    'orig_currency':   txn.get('orig_currency') or '',
                }
                return render_template('expenses/form.html',
                    expense=prefill, users=users, categories=categories,
                    action=url_for('expenses.new_expense'),
                    title='Nowy wydatek', today=today)
        except Exception:
            pass

    # Prefill z faktury Fakturowni
    inv_id = request.args.get('inv')
    prefill = {}
    prefill_invoice = None
    if inv_id:
        try:
            import json as _json
            from models.invoice import get_invoice_by_id
            inv = get_invoice_by_id(int(inv_id))
            if inv:
                raw = _json.loads(inv['raw_json']) if inv.get('raw_json') else {}
                # ksef_number może być pustym stringiem w kolumnie — szukamy też w raw_json
                ksef = (inv.get('ksef_number') or '').strip() \
                    or (raw.get('ksef_number') or '').strip() \
                    or (raw.get('ksef_id') or '').strip() \
                    or (raw.get('gov_id') or '').strip()
                vendor = _fix_vendor_from_raw(raw) or inv.get('vendor_name', '')
                vendor_nip = (raw.get('buyer_tax_no') or inv.get('vendor_nip') or '').strip()
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
                    'contractor_name':  vendor,
                    'contractor_nip':   vendor_nip,
                    'invoice_number':   inv.get('invoice_number', ''),
                    'description':      '',
                    'invoice_status':   'ksef' if ksef else 'none',
                    'invoice_ref':      ksef,
                    'fakturownia_id':   inv['fakturownia_id'],
                }
                prefill_invoice = {
                    'source':          'fakturownia',
                    'id':              inv['id'],
                    'invoice_number':  inv.get('invoice_number') or '',
                    'vendor_name':     vendor,
                    'issue_date':      str(inv.get('issue_date') or '')[:10],
                    'amount_gross':    float(inv.get('amount_gross') or 0) or None,
                }
        except Exception:
            pass

    return render_template('expenses/form.html',
        expense=prefill, users=users, categories=categories,
        action=url_for('expenses.new_expense'),
        title='Nowy wydatek', today=today,
        prefill_invoice=prefill_invoice)


@bp.route('/<int:expense_id>/edit', methods=['GET', 'POST'])
def edit_expense(expense_id):
    expense = get_expense_by_id(expense_id)
    if not expense:
        flash('Wydatek nie istnieje.', 'error')
        return redirect(url_for('expenses.list_expenses'))

    users = get_active_users()
    categories = get_categories()
    today = date.today().isoformat()

    if request.method == 'POST':
        data = _parse_form(request.form)
        errors = _validate(data)
        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('expenses/form.html',
                expense=request.form, users=users, categories=categories,
                action=url_for('expenses.edit_expense', expense_id=expense_id),
                title='Edytuj wydatek', today=today)

        update_expense(expense_id, data)
        flash('Wydatek został zaktualizowany.', 'success')
        return redirect(url_for('expenses.list_expenses'))

    return render_template('expenses/form.html',
        expense=expense, users=users, categories=categories,
        action=url_for('expenses.edit_expense', expense_id=expense_id),
        title='Edytuj wydatek', today=today,
        expense_id=expense_id)


@bp.route('/<int:expense_id>/delete', methods=['POST'])
def delete_expense_view(expense_id):
    delete_expense(expense_id)
    flash('Wydatek został usunięty.', 'success')
    return redirect(url_for('expenses.list_expenses'))


@bp.route('/import-csv', methods=['POST'])
def import_csv():
    flash('Import CSV zostanie wkrótce dostępny.', 'info')
    return redirect(url_for('expenses.list_expenses'))
