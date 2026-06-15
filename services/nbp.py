"""Pobieranie kursu walut z API NBP (Narodowy Bank Polski)."""
import logging
from datetime import date, timedelta

import requests

_LOG = logging.getLogger(__name__)
_TIMEOUT = 8
_BASE = 'https://api.nbp.pl/api/exchangerates/rates/A'


def get_nbp_rate(currency: str, date_str: str) -> float | None:
    """
    Zwraca kurs średni (mid) waluty w stosunku do PLN na podaną datę.
    Jeśli NBP nie opublikowało kursu na ten dzień (weekend, święto),
    cofa się o kolejne dni (max 10) szukając ostatniego dostępnego.
    Zwraca None, gdy nie uda się pobrać kursu.
    """
    if not currency or currency.upper() == 'PLN':
        return 1.0

    curr = currency.upper()
    try:
        query_date = date.fromisoformat(date_str[:10])
    except (ValueError, TypeError):
        query_date = date.today()

    for offset in range(11):
        d = query_date - timedelta(days=offset)
        url = f'{_BASE}/{curr}/{d.isoformat()}/?format=json'
        try:
            r = requests.get(url, timeout=_TIMEOUT)
            if r.status_code == 200:
                data = r.json()
                rate = data['rates'][0]['mid']
                _LOG.info('NBP %s %s = %.4f PLN (offset %d)', curr, d, rate, offset)
                return float(rate)
            if r.status_code == 404:
                continue
            _LOG.warning('NBP API HTTP %s dla %s %s', r.status_code, curr, d)
            return None
        except Exception as exc:
            _LOG.warning('NBP API błąd dla %s %s: %s', curr, d, exc)
            return None

    _LOG.warning('NBP: brak kursu %s w okolicy %s', curr, date_str)
    return None


def convert_to_pln(amount: float, currency: str, date_str: str) -> tuple[float, float | None]:
    """
    Przelicza kwotę z waluty obcej na PLN.
    Zwraca (kwota_pln, kurs) lub (amount, None) gdy kurs niedostępny.
    """
    if not currency or currency.upper() == 'PLN':
        return amount, None
    rate = get_nbp_rate(currency, date_str)
    if rate is None:
        return amount, None
    return round(amount * rate, 2), rate
