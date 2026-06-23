import re

_LOWERCASE_CONNECTORS = {'i', 'w', 'z', 'na', 'do', 'dla', 'u', 'o', 'a', 'ze', 'we', 'pod', 'nad'}


def smart_title_case(value: str) -> str:
    """Zamienia tekst pisany WIELKIMI LITERAMI (typowe dla rejestrów GUS/MF/KRS) na naturalny zapis,
    np. 'ORLEN SPÓŁKA AKCYJNA' -> 'Orlen Spółka Akcyjna'."""
    if not value:
        return value
    words = value.title().split(' ')
    return ' '.join(
        w.lower() if i > 0 and w.lower() in _LOWERCASE_CONNECTORS else w
        for i, w in enumerate(words)
    )


def format_phone(raw: str, default_country_code: str = '48') -> str:
    """Normalizuje numer telefonu do formatu '(+xx) xxx xxx xxx'.

    Zakłada krajowy numer 9-cyfrowy (jak w Polsce) — nadwyżkowe cyfry na początku
    traktowane są jako kod kraju. Działa idempotentnie (już sformatowany numer
    przepuszczony przez funkcję ponownie da ten sam wynik).
    """
    if not raw or not raw.strip():
        return raw
    digits = re.sub(r'\D', '', raw)
    if not digits:
        return raw.strip()

    if digits.startswith('00'):
        digits = digits[2:]

    if len(digits) > 9:
        country, national = digits[:-9], digits[-9:]
    else:
        country, national = default_country_code, digits

    groups = [national[i:i + 3] for i in range(0, len(national), 3) if national[i:i + 3]]
    return f"(+{country}) {' '.join(groups)}"
