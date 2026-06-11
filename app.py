from flask import Flask, jsonify, request
from config import Config
import database

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY
database.init_app(app)

MONTHS_PL = {
    1: 'styczeń', 2: 'luty', 3: 'marzec', 4: 'kwiecień',
    5: 'maj', 6: 'czerwiec', 7: 'lipiec', 8: 'sierpień',
    9: 'wrzesień', 10: 'październik', 11: 'listopad', 12: 'grudzień',
}


@app.template_filter('pln')
def pln_format(value):
    try:
        v = float(value or 0)
        formatted = f"{v:,.2f}".replace(',', ' ').replace('.', ',')
        return f"{formatted} zł"
    except (TypeError, ValueError):
        return "0,00 zł"


@app.template_filter('ddmmyyyy')
def ddmmyyyy(value):
    if value is None:
        return ''
    if hasattr(value, 'strftime'):
        return value.strftime('%d.%m.%Y')
    try:
        from datetime import date
        y, m, d = str(value)[:10].split('-')
        return f"{d}.{m}.{y}"
    except Exception:
        return str(value)


@app.template_filter('date_iso')
def date_iso(value):
    if value is None:
        return ''
    if hasattr(value, 'strftime'):
        return value.strftime('%Y-%m-%d')
    return str(value)[:10]


@app.template_filter('vat_label')
def vat_label(value):
    try:
        v = float(value)
        if v < 0:
            return 'zw.'
        return f"{int(v)}%"
    except (TypeError, ValueError):
        return str(value)


@app.template_filter('month_pl')
def month_pl(value):
    """'2025-06' → 'czerwiec 2025'"""
    try:
        y, m = str(value).split('-')
        return f"{MONTHS_PL[int(m)]} {y}"
    except Exception:
        return str(value)


@app.context_processor
def inject_globals():
    try:
        from models.invoice import get_pending_count
        cnt = get_pending_count()
    except Exception:
        cnt = 0
    try:
        from models.bank_transaction import get_pending_bank_count
        bank_cnt = get_pending_bank_count()
    except Exception:
        bank_cnt = 0
    return {
        'pending_count':      cnt,
        'bank_pending_count': bank_cnt,
        'app_name':           Config.APP_NAME,
    }


@app.route('/api/fakturownia/invoices/<int:inv_id>/details')
def api_invoice_details(inv_id):
    import json as _json
    from models.invoice import get_invoice_by_id
    inv = get_invoice_by_id(inv_id)
    if not inv:
        return jsonify({'error': 'Nie znaleziono faktury'}), 404
    try:
        raw = _json.loads(inv['raw_json']) if inv.get('raw_json') else {}
    except Exception:
        raw = {}
    # Przeparsuj product_cache jeśli to string JSON
    pc = raw.get('product_cache')
    if isinstance(pc, str) and pc.strip().startswith('['):
        try:
            raw['product_cache'] = _json.loads(pc)
        except Exception:
            raw['product_cache'] = []
    return jsonify(raw)


@app.route('/api/expenses/pending-count')
def api_expenses_pending_count():
    from models.invoice import get_pending_count
    return jsonify({'count': get_pending_count()})


@app.route('/api/expenses/<int:expense_id>/transactions', methods=['GET'])
def api_expense_transactions_get(expense_id):
    from models.expense import get_expense_transactions
    rows = get_expense_transactions(expense_id)
    result = []
    for r in rows:
        row = dict(r)
        for k in ('date', 'created_at'):
            if row.get(k):
                row[k] = str(row[k])
        result.append(row)
    return jsonify(result)


@app.route('/api/expenses/<int:expense_id>/transactions', methods=['POST'])
def api_expense_transactions_post(expense_id):
    from models.expense import link_transaction
    data = request.get_json() or {}
    bank_txn_id = data.get('bank_txn_id')
    if not bank_txn_id:
        return jsonify({'error': 'bank_txn_id wymagany'}), 400
    result = link_transaction(expense_id, int(bank_txn_id))
    return jsonify(result)


@app.route('/api/expenses/<int:expense_id>/transactions/<int:bank_txn_id>', methods=['DELETE'])
def api_expense_transactions_delete(expense_id, bank_txn_id):
    from models.expense import unlink_transaction
    result = unlink_transaction(expense_id, bank_txn_id)
    return jsonify(result)


@app.route('/api/bank/search')
def api_bank_search():
    from models.bank_transaction import search_bank_transactions
    q = request.args.get('q', '').strip() or None
    bank = request.args.get('bank', '').strip() or None
    min_amount = request.args.get('min_amount', type=float)
    max_amount = request.args.get('max_amount', type=float)
    entity_type = request.args.get('entity_type', 'expense')
    entity_id = request.args.get('entity_id', type=int)
    rows = search_bank_transactions(
        q=q, bank=bank, min_amount=min_amount, max_amount=max_amount,
        for_expense_id=entity_id if entity_type == 'expense' else None,
        for_income_id=entity_id if entity_type == 'income' else None,
    )

    # Smart scoring: dopasowanie po kwocie i numerze faktury
    entity_gross = None
    entity_invoice = None
    if entity_id:
        try:
            if entity_type == 'expense':
                from models.expense import get_expense_by_id
                ent = get_expense_by_id(entity_id)
            else:
                from models.income import get_income_by_id
                ent = get_income_by_id(entity_id)
            if ent:
                entity_gross = float(ent.get('amount_gross') or 0)
                entity_invoice = (ent.get('invoice_number') or '').strip()
        except Exception:
            pass
    else:
        # tryb nowy — kwota i numer faktury przekazane bezpośrednio z formularza
        _a = request.args.get('amount', type=float)
        if _a:
            entity_gross = _a
        _inv = request.args.get('invoice_number', '').strip()
        if _inv:
            entity_invoice = _inv

    result = []
    for r in rows:
        row = dict(r)
        for k in ('date', 'created_at'):
            if row.get(k):
                row[k] = str(row[k])
        score = 0
        if entity_gross and entity_gross > 0:
            txn_abs = abs(float(row.get('amount') or 0))
            if abs(txn_abs - entity_gross) < 0.02:
                score += 2
        if entity_invoice:
            desc = (row.get('description') or '') + ' ' + (row.get('counterparty') or '')
            if entity_invoice.lower() in desc.lower():
                score += 1
        row['score'] = score
        result.append(row)

    def _sort_key(x):
        date_int = int((x.get('date') or '0000-00-00').replace('-', '')) if x.get('date') else 0
        return (-x['score'], -date_int)
    result.sort(key=_sort_key)
    return jsonify(result)


@app.route('/api/incomes/<int:income_id>/transactions', methods=['GET'])
def api_income_transactions_get(income_id):
    from models.income import get_income_transactions
    rows = get_income_transactions(income_id)
    result = []
    for r in rows:
        row = dict(r)
        for k in ('date', 'created_at'):
            if row.get(k):
                row[k] = str(row[k])
        result.append(row)
    return jsonify(result)


@app.route('/api/incomes/<int:income_id>/transactions', methods=['POST'])
def api_income_transactions_post(income_id):
    from models.income import link_income_transaction
    data = request.get_json() or {}
    bank_txn_id = data.get('bank_txn_id')
    if not bank_txn_id:
        return jsonify({'error': 'bank_txn_id wymagany'}), 400
    result = link_income_transaction(income_id, int(bank_txn_id))
    return jsonify(result)


@app.route('/api/incomes/<int:income_id>/transactions/<int:bank_txn_id>', methods=['DELETE'])
def api_income_transactions_delete(income_id, bank_txn_id):
    from models.income import unlink_income_transaction
    result = unlink_income_transaction(income_id, bank_txn_id)
    return jsonify(result)


@app.route('/api/ksef-preview/<entity_type>/<int:entity_id>')
def api_ksef_preview(entity_type, entity_id):
    import json as _json
    from database import get_db

    if entity_type == 'expense':
        from models.expense import get_expense_by_id
        entity = get_expense_by_id(entity_id)
        if not entity:
            return jsonify({'error': 'Nie znaleziono'}), 404
        ksef_number = entity.get('invoice_ref') or ''
        db = get_db()
        with db.cursor() as cur:
            cur.execute(
                "SELECT raw_json, invoice_type FROM fakturownia_invoices "
                "WHERE assigned_expense_id = %s LIMIT 1",
                (entity_id,)
            )
            fi = cur.fetchone()
    elif entity_type == 'income':
        from models.income import get_income_by_id
        entity = get_income_by_id(entity_id)
        if not entity:
            return jsonify({'error': 'Nie znaleziono'}), 404
        ksef_number = entity.get('invoice_ref') or ''
        fakturownia_id = entity.get('fakturownia_id') or ''
        db = get_db()
        fi = None
        if fakturownia_id:
            with db.cursor() as cur:
                cur.execute(
                    "SELECT raw_json, invoice_type FROM fakturownia_invoices "
                    "WHERE fakturownia_id = %s LIMIT 1",
                    (fakturownia_id,)
                )
                fi = cur.fetchone()
        if not fi:
            with db.cursor() as cur:
                cur.execute(
                    "SELECT raw_json, invoice_type FROM fakturownia_invoices "
                    "WHERE assigned_expense_id = %s LIMIT 1",
                    (entity_id,)
                )
                fi = cur.fetchone()
    else:
        return jsonify({'error': 'Nieznany typ'}), 400

    if fi and fi.get('raw_json'):
        try:
            raw = _json.loads(fi['raw_json'])
        except Exception:
            raw = {}
        pc = raw.get('product_cache')
        if isinstance(pc, str) and pc.strip().startswith('['):
            try:
                raw['product_cache'] = _json.loads(pc)
            except Exception:
                raw['product_cache'] = []
        return jsonify({
            'has_fakturownia_data': True,
            'invoice_type': fi.get('invoice_type') or entity_type,
            'data': raw,
        })

    return jsonify({
        'has_fakturownia_data': False,
        'ksef_number': ksef_number,
    })


@app.route('/api/fakturownia/test')
def api_fakturownia_test():
    from models.settings import get_setting
    subdomain = get_setting('fakturownia_subdomain', '')
    api_key = get_setting('fakturownia_api_key', '')
    if not subdomain or not api_key:
        return jsonify({'ok': False, 'message': 'Brak konfiguracji (subdomena lub klucz API).'})
    try:
        from services.fakturownia import FakturowniaClient
        result = FakturowniaClient(subdomain, api_key).test_connection()
        return jsonify(result)
    except Exception as e:
        return jsonify({'ok': False, 'message': str(e)})


@app.route('/api/fakturownia/sync', methods=['POST'])
def api_fakturownia_sync():
    from models.settings import get_setting, set_setting
    from models.invoice import add_sync_log
    subdomain = get_setting('fakturownia_subdomain', '')
    api_key = get_setting('fakturownia_api_key', '')
    if not subdomain or not api_key:
        return jsonify({'status': 'error', 'message': 'Brak konfiguracji.'})
    try:
        from services.fakturownia import FakturowniaClient
        from database import get_db
        from datetime import datetime
        filter_cat = get_setting('fakturownia_filter_category', 'expense')
        result = FakturowniaClient(subdomain, api_key).sync_to_db(get_db(), filter_category=filter_cat)
        set_setting('fakturownia_last_sync', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        return jsonify(result)
    except Exception as e:
        from models.invoice import add_sync_log
        add_sync_log(0, 0, 0, 'error', str(e))
        return jsonify({'status': 'error', 'message': str(e)})


@app.route('/api/bank/bulk-reject', methods=['POST'])
def api_bank_bulk_reject():
    from models.bank_transaction import bulk_reject_bank
    data = request.get_json(silent=True) or {}
    ids = [int(i) for i in data.get('ids', []) if str(i).isdigit()]
    if not ids:
        return jsonify({'status': 'error', 'message': 'Brak ID.'})
    affected = bulk_reject_bank(ids)
    return jsonify({'status': 'ok', 'affected': affected})


@app.route('/api/fakturownia/bulk-reject', methods=['POST'])
def api_bulk_reject():
    from models.invoice import bulk_reject
    data = request.get_json(silent=True) or {}
    ids = [int(i) for i in data.get('ids', []) if str(i).isdigit()]
    if not ids:
        return jsonify({'status': 'error', 'message': 'Brak ID.'})
    affected = bulk_reject(ids)
    return jsonify({'status': 'ok', 'affected': affected})


@app.route('/api/fakturownia/bulk-accept', methods=['POST'])
def api_bulk_accept():
    """Automatycznie tworzy wydatki/przychody z zaznaczonych faktur."""
    import json as _json
    from datetime import datetime as _dt
    from models.invoice import get_invoices_by_ids
    from models.expense import create_expense
    from models.income import create_income
    from database import get_db

    data = request.get_json(silent=True) or {}
    ids = [int(i) for i in data.get('ids', []) if str(i).isdigit()]
    if not ids:
        return jsonify({'status': 'error', 'message': 'Brak ID.'})

    invoices = get_invoices_by_ids(ids)
    created_expenses = 0
    created_incomes = 0
    errors = []

    for inv in invoices:
        if inv['status'] != 'pending':
            continue
        try:
            raw = _json.loads(inv['raw_json']) if inv.get('raw_json') else {}
            issue_date = str(inv.get('issue_date') or '')[:10] or _dt.today().strftime('%Y-%m-%d')
            gross = float(inv.get('amount_gross') or 0)
            net   = float(inv.get('amount_net') or gross)
            vat_a = float(inv.get('vat_amount') or 0)
            vat_rate = round((gross - net) / net * 100, 0) if net > 0 else 23.0

            if inv.get('invoice_type') == 'income':
                record_id = create_income({
                    'date':           issue_date,
                    'client_name':    inv.get('vendor_name') or '',
                    'client_nip':     inv.get('vendor_nip') or '',
                    'description':    f"Faktura {inv['invoice_number']}",
                    'invoice_number': inv.get('invoice_number') or '',
                    'amount_gross':   gross,
                    'vat_rate':       vat_rate,
                    'amount_net':     net,
                    'invoice_status': 'ksef' if inv.get('ksef_number') else 'none',
                    'invoice_ref':    inv.get('ksef_number') or None,
                    'payment_status': 'paid' if raw.get('payment_status') == 'paid' else 'unpaid',
                    'fakturownia_id': inv['fakturownia_id'],
                })
                created_incomes += 1
            else:
                record_id = create_expense({
                    'date':               issue_date,
                    'responsible_person': 'Auto-import',
                    'description':        f"Faktura {inv['invoice_number']}"
                                          + (f" – {inv['vendor_name']}" if inv.get('vendor_name') else ''),
                    'amount_gross':       gross,
                    'vat_rate':           vat_rate,
                    'amount_net':         net,
                    'payment_percent':    0,
                    'invoice_status':     'ksef' if inv.get('ksef_number') else 'none',
                    'invoice_ref':        inv.get('ksef_number') or None,
                })
                created_expenses += 1

            db = get_db()
            with db.cursor() as cur:
                cur.execute(
                    "UPDATE fakturownia_invoices SET status='assigned', assigned_expense_id=%s "
                    "WHERE id=%s",
                    (record_id, inv['id'])
                )
            db.commit()
        except Exception as exc:
            errors.append(f"ID {inv['id']}: {exc}")

    return jsonify({
        'status':           'ok' if not errors else 'partial',
        'created_expenses': created_expenses,
        'created_incomes':  created_incomes,
        'errors':           errors,
    })


from routes.dashboard import bp as dashboard_bp
from routes.expenses import bp as expenses_bp
from routes.income import bp as income_bp
from routes.settings import bp as settings_bp
from routes.users import bp as users_bp

app.register_blueprint(dashboard_bp)
app.register_blueprint(expenses_bp)
app.register_blueprint(income_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(users_bp)

if __name__ == '__main__':
    app.run(debug=Config.DEBUG, host='0.0.0.0', port=5001)
