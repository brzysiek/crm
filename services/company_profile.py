"""Pobiera profil firmy ze strony WWW: scrapuje stronę główną (+ stronę kontaktową,
jeśli trzeba) i przepuszcza tekst przez Gemini, by wyciągnąć opis, branże i dane kontaktowe.
"""
import json
import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import requests

from services.text_utils import smart_title_case

TIMEOUT = 15
MAX_TEXT_CHARS = 6000
USER_AGENT = 'Mozilla/5.0 (compatible; RosliNarniaCRM/1.0)'
CONTACT_KEYWORDS = ('kontakt', 'contact')

PROFILE_PROMPT = (
    "Na podstawie poniższego tekstu ze strony internetowej firmy, zwróć WYŁĄCZNIE obiekt JSON "
    "(bez markdown, bez dodatkowego tekstu) z polami:\n"
    "- description: krótki (2-3 zdania), rzeczowy opis działalności firmy w języku polskim\n"
    "- industries: lista maksymalnie 3 branż/sektorów działalności firmy (krótkie nazwy, po polsku)\n"
    "- email: adres email kontaktowy firmy, jeśli widoczny w tekście, inaczej \"\"\n"
    "- phone: numer telefonu firmy, jeśli widoczny w tekście, inaczej \"\"\n"
    "- nip: numer NIP firmy, jeśli widoczny w tekście, inaczej \"\"\n"
    "- city: miasto siedziby firmy, jeśli widoczne, inaczej \"\"\n"
    "- street: nazwa ulicy siedziby, jeśli widoczna, inaczej \"\"\n"
    "- house_number: numer domu/budynku, jeśli widoczny, inaczej \"\"\n"
    "- flat_number: numer lokalu, jeśli widoczny, inaczej \"\"\n"
    "- postal_code: kod pocztowy w formacie 00-000, jeśli widoczny, inaczej \"\"\n\n"
    "Jeśli czegoś nie da się ustalić z tekstu, zwróć dla tego pola puste \"\" (a dla industries [])."
)


class _HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._skip_depth = 0
        self._chunks = []
        self.links = []
        self._current_href = None
        self._current_link_text = []

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript'):
            self._skip_depth += 1
        if tag == 'a':
            href = dict(attrs).get('href')
            if href:
                self._current_href = href
                self._current_link_text = []

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript') and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag == 'a' and self._current_href is not None:
            self.links.append((self._current_href, ' '.join(self._current_link_text).strip()))
            self._current_href = None
            self._current_link_text = []

    def handle_data(self, data):
        if self._skip_depth > 0:
            return
        text = data.strip()
        if text:
            self._chunks.append(text)
            if self._current_href is not None:
                self._current_link_text.append(text)

    def get_text(self) -> str:
        return ' '.join(self._chunks)


def _normalize_url(url: str) -> str:
    url = (url or '').strip()
    if not url:
        return ''
    if not re.match(r'^https?://', url, re.IGNORECASE):
        url = 'https://' + url
    return url


def _fetch_page(url: str) -> tuple[str, list]:
    resp = requests.get(url, timeout=TIMEOUT, headers={'User-Agent': USER_AGENT})
    resp.raise_for_status()
    parser = _HTMLTextExtractor()
    parser.feed(resp.text)
    return parser.get_text()[:MAX_TEXT_CHARS], parser.links


def _find_contact_url(base_url: str, links: list) -> str | None:
    base_host = urlparse(base_url).netloc
    for href, text in links:
        haystack = f"{href} {text}".lower()
        if any(kw in haystack for kw in CONTACT_KEYWORDS):
            absolute = urljoin(base_url, href)
            if urlparse(absolute).netloc == base_host:
                return absolute
    return None


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


def scrape_company_site(url: str) -> dict:
    """Pobiera tekst strony głównej i — jeśli znaleziono link — strony kontaktowej."""
    normalized = _normalize_url(url)
    if not normalized:
        return {'ok': False, 'error': 'Podaj adres strony WWW.'}
    try:
        homepage_text, links = _fetch_page(normalized)
    except Exception as e:
        return {'ok': False, 'error': f'Nie udało się pobrać strony: {e}'}

    contact_text = ''
    contact_url = _find_contact_url(normalized, links)
    if contact_url and contact_url != normalized:
        try:
            contact_text, _ = _fetch_page(contact_url)
        except Exception:
            contact_text = ''

    return {'ok': True, 'homepage_text': homepage_text, 'contact_text': contact_text}


def extract_company_profile(homepage_text: str, contact_text: str,
                             api_key: str, model: str = 'gemini-2.5-flash') -> dict:
    combined = f"=== STRONA GŁÓWNA ===\n{homepage_text}"
    if contact_text:
        combined += f"\n\n=== STRONA KONTAKTOWA ===\n{contact_text}"

    payload = {
        'contents': [{'parts': [{'text': combined + '\n\n' + PROFILE_PROMPT}]}],
        'generationConfig': {
            'temperature': 0.2,
            'maxOutputTokens': 1024,
            'responseMimeType': 'application/json',
        },
    }
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}'
    try:
        resp = requests.post(url, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        candidates = data.get('candidates', [])
        if not candidates:
            reason = (data.get('promptFeedback') or {}).get('blockReason', 'brak odpowiedzi')
            return {'ok': False, 'error': f'Gemini nie zwrócił odpowiedzi: {reason}'}
        text = ''.join(p.get('text', '') for p in candidates[0].get('content', {}).get('parts', []))
        parsed = _extract_json(text)
    except Exception as e:
        return {'ok': False, 'error': f'Błąd wywołania AI: {e}'}

    industries = parsed.get('industries') or []
    if isinstance(industries, str):
        industries = [industries]
    industries = [str(i).strip() for i in industries if str(i).strip()][:3]

    return {
        'ok': True,
        'data': {
            'description': (parsed.get('description') or '').strip(),
            'industries': industries,
            'email': (parsed.get('email') or '').strip(),
            'phone': (parsed.get('phone') or '').strip(),
            'nip': re.sub(r'\D', '', parsed.get('nip') or ''),
            'city': smart_title_case((parsed.get('city') or '').strip()),
            'street': smart_title_case((parsed.get('street') or '').strip()),
            'house_number': (parsed.get('house_number') or '').strip(),
            'flat_number': (parsed.get('flat_number') or '').strip(),
            'postal_code': (parsed.get('postal_code') or '').strip(),
        },
    }


def build_company_profile(url: str, api_key: str, model: str = 'gemini-2.5-flash') -> dict:
    if not api_key:
        return {'ok': False, 'error': 'Brak klucza API Gemini — skonfiguruj go w Ustawieniach ogólnych.'}
    scraped = scrape_company_site(url)
    if not scraped.get('ok'):
        return scraped
    return extract_company_profile(scraped['homepage_text'], scraped.get('contact_text', ''), api_key, model)
