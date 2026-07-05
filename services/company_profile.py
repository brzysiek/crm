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
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    raise ValueError(f"Nie udało się sparsować JSON z odpowiedzi modelu (długość {len(text)} znaków): {text!r}")


FAVICON_TIMEOUT = 10
_ICON_RELS = ('icon', 'apple-touch-icon', 'apple-touch-icon-precomposed', 'mask-icon')


def _icon_area(sizes_attr: str) -> int:
    """Szacuje 'jakość' ikony na podstawie atrybutu sizes (np. '32x32', '16x16 180x180', 'any')."""
    sizes_attr = (sizes_attr or '').strip().lower()
    if not sizes_attr:
        return 16 * 16
    if sizes_attr == 'any':
        return 1_000_000
    best = 0
    for part in sizes_attr.split():
        match = re.match(r'(\d+)x(\d+)', part)
        if match:
            best = max(best, int(match.group(1)) * int(match.group(2)))
    return best or 16 * 16


class _FaviconLinkExtractor(HTMLParser):
    """Zbiera wszystkie <link rel="icon"/apple-touch-icon/...>, dopuszczając rel
    złożony z kilku tokenów (np. rel="shortcut icon")."""

    def __init__(self):
        super().__init__()
        self.icons = []  # [(href, area), ...]

    def handle_starttag(self, tag, attrs):
        if tag != 'link':
            return
        attrs_dict = {k.lower(): (v or '') for k, v in attrs}
        rel_tokens = attrs_dict.get('rel', '').lower().split()
        href = attrs_dict.get('href')
        if not href or not any(t in _ICON_RELS for t in rel_tokens):
            return
        self.icons.append((href, _icon_area(attrs_dict.get('sizes', ''))))

    def best_icon(self) -> str | None:
        if not self.icons:
            return None
        return max(self.icons, key=lambda pair: pair[1])[0]


def _url_variants(normalized: str) -> list[str]:
    """Zwraca warianty adresu do wypróbowania: oryginalny, z/bez 'www.' i alternatywny schemat,
    na wypadek gdyby strona blokowała/przekierowywała jeden z wariantów."""
    variants = [normalized]
    parsed = urlparse(normalized)
    host = parsed.netloc
    alt_host = host[4:] if host.startswith('www.') else 'www.' + host
    variants.append(parsed._replace(netloc=alt_host).geturl())
    for v in list(variants):
        alt_scheme = 'http' if parsed.scheme == 'https' else 'https'
        variants.append(urlparse(v)._replace(scheme=alt_scheme).geturl())
    seen = set()
    ordered = []
    for v in variants:
        if v not in seen:
            seen.add(v)
            ordered.append(v)
    return ordered


def _get_with_retry(url: str, attempts: int = 2):
    last_exc = None
    for _ in range(attempts):
        try:
            resp = requests.get(url, timeout=FAVICON_TIMEOUT, headers={'User-Agent': USER_AGENT})
            resp.raise_for_status()
            return resp
        except Exception as e:
            last_exc = e
    raise last_exc


def _is_reachable(url: str) -> bool:
    try:
        resp = requests.head(url, timeout=FAVICON_TIMEOUT, headers={'User-Agent': USER_AGENT}, allow_redirects=True)
        if resp.status_code < 400:
            return True
        # Niektóre serwery nie obsługują HEAD poprawnie (405/501) — spróbuj GET.
        resp = requests.get(url, timeout=FAVICON_TIMEOUT, headers={'User-Agent': USER_AGENT}, stream=True)
        resp.close()
        return resp.status_code < 400
    except Exception:
        return False


def get_favicon_url(url: str) -> str | None:
    """Zwraca adres URL favicony strony (z <link rel="icon">, albo domyślny /favicon.ico).
    Próbuje kilku wariantów adresu (www/bez www, http/https) i weryfikuje, że znaleziona
    ikona faktycznie się ładuje, zanim ją zwróci. Nigdy nie zgłasza wyjątku — gdy strona
    jest nieosiągalna, zwraca None."""
    normalized = _normalize_url(url)
    if not normalized:
        return None

    resp = None
    base_url = normalized
    for candidate in _url_variants(normalized):
        try:
            resp = _get_with_retry(candidate)
            base_url = candidate
            break
        except Exception:
            continue
    if resp is None:
        return None

    candidates = []
    try:
        parser = _FaviconLinkExtractor()
        parser.feed(resp.text)
        best = parser.best_icon()
        if best:
            candidates.append(urljoin(resp.url or base_url, best))
    except Exception:
        pass
    candidates.append(urljoin(resp.url or base_url, '/favicon.ico'))

    for candidate_url in candidates:
        if _is_reachable(candidate_url):
            return candidate_url
    return None


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
            'maxOutputTokens': 2048,
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
