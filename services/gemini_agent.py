"""Gemini-based intent parser dla asystenta AI: polecenie tekstowe/głosowe -> akcja w CRM."""
import json
import re

import requests

TIMEOUT = 60

_FIELD_KEYS = (
    'company_name', 'first_name', 'last_name', 'email', 'phone', 'position',
    'city', 'website', 'nip', 'source', 'description', 'deal_name', 'amount',
    'note_body',
)

_SYSTEM_PROMPT = """Jesteś asystentem AI wbudowanym w system CRM/finansowy firmy. Analizujesz
polecenie użytkownika (wypowiedziane głosowo i przepisane na tekst, albo wpisane ręcznie)
w języku polskim i zwracasz WYŁĄCZNIE jeden obiekt JSON, bez markdown, bez dodatkowego tekstu,
opisujący co użytkownik chce zrobić.

Pole "intent" — jedna z dwóch wartości:
- "note"   — użytkownik chce dodać notatkę do istniejącej firmy (klienta), kontaktu (osoby) lub interesu
- "create" — użytkownik chce dodać/utworzyć nową firmę (klienta), nowy kontakt (osobę) lub nowy interes

Pole "entity_type" — czego dotyczy polecenie:
- "company" — firma / klient
- "contact" — osoba / kontakt
- "deal"    — interes / szansa sprzedażowa

Pole "fields" — obiekt z wyekstrahowanymi danymi (zawsze zwróć klucz, pusty string "" jeśli
danej informacji nie podano):
- company_name: nazwa firmy/klienta, do której odnosi się polecenie
- first_name, last_name: imię i nazwisko osoby/kontaktu
- email, phone: dane kontaktowe
- position: stanowisko kontaktu w firmie
- city, website, nip: dodatkowe dane firmy
- source: źródło pozyskania klienta (np. "polecenie", "strona www", "targi", "LinkedIn")
- description: opis / dodatkowe uwagi do firmy, kontaktu lub interesu
- deal_name: nazwa interesu/szansy sprzedażowej
- amount: kwota interesu — sama liczba, bez waluty i spacji (np. "15000"), "" jeśli nieznana
- note_body: TYLKO gdy intent="note" — zwięzłe, konkretne podsumowanie treści notatki
  przeformułowane na 1-3 zdania (nie dosłowna transkrypcja polecenia)

Zasady:
- Jeśli polecenie mówi o zapisaniu/dodaniu notatki, uwagi, informacji o rozmowie/spotkaniu
  dla konkretnej firmy/osoby/interesu — intent="note".
- Jeśli polecenie mówi o dodaniu/utworzeniu/założeniu nowego klienta, kontaktu lub interesu —
  intent="create".
- Gdy niejednoznaczne, wybierz najbardziej prawdopodobną interpretację, nie pytaj o doprecyzowanie.
- Zwróć WYŁĄCZNIE JSON w dokładnie tym kształcie:
{"intent": "note", "entity_type": "company", "fields": {"company_name": "", "first_name": "",
"last_name": "", "email": "", "phone": "", "position": "", "city": "", "website": "", "nip": "",
"source": "", "description": "", "deal_name": "", "amount": "", "note_body": ""}}
"""


def _extract_json(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    cleaned = re.sub(r'^```(?:json)?\s*', '', text, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*```\s*$', '', cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return json.loads(match.group())
    raise ValueError(f"Nie udało się sparsować JSON z odpowiedzi modelu: {text[:300]!r}")


def parse_command(text: str, api_key: str, model: str = 'gemini-2.5-flash') -> dict:
    """Wysyła polecenie użytkownika do Gemini i zwraca ustrukturyzowaną intencję.

    Zwraca {'intent':.., 'entity_type':.., 'fields': {...}} albo {'error': <message>}.
    """
    try:
        payload = {
            'contents': [{'parts': [
                {'text': _SYSTEM_PROMPT},
                {'text': f'Polecenie użytkownika: "{text}"'},
            ]}],
            'generationConfig': {
                'temperature':      0.2,
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

        raw = ''
        for part in candidates[0].get('content', {}).get('parts', []):
            raw += part.get('text', '')

        if candidates[0].get('finishReason') == 'MAX_TOKENS':
            return {'error': 'Odpowiedź modelu została ucięta (MAX_TOKENS).'}

        parsed = _extract_json(raw)

        intent = parsed.get('intent')
        entity_type = parsed.get('entity_type')
        if intent not in ('note', 'create'):
            intent = 'note'
        if entity_type not in ('company', 'contact', 'deal'):
            entity_type = 'company'

        fields_in = parsed.get('fields') or {}
        fields = {k: str(fields_in.get(k, '') or '').strip() for k in _FIELD_KEYS}

        return {'intent': intent, 'entity_type': entity_type, 'fields': fields}

    except Exception as exc:
        return {'error': str(exc)}
