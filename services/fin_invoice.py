"""Zapisy do Fakturowni — jedyne miejsce w CRM, które tworzy i zmienia dokumenty.

Trzy zasady, na których to stoi:

1. **Fakturownia zostaje źródłem prawdy.** Zapis idzie do API, a lustro
   `fin_documents` odświeżamy odpowiedzią, którą API zwróciło — nigdy nie
   piszemy do lustra „na wiarę”, że zapis się udał.
2. **Idempotencja przez `oid`.** Każdy dokument tworzony z CRM ma zewnętrzny
   identyfikator i leci z `oid_unique='yes'`. Przed utworzeniem sprawdzamy
   `?oid=`, więc powtórzone wywołanie (agent przetwarzający tę samą skrzynkę
   dwa razy) zwraca istniejący dokument zamiast wystawiać bliźniaka.
3. **KSeF nigdy domyślnie.** Wysyłka do KSeF jest nieodwracalna — `send_to_ksef`
   domyślnie jest wyłączone, a odpowiedź zawsze mówi wprost, czy dokument
   poleciał i z jakim statusem. Uwaga: konto Fakturowni może mieć włączoną
   *automatyczną* wysyłkę (`gov_auto_send_mode`), której API nie da się wyłączyć
   ani odczytać — dlatego po każdym utworzeniu faktury przychodowej czytamy
   `gov_status` z odpowiedzi i raportujemy stan faktyczny, a nie życzeniowy.

Role kupujący/sprzedający przy kosztach są w Fakturowni odwrócone: dostawca
siedzi w `buyer_*`, my w `seller_*`. Na zewnątrz tego nie powtarzamy — tool
kosztowy przyjmuje `supplier_*` i sam mapuje na `buyer_*`, tak samo jak lustro,
w którym kontrahentem zawsze jest `buyer_*`.
"""
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import models.fin_audit as fin_audit
import models.fin_document as fin_document
from database import get_db
from models.settings import get_setting
from services.fakturownia_api import FakturowniaApi, FakturowniaError, is_income_doc
from services.fin_sync import sync_one

# Tylko te rodzaje dokumentów KSeF w ogóle przyjmuje; reszta dostaje
# `not_applicable`, więc nie ma sensu ich wysyłać.
KSEF_KINDS = ('vat', 'correction', 'vat_mp', 'vat_margin', 'wdt', 'export_products',
              'advance', 'final')

# Statusy oznaczające „dokument jest już w obiegu KSeF” — treści takiego
# dokumentu nie wolno podmieniać, na to jest faktura korygująca.
KSEF_LOCKED_STATUSES = ('ok', 'processing', 'offline', 'duplicate_error',
                        'demo_ok', 'demo_processing', 'demo_offline')

# Co wolno zmieniać na dokumencie już zamkniętym w KSeF: nic z treści faktury,
# tylko nasze własne pola porządkowe i daty księgowe.
SAFE_UPDATE_FIELDS = ('description', 'oid', 'accounting_kind',
                      'accounting_vat_tax_date', 'accounting_income_tax_date')

UPDATABLE_FIELDS = SAFE_UPDATE_FIELDS + (
    'number', 'issue_date', 'sell_date', 'payment_to', 'payment_type',
    'buyer_name', 'buyer_tax_no', 'buyer_street', 'buyer_post_code', 'buyer_city',
    'buyer_country', 'buyer_email', 'buyer_company',
)

DATE_FIELDS = ('issue_date', 'sell_date', 'payment_to', 'paid_date',
               'accounting_vat_tax_date', 'accounting_income_tax_date')


class FinWriteError(RuntimeError):
    """Zapis odrzucony przez nas albo przez Fakturownię — z komunikatem dla człowieka."""


# ── walidacja wejścia ────────────────────────────────────────────────────────

def _money(value, label: str) -> Decimal:
    try:
        amount = Decimal(str(value).replace(' ', '').replace(',', '.'))
    except (InvalidOperation, ValueError, TypeError):
        raise FinWriteError(f'{label}: „{value}” to nie kwota.')
    return amount.quantize(Decimal('0.01'))


def _day(value, label: str, required: bool = False) -> str | None:
    if value in (None, ''):
        if required:
            raise FinWriteError(f'{label}: brak daty.')
        return None
    if isinstance(value, (date, datetime)):
        return value.strftime('%Y-%m-%d')
    try:
        return datetime.strptime(str(value).strip()[:10], '%Y-%m-%d').strftime('%Y-%m-%d')
    except ValueError:
        raise FinWriteError(f'{label}: „{value}” nie jest datą RRRR-MM-DD.')


def _tax(value) -> str | int:
    """Stawka VAT: liczba (23, 8, 5, 0) albo symbol (zw, np, oo). Fakturownia
    przyjmuje jedno i drugie, my tylko pilnujemy, żeby nie poszło nic dziwnego."""
    text = str(value).strip().lower().replace('%', '').replace(',', '.')
    if text in ('zw', 'np', 'oo', 'n/a', 'na', 'nie podlega'):
        return text
    try:
        number = Decimal(text)
    except (InvalidOperation, ValueError):
        raise FinWriteError(f'Stawka VAT „{value}”: podaj liczbę (np. 23) albo zw/np/oo.')
    if number < 0 or number > 100:
        raise FinWriteError(f'Stawka VAT „{value}” jest poza zakresem 0–100.')
    return int(number) if number == number.to_integral_value() else float(number)


def build_positions(positions: list[dict] | None, title: str = '',
                    total_gross=None, vat_rate=23) -> list[dict]:
    """Pozycje faktury. Albo pełna lista, albo skrót jednopozycyjny
    (`title` + `total_gross` + `vat_rate`) — typowy koszt to jedna linia."""
    if positions:
        out = []
        for index, raw in enumerate(positions, start=1):
            if not isinstance(raw, dict):
                raise FinWriteError(f'Pozycja {index}: oczekuję obiektu z polami name/total_price_gross/tax.')
            name = str(raw.get('name') or '').strip()
            if not name:
                raise FinWriteError(f'Pozycja {index}: brak nazwy.')
            gross = raw.get('total_price_gross', raw.get('total_gross'))
            if gross in (None, ''):
                raise FinWriteError(f'Pozycja {index} („{name}”): brak total_price_gross.')
            quantity = raw.get('quantity', 1) or 1
            out.append({
                'name': name[:400],
                'quantity': float(_money(quantity, f'Pozycja {index}: ilość')),
                'total_price_gross': float(_money(gross, f'Pozycja {index}: kwota brutto')),
                'tax': _tax(raw.get('tax', vat_rate)),
            })
        return out
    if total_gross in (None, ''):
        raise FinWriteError('Podaj `positions` albo `total_gross` — bez kwoty nie wystawię dokumentu.')
    return [{
        'name': (str(title).strip() or 'Usługa')[:400],
        'quantity': 1,
        'total_price_gross': float(_money(total_gross, 'Kwota brutto')),
        'tax': _tax(vat_rate),
    }]


def make_oid(prefix: str = 'CRM') -> str:
    """Zewnętrzny identyfikator nadawany przez CRM. Data dla czytelności
    w Fakturowni, losowy ogon dla unikalności."""
    return f"{prefix}-{date.today():%Y%m%d}-{uuid.uuid4().hex[:10]}"


def _department_id() -> int | None:
    """Dział wystawiający. Z ustawień, a gdy ich nie ma — dział główny konta.
    Dane sprzedawcy wymagane przez KSeF bierze wtedy Fakturownia z działu,
    zamiast żebyśmy je tu duplikowali i ryzykowali rozjazd."""
    configured = str(get_setting('fakturownia_department_id', '') or '').strip()
    if configured.isdigit():
        return int(configured)
    return None


# ── tworzenie dokumentów ─────────────────────────────────────────────────────

def _ksef_report(raw: dict, requested: bool, is_income: bool) -> dict:
    """Jednoznaczna odpowiedź na pytanie „czy to poszło do KSeF?”."""
    status = (raw.get('gov_status') or '') or None
    sent = bool(status) and status.replace('demo_', '') in (
        'ok', 'processing', 'offline', 'status_check_error')
    report = {
        'requested': bool(requested),
        'sent': sent,
        'gov_status': status,
        'gov_id': raw.get('gov_id') or None,
        'gov_send_date': raw.get('gov_send_date') or None,
        'gov_error_messages': raw.get('gov_error_messages') or None,
        'gov_verification_link': raw.get('gov_verification_link') or None,
    }
    if not is_income:
        report['note'] = ('Dokument kosztowy — do KSeF się nie wysyła. `gov_status` na '
                          'kosztach oznacza, że faktura przyszła z KSeF, nie że tam poleciała.')
    elif sent and not requested:
        report['note'] = ('Dokument poszedł do KSeF, choć o to nie prosiłem — konto ma '
                          'włączoną automatyczną wysyłkę (Ustawienia → KSeF w Fakturowni). '
                          'Tego nie da się wyłączyć przez API.')
    elif requested and not sent:
        report['note'] = ('Poprosiłem o wysyłkę, ale KSeF jej nie potwierdził — sprawdź '
                          '`gov_error_messages` i `gov_status`.')
    elif status == 'processing' or status == 'demo_processing':
        report['note'] = 'Wysyłka w toku — numer KSeF (`gov_id`) pojawi się po przetworzeniu.'
    return report


def _created_response(raw: dict, requested_ksef: bool, is_income: bool,
                      duplicate: bool = False) -> dict:
    mirror = sync_one(int(raw['id']), raw=raw)
    return {
        'fakturownia_id': int(raw['id']),
        'number': raw.get('number') or None,
        'kind': raw.get('kind'),
        'is_income': is_income,
        'oid': raw.get('oid') or None,
        'price_net': raw.get('price_net'),
        'price_tax': raw.get('price_tax'),
        'price_gross': raw.get('price_gross'),
        'currency': raw.get('currency'),
        'status': raw.get('status'),
        'duplicate': duplicate,
        'ksef': _ksef_report(raw, requested_ksef, is_income),
        'mirror': mirror,
        'url': f"https://{get_setting('fakturownia_subdomain', '')}.fakturownia.pl/invoices/{raw['id']}",
    }


def create_document(is_income: bool, *, counterparty: dict, positions: list[dict],
                    kind: str = 'vat', issue_date=None, sell_date=None, payment_to=None,
                    number: str = '', description: str = '', currency: str = 'PLN',
                    accounting_kind: str = '', oid: str = '', send_to_ksef: bool = False,
                    actor: str = 'agent', api: FakturowniaApi = None,
                    extra: dict = None) -> dict:
    """Tworzy fakturę w Fakturowni i wciąga ją do lustra.

    `counterparty` to już gotowe pola `buyer_*` (dla kosztu: dostawca, dla
    przychodu: klient). Zwraca m.in. `ksef` z jednoznaczną informacją o wysyłce
    i `duplicate=True`, gdy dokument o tym `oid` już istniał.
    """
    api = api or FakturowniaApi.from_settings()
    kind = (kind or 'vat').strip().lower()
    oid = (oid or '').strip() or make_oid()

    if send_to_ksef and not is_income:
        raise FinWriteError('Faktury kosztowej nie wysyła się do KSeF — to dokument '
                            'wystawiony przez dostawcę, nie przez Ciebie.')
    if send_to_ksef and kind not in KSEF_KINDS:
        raise FinWriteError(f'Dokumentu „{kind}” KSeF nie przyjmuje '
                            f'(przyjmuje: {", ".join(KSEF_KINDS)}).')

    # Idempotencja przed zapisem: tego samego `oid` nie wystawiamy dwa razy.
    existing = api.find_invoice_by_oid(oid)
    if existing:
        fin_audit.log('create_invoice.duplicate', actor=actor,
                      fakturownia_id=int(existing['id']), payload={'oid': oid},
                      response={'number': existing.get('number')}, ok=True)
        get_db().commit()
        return _created_response(existing, send_to_ksef, is_income, duplicate=True)

    invoice = {
        'kind': kind,
        'income': '1' if is_income else '0',
        'oid': oid,
        'oid_unique': 'yes',
        'issue_date': _day(issue_date or date.today(), 'issue_date'),
        'currency': (currency or 'PLN').strip().upper()[:3],
        'positions': positions,
        **{k: v for k, v in (counterparty or {}).items() if v not in (None, '')},
    }
    for field, value in (('sell_date', sell_date), ('payment_to', payment_to)):
        stamp = _day(value, field)
        if stamp:
            invoice[field] = stamp
    if payment_to:
        invoice['payment_to_kind'] = 'other_date'
    if number.strip():
        invoice['number'] = number.strip()[:128]
    if description.strip():
        invoice['description'] = description.strip()[:256]
    if accounting_kind.strip():
        invoice['accounting_kind'] = accounting_kind.strip()
    department = _department_id()
    if department:
        invoice['department_id'] = department
    invoice.update({k: v for k, v in (extra or {}).items() if v not in (None, '')})

    try:
        raw = api.create_invoice(invoice, send_to_ksef=send_to_ksef)
    except FakturowniaError as e:
        fin_audit.log('create_invoice', actor=actor, payload=invoice, response=str(e), ok=False)
        get_db().commit()
        # Konto może mieć „Zablokuj tworzenie faktur niezgodnych z KSeF” — wtedy
        # 422 z listą brakujących pól jest jedyną informacją, co poprawić.
        raise FinWriteError(f'Fakturownia odrzuciła dokument: {e}') from e

    if not isinstance(raw, dict) or not raw.get('id'):
        fin_audit.log('create_invoice', actor=actor, payload=invoice, response=raw, ok=False)
        get_db().commit()
        raise FinWriteError(f'Fakturownia nie zwróciła id utworzonego dokumentu: {str(raw)[:300]}')

    fin_audit.log('create_invoice', actor=actor, fakturownia_id=int(raw['id']),
                  payload={**invoice, 'send_to_ksef': send_to_ksef}, response=raw, ok=True)
    get_db().commit()
    return _created_response(raw, send_to_ksef, is_income)


# ── płatności ────────────────────────────────────────────────────────────────

def mark_paid(fakturownia_id: int, amount=None, paid_date=None, actor: str = 'agent',
              api: FakturowniaApi = None) -> dict:
    """Oznacza dokument jako opłacony.

    `amount` to **łączna** kwota zapłacona na tym dokumencie, nie dopłata —
    dzięki temu powtórzone wywołanie nic nie psuje. Pusta = pełne brutto.

    Zapis idzie przez `PUT /invoices/{id}` (pola `paid`, `paid_date`, `status`),
    a nie przez `POST /banking/payments.json`, bo tak wygląda to konto: nie ma
    na nim ani jednej płatności w rejestrze bankowym, a statusy opłacenia
    siedzą wprost na fakturach. Drugi rejestr tylko rozjechałby te dane.
    """
    api = api or FakturowniaApi.from_settings()
    doc = fin_document.get_document(int(fakturownia_id))
    if not doc:
        raise FinWriteError(f'Nie znam dokumentu {fakturownia_id} — zsynchronizuj najpierw lustro.')

    gross = Decimal(str(doc['price_gross'] or '0'))
    paid = _money(amount, 'amount') if amount not in (None, '') else gross
    if paid < 0:
        raise FinWriteError('Kwota zapłaty nie może być ujemna.')

    warning = None
    if paid > gross:
        warning = (f'Kwota {paid} przekracza brutto dokumentu ({gross}) — zapisuję ją '
                   'tak, jak podałeś, ale sprawdź, czy to nie pomyłka.')
    status = 'paid' if paid >= gross and gross > 0 else ('partial' if paid > 0 else 'issued')
    fields = {
        'paid': float(paid),
        'paid_date': _day(paid_date or date.today(), 'paid_date'),
        'status': status,
    }
    try:
        raw = api.update_invoice(int(fakturownia_id), fields)
    except FakturowniaError as e:
        fin_audit.log('mark_paid', actor=actor, fakturownia_id=int(fakturownia_id),
                      payload=fields, response=str(e), ok=False)
        get_db().commit()
        raise FinWriteError(f'Fakturownia odrzuciła zapis płatności: {e}') from e

    fin_audit.log('mark_paid', actor=actor, fakturownia_id=int(fakturownia_id),
                  payload=fields, response=raw, ok=True)
    get_db().commit()
    mirror = sync_one(int(fakturownia_id), raw=raw if isinstance(raw, dict) and raw.get('id') else None,
                      api=api)
    fresh = fin_document.get_document(int(fakturownia_id)) or {}
    return {
        'fakturownia_id': int(fakturownia_id),
        'number': fresh.get('number') or doc.get('number'),
        'status': fresh.get('status'),
        'price_gross': fresh.get('price_gross'),
        'paid_amount': fresh.get('paid_amount'),
        'paid_date': fresh.get('paid_date'),
        'amount_left': (Decimal(str(fresh.get('price_gross') or '0'))
                        - Decimal(str(fresh.get('paid_amount') or '0'))),
        'warning': warning,
        'mirror': mirror,
    }


# ── edycja ───────────────────────────────────────────────────────────────────

def update_document(fakturownia_id: int, fields: dict, actor: str = 'agent',
                    api: FakturowniaApi = None) -> dict:
    """Zmienia wybrane pola dokumentu. Biała lista pól, a na dokumencie już
    obecnym w KSeF przechodzą tylko pola porządkowe — treści faktury w obiegu
    KSeF nie podmienia się edycją, tylko korektą."""
    api = api or FakturowniaApi.from_settings()
    doc = fin_document.get_document(int(fakturownia_id))
    if not doc:
        raise FinWriteError(f'Nie znam dokumentu {fakturownia_id} — zsynchronizuj najpierw lustro.')

    clean, rejected = {}, []
    for key, value in (fields or {}).items():
        if key not in UPDATABLE_FIELDS:
            rejected.append(key)
            continue
        clean[key] = _day(value, key) if key in DATE_FIELDS else value
    if rejected:
        raise FinWriteError(f'Nie zmieniam pól: {", ".join(sorted(rejected))}. '
                            f'Dozwolone: {", ".join(UPDATABLE_FIELDS)}.')
    if not clean:
        raise FinWriteError('Nie podałeś żadnego pola do zmiany.')

    gov = (doc.get('gov_status') or '')
    if doc.get('is_income') and gov in KSEF_LOCKED_STATUSES:
        blocked = [k for k in clean if k not in SAFE_UPDATE_FIELDS]
        if blocked:
            raise FinWriteError(
                f'Faktura {doc.get("number")} jest w KSeF (gov_status={gov}) — nie zmienię '
                f'pól {", ".join(sorted(blocked))}. Treść dokumentu w obiegu KSeF poprawia się '
                f'fakturą korygującą. Bez przeszkód zmienię: {", ".join(SAFE_UPDATE_FIELDS)}.')

    try:
        raw = api.update_invoice(int(fakturownia_id), clean)
    except FakturowniaError as e:
        fin_audit.log('update_invoice', actor=actor, fakturownia_id=int(fakturownia_id),
                      payload=clean, response=str(e), ok=False)
        get_db().commit()
        raise FinWriteError(f'Fakturownia odrzuciła zmianę: {e}') from e

    fin_audit.log('update_invoice', actor=actor, fakturownia_id=int(fakturownia_id),
                  payload=clean, response=raw, ok=True)
    get_db().commit()
    mirror = sync_one(int(fakturownia_id),
                      raw=raw if isinstance(raw, dict) and raw.get('id') else None, api=api)
    return {'fakturownia_id': int(fakturownia_id), 'changed': sorted(clean),
            'mirror': mirror, 'document': fin_document.get_document(int(fakturownia_id))}


# ── KSeF ─────────────────────────────────────────────────────────────────────

def send_to_ksef(fakturownia_id: int, actor: str = 'agent',
                 api: FakturowniaApi = None) -> dict:
    """Wysyła istniejącą fakturę do KSeF. Operacja nieodwracalna."""
    api = api or FakturowniaApi.from_settings()
    doc = fin_document.get_document(int(fakturownia_id))
    if not doc:
        raise FinWriteError(f'Nie znam dokumentu {fakturownia_id} — zsynchronizuj najpierw lustro.')
    if not doc.get('is_income'):
        raise FinWriteError('To dokument kosztowy — wystawił go dostawca i to on odpowiada '
                            'za jego obecność w KSeF. Z CRM go nie wysyłam.')
    if (doc.get('kind') or '') not in KSEF_KINDS:
        raise FinWriteError(f'Dokument „{doc.get("kind")}” nie kwalifikuje się do KSeF '
                            f'(KSeF przyjmuje: {", ".join(KSEF_KINDS)}).')
    if (doc.get('gov_status') or '') in ('ok', 'demo_ok'):
        return {'fakturownia_id': int(fakturownia_id), 'number': doc.get('number'),
                'already_sent': True,
                'ksef': {'requested': False, 'sent': True, 'gov_status': doc.get('gov_status'),
                         'gov_id': doc.get('gov_id') or None,
                         'note': 'Faktura już jest w KSeF — drugi raz nie wysyłam.'}}

    try:
        raw = api.send_invoice_to_ksef(int(fakturownia_id))
    except FakturowniaError as e:
        fin_audit.log('send_to_ksef', actor=actor, fakturownia_id=int(fakturownia_id),
                      payload={'send_to_ksef': 'yes'}, response=str(e), ok=False)
        get_db().commit()
        raise FinWriteError(f'Wysyłka do KSeF nie udała się: {e}') from e

    fin_audit.log('send_to_ksef', actor=actor, fakturownia_id=int(fakturownia_id),
                  payload={'send_to_ksef': 'yes'}, response=raw, ok=True)
    get_db().commit()
    raw = raw if isinstance(raw, dict) and raw.get('id') else api.get_invoice(int(fakturownia_id))
    mirror = sync_one(int(fakturownia_id), raw=raw)
    return {'fakturownia_id': int(fakturownia_id), 'number': raw.get('number'),
            'already_sent': False, 'ksef': _ksef_report(raw, True, True), 'mirror': mirror}


def ksef_status(fakturownia_id: int, api: FakturowniaApi = None) -> dict:
    """Odczyt statusu KSeF wprost z Fakturowni (plus odświeżenie lustra).
    Po utworzeniu faktura bywa w stanie `processing` — numer KSeF pojawia się
    dopiero po przetworzeniu, więc status trzeba dopytać."""
    api = api or FakturowniaApi.from_settings()
    raw = api.get_invoice(int(fakturownia_id))
    if not isinstance(raw, dict) or not raw.get('id'):
        raise FinWriteError(f'Fakturownia nie zwróciła dokumentu {fakturownia_id}.')
    mirror = sync_one(int(fakturownia_id), raw=raw)
    return {'fakturownia_id': int(fakturownia_id), 'number': raw.get('number'),
            'ksef': _ksef_report(raw, False, is_income_doc(raw)), 'mirror': mirror}
