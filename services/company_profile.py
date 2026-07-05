"""Pobiera profil firmy ze strony WWW: scrapuje stronę główną (+ stronę kontaktową,
jeśli trzeba) i przepuszcza tekst przez Gemini, by wyciągnąć opis, branże i dane kontaktowe.
"""
import base64
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


MAX_FAVICON_BYTES = 512 * 1024  # ikony są małe — to bezpieczny margines


def _sniff_image_type(data: bytes) -> str | None:
    """Rozpoznaje typ obrazka po nagłówku bajtów — przydatne gdy serwer nie zwraca
    poprawnego Content-Type (częste dla /favicon.ico, np. application/octet-stream)."""
    head = data[:16]
    if head.startswith(b'\x89PNG'):
        return 'image/png'
    if head[:4] in (b'\x00\x00\x01\x00', b'\x00\x00\x02\x00'):
        return 'image/x-icon'
    if head.startswith(b'\xff\xd8'):
        return 'image/jpeg'
    if head.startswith(b'GIF87a') or head.startswith(b'GIF89a'):
        return 'image/gif'
    stripped = data.lstrip()[:5]
    if stripped.startswith(b'<?xml') or stripped.startswith(b'<svg'):
        return 'image/svg+xml'
    return None


def _download_as_data_uri(url: str) -> str | None:
    """Pobiera obrazek spod danego adresu i zwraca go jako data URI (base64) do zapisania
    w bazie — dzięki temu strona nie musi za każdym razem hotlinkować obrazka z serwera
    firmy, co bywa blokowane przez jej WAF. Zwraca None, gdy się nie uda, plik nie jest
    obrazkiem, albo jest za duży."""
    try:
        resp = requests.get(url, timeout=FAVICON_TIMEOUT, headers={'User-Agent': USER_AGENT}, stream=True)
        if resp.status_code >= 400:
            return None
        chunks = []
        total = 0
        for chunk in resp.iter_content(8192):
            total += len(chunk)
            if total > MAX_FAVICON_BYTES:
                return None
            chunks.append(chunk)
        data = b''.join(chunks)
        if not data:
            return None
        content_type = (resp.headers.get('Content-Type') or '').split(';')[0].strip().lower()
        if not content_type.startswith('image/'):
            content_type = _sniff_image_type(data)
            if not content_type:
                return None
        encoded = base64.b64encode(data).decode('ascii')
        return f'data:{content_type};base64,{encoded}'
    except Exception:
        return None


def _google_favicon_fallback(normalized: str) -> str:
    """Serwis Google pobiera ikonę ze swoich serwerów, więc omija ewentualne blokady
    (np. WAF/Wordfence blokujący zakresy IP hostingu współdzielonego) które mogą
    uniemożliwiać bezpośrednie pobranie strony z naszego serwera."""
    domain = urlparse(normalized).netloc
    return f'https://www.google.com/s2/favicons?sz=64&domain={domain}'


def get_favicon_url(url: str) -> str | None:
    """Pobiera ikonę firmy (z <link rel="icon">, albo domyślny /favicon.ico) i zwraca ją
    jako data URI (base64) do zapisania w bazie danych. Próbuje kilku wariantów adresu
    (www/bez www, http/https). Gdy bezpośrednie pobranie strony się nie powiedzie (np.
    hosting jest blokowany przez WAF docelowej strony) albo żadna znaleziona ikona się nie
    pobierze, spada na serwis Google, który pobiera ikonę z własnych serwerów.
    Nigdy nie zgłasza wyjątku."""
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

    if resp is not None:
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
            data_uri = _download_as_data_uri(candidate_url)
            if data_uri:
                return data_uri

    return _download_as_data_uri(_google_favicon_fallback(normalized))


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
