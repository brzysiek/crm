"""Wykrywanie prawdopodobnych duplikatów wśród kontaktów CRM.

Kontakty porównywane są parami. Żeby uniknąć porównania każdy-z-każdym (kosztowne
przy dużej liczbie kontaktów), pary-kandydatów wyszukiwane są przez „blokowanie”:
dwa kontakty trafiają do porównania tylko wtedy, gdy mają identyczny email,
identyczny (znormalizowany) telefon, to samo nazwisko albo zamienione miejscami
imię/nazwisko. Dopiero w obrębie takiej pary liczone jest właściwe
prawdopodobieństwo duplikatu (0-100) na podstawie kilku niezależnych sygnałów.
"""
import re
import unicodedata
from difflib import SequenceMatcher
from itertools import combinations

from models.crm_contact import get_all_contacts

MIN_SCORE = 35

LEVEL_HIGH, LEVEL_MEDIUM, LEVEL_LOW = 'high', 'medium', 'low'
LEVEL_LABELS = {LEVEL_HIGH: 'Wysokie', LEVEL_MEDIUM: 'Średnie', LEVEL_LOW: 'Niskie'}


def _fold(s: str | None) -> str:
    """Usuwa polskie znaki diakrytyczne i normalizuje białe znaki/wielkość liter,
    żeby porównanie nie zależało od "ł/l", "ą/a" itp."""
    if not s:
        return ''
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')
    return re.sub(r'\s+', ' ', s).strip().lower()


def _norm_phone(s: str | None) -> str:
    digits = re.sub(r'\D', '', s or '')
    if len(digits) > 9:
        digits = digits[-9:]
    return digits


def _norm_email(s: str | None) -> str:
    return (s or '').strip().lower()


def _full_name(c: dict) -> str:
    return _fold(f"{c.get('first_name', '')} {c.get('last_name', '')}")


def score_pair(a: dict, b: dict) -> tuple[int, list[str]]:
    """Zwraca (score 0-100, lista powodów) — prawdopodobieństwo, że `a` i `b`
    to w rzeczywistości ta sama osoba wpisana dwa razy."""
    score = 0
    reasons = []

    email_a, email_b = _norm_email(a.get('email')), _norm_email(b.get('email'))
    if email_a and email_b and email_a == email_b:
        score += 60
        reasons.append('Ten sam adres email')

    phone_a, phone_b = _norm_phone(a.get('phone')), _norm_phone(b.get('phone'))
    if phone_a and phone_b and len(phone_a) >= 7 and phone_a == phone_b:
        score += 50
        reasons.append('Ten sam numer telefonu')

    first_a, last_a = _fold(a.get('first_name')), _fold(a.get('last_name'))
    first_b, last_b = _fold(b.get('first_name')), _fold(b.get('last_name'))
    name_a, name_b = _full_name(a), _full_name(b)

    if name_a and name_b:
        if name_a == name_b:
            score += 40
            reasons.append('Identyczne imię i nazwisko')
        elif first_a and last_a and first_a == last_b and last_a == first_b:
            score += 30
            reasons.append('Zamienione miejscami imię i nazwisko')
        else:
            ratio = SequenceMatcher(None, name_a, name_b).ratio()
            if ratio >= 0.92:
                score += 30
                reasons.append('Bardzo podobne imię i nazwisko (literówka?)')
            elif ratio >= 0.82:
                score += 15
                reasons.append('Podobne imię i nazwisko')

    if a.get('company_id') and a.get('company_id') == b.get('company_id'):
        score += 10
        reasons.append('Ta sama firma')

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
    """Zwraca listę kandydatów na duplikaty wśród aktywnych (niezarchiwizowanych)
    kontaktów, posortowaną od najbardziej prawdopodobnych."""
    contacts = get_all_contacts(limit=None)
    by_id = {c['id']: c for c in contacts}

    blocks: dict[tuple, set] = {}
    for c in contacts:
        first_f, last_f = _fold(c.get('first_name')), _fold(c.get('last_name'))
        keys = [
            _block_key('email', _norm_email(c.get('email'))),
            _block_key('last', last_f if len(last_f) >= 2 else ''),
        ]
        phone = _norm_phone(c.get('phone'))
        if len(phone) >= 7:
            keys.append(('phone', phone))
        if len(first_f) >= 2 and len(last_f) >= 2:
            keys.append(('swap', tuple(sorted([first_f, last_f]))))
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
