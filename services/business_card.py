"""Orchestruje przetwarzanie zeskanowanej wizytówki: OCR obu stron -> enrichment
(strona WWW i/lub NIP) -> dopasowanie/dodanie firmy i kontaktu -> zapis zdjęć na Drive."""
import difflib
import re
import time

from models.crm_company import create_company, derive_short_name, get_company_by_nip, search_companies
from models.crm_contact import create_contact, search_contacts
from models.crm_file import ALLOWED_EXTENSIONS, add_file
from services.company_lookup import lookup_by_nip
from services.company_profile import build_company_profile
from services.gdrive import GoogleDriveClient
from services.gemini_ocr import extract_business_card_text, ocr_business_card

_MATCH_THRESHOLD = 0.55
_PUBLIC_EMAIL_DOMAINS = {
    'gmail.com', 'wp.pl', 'o2.pl', 'onet.pl', 'onet.eu', 'interia.pl', 'interia.eu',
    'yahoo.com', 'hotmail.com', 'outlook.com', 'icloud.com', 'poczta.fm', 'tlen.pl',
}
_MIME_TO_EXT = {v: k for k, v in ALLOWED_EXTENSIONS.items() if k in ('jpg', 'png', 'heic')}


def _best_match(hint: str, candidates: list[dict], label_fn):
    if not hint or not candidates:
        return None
    hint_norm = hint.strip().lower()
    if not hint_norm:
        return None
    best, best_score = None, 0.0
    for c in candidates:
        label = label_fn(c).strip().lower()
        if not label:
            continue
        score = difflib.SequenceMatcher(None, hint_norm, label).ratio()
        if label == hint_norm:
            score = 1.0
        elif label.startswith(hint_norm) or hint_norm.startswith(label):
            score = max(score, 0.85)
        if score > best_score:
            best, best_score = c, score
    return best if best is not None and best_score >= _MATCH_THRESHOLD else None


def _company_label(c):
    return c.get('short_name') or c.get('name') or ''


def _contact_label(c):
    return f"{c.get('first_name', '')} {c.get('last_name', '')}".strip()


def _website_from_email(email: str) -> str:
    email = (email or '').strip().lower()
    if '@' not in email:
        return ''
    domain = email.rsplit('@', 1)[-1].strip()
    if not domain or domain in _PUBLIC_EMAIL_DOMAINS:
        return ''
    return domain


def _first(*values) -> str:
    for v in values:
        v = (v or '').strip()
        if v:
            return v
    return ''


def process_business_card(front: tuple[bytes, str] | None, back: tuple[bytes, str] | None,
                           api_key: str, model: str, drive_api_token: str, drive_root_id: str,
                           user_id: int | None) -> dict:
    """Przetwarza zdjęcia wizytówki (przód i/lub tył, każde jako (bytes, mime_type)):
    OCR -> enrichment (WWW / NIP) -> dopasowanie lub utworzenie firmy i kontaktu ->
    zapis zdjęć w Google Drive. Zwraca słownik wyniku albo {'ok': False, 'error': ...}."""
    if not api_key:
        return {'ok': False, 'error': 'Brak klucza API Gemini — skonfiguruj go w Ustawieniach ogólnych.'}

    images = [img for img in (front, back) if img is not None]
    if not images:
        return {'ok': False, 'error': 'Nie przesłano żadnego zdjęcia wizytówki.'}

    ocr = ocr_business_card(images, api_key, model)
    if ocr.get('error'):
        return {'ok': False, 'error': f'Błąd OCR wizytówki: {ocr["error"]}'}

    uploads = []
    if back:
        uploads.append((*back, 'tyl'))
    if front:
        uploads.append((*front, 'przod'))

    return _process_extracted(ocr, api_key, model, drive_api_token, drive_root_id, user_id, uploads)


def process_business_card_from_text(text: str, api_key: str, model: str, drive_api_token: str,
                                     drive_root_id: str, user_id: int | None) -> dict:
    """Przetwarza wklejony tekst stopki maila: ekstrakcja danych -> enrichment (WWW / NIP) ->
    dopasowanie lub utworzenie firmy i kontaktu. Zwraca słownik wyniku albo {'ok': False, 'error': ...}."""
    if not api_key:
        return {'ok': False, 'error': 'Brak klucza API Gemini — skonfiguruj go w Ustawieniach ogólnych.'}

    text = (text or '').strip()
    if not text:
        return {'ok': False, 'error': 'Wklej tekst stopki maila.'}

    extracted = extract_business_card_text(text, api_key, model)
    if extracted.get('error'):
        return {'ok': False, 'error': f'Błąd odczytu stopki maila: {extracted["error"]}'}

    return _process_extracted(extracted, api_key, model, drive_api_token, drive_root_id, user_id, [])


def _process_extracted(extracted: dict, api_key: str, model: str, drive_api_token: str, drive_root_id: str,
                        user_id: int | None, uploads: list[tuple[bytes, str, str]]) -> dict:
    """Wspólna logika po uzyskaniu wyekstrahowanych danych (z OCR wizytówki lub z tekstu stopki maila):
    enrichment (WWW / NIP) -> dopasowanie lub utworzenie firmy i kontaktu -> zapis plików (jeśli podano)."""
    ocr = extracted
    company_name_card = (ocr.get('company_name') or '').strip()
    if not company_name_card:
        return {'ok': False, 'error': 'Nie udało się odczytać nazwy firmy.'}

    nip = re.sub(r'\D', '', ocr.get('company_nip') or '')
    website = _first(ocr.get('company_website'),
                      _website_from_email(ocr.get('company_email')),
                      _website_from_email(ocr.get('contact_email')))

    lookup_data = {}
    if nip:
        lookup_result = lookup_by_nip(nip)
        if lookup_result.get('ok'):
            lookup_data = lookup_result['data']

    profile_data = {}
    if website:
        profile_result = build_company_profile(website, api_key, model)
        if profile_result.get('ok'):
            profile_data = profile_result['data']

    final_name = lookup_data.get('name') or company_name_card
    final_short_name = company_name_card if lookup_data.get('name') else derive_short_name(final_name)

    company_data = {
        'name': final_name,
        'short_name': final_short_name,
        'relation_type': 'lead',
        'country': lookup_data.get('country') or 'Polska',
        'city': _first(ocr.get('company_city'), lookup_data.get('city'), profile_data.get('city')),
        'street': _first(ocr.get('company_street'), lookup_data.get('street'), profile_data.get('street')),
        'house_number': _first(ocr.get('company_house_number'), lookup_data.get('house_number'),
                                profile_data.get('house_number')),
        'flat_number': _first(ocr.get('company_flat_number'), lookup_data.get('flat_number'),
                               profile_data.get('flat_number')),
        'postal_code': _first(ocr.get('company_postal_code'), lookup_data.get('postal_code'),
                               profile_data.get('postal_code')),
        'email': _first(ocr.get('company_email'), profile_data.get('email')),
        'phone': _first(ocr.get('company_phone'), profile_data.get('phone')),
        'website': website,
        'nip': _first(nip, lookup_data.get('nip'), profile_data.get('nip')),
        'krs': _first(ocr.get('company_krs'), lookup_data.get('krs')),
        'description': profile_data.get('description') or None,
    }
    industries = profile_data.get('industries') or []

    company_created = False
    company = None
    if company_data['nip']:
        company = get_company_by_nip(company_data['nip'])
    if not company:
        hint = final_short_name or final_name
        company = _best_match(hint, search_companies(hint, limit=8), _company_label)
    if company:
        company_id = company['id']
        company_display_name = _company_label(company) or final_name
    else:
        company_id = create_company(company_data, user_id, tags=[], industries=industries)
        company_created = True
        company_display_name = final_short_name or final_name

    first_name = (ocr.get('first_name') or '').strip()
    last_name = (ocr.get('last_name') or '').strip()
    contact_created = False
    contact_id = None
    contact_display_name = None
    if first_name and last_name:
        hint = f'{first_name} {last_name}'.strip()
        contact_match = _best_match(hint, search_contacts(hint, company_id=company_id, limit=8), _contact_label)
        if contact_match:
            contact_id = contact_match['id']
            contact_display_name = _contact_label(contact_match)
        else:
            contact_data = {
                'company_id': company_id,
                'first_name': first_name,
                'last_name': last_name,
                'position': (ocr.get('position') or '').strip() or None,
                'email': _first(ocr.get('contact_email'), ocr.get('company_email')) or None,
                'phone': _first(ocr.get('contact_phone'), ocr.get('company_phone')) or None,
            }
            contact_id = create_contact(contact_data, user_id)
            contact_created = True
            contact_display_name = hint

    warning = None
    if uploads:
        if drive_api_token and drive_root_id:
            try:
                client = GoogleDriveClient(drive_api_token, drive_root_id)
                crm_folder_id = client.find_or_create_folder('CRM', drive_root_id)
                company_folder_id = client.find_or_create_folder(company_display_name, crm_folder_id)
                cards_folder_id = client.find_or_create_folder('wizytówki', company_folder_id)
                stamp = time.strftime('%Y%m%d_%H%M%S')
                for side_bytes, side_mime, side_label in uploads:
                    ext = _MIME_TO_EXT.get(side_mime, 'jpg')
                    file_name = f'wizytowka_{stamp}_{side_label}.{ext}'
                    result = client.upload_file(file_name, side_mime, side_bytes, cards_folder_id)
                    add_file(company_id, contact_id, file_name, result['id'], side_mime, len(side_bytes),
                             user_id, category='business_card')
            except Exception as e:
                warning = f'Firma/kontakt zapisane, ale nie udało się zapisać zdjęć wizytówki w Google Drive: {e}'
        else:
            warning = 'Firma/kontakt zapisane, ale zdjęcia wizytówki nie zostały zapisane — skonfiguruj Google Drive w Ustawieniach.'

    return {
        'ok': True,
        'company_id': company_id,
        'company_name': company_display_name,
        'company_created': company_created,
        'contact_id': contact_id,
        'contact_name': contact_display_name,
        'contact_created': contact_created,
        'warning': warning,
    }
