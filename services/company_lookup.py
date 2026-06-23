import re
from datetime import date

import requests

from services.text_utils import smart_title_case

MF_WHITELIST_URL = 'https://wl-api.mf.gov.pl/api/search/nip/{nip}'
KRS_URL = 'https://api-krs.ms.gov.pl/api/krs/OdpisAktualny/{krs}'


def _parse_address(addr: str) -> dict:
    """Parsuje adres w formacie 'ULICA NUMER, KOD MIEJSCOWOŚĆ' (jak w wykazie podatników VAT MF)."""
    result = {'street': '', 'house_number': '', 'flat_number': '', 'postal_code': '', 'city': ''}
    if not addr:
        return result

    parts = [p.strip() for p in addr.split(',')]
    street_part = parts[0] if parts else ''
    city_part = parts[1] if len(parts) > 1 else ''

    m = re.match(r'^(.*?)\s+([\d]+[A-Za-z]?(?:/\d+[A-Za-z]?)?)$', street_part)
    if m:
        result['street'] = m.group(1).strip()
        num = m.group(2)
        if '/' in num:
            house, flat = num.split('/', 1)
            result['house_number'] = house
            result['flat_number'] = flat
        else:
            result['house_number'] = num
    else:
        result['street'] = street_part

    m2 = re.search(r'(\d{2}-\d{3})', city_part)
    if m2:
        result['postal_code'] = m2.group(1)
        result['city'] = city_part.replace(m2.group(1), '').strip()
    else:
        result['city'] = city_part

    result['street'] = smart_title_case(result['street'])
    result['city'] = smart_title_case(result['city'])
    return result


def lookup_by_nip(nip: str) -> dict:
    """Pobiera dane firmy z Wykazu podatników VAT (Ministerstwo Finansów) — bez klucza API."""
    digits = re.sub(r'\D', '', nip or '')
    if not digits:
        return {'ok': False, 'error': 'Podaj NIP.'}

    url = MF_WHITELIST_URL.format(nip=digits)
    try:
        resp = requests.get(url, params={'date': date.today().isoformat()}, timeout=10)
        resp.raise_for_status()
        payload = resp.json()
    except Exception as e:
        return {'ok': False, 'error': f'Błąd połączenia z wykazem MF: {e}'}

    subject = (payload.get('result') or {}).get('subject')
    if not subject:
        return {'ok': False, 'error': 'Nie znaleziono firmy o podanym NIP w wykazie podatników VAT.'}

    addr = _parse_address(subject.get('workingAddress') or subject.get('residenceAddress') or '')
    return {
        'ok': True,
        'data': {
            'name': smart_title_case(subject.get('name') or ''),
            'nip': subject.get('nip') or digits,
            'krs': subject.get('krs') or '',
            'regon': subject.get('regon') or '',
            'country': 'Polska',
            **addr,
        },
    }


def lookup_by_krs(krs: str) -> dict:
    """Pobiera dane firmy z Krajowego Rejestru Sądowego (Ministerstwo Sprawiedliwości) — bez klucza API."""
    digits = re.sub(r'\D', '', krs or '')
    if not digits:
        return {'ok': False, 'error': 'Podaj numer KRS.'}
    digits = digits.zfill(10)

    url = KRS_URL.format(krs=digits)
    try:
        resp = requests.get(url, params={'rejestr': 'P', 'format': 'json'}, timeout=10)
        if resp.status_code == 404:
            return {'ok': False, 'error': 'Nie znaleziono firmy o podanym numerze KRS.'}
        resp.raise_for_status()
        payload = resp.json()
    except Exception as e:
        return {'ok': False, 'error': f'Błąd połączenia z rejestrem KRS: {e}'}

    dzial1 = (((payload.get('odpis') or {}).get('dane') or {}).get('dzial1')) or {}
    dane_podmiotu = dzial1.get('danePodmiotu') or {}
    identyfikatory = dane_podmiotu.get('identyfikatory') or {}
    adres = ((dzial1.get('siedzibaIAdres') or {}).get('adres')) or {}

    name = dane_podmiotu.get('nazwa') or ''
    if not name:
        return {'ok': False, 'error': 'Nie udało się odczytać danych z odpowiedzi KRS.'}

    return {
        'ok': True,
        'data': {
            'name': smart_title_case(name),
            'nip': identyfikatory.get('nip') or '',
            'krs': digits,
            'regon': identyfikatory.get('regon') or '',
            'country': smart_title_case(adres.get('kraj') or 'Polska'),
            'city': smart_title_case(adres.get('miejscowosc') or ''),
            'street': smart_title_case(adres.get('ulica') or ''),
            'house_number': adres.get('nrDomu') or '',
            'flat_number': adres.get('nrLokalu') or '',
            'postal_code': adres.get('kodPocztowy') or '',
        },
    }
