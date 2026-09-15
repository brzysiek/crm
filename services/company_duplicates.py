"""Wykrywanie prawdopodobnych duplikatów wśród firm CRM.

Firmy porównywane są parami. Żeby uniknąć porównania każdy-z-każdym (kosztowne
przy dużej liczbie firm), pary-kandydatów wyszukiwane są przez „blokowanie”:
dwie firmy trafiają do porównania tylko wtedy, gdy mają identyczny NIP, KRS,
email, telefon, domenę strony WWW albo podobną nazwę/nazwę skróconą. Dopiero
w obrębie takiej pary liczone jest właściwe prawdopodobieństwo duplikatu
(0-100) na podstawie kilku niezależnych sygnałów.
"""
import re
import unicodedata
from difflib import SequenceMatcher
from itertools import combinations

from models.crm_company import _extract_domain, get_all_companies

MIN_SCORE = 35

LEVEL_HIGH, LEVEL_MEDIUM, LEVEL_LOW = 'high', 'medium', 'low'
LEVEL_LABELS = {LEVEL_HIGH: 'Wysokie', LEVEL_MEDIUM: 'Średnie', LEVEL_LOW: 'Niskie'}


def _fold(s: str | None) -> str:
    if not s:
        return ''
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')
    return re.sub(r'\s+', ' ', s).strip().lower()


def _norm_digits(s: str | None) -> str:
    return re.sub(r'\D', '', s or '')


def _norm_phone(s: str | None) -> str:
    digits = _norm_digits(s)
    if len(digits) > 9:
        digits = digits[-9:]
    return digits


def _norm_email(s: str | None) -> str:
    return (s or '').strip().lower()


def score_pair(a: dict, b: dict) -> tuple[int, list[str]]:
    score = 0
    reasons = []

    nip_a, nip_b = _norm_digits(a.get('nip')), _norm_digits(b.get('nip'))
    if nip_a and nip_b and nip_a == nip_b:
        score += 70
        reasons.append('Ten sam NIP')

    krs_a, krs_b = _norm_digits(a.get('krs')), _norm_digits(b.get('krs'))
    if krs_a and krs_b and krs_a == krs_b:
        score += 60
        reasons.append('Ten sam KRS')

    domain_a, domain_b = _extract_domain(a.get('website')), _extract_domain(b.get('website'))
    if domain_a and domain_b and domain_a == domain_b:
        score += 40
        reasons.append('Ta sama domena strony WWW')

    email_a, email_b = _norm_email(a.get('email')), _norm_email(b.get('email'))
    if email_a and email_b and email_a == email_b:
        score += 45
        reasons.append('Ten sam adres email')

    phone_a, phone_b = _norm_phone(a.get('phone')), _norm_phone(b.get('phone'))
    if phone_a and phone_b and len(phone_a) >= 7 and phone_a == phone_b:
        score += 35
        reasons.append('Ten sam numer telefonu')

    name_a, name_b = _fold(a.get('name')), _fold(b.get('name'))
    short_a, short_b = _fold(a.get('short_name')), _fold(b.get('short_name'))

    if name_a and name_b and name_a == name_b:
        score += 45
        reasons.append('Identyczna nazwa')
    elif short_a and short_b and short_a == short_b:
        score += 35
        reasons.append('Identyczna nazwa skrócona')
    elif name_a and name_b:
        ratio = SequenceMatcher(None, name_a, name_b).ratio()
        if ratio >= 0.92:
            score += 30
            reasons.append('Bardzo podobna nazwa (literówka?)')
        elif ratio >= 0.82:
            score += 15
            reasons.append('Podobna nazwa')

    city_a, city_b = _fold(a.get('city')), _fold(b.get('city'))
    if score > 0 and city_a and city_b and city_a == city_b:
        score += 5
        reasons.append('To samo miasto')

    return min(score, 100), reasons


def score_level(score: int) -> str:
    if score >= 70:
        return LEVEL_HIGH
    if score >= 50:
        return LEVEL_MEDIUM
    return LEVEL_LOW


def _block_key(kind: str, value: str):
    return (kind, value) if value else None


def find_duplicate_pairs(min_score: int = MIN_SCORE) -> list[dict]:
    companies = get_all_companies(limit=None)
    by_id = {c['id']: c for c in companies}

    blocks: dict[tuple, set] = {}
    for c in companies:
        name_f = _fold(c.get('name'))
        short_f = _fold(c.get('short_name'))
        keys = [
            _block_key('nip', _norm_digits(c.get('nip'))),
            _block_key('krs', _norm_digits(c.get('krs'))),
            _block_key('email', _norm_email(c.get('email'))),
            _block_key('domain', _extract_domain(c.get('website'))),
            _block_key('name', name_f if len(name_f) >= 3 else ''),
            _block_key('short', short_f if len(short_f) >= 3 else ''),
        ]
        phone = _norm_phone(c.get('phone'))
        if len(phone) >= 7:
            keys.append(('phone', phone))
        for key in keys:
            if key:
                blocks.setdefault(key, set()).add(c['id'])

    candidate_pairs = set()
    for ids in blocks.values():
        if len(ids) < 2:
            continue
        for a_id, b_id in combinations(sorted(ids), 2):
            candidate_pairs.add((a_id, b_id))

    results = []
    for a_id, b_id in candidate_pairs:
        a, b = by_id[a_id], by_id[b_id]
        score, reasons = score_pair(a, b)
        if score >= min_score:
            results.append({
                'a': a, 'b': b, 'score': score,
                'level': score_level(score), 'level_label': LEVEL_LABELS[score_level(score)],
                'reasons': reasons,
            })

    results.sort(key=lambda p: -p['score'])
    return results
