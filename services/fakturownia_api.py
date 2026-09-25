"""Klient REST Fakturowni dla modułu Finanse v2.

Fakturownia nie używa nagłówka Authorization — token idzie w query stringu (GET)
albo w ciele JSON obok obiektu (POST/PUT). Limit to ~1000 zapytań na minutę
z jednego IP i 2 równoległe połączenia, bez udokumentowanego 429/Retry-After,
więc chodzimy sekwencyjnie i z backoffem.
"""
import time

import requests

from models.settings import get_setting

TIMEOUT = 20
PER_PAGE = 100          # twardy limit API
MAX_RETRIES = 3


class FakturowniaError(RuntimeError):
    pass


class FakturowniaApi:
    def __init__(self, subdomain: str, api_token: str):
        if not subdomain or not api_token:
            raise FakturowniaError('Brak subdomeny lub klucza API Fakturowni (Ustawienia → Ogólne).')
        self.base_url = f"https://{subdomain.strip()}.fakturownia.pl"
        self.api_token = api_token.strip()

    @classmethod
    def from_settings(cls) -> 'FakturowniaApi':
        return cls(get_setting('fakturownia_subdomain', ''), get_setting('fakturownia_api_key', ''))

    # ── niski poziom ─────────────────────────────────────────────────────────
    def _request(self, method: str, path: str, params: dict = None, payload: dict = None):
        url = f"{self.base_url}{path}"
        params = {**(params or {}), 'api_token': self.api_token}
        body = {**(payload or {}), 'api_token': self.api_token} if payload is not None else None

        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                resp = requests.request(method, url, params=params, json=body, timeout=TIMEOUT)
            except (requests.Timeout, requests.ConnectionError) as e:
                last_error = f'Błąd połączenia: {str(e)[:150]}'
            else:
                if resp.status_code in (429, 500, 502, 503, 504):
                    last_error = f'Serwer zwrócił {resp.status_code}'
                elif resp.status_code == 401:
                    raise FakturowniaError('Błędny klucz API Fakturowni (401).')
                elif resp.status_code >= 400:
                    raise FakturowniaError(f'{method} {path} → {resp.status_code}: {resp.text[:200]}')
                else:
                    return resp.json() if resp.content else None
            time.sleep(1.5 * (attempt + 1))
        raise FakturowniaError(f'{method} {path}: {last_error}')

    def get(self, path: str, params: dict = None):
        return self._request('GET', path, params=params)

    def post(self, path: str, payload: dict, params: dict = None):
        return self._request('POST', path, params=params, payload=payload)

    def put(self, path: str, payload: dict, params: dict = None):
        return self._request('PUT', path, params=params, payload=payload)

    # ── faktury ──────────────────────────────────────────────────────────────
    def iter_invoices(self, income: bool, max_pages: int = 100):
        """Faktury od najświeższej modyfikacji. Zwraca strony, żeby sync mógł
        przerwać paginację, gdy zejdzie poniżej kursora.

        Koszt i przychód to ten sam zasób — rozróżnia je pole `income`.
        Parametr `income=no` zwraca wyłącznie koszty; bez niego API oddaje
        przychody, więc filtrujemy jeszcze po stronie klienta dla pewności.
        """
        params = {'period': 'all', 'order': 'updated_at.desc', 'per_page': PER_PAGE}
        if not income:
            params['income'] = 'no'
        for page in range(1, max_pages + 1):
            batch = self.get('/invoices.json', {**params, 'page': page})
            if not isinstance(batch, list) or not batch:
                return
            wanted = [d for d in batch if is_income_doc(d) == income]
            yield wanted
            if len(batch) < PER_PAGE:
                return

    def get_invoice(self, invoice_id: int) -> dict:
        return self.get(f'/invoices/{invoice_id}.json')

    def find_invoice_by_oid(self, oid: str) -> dict | None:
        """Faktura po zewnętrznym identyfikatorze — klucz idempotencji zapisów.

        Sprawdzone na żywo: `?oid=` filtruje po stronie serwera (nieistniejące
        oid zwraca pustą listę, nie całą listę faktur). `period=all`, bo bez
        tego API patrzy tylko na bieżący miesiąc.
        """
        if not (oid or '').strip():
            return None
        found = self.get('/invoices.json', {'oid': oid.strip(), 'period': 'all', 'per_page': 5})
        if not isinstance(found, list):
            return None
        # Filtr serwera bierzemy na słowo tylko po sprawdzeniu — gdyby Fakturownia
        # kiedyś go zignorowała, wolę nic nie znaleźć niż dopasować obcą fakturę.
        exact = [d for d in found if str(d.get('oid') or '').strip() == oid.strip()]
        return exact[0] if exact else None

    # ── zapisy ───────────────────────────────────────────────────────────────
    #
    # `gov_save_and_send` i `send_to_ksef` to parametry poza obiektem `invoice`.
    # Wysyłka do KSeF jest nieodwracalna, więc nigdy nie dokładamy jej domyślnie.

    def create_invoice(self, invoice: dict, send_to_ksef: bool = False) -> dict:
        payload = {'invoice': invoice}
        if send_to_ksef:
            payload['gov_save_and_send'] = True
        return self.post('/invoices.json', payload)

    def update_invoice(self, invoice_id: int, fields: dict) -> dict:
        return self.put(f'/invoices/{invoice_id}.json', {'invoice': fields})

    def send_invoice_to_ksef(self, invoice_id: int) -> dict:
        """Wysyłka istniejącej faktury. Tak, to GET — tak każe dokumentacja
        Fakturowni (`GET /invoices/{ID}.json?send_to_ksef=yes`); metoda nie jest
        bezpieczna wbrew nazwie HTTP, dlatego stoi tu osobno i jawnie.
        """
        return self.get(f'/invoices/{invoice_id}.json', {'send_to_ksef': 'yes'})

    def test_connection(self) -> dict:
        try:
            self.get('/invoices.json', {'per_page': 1})
            return {'ok': True, 'message': 'Połączenie z Fakturownią działa.'}
        except FakturowniaError as e:
            return {'ok': False, 'message': str(e)}


def is_income_doc(doc: dict) -> bool:
    """API zwraca `income` raz jako "1"/"0", raz jako bool — normalizujemy."""
    value = doc.get('income')
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ('1', 'true', 'yes', 't')
