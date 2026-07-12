"""Gemini-based parser dla szybkiego dodawania zadań GTD: tekst/głos -> zadanie."""
import json
import re

import requests

TIMEOUT = 60

_SYSTEM_PROMPT_TMPL = """Jesteś asystentem AI wbudowanym w system do zarządzania zadaniami metodą
Getting Things Done (GTD). Analizujesz krótką notatkę użytkownika (wypowiedzianą głosowo i
przepisaną na tekst, albo wpisaną ręcznie) w języku polskim i zwracasz WYŁĄCZNIE jeden obiekt
JSON, bez markdown, bez dodatkowego tekstu.

Dzisiejsza data: {today} ({weekday}).

Pola do zwrócenia:
- "title": zwięzły, konkretny tytuł zadania (przeformułowany, nie dosłowna transkrypcja, bez dat)
- "due_date": termin ostateczny w formacie YYYY-MM-DD, jeśli użytkownik podał konkretną datę lub
  względną (np. "jutro", "w piątek", "za tydzień") — przelicz względem dzisiejszej daty. Pusty
  string "" jeśli nie podano żadnego terminu.
- "is_project": true jeśli notatka opisuje coś większego, wieloetapowego (np. "zorganizować
  wyjazd", "przygotować ofertę dla klienta X") a nie pojedynczą czynność — inaczej false.

Zwróć WYŁĄCZNIE JSON w dokładnie tym kształcie:
{{"title": "", "due_date": "", "is_project": false}}
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


_WEEKDAY_PL = ('poniedziałek', 'wtorek', 'środa', 'czwartek', 'piątek', 'sobota', 'niedziela')


def parse_task_text(text: str, api_key: str, today, model: str = 'gemini-2.5-flash') -> dict:
    """Parsuje szybko wpisaną/wypowiedzianą notatkę na strukturalne zadanie.

    `today` to obiekt date użyty do przeliczenia dat względnych.
    Zwraca {'title':.., 'due_date':.., 'is_project':..} albo {'error': ..}.
    """
    try:
        prompt = _SYSTEM_PROMPT_TMPL.format(
            today=today.isoformat(), weekday=_WEEKDAY_PL[today.weekday()]
        )
        payload = {
            'contents': [{'parts': [
                {'text': prompt},
                {'text': f'Notatka użytkownika: "{text}"'},
            ]}],
            'generationConfig': {
                'temperature':      0.2,
                'maxOutputTokens':  1024,
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

        title = str(parsed.get('title') or '').strip() or text.strip()
        due_date = str(parsed.get('due_date') or '').strip()
        if due_date and not re.match(r'^\d{4}-\d{2}-\d{2}$', due_date):
            due_date = ''
        is_project = bool(parsed.get('is_project'))

        return {'title': title, 'due_date': due_date, 'is_project': is_project}

    except Exception as exc:
        return {'error': str(exc)}
