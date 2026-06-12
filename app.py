from flask import Flask, jsonify, request
from config import Config
import database
import traceback as _tb

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
    try:
        from models.gdrive_invoice import get_gdrive_pending_count
        gdrive_cnt = get_gdrive_pending_count()
    except Exception:
        gdrive_cnt = 0
    return {
        'pending_count':       cnt,
        'bank_pending_count':  bank_cnt,
        'gdrive_pending_count': gdrive_cnt,
        'app_name':            Config.APP_NAME,
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

            record = {
                'gdrive_file_id':   fid,
                'file_name':        fname,
                'file_modified_at': fmod,
                'gdrive_year':      gdrive_year,
                'gdrive_month':     gdrive_month,
                'invoice_number':   ocr.get('invoice_number') or None,
                'vendor_name':      ocr.get('vendor_name') or None,
                'vendor_nip':       ocr.get('vendor_nip') or None,
                'issue_date':       ocr.get('issue_date') or None,
                'amount_gross':     ocr.get('amount_gross'),
                'amount_net':       ocr.get('amount_net'),
                'vat_amount':       ocr.get('vat_amount'),
                'invoice_type':     ocr.get('invoice_type', 'expense'),
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

            file_name = (inv.get('file_name') or '').strip()

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
