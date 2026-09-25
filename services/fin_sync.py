"""Synchronizacja dokumentów z Fakturowni do lustra `fin_documents`.

API nie ma filtra „zmienione od…”, jest tylko sortowanie `updated_at.desc`.
Dlatego delta robi się kursorem: idziemy od najświeższej modyfikacji i kończymy,
gdy cała strona jest starsza niż ostatni sync minus okno zakładki. Pełny przebieg
(`full=True`) przechodzi wszystko.

Webhooki Fakturowni nie odpalają się dla faktur kosztowych (także tych
pobranych z KSeF), więc polling jest tu jedyną drogą, nie optymalizacją.
"""
import json
import re
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from database import get_db
from models.fin_document import upsert_document
from services.fakturownia_api import FakturowniaApi, is_income_doc
from services.fin_rules import apply_rules

OVERLAP = timedelta(days=1)   # zakładka na wypadek rozjazdu zegarów i stron


def _dec(value, default='0') -> Decimal:
    if value in (None, ''):
        value = default
    try:
        return Decimal(str(value).replace(' ', '').replace(',', '.'))
    except (InvalidOperation, ValueError):
        return Decimal(default)


def _date(value):
    """'2026-09-24' albo '2026-09' (Fakturownia dopuszcza sam miesiąc) → date."""
    if not value:
        return None
    text = str(value)[:10]
    for fmt, pad in (('%Y-%m-%d', text), ('%Y-%m', text[:7])):
        try:
            return datetime.strptime(pad, fmt).date()
        except ValueError:
            continue
    return None


def _datetime(value):
    if not value:
        return None
    text = str(value).replace('T', ' ')[:19]
    try:
        return datetime.strptime(text, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        return None


def _rate(raw: dict) -> Decimal:
    for key in ('exchange_currency_rate', 'currency_exchange_rate', 'exchange_rate'):
        rate = _dec(raw.get(key), '0')
        if rate > 0:
            return rate
    return Decimal('1')


EU_PREFIXES = ('PL', 'DE', 'IE', 'FR', 'CZ', 'SK', 'LT', 'LV', 'EE', 'NL', 'BE',
               'ES', 'IT', 'AT', 'SE', 'DK', 'FI', 'HU', 'RO', 'BG', 'GB', 'LU')


def normalize_tax_no(value) -> str:
    """NIP do porównań: ten sam kontrahent bywa i "5262544258", i "PL5262544258".

    Zostaje samo [A-Z0-9], a prefiks kraju spada tylko wtedy, gdy reszta wygląda
    na polski NIP (10 cyfr) — przy IE8256796U obcięcie "IE" zepsułoby numer.
    """
    text = re.sub(r'[^A-Za-z0-9]', '', str(value or '')).upper()
    if len(text) == 12 and text[:2] in EU_PREFIXES and text[2:].isdigit():
        return text[2:]
    return text


def map_invoice(raw: dict) -> dict:
    """Faktura z API → wiersz `fin_documents`.

    Uwaga na odwrócone role: przy fakturach kosztowych Fakturownia trzyma
    dostawcę w `buyer_*`, a nas samych w `seller_*`. Kontrahentem jest więc
    zawsze `buyer_*` — i dla kosztu, i dla przychodu.
    """
    currency = (raw.get('currency') or 'PLN').upper()
    rate = _rate(raw) if currency != 'PLN' else Decimal('1')
    net, tax, gross = _dec(raw.get('price_net')), _dec(raw.get('price_tax')), _dec(raw.get('price_gross'))
    return {
        'fakturownia_id': int(raw['id']),
        'department_id': raw.get('department_id') or None,
        'kind': (raw.get('kind') or 'vat')[:32],
        'is_income': 1 if is_income_doc(raw) else 0,
        'number': (raw.get('number') or '')[:128],
        'issue_date': _date(raw.get('issue_date')),
        'sell_date': _date(raw.get('sell_date')),
        'delivery_date': _date(raw.get('delivery_date')),
        'payment_to': _date(raw.get('payment_to')),
        'paid_date': _date(raw.get('paid_date')),
        # Daty księgowe Fakturowni: dla kosztów `accounting_vat_tax_date` to data
        # otrzymania faktury, od której liczy się prawo do odliczenia — bywa
        # w innym miesiącu niż wystawienie. Gdy pusta, zostaje data wystawienia.
        'vat_date': _date(raw.get('accounting_vat_tax_date')) or _date(raw.get('issue_date')),
        'income_tax_date': (_date(raw.get('accounting_income_tax_date'))
                            or _date(raw.get('issue_date'))),
        'status': (raw.get('status') or 'issued')[:24],
        'currency': currency[:3],
        'exchange_rate': rate,
        'price_net': net,
        'price_tax': tax,
        'price_gross': gross,
        'paid_amount': _dec(raw.get('paid')),
        'net_pln': (net * rate).quantize(Decimal('0.01')),
        'tax_pln': (tax * rate).quantize(Decimal('0.01')),
        'gross_pln': (gross * rate).quantize(Decimal('0.01')),
        'counterparty_name': (raw.get('buyer_name') or '')[:256],
        'counterparty_tax_no': (raw.get('buyer_tax_no') or '')[:32],
        'counterparty_tax_no_norm': normalize_tax_no(raw.get('buyer_tax_no'))[:32],
        'accounting_kind': (raw.get('accounting_kind') or '')[:32],
        'fakturownia_category_id': raw.get('category_id') or None,
        'gov_id': (raw.get('gov_id') or '')[:128],
        'gov_status': (raw.get('gov_status') or '')[:40],
        'gov_send_date': _datetime(raw.get('gov_send_date')),
        'description': raw.get('description') or None,
        'oid': (raw.get('oid') or '')[:128],
        'raw_json': json.dumps(raw, ensure_ascii=False, default=str),
        'fakturownia_updated_at': _datetime(raw.get('updated_at')),
    }


def sync_one(fakturownia_id: int, api: FakturowniaApi = None, raw: dict = None) -> dict:
    """Wciąga jeden dokument do lustra — po zapisie do Fakturowni, żeby CRM nie
    pokazywał stanu z przed zmiany do najbliższego pełnego synca.

    `raw` pozwala podać odpowiedź, którą i tak już mamy z POST/PUT, zamiast
    dopytywać API drugi raz. Reguły kategorii przechodzą tylko nowe dokumenty.
    """
    if raw is None:
        api = api or FakturowniaApi.from_settings()
        raw = api.get_invoice(int(fakturownia_id))
    if not isinstance(raw, dict) or not raw.get('id'):
        raise ValueError(f'Fakturownia nie zwróciła dokumentu {fakturownia_id}.')
    data = map_invoice(raw)
    db = get_db()
    try:
        result = upsert_document(data)
        db.commit()
    except Exception:
        db.rollback()
        raise
    categorized = apply_rules(only_ids=[data['fakturownia_id']])['assigned'] if result == 'new' else 0
    return {'fakturownia_id': data['fakturownia_id'], 'result': result, 'categorized': categorized}


def get_sync_state(resource: str = 'documents') -> dict:
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM fin_sync_state WHERE resource = %s", (resource,))
        row = cur.fetchone()
    return dict(row) if row else {'resource': resource, 'cursor_updated_at': None,
                                  'last_run_at': None, 'last_status': '', 'items_seen': 0,
                                  'items_changed': 0, 'message': ''}


def _save_state(resource: str, cursor_at, status: str, seen: int, changed: int, message: str) -> None:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """INSERT INTO fin_sync_state
                   (resource, cursor_updated_at, last_run_at, last_status, items_seen, items_changed, message)
               VALUES (%s, %s, NOW(), %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
                   cursor_updated_at = VALUES(cursor_updated_at), last_run_at = VALUES(last_run_at),
                   last_status = VALUES(last_status), items_seen = VALUES(items_seen),
                   items_changed = VALUES(items_changed), message = VALUES(message)""",
            (resource, cursor_at, status, seen, changed, message[:2000]))
    db.commit()


def sync_documents(full: bool = False, api: FakturowniaApi = None) -> dict:
    """Pobiera zmienione dokumenty. Zwraca podsumowanie przebiegu."""
    api = api or FakturowniaApi.from_settings()
    state = get_sync_state('documents')
    cursor = None if full else state.get('cursor_updated_at')
    stop_before = (cursor - OVERLAP) if cursor else None

    seen = new = updated = 0
    newest = cursor
    warnings: list[str] = []
    fresh_ids: list[int] = []      # nowe dokumenty idą potem przez reguły kategorii

    try:
        for income in (False, True):
            for page in api.iter_invoices(income=income):
                page_newest = None
                for raw in page:
                    data = map_invoice(raw)
                    result = upsert_document(data)
                    seen += 1
                    if result == 'new':
                        new += 1
                        fresh_ids.append(data['fakturownia_id'])
                    elif result == 'updated':
                        updated += 1
                    stamp = data['fakturownia_updated_at']
                    if stamp:
                        page_newest = max(page_newest or stamp, stamp)
                        newest = max(newest or stamp, stamp)
                    if data['currency'] != 'PLN' and data['exchange_rate'] == 1:
                        warnings.append(f"Brak kursu dla {data['number']} ({data['currency']})")
                if stop_before and page_newest and page_newest < stop_before:
                    break
        get_db().commit()
    except Exception as e:
        get_db().rollback()
        _save_state('documents', cursor, 'error', seen, new + updated, str(e)[:500])
        raise

    # Reguły dopiero po commicie lustra: gdyby sync padł, nie zostawimy
    # kategorii przypiętych do dokumentów, których w bazie nie ma.
    categorized = apply_rules(only_ids=fresh_ids)['assigned'] if fresh_ids else 0

    message = '; '.join(warnings[:5])
    _save_state('documents', newest, 'ok', seen, new + updated, message)
    return {'seen': seen, 'new': new, 'updated': updated, 'full': full,
            'categorized': categorized, 'cursor': newest, 'warnings': warnings}
