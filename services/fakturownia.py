import calendar
import json
from datetime import date, timedelta

import requests

from models.invoice import add_sync_log, upsert_invoice

TIMEOUT = 15


class FakturowniaClient:
    BASE_URL = "https://{subdomain}.fakturownia.pl"

    def __init__(self, subdomain: str, api_token: str):
        self.base_url = self.BASE_URL.format(subdomain=subdomain.strip())
        self.api_token = api_token.strip()

    def _get(self, path: str, params: dict = None) -> requests.Response:
        url = f"{self.base_url}{path}"
        p = {'api_token': self.api_token}
        if params:
            p.update(params)
        resp = requests.get(url, params=p, timeout=TIMEOUT)
        return resp

    def test_connection(self) -> dict:
        try:
            resp = self._get('/invoices.json', {'per_page': 1})
            if resp.status_code == 200:
                data = resp.json()
                count = len(data) if isinstance(data, list) else '?'
                return {'ok': True, 'message': f'Połączenie działa. Widocznych faktur (próbka): {count}.'}
            elif resp.status_code == 401:
                return {'ok': False, 'message': 'Błędny klucz API (401 Unauthorized).'}
            else:
                return {'ok': False, 'message': f'Serwer zwrócił status: {resp.status_code}'}
        except requests.Timeout:
            return {'ok': False, 'message': 'Przekroczono czas oczekiwania (timeout 15s).'}
        except requests.ConnectionError as e:
            return {'ok': False, 'message': f'Błąd połączenia: {str(e)[:120]}'}

    def _fetch_all_pages(self, params: dict) -> list[dict]:
        """Pobiera wszystkie strony z paginacją."""
        all_items = []
        page = 1
        while True:
            p = {**params, 'page': page, 'per_page': 100}
            resp = self._get('/invoices.json', p)
            resp.raise_for_status()
            batch = resp.json()
            if not isinstance(batch, list) or len(batch) == 0:
                break
            all_items.extend(batch)
            if len(batch) < 100:
                break
            page += 1
        return all_items

    def fetch_invoices(self, period_start: str, period_end: str,
                       filter_category: str = 'expense') -> list[dict]:
        """
        Pobiera faktury z podanego okresu.

        filter_category:
          'expense'  – faktury kosztowe  (income=no)
          'income'   – faktury przychodowe (income=yes)
          'all'      – wszystkie faktury (income=yes i income=no, pobrane osobno i połączone)

        Fakturownia dokumentuje wyłącznie wartości tekstowe 'yes'/'no' dla tego
        parametru (nie 1/0) — patrz https://github.com/fakturownia/API. Dla 'all'
        odpytujemy jawnie oba warianty zamiast polegać na zachowaniu domyślnym,
        gdy parametr income nie jest podany wcale.
        """
        params = {
            'period':          'more',
            'date_from':       period_start,
            'date_to':         period_end,
            # sell_date (transaction_date) ma priorytet w _normalize() przy zapisie
            # do naszej bazy, więc filtrujemy po tym samym polu co API Fakturowni.
            'search_date_type': 'transaction_date',
        }

        if filter_category == 'all':
            items = []
            for income_value in ('yes', 'no'):
                items.extend(self._fetch_all_pages({**params, 'income': income_value}))
        else:
            params['income'] = 'yes' if filter_category == 'income' else 'no'
            items = self._fetch_all_pages(params)

        return self._normalize(items)

    def fetch_all_invoices(self, filter_category: str = 'expense') -> list[dict]:
        """Pobiera WSZYSTKIE faktury bez filtra dat."""
        if filter_category == 'all':
            items = []
            for income_value in ('yes', 'no'):
                items.extend(self._fetch_all_pages({'income': income_value}))
        else:
            income_value = 'yes' if filter_category == 'income' else 'no'
            items = self._fetch_all_pages({'income': income_value})
        return self._normalize(items)

    def _normalize(self, raw: list) -> list[dict]:
        from services.nbp import convert_to_pln
        result = []
        for inv in raw:
            income_flag = inv.get('income')
            if isinstance(income_flag, str):
                is_income = income_flag.strip().lower() in ('1', 'true', 'yes')
            else:
                is_income = bool(income_flag)
            if is_income:
                inv_type = 'income'
            else:
                inv_type = 'expense'
            # Fakturownia dla dokumentów zakupowych (income=false) odwraca role:
            #   seller_* = nabywca (my, Arborum)
            #   buyer_*  = dostawca (wystawiający, kontrahent)
            # Dla dokumentów sprzedażowych (income=true):
            #   seller_* = wystawiający (my, Arborum)
            #   buyer_*  = odbiorca (klient)
            # W obu przypadkach kontrahent to buyer_*.
            counterparty_name = inv.get('buyer_name') or inv.get('seller_name', '')
            counterparty_nip  = inv.get('buyer_tax_no') or inv.get('seller_tax_no', '')

            currency    = (inv.get('currency') or 'PLN').strip().upper()
            issue_date  = inv.get('sell_date') or inv.get('issue_date', '')
            raw_gross   = _to_float(inv.get('price_gross') or inv.get('gross_price'))
            raw_net     = _to_float(inv.get('price_net')   or inv.get('net_price'))
            raw_vat     = _to_float(inv.get('price_tax')   or inv.get('tax_price'))

            orig_amount   = None
            exchange_rate = None
            if currency != 'PLN' and raw_gross is not None:
                orig_amount = raw_gross
                pln_gross, exchange_rate = convert_to_pln(raw_gross, currency, issue_date)
                if exchange_rate and raw_net is not None:
                    raw_net = round(raw_net * exchange_rate, 2)
                if exchange_rate and raw_vat is not None:
                    raw_vat = round(raw_vat * exchange_rate, 2)
                raw_gross = pln_gross

            result.append({
                'fakturownia_id': str(inv.get('id', '')),
                'invoice_number': inv.get('number', ''),
                'vendor_name':    counterparty_name,
                'vendor_nip':     counterparty_nip,
                'issue_date':     issue_date,
                'payment_to':     inv.get('payment_to') or '',
                'amount_gross':   raw_gross,
                'amount_net':     raw_net,
                'vat_amount':     raw_vat,
                'ksef_number':    inv.get('ksef_number') or inv.get('ksef_id') or '',
                'invoice_type':   inv_type,
                'currency':       currency,
                'orig_amount':    orig_amount,
                'exchange_rate':  exchange_rate,
                'raw_json':       json.dumps(inv, ensure_ascii=False),
            })
        return result

    def sync_to_db(self, db_conn, period_days: int = 365,
                   filter_category: str = 'expense', month: str = None) -> dict:
        """
        Synchronizuje faktury z ostatnich period_days dni, albo — jeśli podano
        month (format 'YYYY-MM') — z konkretnego miesiąca.
        filter_category: 'expense' | 'income' | 'all'
        """
        if month:
            year, mon = (int(part) for part in month.split('-'))
            period_start = date(year, mon, 1).isoformat()
            last_day = calendar.monthrange(year, mon)[1]
            period_end = date(year, mon, last_day).isoformat()
        else:
            today = date.today()
            period_start = (today - timedelta(days=period_days)).isoformat()
            period_end = today.isoformat()

        try:
            invoices = self.fetch_invoices(period_start, period_end, filter_category)
        except Exception as exc:
            add_sync_log(0, 0, 0, 'error', str(exc))
            raise

        fetched = len(invoices)
        new_count = 0
        for inv in invoices:
            try:
                if upsert_invoice(inv):
                    new_count += 1
            except Exception:
                pass

        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS cnt FROM fakturownia_invoices WHERE status='pending'"
            )
            pending = cur.fetchone()['cnt']

        add_sync_log(fetched, new_count, pending, 'ok',
                     f"Synchronizacja {period_start}–{period_end}, "
                     f"pobrano: {fetched}, nowych: {new_count}")

        return {
            'fetched': fetched,
            'new': new_count,
            'pending': pending,
            'status': 'ok',
        }


def _to_float(value) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
