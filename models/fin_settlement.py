"""Rozliczenia dokumentów bez przelewu.

Jeden wiersz na dokument: świadoma decyzja człowieka, że zapłata nie przeszła
przez żaden wgrany wyciąg. To lustrzane odbicie `ignored` na operacjach
bankowych — tam „ta operacja nie ma dokumentu”, tu „ten dokument nie ma operacji”.
"""
from database import get_db

REASONS = {
    'cash': 'gotówka',
    'private': 'karta lub konto prywatne',
    'offset': 'kompensata',
    'other_account': 'konto spoza wyciągów',
    'no_payment': 'nie wymaga zapłaty',
    'other': 'inne',
}


def get(fakturownia_id: int) -> dict | None:
    with get_db().cursor() as cur:
        cur.execute("SELECT * FROM fin_settlements WHERE fakturownia_id = %s", (int(fakturownia_id),))
        row = cur.fetchone()
    return dict(row) if row else None


def save(fakturownia_id: int, reason: str, settled_date, note: str = '',
         created_by: str = '') -> None:
    with get_db().cursor() as cur:
        cur.execute("""INSERT INTO fin_settlements (fakturownia_id, reason, settled_date, note, created_by)
                       VALUES (%s, %s, %s, %s, %s)
                       ON DUPLICATE KEY UPDATE reason = VALUES(reason),
                                               settled_date = VALUES(settled_date),
                                               note = VALUES(note),
                                               created_by = VALUES(created_by)""",
                    (int(fakturownia_id), reason, settled_date, (note or '')[:512],
                     (created_by or '')[:64]))


def set_payment_marked(fakturownia_id: int) -> None:
    with get_db().cursor() as cur:
        cur.execute("UPDATE fin_settlements SET payment_marked = 1 WHERE fakturownia_id = %s",
                    (int(fakturownia_id),))


def delete(fakturownia_id: int) -> int:
    with get_db().cursor() as cur:
        cur.execute("DELETE FROM fin_settlements WHERE fakturownia_id = %s", (int(fakturownia_id),))
        return cur.rowcount
