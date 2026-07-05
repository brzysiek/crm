from flask import Flask, Response, jsonify, redirect, request, session, url_for
from werkzeug.exceptions import HTTPException
from config import Config
import database
import traceback as _tb
import logging
import os
import re
from logging.handlers import RotatingFileHandler
from datetime import datetime as _dt

_BUILD_ID = _dt.now().strftime('%Y%m%d.%H%M')

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY
database.init_app(app)

# Logowanie do pliku
_log_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(_log_dir, exist_ok=True)
_file_handler = RotatingFileHandler(
    os.path.join(_log_dir, 'app.log'),
    maxBytes=5 * 1024 * 1024,  # 5 MB
    backupCount=3,
    encoding='utf-8',
)
_file_handler.setFormatter(logging.Formatter(
    '[%(asctime)s] %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
))
_file_handler.setLevel(logging.INFO)
app.logger.addHandler(_file_handler)
app.logger.setLevel(logging.INFO)

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
    """'2025-06' (lub date '2025-06-01') → 'czerwiec 2025'"""
    try:
        parts = str(value).split('-')
        y, m = parts[0], parts[1]
        return f"{MONTHS_PL[int(m)]} {y}"
    except Exception:
        return str(value)


@app.errorhandler(Exception)
def handle_exception(e):
    """Dla /api/* zawsze zwraca JSON zamiast HTML strony błędu."""
    if isinstance(e, HTTPException):
        if request.path.startswith('/api/'):
            return jsonify({'ok': False, 'message': e.description}), e.code
        return e
    app.logger.error(_tb.format_exc())
    if request.path.startswith('/api/'):
        return jsonify({'ok': False, 'message': f'Błąd serwera: {str(e)}'}), 500
    return '<h1>Błąd serwera (500)</h1><pre>' + _tb.format_exc() + '</pre>', 500


@app.before_request
def require_login():
    open_endpoints = {'auth.login', 'auth.logout', 'static'}
    ep = request.endpoint or ''
    if ep in open_endpoints or ep.startswith('static'):
        return
    if not session.get('user_id'):
        app.logger.warning('Nieautoryzowany dostęp: %s %s', request.method, request.path)
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Unauthorized'}), 401
        return redirect(url_for('auth.login'))


@app.context_processor
def inject_globals():
    try:
        from models.invoice import get_pending_count
        cnt = get_pending_count()
    except Exception as _e:
        app.logger.error('inject_globals: get_pending_count failed: %s', _e)
        cnt = 0
    try:
        from models.bank_transaction import get_pending_bank_count
        bank_cnt = get_pending_bank_count()
    except Exception as _e:
        app.logger.error('inject_globals: get_pending_bank_count failed: %s', _e)
        bank_cnt = 0
    try:
        from models.gdrive_invoice import get_gdrive_pending_count
        gdrive_cnt = get_gdrive_pending_count()
    except Exception as _e:
        app.logger.error('inject_globals: get_gdrive_pending_count failed: %s', _e)
        gdrive_cnt = 0
    try:
        from models.dictionary import get_vat_rates, get_payment_methods
        vat_rates       = get_vat_rates()
        payment_methods = get_payment_methods()
    except Exception:
        vat_rates       = [
            {'value': '23', 'label': '23%'}, {'value': '8', 'label': '8%'},
            {'value': '5',  'label': '5%'},  {'value': '0', 'label': '0%'},
            {'value': '-1', 'label': 'zw.'},
        ]
        payment_methods = [
            {'value': 'transfer', 'label': 'Przelew / karta'},
            {'value': 'cash',     'label': 'Gotówka'},
        ]
    return {
        'pending_count':        cnt,
        'bank_pending_count':   bank_cnt,
        'gdrive_pending_count': gdrive_cnt,
        'app_name':             Config.APP_NAME,
        'vat_rates':            vat_rates,
        'payment_methods':      payment_methods,
        'build_id':             _BUILD_ID,
        'current_user': {
            'id':        session.get('user_id'),
            'username':  session.get('username', ''),
            'full_name': session.get('full_name', ''),
        },
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


@app.route('/api/expenses/bulk-category', methods=['POST'])
def api_expenses_bulk_category():
    from models.expense import bulk_set_category
    data = request.get_json(silent=True) or {}
    ids = [int(i) for i in data.get('ids', []) if str(i).isdigit()]
    if not ids:
        return jsonify({'status': 'error', 'message': 'Brak ID.'})
    category = (data.get('category') or '').strip() or None
    affected = bulk_set_category(ids, category)
    return jsonify({'status': 'ok', 'affected': affected})


@app.route('/api/expenses/bulk-person', methods=['POST'])
def api_expenses_bulk_person():
    from models.expense import bulk_set_responsible_person
    data = request.get_json(silent=True) or {}
    ids = [int(i) for i in data.get('ids', []) if str(i).isdigit()]
    if not ids:
        return jsonify({'status': 'error', 'message': 'Brak ID.'})
    person = (data.get('person') or '').strip() or None
    affected = bulk_set_responsible_person(ids, person)
    return jsonify({'status': 'ok', 'affected': affected})


@app.route('/api/bank/suggest-for-invoice')
def api_bank_suggest_for_invoice():
    """Zwraca najlepiej pasującą transakcję bankową dla faktury (bez encji)."""
    from models.bank_transaction import search_bank_transactions
    amount         = request.args.get('amount', type=float)
    invoice_number = request.args.get('invoice_number', '').strip()
    rows = search_bank_transactions()
    best, best_score = _score_best(rows, amount, invoice_number)
    if best_score > 0 and best:
        result = _txn_to_json(best)
        result['score'] = best_score
        return jsonify(result)
    return jsonify(None)


@app.route('/api/bank/suggest-for-invoices', methods=['POST'])
def api_bank_suggest_for_invoices():
    """Batch: przyjmuje listę faktur, zwraca mapę inv_id → najlepsza transakcja.

    Body: {"invoices": [{"id": 1, "amount": 123.45, "invoice_number": "FS/1/2026"}, ...]}
    Odpowiedź: {"1": {...txn...}, "2": null, ...}
    """
    from models.bank_transaction import search_bank_transactions
    data = request.get_json(silent=True) or {}
    invoices = data.get('invoices') or []
    if not invoices:
        return jsonify({})

    rows = list(search_bank_transactions())   # 1 zapytanie do DB dla wszystkich

    result = {}
    available = rows          # będziemy filtrować użyte transakcje
    for inv in invoices:
        inv_id  = str(inv.get('id', ''))
        amount  = float(inv.get('amount') or 0)
        inv_num = str(inv.get('invoice_number') or '').strip()
        best, best_score = _score_best(available, amount, inv_num)
        if best_score > 0 and best:
            txn = _txn_to_json(best)
            txn['score'] = best_score
            result[inv_id] = txn
            # Usuń z puli — ta transakcja jest już "zarezerwowana" dla tej faktury
            available = [r for r in available if r['id'] != best['id']]
        else:
            result[inv_id] = None
    return jsonify(result)


def _score_best(rows: list, amount: float, invoice_number: str):
    """Pomocnicza: wybiera najlepiej pasującą transakcję ze zbioru wierszy."""
    best = None
    best_score = 0
    inv_lower = (invoice_number or '').lower()
    for row in rows:
        score = 0
        txn_abs = abs(float(row.get('amount') or 0))
        if amount and amount > 0 and abs(txn_abs - amount) < 0.02:
            score += 2
        if inv_lower:
            desc = ((row.get('description') or '') + ' ' +
                    (row.get('counterparty') or '')).lower()
            if inv_lower in desc:
                score += 1
        if score > best_score:
            best_score = score
            best = row
    return best, best_score


def _txn_to_json(row: dict) -> dict:
    """Konwertuje wiersz transakcji do JSON-serializowalnego słownika."""
    result = dict(row)
    for k in ('date', 'created_at'):
        if result.get(k):
            result[k] = str(result[k])
    return result


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


@app.route('/api/incomes/bulk-category', methods=['POST'])
def api_incomes_bulk_category():
    from models.income import bulk_set_category
    data = request.get_json(silent=True) or {}
    ids = [int(i) for i in data.get('ids', []) if str(i).isdigit()]
    if not ids:
        return jsonify({'status': 'error', 'message': 'Brak ID.'})
    category = (data.get('category') or '').strip() or None
    affected = bulk_set_category(ids, category)
    return jsonify({'status': 'ok', 'affected': affected})


@app.route('/api/incomes/bulk-person', methods=['POST'])
def api_incomes_bulk_person():
    from models.income import bulk_set_paid_by
    data = request.get_json(silent=True) or {}
    ids = [int(i) for i in data.get('ids', []) if str(i).isdigit()]
    if not ids:
        return jsonify({'status': 'error', 'message': 'Brak ID.'})
    person = (data.get('person') or '').strip() or None
    affected = bulk_set_paid_by(ids, person)
    return jsonify({'status': 'ok', 'affected': affected})


@app.route('/api/expenses/bulk-revert', methods=['POST'])
def api_expenses_bulk_revert():
    """Cofnij akceptację: usuwa wydatki i przywraca powiązane transakcje/faktury do pending."""
    from models.expense import bulk_delete_expenses
    data = request.get_json(silent=True) or {}
    ids = [int(i) for i in data.get('ids', []) if str(i).isdigit()]
    if not ids:
        return jsonify({'status': 'error', 'message': 'Brak ID.'})
    affected = bulk_delete_expenses(ids)
    return jsonify({'status': 'ok', 'affected': affected})


@app.route('/api/incomes/bulk-revert', methods=['POST'])
def api_incomes_bulk_revert():
    """Cofnij akceptację: usuwa przychody i przywraca powiązane transakcje/faktury do pending."""
    from models.income import bulk_delete_incomes
    data = request.get_json(silent=True) or {}
    ids = [int(i) for i in data.get('ids', []) if str(i).isdigit()]
    if not ids:
        return jsonify({'status': 'error', 'message': 'Brak ID.'})
    affected = bulk_delete_incomes(ids)
    return jsonify({'status': 'ok', 'affected': affected})


@app.route('/api/invoices/linked/<entity_type>/<int:entity_id>')
def api_invoices_linked(entity_type, entity_id):
    """All invoices (fakturownia + gdrive) linked to an expense or income record."""
    from database import get_db as _get_db
    db = _get_db()
    result = []
    with db.cursor() as cur:
        cur.execute(
            "SELECT id, invoice_number, vendor_name, issue_date, amount_gross "
            "FROM fakturownia_invoices WHERE assigned_expense_id=%s AND status='assigned' "
            "AND invoice_type=%s",
            (entity_id, entity_type)
        )
        for row in cur.fetchall():
            result.append({
                'source': 'fakturownia',
                'id': row['id'],
                'invoice_number': row.get('invoice_number') or '',
                'vendor_name': row.get('vendor_name') or '',
                'issue_date': str(row['issue_date'])[:10] if row.get('issue_date') else '',
                'amount_gross': float(row['amount_gross']) if row.get('amount_gross') is not None else None,
            })
    with db.cursor() as cur:
        cur.execute(
            "SELECT id, file_name, invoice_number, vendor_name, issue_date, amount_gross "
            "FROM gdrive_invoices WHERE assigned_record_id=%s AND status='assigned' "
            "AND invoice_type=%s",
            (entity_id, entity_type)
        )
        for row in cur.fetchall():
            result.append({
                'source': 'gdrive',
                'id': row['id'],
                'invoice_number': row.get('invoice_number') or row.get('file_name') or '',
                'vendor_name': row.get('vendor_name') or '',
                'issue_date': str(row['issue_date'])[:10] if row.get('issue_date') else '',
                'amount_gross': float(row['amount_gross']) if row.get('amount_gross') is not None else None,
                'file_name': row.get('file_name') or '',
            })
    return jsonify(result)


@app.route('/api/invoices/search')
def api_invoices_search():
    """Search pending invoices from both sources for linking."""
    from database import get_db as _get_db
    q = request.args.get('q', '').strip()
    entity_type = request.args.get('entity_type', '')
    db = _get_db()
    result = []

    sql = ("SELECT id, invoice_number, vendor_name, issue_date, amount_gross "
           "FROM fakturownia_invoices WHERE status='pending'")
    params = []
    if entity_type in ('expense', 'income'):
        sql += " AND invoice_type=%s"
        params.append(entity_type)
    if q:
        sql += " AND (invoice_number LIKE %s OR vendor_name LIKE %s)"
        like = f"%{q}%"
        params.extend([like, like])
    sql += " ORDER BY issue_date DESC LIMIT 50"
    with db.cursor() as cur:
        cur.execute(sql, params)
        for row in cur.fetchall():
            result.append({
                'source': 'fakturownia',
                'id': row['id'],
                'invoice_number': row.get('invoice_number') or '',
                'vendor_name': row.get('vendor_name') or '',
                'issue_date': str(row['issue_date'])[:10] if row.get('issue_date') else '',
                'amount_gross': float(row['amount_gross']) if row.get('amount_gross') is not None else None,
            })

    sql = ("SELECT id, file_name, invoice_number, vendor_name, issue_date, amount_gross "
           "FROM gdrive_invoices WHERE status='pending'")
    params = []
    if entity_type in ('expense', 'income'):
        sql += " AND invoice_type=%s"
        params.append(entity_type)
    if q:
        sql += " AND (invoice_number LIKE %s OR vendor_name LIKE %s OR file_name LIKE %s)"
        like = f"%{q}%"
        params.extend([like, like, like])
    sql += " ORDER BY issue_date DESC LIMIT 50"
    with db.cursor() as cur:
        cur.execute(sql, params)
        for row in cur.fetchall():
            result.append({
                'source': 'gdrive',
                'id': row['id'],
                'invoice_number': row.get('invoice_number') or row.get('file_name') or '',
                'vendor_name': row.get('vendor_name') or '',
                'issue_date': str(row['issue_date'])[:10] if row.get('issue_date') else '',
                'amount_gross': float(row['amount_gross']) if row.get('amount_gross') is not None else None,
                'file_name': row.get('file_name') or '',
            })

    return jsonify(result)


@app.route('/api/invoices/link', methods=['POST'])
def api_invoice_link():
    """Link a pending invoice to an expense or income (AJAX, edit mode)."""
    data = request.get_json(silent=True) or {}
    source = data.get('source')
    invoice_id = data.get('invoice_id')
    entity_id = data.get('entity_id')
    if not source or not invoice_id or not entity_id:
        return jsonify({'ok': False, 'error': 'Brak danych'}), 400
    try:
        if source == 'fakturownia':
            from models.invoice import assign_invoice
            assign_invoice(int(invoice_id), int(entity_id))
        elif source == 'gdrive':
            from models.gdrive_invoice import assign_gdrive_invoice
            assign_gdrive_invoice(int(invoice_id), int(entity_id))
        else:
            return jsonify({'ok': False, 'error': 'Nieznane źródło'}), 400
        return jsonify({'ok': True})
    except Exception as e:
        app.logger.error('invoice link error: %s', e)
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/invoices/unlink/<source>/<int:invoice_id>', methods=['DELETE'])
def api_invoice_unlink(source, invoice_id):
    """Unlink (return to pending) a previously assigned invoice."""
    from database import get_db as _get_db
    db = _get_db()
    try:
        if source == 'fakturownia':
            with db.cursor() as cur:
                cur.execute(
                    "UPDATE fakturownia_invoices SET status='pending', assigned_expense_id=NULL "
                    "WHERE id=%s AND status='assigned'",
                    (invoice_id,)
                )
            db.commit()
        elif source == 'gdrive':
            with db.cursor() as cur:
                cur.execute(
                    "UPDATE gdrive_invoices SET status='pending', assigned_record_id=NULL "
                    "WHERE id=%s AND status='assigned'",
                    (invoice_id,)
                )
            db.commit()
        else:
            return jsonify({'ok': False, 'error': 'Nieznane źródło'}), 400
        return jsonify({'ok': True})
    except Exception as e:
        app.logger.error('invoice unlink error: %s', e)
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/disk-preview/<entity_type>/<int:entity_id>')
def api_disk_preview(entity_type, entity_id):
    """Return OCR data for a GDrive invoice linked to an expense or income."""
    import json as _json
    from models.gdrive_invoice import get_gdrive_invoice_by_id
    from database import get_db

    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT * FROM gdrive_invoices WHERE assigned_record_id = %s AND status = 'assigned'",
            (entity_id,)
        )
        row = cur.fetchone()

    if not row:
        return jsonify({'error': 'Nie znaleziono powiązanej faktury z Dysku Google'}), 404

    try:
        ocr = _json.loads(row['ocr_raw']) if row.get('ocr_raw') else {}
    except Exception:
        ocr = {}

    return jsonify({
        'file_name':      row.get('file_name', ''),
        'gdrive_year':    row.get('gdrive_year'),
        'gdrive_month':   row.get('gdrive_month'),
        'invoice_number': row.get('invoice_number', ''),
        'vendor_name':    row.get('vendor_name', ''),
        'vendor_nip':     row.get('vendor_nip', ''),
        'issue_date':     str(row['issue_date']) if row.get('issue_date') else '',
        'amount_gross':   float(row['amount_gross']) if row.get('amount_gross') else None,
        'amount_net':     float(row['amount_net']) if row.get('amount_net') else None,
        'vat_amount':     float(row['vat_amount']) if row.get('vat_amount') else None,
        'invoice_type':   row.get('invoice_type', ''),
        'ocr':            ocr,
    })


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


@app.route('/api/gdrive/test')
def api_gdrive_test():
    from models.settings import get_setting
    api_token = get_setting('google_drive_api_token', '')
    folder_id = get_setting('google_drive_folder_id', '')
    if not api_token:
        return jsonify({'ok': False, 'message': 'Brak tokenu / klucza API Google Drive.'})
    if not folder_id:
        return jsonify({'ok': False, 'message': 'Brak ID folderu głównego Google Drive.'})
    try:
        from services.gdrive import GoogleDriveClient
        client = GoogleDriveClient(api_token, folder_id)
        folders = client.list_subfolders(folder_id)
        count = len(folders)
        names = ', '.join(f['name'] for f in folders[:5])
        suffix = '…' if count > 5 else ''
        return jsonify({
            'ok': True,
            'message': f'Połączenie działa. Znaleziono {count} podfolderów: {names}{suffix}',
        })
    except Exception as e:
        return jsonify({'ok': False, 'message': f'Błąd: {str(e)}'})


@app.route('/api/gemini/test')
def api_gemini_test():
    from models.settings import get_setting
    import requests as _req
    api_key = get_setting('gemini_api_key', '')
    model   = get_setting('gemini_model', 'gemini-2.5-flash')
    if not api_key:
        return jsonify({'ok': False, 'message': 'Brak klucza API Gemini.'})
    try:
        url = (
            'https://generativelanguage.googleapis.com/v1beta/'
            f'models/{model}:generateContent?key={api_key}'
        )
        payload = {
            'contents': [{'parts': [{'text': 'Reply with exactly: OK'}]}],
            'generationConfig': {'maxOutputTokens': 10, 'temperature': 0},
        }
        resp = _req.post(url, json=payload, timeout=15)
        if resp.status_code == 200:
            return jsonify({'ok': True, 'message': f'Połączenie z modelem {model} działa poprawnie.'})
        elif resp.status_code == 400:
            return jsonify({'ok': False, 'message': f'Błąd 400 — nieprawidłowe żądanie: {resp.text[:200]}'})
        elif resp.status_code == 403:
            return jsonify({'ok': False, 'message': 'Błąd 403 — nieprawidłowy klucz API lub brak uprawnień.'})
        else:
            return jsonify({'ok': False, 'message': f'Serwer zwrócił status: {resp.status_code}'})
    except Exception as e:
        return jsonify({'ok': False, 'message': f'Błąd połączenia: {str(e)[:150]}'})


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
        data = request.get_json(silent=True) or {}
        month = (data.get('month') or '').strip() or None
        filter_cat = get_setting('fakturownia_filter_category', 'all')
        result = FakturowniaClient(subdomain, api_key).sync_to_db(
            get_db(), filter_category=filter_cat, month=month)
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


@app.route('/api/bank/bulk-accept', methods=['POST'])
def api_bank_bulk_accept():
    """Automatycznie tworzy wydatki/przychody z zaznaczonych transakcji bankowych.

    Typ (wydatek/przychód) wynika ze znaku kwoty transakcji — tak samo jak
    przyciski 'Utwórz wydatek/przychód' na karcie pojedynczej transakcji.
    """
    from models.bank_transaction import get_bank_transactions_by_ids
    from models.expense import create_expense, link_transaction
    from models.income import create_income, link_income_transaction

    data = request.get_json(silent=True) or {}
    ids = [int(i) for i in data.get('ids', []) if str(i).isdigit()]
    if not ids:
        return jsonify({'status': 'error', 'message': 'Brak ID.'})

    txns = get_bank_transactions_by_ids(ids)
    created_expenses = 0
    created_incomes = 0
    errors = []

    for txn in txns:
        if txn['status'] != 'pending':
            continue
        try:
            amount = abs(float(txn['amount'] or 0))
            vat_rate = 23.0
            amount_net = round(amount / (1 + vat_rate / 100), 2)
            description = (txn.get('description') or txn.get('counterparty')
                           or 'Transakcja bankowa')
            orig_amount = float(txn['orig_amount']) if txn.get('orig_amount') else None
            orig_currency = txn.get('orig_currency') if orig_amount else None

            if float(txn['amount'] or 0) < 0:
                record_id = create_expense({
                    'date':               txn['date'],
                    'responsible_person': 'Auto-import',
                    'contractor_name':    txn.get('counterparty') or None,
                    'description':        description,
                    'amount_gross':       amount,
                    'vat_rate':           vat_rate,
                    'amount_net':         amount_net,
                    'orig_amount':        orig_amount,
                    'orig_currency':      orig_currency,
                    'invoice_status':     'none',
                    'paid_by':            'Auto-import',
                    'payment_method':     'transfer',
                    'source':             txn.get('bank'),
                })
                link_transaction(record_id, txn['id'])
                created_expenses += 1
            else:
                record_id = create_income({
                    'date':            txn['date'],
                    'client_name':     txn.get('counterparty') or None,
                    'description':     description,
                    'amount_gross':    amount,
                    'vat_rate':        vat_rate,
                    'amount_net':      amount_net,
                    'orig_amount':     orig_amount,
                    'orig_currency':   orig_currency,
                    'invoice_status':  'none',
                    'payment_method':  'transfer',
                    'payment_status':  'paid',
                    'source':          txn.get('bank'),
                })
                link_income_transaction(record_id, txn['id'])
                created_incomes += 1
        except Exception as exc:
            errors.append(f"ID {txn['id']}: {exc}")

    return jsonify({
        'status':           'ok' if not errors else 'partial',
        'created_expenses':  created_expenses,
        'created_incomes':   created_incomes,
        'errors':            errors,
    })


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
    from models.expense import create_expense, link_transaction
    from models.income import create_income, link_income_transaction
    from models.bank_transaction import search_bank_transactions
    from database import get_db

    data = request.get_json(silent=True) or {}
    ids = [int(i) for i in data.get('ids', []) if str(i).isdigit()]
    if not ids:
        return jsonify({'status': 'error', 'message': 'Brak ID.'})

    invoices = get_invoices_by_ids(ids)
    created_expenses = 0
    created_incomes = 0
    auto_linked = 0
    errors = []

    # Pobierz transakcje raz — nie N razy w pętli
    from models.bank_transaction import search_bank_transactions as _search_txns
    try:
        _all_txns = list(_search_txns())   # kopia — będziemy usuwać użyte
    except Exception:
        _all_txns = []

    for inv in invoices:
        if inv['status'] != 'pending':
            continue
        try:
            raw = _json.loads(inv['raw_json']) if inv.get('raw_json') else {}
            issue_date = str(inv.get('issue_date') or '')[:10] or _dt.today().strftime('%Y-%m-%d')
            gross    = float(inv.get('amount_gross') or 0)
            net      = float(inv.get('amount_net') or gross)
            vat_rate = round((gross - net) / net * 100, 0) if net > 0 else 23.0
            inv_number = (inv.get('invoice_number') or '').strip()

            # Szukaj dopasowania wśród JESZCZE NIEUŻYTYCH transakcji
            best, _ = _score_best(_all_txns, gross, inv_number)
            best_bank = best['bank'] if best else None

            # Fallback chain dla ksef_number (może być w raw_json)
            ksef = (inv.get('ksef_number') or '').strip() \
                or (raw.get('ksef_number') or '').strip() \
                or (raw.get('ksef_id') or '').strip() \
                or (raw.get('gov_id') or '').strip()

            inv_currency  = (inv.get('currency') or 'PLN').upper()
            inv_orig      = float(inv['orig_amount']) if inv.get('orig_amount') else None

            if inv.get('invoice_type') == 'income':
                client_name = (raw.get('buyer_name') or inv.get('vendor_name') or '').strip()
                client_nip  = (raw.get('buyer_tax_no') or inv.get('vendor_nip') or '').strip()
                record_id = create_income({
                    'date':           issue_date,
                    'client_name':    client_name,
                    'client_nip':     client_nip,
                    'description':    f"Faktura {inv_number}",
                    'invoice_number': inv_number,
                    'amount_gross':   gross,
                    'vat_rate':       vat_rate,
                    'amount_net':     net,
                    'invoice_status': 'ksef' if ksef else 'none',
                    'invoice_ref':    ksef or None,
                    'payment_status': 'paid' if raw.get('payment_status') == 'paid' else 'unpaid',
                    'fakturownia_id': inv['fakturownia_id'],
                    'source':         best_bank,
                    'payment_method': 'transfer' if best_bank else None,
                    'orig_amount':    inv_orig,
                    'orig_currency':  inv_currency if inv_orig else None,
                })
                created_incomes += 1
                if best:
                    try:
                        link_income_transaction(record_id, best['id'])
                        auto_linked += 1
                        # Usuń transakcję z puli żeby nie przypisać jej do kolejnej faktury
                        _all_txns = [t for t in _all_txns if t['id'] != best['id']]
                    except Exception:
                        pass
            else:
                vendor     = (raw.get('buyer_name') or inv.get('vendor_name') or '').strip()
                vendor_nip = (raw.get('buyer_tax_no') or inv.get('vendor_nip') or '').strip()
                record_id = create_expense({
                    'date':               issue_date,
                    'responsible_person': 'Auto-import',
                    'contractor_name':    vendor or None,
                    'contractor_nip':     vendor_nip or None,
                    'invoice_number':     inv_number or None,
                    'description':        f"Faktura {inv_number}"
                                          + (f" – {vendor}" if vendor else ''),
                    'amount_gross':       gross,
                    'vat_rate':           vat_rate,
                    'amount_net':         net,
                    'payment_percent':    0,
                    'invoice_status':     'ksef' if ksef else 'none',
                    'invoice_ref':        ksef or None,
                    'source':             best_bank,
                    'payment_method':     'transfer' if best_bank else None,
                    'orig_amount':        inv_orig,
                    'orig_currency':      inv_currency if inv_orig else None,
                })
                created_expenses += 1
                if best:
                    try:
                        link_transaction(record_id, best['id'])
                        auto_linked += 1
                        # Usuń transakcję z puli żeby nie przypisać jej do kolejnej faktury
                        _all_txns = [t for t in _all_txns if t['id'] != best['id']]
                    except Exception:
                        pass

            db = get_db()
            with db.cursor() as cur:
                cur.execute(
                    "UPDATE fakturownia_invoices SET status='assigned', assigned_expense_id=%s "
                    "WHERE id=%s",
                    (record_id, inv['id'])
                )
            db.commit()
        except Exception as exc:
            errors.append(f"ID {inv['id']}: {exc}\n{_tb.format_exc()}")

    total_created = created_expenses + created_incomes
    unlinked = total_created - auto_linked   # ile wydatków/przychodów bez transakcji
    return jsonify({
        'status':           'ok' if not errors else 'partial',
        'created_expenses': created_expenses,
        'created_incomes':  created_incomes,
        'auto_linked':      auto_linked,
        'unlinked':         unlinked,
        'errors':           errors,
    })


def _find_best_txn(gross: float, invoice_number: str,
                   for_expense_id: int = None,
                   for_income_id: int = None) -> dict | None:
    """Zwraca najlepiej pasującą transakcję bankową (score > 0) lub None."""
    from models.bank_transaction import search_bank_transactions
    rows = search_bank_transactions(
        for_expense_id=for_expense_id,
        for_income_id=for_income_id,
    )
    best = None
    best_score = 0
    inv_lower = (invoice_number or '').lower()
    for row in rows:
        score = 0
        txn_abs = abs(float(row.get('amount') or 0))
        if gross > 0 and abs(txn_abs - gross) < 0.02:
            score += 2
        if inv_lower:
            desc = ((row.get('description') or '') + ' ' +
                    (row.get('counterparty') or '')).lower()
            if inv_lower in desc:
                score += 1
        if score > best_score:
            best_score = score
            best = row
    return best if best_score > 0 else None


@app.route('/api/gdrive/folders')
def api_gdrive_folders():
    from models.settings import get_setting
    from services.gdrive import GoogleDriveClient
    api_token = get_setting('google_drive_api_token', '')
    root_folder_id = get_setting('google_drive_folder_id', '')
    if not api_token or not root_folder_id:
        return jsonify({'error': 'Brak konfiguracji Google Drive. Skonfiguruj w Ustawieniach ogólnych.'}), 400
    parent_id = request.args.get('parent_id', '').strip() or root_folder_id
    try:
        client = GoogleDriveClient(api_token, root_folder_id)
        folders = client.list_subfolders(parent_id)
        return jsonify(folders)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/gdrive/files')
def api_gdrive_files():
    from models.settings import get_setting
    from services.gdrive import GoogleDriveClient
    from models.gdrive_invoice import get_processed_file_ids
    api_token = get_setting('google_drive_api_token', '')
    root_folder_id = get_setting('google_drive_folder_id', '')
    if not api_token or not root_folder_id:
        return jsonify({'error': 'Brak konfiguracji Google Drive.'}), 400
    folder_id = request.args.get('folder_id', '').strip()
    if not folder_id:
        return jsonify({'error': 'Wymagany parametr folder_id.'}), 400
    try:
        client = GoogleDriveClient(api_token, root_folder_id)
        files = client.list_pdf_files(folder_id)
        processed = get_processed_file_ids()
        for f in files:
            f['already_processed'] = f['id'] in processed
        return jsonify(files)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/gdrive/ocr', methods=['POST'])
def api_gdrive_ocr():
    import json as _json
    from models.settings import get_setting
    from services.gdrive import GoogleDriveClient
    from services.gemini_ocr import ocr_invoice_pdf
    from models.gdrive_invoice import upsert_gdrive_invoice

    api_token = get_setting('google_drive_api_token', '')
    root_folder_id = get_setting('google_drive_folder_id', '')
    gemini_key = get_setting('gemini_api_key', '')
    gemini_model = get_setting('gemini_model', 'gemini-2.5-flash')
    if not api_token or not root_folder_id:
        return jsonify({'error': 'Brak konfiguracji Google Drive.'}), 400
    if not gemini_key:
        return jsonify({'error': 'Brak klucza API Gemini.'}), 400

    data = request.get_json(silent=True) or {}
    file_ids = data.get('file_ids', [])
    gdrive_year  = data.get('year')
    gdrive_month = data.get('month')

    if not file_ids:
        return jsonify({'error': 'Brak file_ids.'}), 400

    client = GoogleDriveClient(api_token, root_folder_id)
    results = []

    for file_entry in file_ids:
        # file_entry may be a dict {id, name, modifiedTime} or a plain string id
        if isinstance(file_entry, dict):
            fid  = file_entry.get('id', '')
            fname = file_entry.get('name', fid)
            fmod  = file_entry.get('modifiedTime')
        else:
            fid  = str(file_entry)
            fname = fid
            fmod  = None

        try:
            pdf_bytes = client.download_file(fid)
            ocr = ocr_invoice_pdf(pdf_bytes, gemini_key, model=gemini_model)

            if 'error' in ocr:
                results.append({'file_id': fid, 'file_name': fname, 'success': False,
                                 'error': ocr['error']})
                continue

            from services.nbp import convert_to_pln as _nbp
            currency    = (ocr.get('currency') or 'PLN').strip().upper()
            issue_date  = ocr.get('issue_date') or None
            raw_gross   = ocr.get('amount_gross')
            raw_net     = ocr.get('amount_net')
            raw_vat     = ocr.get('vat_amount')
            orig_amount   = None
            exchange_rate = None
            if currency != 'PLN' and raw_gross is not None:
                orig_amount = raw_gross
                pln_gross, exchange_rate = _nbp(raw_gross, currency, issue_date or '')
                if exchange_rate:
                    raw_net = round(raw_net * exchange_rate, 2) if raw_net else None
                    raw_vat = round(raw_vat * exchange_rate, 2) if raw_vat else None
                raw_gross = pln_gross

            record = {
                'gdrive_file_id':   fid,
                'file_name':        fname,
                'file_modified_at': fmod,
                'gdrive_year':      gdrive_year,
                'gdrive_month':     gdrive_month,
                'invoice_number':   ocr.get('invoice_number') or None,
                'vendor_name':      ocr.get('vendor_name') or None,
                'vendor_nip':       ocr.get('vendor_nip') or None,
                'issue_date':       issue_date,
                'amount_gross':     raw_gross,
                'amount_net':       raw_net,
                'vat_amount':       raw_vat,
                'invoice_type':     ocr.get('invoice_type', 'expense'),
                'currency':         currency,
                'orig_amount':      orig_amount,
                'exchange_rate':    exchange_rate,
                'ocr_raw':          _json.dumps(ocr, ensure_ascii=False),
            }
            is_new = upsert_gdrive_invoice(record)
            results.append({
                'file_id':        fid,
                'file_name':      fname,
                'success':        True,
                'is_new':         is_new,
                **{k: ocr.get(k) for k in (
                    'invoice_number', 'vendor_name', 'vendor_nip',
                    'issue_date', 'amount_gross', 'amount_net',
                    'vat_amount', 'invoice_type', 'confidence_note'
                )},
            })
        except Exception as exc:
            results.append({'file_id': fid, 'file_name': fname, 'success': False,
                             'error': str(exc)})

    return jsonify({'status': 'ok', 'results': results})


@app.route('/api/gdrive/invoices/<int:inv_id>/details')
def api_gdrive_invoice_details(inv_id):
    import json as _json
    from models.gdrive_invoice import get_gdrive_invoice_by_id
    inv = get_gdrive_invoice_by_id(inv_id)
    if not inv:
        return jsonify({'error': 'Nie znaleziono faktury'}), 404
    try:
        raw = _json.loads(inv['ocr_raw']) if inv.get('ocr_raw') else {}
    except Exception:
        raw = {}
    return jsonify(raw)


@app.route('/api/gdrive/invoices/<int:inv_id>/pdf')
def api_gdrive_invoice_pdf(inv_id):
    """Strumieniuje oryginalny plik PDF faktury z Google Drive (podgląd w popupie)."""
    import unicodedata
    from urllib.parse import quote
    from models.settings import get_setting
    from models.gdrive_invoice import get_gdrive_invoice_by_id
    from services.gdrive import GoogleDriveClient

    inv = get_gdrive_invoice_by_id(inv_id)
    if not inv:
        return jsonify({'error': 'Nie znaleziono faktury'}), 404

    api_token = get_setting('google_drive_api_token', '')
    root_folder_id = get_setting('google_drive_folder_id', '')
    if not api_token or not root_folder_id:
        return jsonify({'error': 'Brak konfiguracji Google Drive.'}), 400

    try:
        client = GoogleDriveClient(api_token, root_folder_id)
        pdf_bytes = client.download_file(inv['gdrive_file_id'])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    # Content-Disposition musi być latin-1-kodowalny — polskie znaki (ą, ć, ż…)
    # w nazwie pliku z Dysku Google wywalały cały response (pusty iframe w popupie).
    display_name = inv.get('file_name') or 'faktura.pdf'
    ascii_name = unicodedata.normalize('NFKD', display_name).encode('ascii', 'ignore').decode('ascii') or 'faktura.pdf'

    return Response(pdf_bytes, mimetype='application/pdf', headers={
        'Content-Disposition': (
            f'inline; filename="{ascii_name}"; '
            f"filename*=UTF-8''{quote(display_name)}"
        )
    })


@app.route('/api/gdrive/invoices/<int:inv_id>', methods=['GET'])
def api_gdrive_invoice_get(inv_id):
    """Zwraca edytowalne pola faktury (do formularza korekty w popupie)."""
    from models.gdrive_invoice import get_gdrive_invoice_by_id
    inv = get_gdrive_invoice_by_id(inv_id)
    if not inv:
        return jsonify({'error': 'Nie znaleziono faktury'}), 404
    return jsonify({
        'id': inv['id'],
        'status': inv['status'],
        'file_name': inv.get('file_name'),
        'invoice_number': inv.get('invoice_number'),
        'vendor_name': inv.get('vendor_name'),
        'vendor_nip': inv.get('vendor_nip'),
        'issue_date': inv['issue_date'].isoformat() if inv.get('issue_date') else None,
        'amount_gross': float(inv['amount_gross']) if inv.get('amount_gross') is not None else None,
        'amount_net': float(inv['amount_net']) if inv.get('amount_net') is not None else None,
        'vat_amount': float(inv['vat_amount']) if inv.get('vat_amount') is not None else None,
        'invoice_type': inv.get('invoice_type', 'expense'),
        'currency': inv.get('currency'),
    })


@app.route('/api/gdrive/invoices/<int:inv_id>/update', methods=['POST'])
def api_gdrive_invoice_update(inv_id):
    """Zapisuje ręczną korektę danych faktury (w tym typu koszt/przychód) przed akceptacją."""
    from models.gdrive_invoice import update_gdrive_invoice_fields
    data = request.get_json(silent=True) or {}
    try:
        updated = update_gdrive_invoice_fields(inv_id, data)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    if not updated:
        return jsonify({'status': 'error',
                         'message': 'Faktura nie istnieje lub nie jest już oczekująca.'}), 400
    return jsonify({'status': 'ok'})


@app.route('/api/gdrive/bulk-accept', methods=['POST'])
def api_gdrive_bulk_accept():
    """Automatycznie tworzy wydatki/przychody z zaznaczonych faktur z Google Drive."""
    import json as _json
    from datetime import datetime as _dt
    from models.gdrive_invoice import get_gdrive_invoices_by_ids, assign_gdrive_invoice
    from models.expense import create_expense, link_transaction
    from models.income import create_income, link_income_transaction

    data = request.get_json(silent=True) or {}
    ids = [int(i) for i in data.get('ids', []) if str(i).isdigit()]
    if not ids:
        return jsonify({'status': 'error', 'message': 'Brak ID.'})

    invoices = get_gdrive_invoices_by_ids(ids)
    created_expenses = 0
    created_incomes = 0
    auto_linked = 0
    errors = []

    from models.bank_transaction import search_bank_transactions as _search_txns
    try:
        _all_txns = list(_search_txns())
    except Exception:
        _all_txns = []

    for inv in invoices:
        if inv['status'] != 'pending':
            continue
        try:
            issue_date  = str(inv.get('issue_date') or '')[:10] or _dt.today().strftime('%Y-%m-%d')
            gross       = float(inv.get('amount_gross') or 0)
            net         = float(inv.get('amount_net') or gross)
            vat_rate    = round((gross - net) / net * 100, 0) if net > 0 else 23.0
            inv_number  = (inv.get('invoice_number') or '').strip()
            vendor      = (inv.get('vendor_name') or '').strip()
            vendor_nip  = (inv.get('vendor_nip') or '').strip()

            best, _ = _score_best(_all_txns, gross, inv_number)
            best_bank = best['bank'] if best else None

            file_name    = (inv.get('file_name') or '').strip()
            inv_currency = (inv.get('currency') or 'PLN').upper()
            inv_orig     = float(inv['orig_amount']) if inv.get('orig_amount') else None

            if inv.get('invoice_type') == 'income':
                record_id = create_income({
                    'date':           issue_date,
                    'client_name':    vendor or None,
                    'client_nip':     vendor_nip or None,
                    'description':    f"Faktura {inv_number}" + (f" – {vendor}" if vendor else ''),
                    'invoice_number': inv_number or None,
                    'amount_gross':   gross,
                    'vat_rate':       vat_rate,
                    'amount_net':     net,
                    'invoice_status': 'disk',
                    'invoice_ref':    file_name or None,
                    'payment_status': 'unpaid',
                    'fakturownia_id': None,
                    'source':         best_bank,
                    'payment_method': 'transfer' if best_bank else None,
                    'orig_amount':    inv_orig,
                    'orig_currency':  inv_currency if inv_orig else None,
                })
                created_incomes += 1
                if best:
                    try:
                        link_income_transaction(record_id, best['id'])
                        auto_linked += 1
                        _all_txns = [t for t in _all_txns if t['id'] != best['id']]
                    except Exception:
                        pass
            else:
                record_id = create_expense({
                    'date':               issue_date,
                    'responsible_person': 'Auto-import (GDrive)',
                    'contractor_name':    vendor or None,
                    'contractor_nip':     vendor_nip or None,
                    'invoice_number':     inv_number or None,
                    'description':        f"Faktura {inv_number}" + (f" – {vendor}" if vendor else ''),
                    'amount_gross':       gross,
                    'vat_rate':           vat_rate,
                    'amount_net':         net,
                    'payment_percent':    0,
                    'invoice_status':     'disk',
                    'invoice_ref':        file_name or None,
                    'source':             best_bank,
                    'payment_method':     'transfer' if best_bank else None,
                    'orig_amount':        inv_orig,
                    'orig_currency':      inv_currency if inv_orig else None,
                })
                created_expenses += 1
                if best:
                    try:
                        link_transaction(record_id, best['id'])
                        auto_linked += 1
                        _all_txns = [t for t in _all_txns if t['id'] != best['id']]
                    except Exception:
                        pass

            assign_gdrive_invoice(inv['id'], record_id)

        except Exception as exc:
            errors.append(f"ID {inv['id']}: {exc}\n{_tb.format_exc()}")

    total_created = created_expenses + created_incomes
    unlinked = total_created - auto_linked
    return jsonify({
        'status':           'ok' if not errors else 'partial',
        'created_expenses': created_expenses,
        'created_incomes':  created_incomes,
        'auto_linked':      auto_linked,
        'unlinked':         unlinked,
        'errors':           errors,
    })


@app.route('/api/gdrive/bulk-reject', methods=['POST'])
def api_gdrive_bulk_reject():
    from models.gdrive_invoice import bulk_reject_gdrive
    data = request.get_json(silent=True) or {}
    ids = [int(i) for i in data.get('ids', []) if str(i).isdigit()]
    if not ids:
        return jsonify({'status': 'error', 'message': 'Brak ID.'})
    affected = bulk_reject_gdrive(ids)
    return jsonify({'status': 'ok', 'affected': affected})


@app.route('/api/logs')
def api_logs():
    lines = int(request.args.get('lines', 200))
    log_path = os.path.join(os.path.dirname(__file__), 'logs', 'app.log')
    if not os.path.exists(log_path):
        return jsonify({'lines': []})
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
        return jsonify({'lines': [l.rstrip('\n') for l in all_lines[-lines:]]})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/logs/clear', methods=['POST'])
def api_logs_clear():
    log_path = os.path.join(os.path.dirname(__file__), 'logs', 'app.log')
    try:
        open(log_path, 'w').close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/crm/suggest')
def api_crm_suggest():
    kind = request.args.get('type', '')
    q = request.args.get('q', '').strip()
    if kind in ('tag', 'industry'):
        from models.crm_tags import suggest_tags
        return jsonify(suggest_tags(kind, q))
    if kind == 'source':
        from models.crm_tags import suggest_sources
        return jsonify(suggest_sources(q))
    return jsonify([])


@app.route('/api/crm/companies/search')
def api_crm_companies_search():
    from models.crm_company import search_companies
    q = request.args.get('q', '').strip()
    return jsonify(search_companies(q))


@app.route('/api/crm/contacts/search')
def api_crm_contacts_search():
    from models.crm_contact import search_contacts
    q = request.args.get('q', '').strip()
    company_id = request.args.get('company_id', type=int)
    return jsonify(search_contacts(q, company_id=company_id))


@app.route('/api/crm/company-lookup')
def api_crm_company_lookup():
    from services.company_lookup import lookup_by_krs, lookup_by_nip
    nip = request.args.get('nip', '').strip()
    krs = request.args.get('krs', '').strip()
    if nip:
        return jsonify(lookup_by_nip(nip))
    if krs:
        return jsonify(lookup_by_krs(krs))
    return jsonify({'ok': False, 'error': 'Podaj NIP lub KRS.'})


@app.route('/api/crm/companies/scrape-website', methods=['POST'])
def api_crm_companies_scrape_website():
    from models.settings import get_setting
    from services.company_profile import build_company_profile

    data = request.get_json(silent=True) or {}
    url = (data.get('url') or '').strip()
    if not url:
        return jsonify({'ok': False, 'error': 'Podaj adres strony WWW.'})

    api_key = get_setting('gemini_api_key', '')
    model = get_setting('gemini_model', 'gemini-2.5-flash')
    return jsonify(build_company_profile(url, api_key, model))


@app.route('/api/crm/companies/quick-create', methods=['POST'])
def api_crm_companies_quick_create():
    from services.company_lookup import lookup_by_krs, lookup_by_nip
    from models.crm_company import create_company, derive_short_name, get_company_by_nip

    data = request.get_json(silent=True) or {}
    nip = (data.get('nip') or '').strip()
    krs = (data.get('krs') or '').strip()
    if not nip and not krs:
        return jsonify({'ok': False, 'error': 'Podaj NIP lub KRS.'})

    if nip:
        existing = get_company_by_nip(re.sub(r'\D', '', nip))
        if existing:
            return jsonify({'ok': True, 'id': existing['id'],
                             'name': existing['short_name'] or existing['name'], 'created': False})
        result = lookup_by_nip(nip)
    else:
        result = lookup_by_krs(krs)

    if not result.get('ok'):
        return jsonify(result)

    company_data = result['data']
    if company_data.get('nip'):
        existing = get_company_by_nip(company_data['nip'])
        if existing:
            return jsonify({'ok': True, 'id': existing['id'],
                             'name': existing['short_name'] or existing['name'], 'created': False})

    company_id = create_company({
        'name': company_data['name'],
        'short_name': derive_short_name(company_data['name']),
        'relation_type': 'lead',
        'country': company_data.get('country') or 'Polska',
        'city': company_data.get('city') or '',
        'street': company_data.get('street') or '',
        'house_number': company_data.get('house_number') or '',
        'flat_number': company_data.get('flat_number') or '',
        'postal_code': company_data.get('postal_code') or '',
        'nip': company_data.get('nip') or '',
        'krs': company_data.get('krs') or '',
    }, session.get('user_id'), tags=[], industries=[])

    return jsonify({'ok': True, 'id': company_id, 'name': company_data['name'], 'created': True})


@app.route('/api/user-settings/<key>')
def api_get_user_setting(key):
    from models.user_settings import get_user_setting
    return jsonify({'value': get_user_setting(session['user_id'], key)})


@app.route('/api/user-settings/<key>', methods=['POST'])
def api_set_user_setting(key):
    from models.user_settings import set_user_setting
    data = request.get_json(silent=True) or {}
    set_user_setting(session['user_id'], key, data.get('value'))
    return jsonify({'ok': True})


from routes.auth import bp as auth_bp
from routes.crm_companies import bp as crm_companies_bp
from routes.crm_contacts import bp as crm_contacts_bp
from routes.crm_deals import bp as crm_deals_bp
from routes.crm_plan import bp as crm_plan_bp
from routes.dashboard import bp as dashboard_bp
from routes.expenses import bp as expenses_bp
from routes.imports import bp as imports_bp
from routes.income import bp as income_bp
from routes.settings import bp as settings_bp
from routes.users import bp as users_bp

app.register_blueprint(auth_bp)
app.register_blueprint(crm_companies_bp)
app.register_blueprint(crm_contacts_bp)
app.register_blueprint(crm_deals_bp)
app.register_blueprint(crm_plan_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(expenses_bp)
app.register_blueprint(imports_bp)
app.register_blueprint(income_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(users_bp)

if __name__ == '__main__':
    app.run(debug=Config.DEBUG, host='0.0.0.0', port=5001)
