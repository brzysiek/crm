"""Kolejka dokumentów z Dysku Google — wynik OCR czekający na zatwierdzenie.

Zatwierdzony wiersz staje się dokumentem w `fin_documents` (`source='gdrive'`).
Jego `fakturownia_id` pochodzi z osobnej puli, żeby reszta modułu — kategorie,
powiązania z przelewami, podatki — nie musiała wiedzieć, skąd dokument przyszedł.
"""
from database import get_db

# Identyfikatory Fakturowni są rzędu 10^8–10^9; pula Dysku zaczyna się daleko
# ponad nimi, więc te dwa źródła nigdy się nie spotkają.
DRIVE_ID_BASE = 9_000_000_000_000

SOURCE = 'gdrive'

STATUS_LABELS = {'pending': 'Do zatwierdzenia', 'accepted': 'Zatwierdzone', 'rejected': 'Odrzucone'}

OCR_FIELDS = ('file_name', 'file_modified_at', 'is_income', 'kind', 'number',
              'counterparty_name', 'counterparty_tax_no', 'issue_date', 'payment_to',
              'currency', 'price_net', 'price_tax', 'price_gross', 'ocr_note', 'ocr_raw')

EDIT_FIELDS = ('is_income', 'kind', 'number', 'counterparty_name', 'counterparty_tax_no',
               'issue_date', 'payment_to', 'currency', 'price_net', 'price_tax', 'price_gross')


def document_id(queue_id: int) -> int:
    return DRIVE_ID_BASE + int(queue_id)


def is_drive_document(fakturownia_id) -> bool:
    return int(fakturownia_id) > DRIVE_ID_BASE


def get(queue_id: int) -> dict | None:
    with get_db().cursor() as cur:
        cur.execute("SELECT * FROM fin_drive_documents WHERE id = %s", (int(queue_id),))
        row = cur.fetchone()
    return dict(row) if row else None


def get_by_document(fakturownia_id: int) -> dict | None:
    with get_db().cursor() as cur:
        cur.execute("SELECT * FROM fin_drive_documents WHERE fakturownia_id = %s",
                    (int(fakturownia_id),))
        row = cur.fetchone()
    return dict(row) if row else None


def list_queue(status: str = 'pending', limit: int = 300) -> list[dict]:
    with get_db().cursor() as cur:
        cur.execute("""SELECT * FROM fin_drive_documents WHERE status = %s
                       ORDER BY issue_date IS NULL, issue_date DESC, id DESC LIMIT %s""",
                    (status, int(limit)))
        return [dict(r) for r in cur.fetchall()]


def count_by_status() -> dict:
    with get_db().cursor() as cur:
        cur.execute("SELECT status, COUNT(*) AS n FROM fin_drive_documents GROUP BY status")
        return {r['status']: r['n'] for r in cur.fetchall()}


def count_pending() -> int:
    return count_by_status().get('pending', 0)


def file_states(file_ids: list[str]) -> dict:
    """Stan plików w kolejce: {gdrive_file_id: status}. Pliki spoza kolejki pomija."""
    if not file_ids:
        return {}
    marks = ', '.join(['%s'] * len(file_ids))
    with get_db().cursor() as cur:
        cur.execute(f"""SELECT gdrive_file_id, status FROM fin_drive_documents
                        WHERE gdrive_file_id IN ({marks})""", tuple(file_ids))
        return {r['gdrive_file_id']: r['status'] for r in cur.fetchall()}


def save_ocr(gdrive_file_id: str, data: dict) -> dict:
    """Zapisuje odczyt pliku. Zwraca {'outcome': 'new'|'updated'|'accepted', 'id': …}.

    Ponowny OCR nadpisuje wiersz czekający lub odrzucony i przywraca go do
    kolejki — po to się go powtarza. Zatwierdzonego nie rusza: stoi za nim
    dokument, który mógł już zostać skategoryzowany i rozliczony z przelewem.
    """
    values = tuple(data.get(f) for f in OCR_FIELDS)
    with get_db().cursor() as cur:
        cur.execute("SELECT id, status FROM fin_drive_documents WHERE gdrive_file_id = %s",
                    (gdrive_file_id,))
        existing = cur.fetchone()
        if existing and existing['status'] == 'accepted':
            return {'outcome': 'accepted', 'id': existing['id']}
        if existing:
            sets = ', '.join(f'`{f}` = %s' for f in OCR_FIELDS)
            cur.execute(f"UPDATE fin_drive_documents SET {sets}, status = 'pending' WHERE id = %s",
                        values + (existing['id'],))
            return {'outcome': 'updated', 'id': existing['id']}
        columns = ', '.join(f'`{f}`' for f in OCR_FIELDS)
        marks = ', '.join(['%s'] * len(OCR_FIELDS))
        cur.execute(f"INSERT INTO fin_drive_documents (gdrive_file_id, {columns}) "
                    f"VALUES (%s, {marks})", (gdrive_file_id,) + values)
        return {'outcome': 'new', 'id': cur.lastrowid}


def update_fields(queue_id: int, data: dict) -> None:
    fields = [f for f in EDIT_FIELDS if f in data]
    if not fields:
        return
    sets = ', '.join(f'`{f}` = %s' for f in fields)
    with get_db().cursor() as cur:
        cur.execute(f"UPDATE fin_drive_documents SET {sets} WHERE id = %s",
                    tuple(data[f] for f in fields) + (int(queue_id),))


def set_status(queue_id: int, status: str, fakturownia_id: int = None, actor: str = '') -> None:
    with get_db().cursor() as cur:
        cur.execute("""UPDATE fin_drive_documents
                       SET status = %s, fakturownia_id = %s, decided_by = %s WHERE id = %s""",
                    (status, fakturownia_id, (actor or '')[:64], int(queue_id)))
