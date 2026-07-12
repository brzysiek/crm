"""Gemini OCR service — extracts invoice data from PDF bytes."""
import base64
import json
import re

import requests

TIMEOUT = 90

SYSTEM_PROMPT = (
    "You are an invoice data extraction assistant. "
    "Extract the following fields from the invoice PDF and return ONLY a valid JSON object "
    "with no additional text, no markdown, no code fences:\n"
    "- invoice_number: invoice/document number\n"
    "- vendor_name: name of the vendor/seller (the company that issued the invoice)\n"
    "- vendor_nip: tax ID (NIP) of the vendor\n"
    "- issue_date: issue date in YYYY-MM-DD format\n"
    "- payment_to: payment due date in YYYY-MM-DD format\n"
    "- currency: currency code of the invoice (e.g. PLN, EUR, USD, GBP); default PLN if not stated\n"
    "- amount_gross: total gross amount in the invoice currency (plain number, no currency symbols)\n"
    "- amount_net: total net amount in the invoice currency (plain number)\n"
    "- vat_amount: total VAT amount in the invoice currency (plain number)\n"
    "- invoice_type: \"expense\" if this is a purchase/cost invoice, "
    "\"income\" if it is a sales invoice\n"
    "- confidence_note: brief note about extraction confidence or any ambiguities\n\n"
    "Return empty string \"\" for fields you cannot determine. "
    "Numbers must be plain floats (e.g. 123.45), never strings."
)


def _extract_json(text: str) -> dict:
    """Try multiple strategies to extract a JSON object from model output."""
    text = text.strip()

    # Strategy 1: direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 2: strip markdown code fences (```json ... ``` or ``` ... ```)
    cleaned = re.sub(r'^```(?:json)?\s*', '', text, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*```\s*$', '', cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Strategy 3: extract first {...} block
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Nie udało się sparsować JSON z odpowiedzi modelu: {text[:300]!r}")


def ocr_invoice_pdf(pdf_bytes: bytes, api_key: str,
                    model: str = 'gemini-2.5-flash') -> dict:
    """Call Gemini to extract invoice data from a PDF.

    Returns a dict with keys: invoice_number, vendor_name, vendor_nip,
    issue_date, amount_gross, amount_net, vat_amount, invoice_type, confidence_note.
    On failure returns {'error': <message>}.
    """
    try:
        pdf_b64 = base64.b64encode(pdf_bytes).decode('utf-8')

        payload = {
            'contents': [
                {
                    'parts': [
                        {
                            'inline_data': {
                                'mime_type': 'application/pdf',
                                'data':      pdf_b64,
                            }
                        },
                        {'text': SYSTEM_PROMPT},
                    ]
                }
            ],
            'generationConfig': {
                'temperature':      0.1,
                'maxOutputTokens':  8192,
                'responseMimeType': 'application/json',
            },
        }

        url = (
            'https://generativelanguage.googleapis.com/v1beta/'
            f'models/{model}:generateContent?key={api_key}'
        )
        resp = requests.post(url, json=payload, timeout=TIMEOUT)
        resp.raise_for_status()

        data = resp.json()
        candidates = data.get('candidates', [])
        if not candidates:
            finish = data.get('promptFeedback', {}).get('blockReason', 'brak kandydatów')
            return {'error': f'Gemini nie zwrócił odpowiedzi: {finish}'}

        text = ''
        parts = candidates[0].get('content', {}).get('parts', [])
        for part in parts:
            text += part.get('text', '')

        finish_reason = candidates[0].get('finishReason', '')
        if finish_reason == 'MAX_TOKENS':
            return {'error': 'Odpowiedź modelu została ucięta (MAX_TOKENS). Wybierz model z większym limitem tokenów lub skontaktuj się z administratorem.'}

        parsed = _extract_json(text)

        # Normalise numeric fields
        for field in ('amount_gross', 'amount_net', 'vat_amount'):
            val = parsed.get(field)
            if val is not None and val != '':
                try:
                    parsed[field] = float(str(val).replace(',', '.').replace(' ', '').replace('\xa0', ''))
                except (ValueError, TypeError):
                    parsed[field] = None
            else:
                parsed[field] = None

        # Ensure invoice_type is valid
        if parsed.get('invoice_type') not in ('expense', 'income'):
            parsed['invoice_type'] = 'expense'

        return parsed

    except Exception as exc:
        return {'error': str(exc)}


CARD_SYSTEM_PROMPT = (
    "Poniżej znajduje się zdjęcie (lub dwa zdjęcia — przód i tył) wizytówki biznesowej. "
    "Wyciągnij z niej dane firmy oraz osoby kontaktowej i zwróć WYŁĄCZNIE obiekt JSON "
    "(bez markdown, bez dodatkowego tekstu) z polami:\n"
    "- company_name: nazwa firmy widoczna na wizytówce\n"
    "- company_nip: NIP firmy (same cyfry), jeśli widoczny\n"
    "- company_krs: numer KRS, jeśli widoczny\n"
    "- company_website: adres strony WWW firmy, jeśli widoczny\n"
    "- company_email: ogólny/firmowy adres email (np. biuro@, kontakt@), jeśli widoczny i inny niż email osoby\n"
    "- company_phone: firmowy numer telefonu (stacjonarny/centrala), jeśli widoczny i inny niż telefon osoby\n"
    "- company_street: nazwa ulicy siedziby firmy, jeśli widoczna\n"
    "- company_house_number: numer domu/budynku, jeśli widoczny\n"
    "- company_flat_number: numer lokalu, jeśli widoczny\n"
    "- company_postal_code: kod pocztowy w formacie 00-000, jeśli widoczny\n"
    "- company_city: miasto siedziby firmy, jeśli widoczne\n"
    "- first_name: imię osoby kontaktowej, jeśli widoczne\n"
    "- last_name: nazwisko osoby kontaktowej, jeśli widoczne\n"
    "- position: stanowisko osoby kontaktowej, jeśli widoczne\n"
    "- contact_email: bezpośredni, imienny adres email osoby, jeśli widoczny\n"
    "- contact_phone: bezpośredni/komórkowy numer telefonu osoby, jeśli widoczny\n"
    "- confidence_note: krótka uwaga o pewności odczytu lub niejasnościach\n\n"
    "Jeśli podano dwa zdjęcia, potraktuj je jako przód i tył tej samej wizytówki i połącz "
    "informacje z obu stron w jeden komplet danych. Dla pól, których nie da się ustalić, "
    "zwróć pusty string \"\"."
)


TEXT_SYSTEM_PROMPT = (
    "Poniżej znajduje się tekst stopki z wiadomości email (podpis pod mailem). "
    "Wyciągnij z niej dane firmy oraz osoby kontaktowej i zwróć WYŁĄCZNIE obiekt JSON "
    "(bez markdown, bez dodatkowego tekstu) z polami:\n"
    "- company_name: nazwa firmy widoczna w stopce\n"
    "- company_nip: NIP firmy (same cyfry), jeśli widoczny\n"
    "- company_krs: numer KRS, jeśli widoczny\n"
    "- company_website: adres strony WWW firmy, jeśli widoczny\n"
    "- company_email: ogólny/firmowy adres email (np. biuro@, kontakt@), jeśli widoczny i inny niż email osoby\n"
    "- company_phone: firmowy numer telefonu (stacjonarny/centrala), jeśli widoczny i inny niż telefon osoby\n"
    "- company_street: nazwa ulicy siedziby firmy, jeśli widoczna\n"
    "- company_house_number: numer domu/budynku, jeśli widoczny\n"
    "- company_flat_number: numer lokalu, jeśli widoczny\n"
    "- company_postal_code: kod pocztowy w formacie 00-000, jeśli widoczny\n"
    "- company_city: miasto siedziby firmy, jeśli widoczne\n"
    "- first_name: imię osoby kontaktowej (autora maila), jeśli widoczne\n"
    "- last_name: nazwisko osoby kontaktowej, jeśli widoczne\n"
    "- position: stanowisko osoby kontaktowej, jeśli widoczne\n"
    "- contact_email: bezpośredni, imienny adres email osoby, jeśli widoczny\n"
    "- contact_phone: bezpośredni/komórkowy numer telefonu osoby, jeśli widoczny\n"
    "- confidence_note: krótka uwaga o pewności odczytu lub niejasnościach\n\n"
    "Dla pól, których nie da się ustalić, zwróć pusty string \"\"."
)


def _run_card_extraction(parts: list, api_key: str, model: str) -> dict:
    """Wspólna logika wywołania Gemini dla ekstrakcji danych wizytówki/stopki maila
    (`parts` to gotowa lista części żądania — obrazy i/lub tekst z promptem)."""
    try:
        payload = {
            'contents': [{'parts': parts}],
            'generationConfig': {
                'temperature':      0.1,
                'maxOutputTokens':  4096,
                'responseMimeType': 'application/json',
            },
        }

        url = (
            'https://generativelanguage.googleapis.com/v1beta/'
            f'models/{model}:generateContent?key={api_key}'
        )
        resp = requests.post(url, json=payload, timeout=TIMEOUT)
        resp.raise_for_status()

        data = resp.json()
        candidates = data.get('candidates', [])
        if not candidates:
            finish = data.get('promptFeedback', {}).get('blockReason', 'brak kandydatów')
            return {'error': f'Gemini nie zwrócił odpowiedzi: {finish}'}

        text = ''
        parts_out = candidates[0].get('content', {}).get('parts', [])
        for part in parts_out:
            text += part.get('text', '')

        finish_reason = candidates[0].get('finishReason', '')
        if finish_reason == 'MAX_TOKENS':
            return {'error': 'Odpowiedź modelu została ucięta (MAX_TOKENS).'}

        parsed = _extract_json(text)
        parsed['company_nip'] = re.sub(r'\D', '', parsed.get('company_nip') or '')
        parsed['company_krs'] = re.sub(r'\D', '', parsed.get('company_krs') or '')
        return parsed

    except Exception as exc:
        return {'error': str(exc)}


def ocr_business_card(images: list[tuple[bytes, str]], api_key: str,
                       model: str = 'gemini-2.5-flash') -> dict:
    """Odczytuje dane firmy i kontaktu ze zdjęć wizytówki (1-2 zdjęcia: przód, opcjonalnie tył).

    `images` to lista (bytes, mime_type). Zwraca słownik z polami opisanymi w CARD_SYSTEM_PROMPT,
    albo {'error': <komunikat>} przy niepowodzeniu.
    """
    parts = [
        {'inline_data': {'mime_type': mime, 'data': base64.b64encode(img).decode('utf-8')}}
        for img, mime in images
    ]
    parts.append({'text': CARD_SYSTEM_PROMPT})
    return _run_card_extraction(parts, api_key, model)


def extract_business_card_text(text: str, api_key: str, model: str = 'gemini-2.5-flash') -> dict:
    """Wyciąga dane firmy i kontaktu z wklejonego tekstu stopki maila.

    Zwraca słownik z polami opisanymi w TEXT_SYSTEM_PROMPT, albo {'error': <komunikat>}.
    """
    parts = [{'text': f'{TEXT_SYSTEM_PROMPT}\n\n=== TEKST STOPKI ===\n{text}'}]
    return _run_card_extraction(parts, api_key, model)


def transcribe_audio(audio_bytes: bytes, mime_type: str, api_key: str,
                     model: str = 'gemini-2.5-flash') -> dict:
    """Transkrybuje nagranie głosowe (notatka CRM) na tekst po polsku.

    Zwraca {'text': <transkrypt>} albo {'error': <komunikat>}.
    """
    try:
        audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')

        payload = {
            'contents': [
                {
                    'parts': [
                        {
                            'inline_data': {
                                'mime_type': mime_type,
                                'data':      audio_b64,
                            }
                        },
                        {'text': (
                            'Przepisz to nagranie głosowe na tekst w języku polskim. '
                            'Zwróć wyłącznie sam transkrypt, bez dodatkowych komentarzy, '
                            'znaczników czasu ani cudzysłowów.'
                        )},
                    ]
                }
            ],
            'generationConfig': {
                'temperature':     0.1,
                'maxOutputTokens': 8192,
            },
        }

        url = (
            'https://generativelanguage.googleapis.com/v1beta/'
            f'models/{model}:generateContent?key={api_key}'
        )
        resp = requests.post(url, json=payload, timeout=TIMEOUT)
        resp.raise_for_status()

        data = resp.json()
        candidates = data.get('candidates', [])
        if not candidates:
            finish = data.get('promptFeedback', {}).get('blockReason', 'brak kandydatów')
            return {'error': f'Gemini nie zwrócił odpowiedzi: {finish}'}

        text = ''
        parts = candidates[0].get('content', {}).get('parts', [])
        for part in parts:
            text += part.get('text', '')

        finish_reason = candidates[0].get('finishReason', '')
        if finish_reason == 'MAX_TOKENS':
            return {'error': 'Odpowiedź modelu została ucięta (MAX_TOKENS).'}

        text = text.strip()
        if not text:
            return {'error': 'Model nie zwrócił żadnego tekstu.'}

        return {'text': text}

    except Exception as exc:
        return {'error': str(exc)}
