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
    "- amount_gross: total gross amount (plain number, no currency symbols)\n"
    "- amount_net: total net amount (plain number)\n"
    "- vat_amount: total VAT amount (plain number)\n"
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
                'maxOutputTokens':  2048,
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
