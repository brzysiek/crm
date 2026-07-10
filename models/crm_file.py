from database import get_db

ALLOWED_EXTENSIONS = {
    'pdf':  'application/pdf',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'jpg':  'image/jpeg',
    'jpeg': 'image/jpeg',
    'png':  'image/png',
    'heic': 'image/heic',
    'xml':  'application/xml',
}

# Rozszerzenia renderowalne bezpośrednio w przeglądarce w popupie podglądu.
INLINE_PREVIEW_MIMES = {'application/pdf', 'image/jpeg', 'image/png'}


def _valid_user_id(user_id: int | None) -> int | None:
    if not user_id:
        return None
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT id FROM users WHERE id=%s", (user_id,))
        return user_id if cur.fetchone() else None


def add_file(company_id: int, contact_id: int | None, file_name: str, drive_file_id: str,
             mime_type: str, file_size: int, user_id: int | None) -> int:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                """INSERT INTO crm_files
                   (company_id, contact_id, file_name, drive_file_id, mime_type, file_size, user_id)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (company_id, contact_id, file_name, drive_file_id, mime_type, file_size,
                 _valid_user_id(user_id))
            )
        db.commit()
        return cur.lastrowid
    except Exception:
        db.rollback()
        raise


def get_files_for_company(company_id: int) -> list[dict]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT f.*, u.full_name AS user_name
               FROM crm_files f
               LEFT JOIN users u ON u.id = f.user_id
               WHERE f.company_id=%s
               ORDER BY f.created_at DESC, f.id DESC""",
            (company_id,)
        )
        return cur.fetchall()


def get_file_by_id(file_id: int) -> dict | None:
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM crm_files WHERE id=%s", (file_id,))
        return cur.fetchone()


def delete_file(file_id: int) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("DELETE FROM crm_files WHERE id=%s", (file_id,))
        db.commit()
    except Exception:
        db.rollback()
        raise


def files_word(n: int) -> str:
    """Polska odmiana rzeczownika 'plik' w zależności od liczby."""
    if n == 1:
        return 'plik'
    last_digit = n % 10
    last_two = n % 100
    if 2 <= last_digit <= 4 and not (12 <= last_two <= 14):
        return 'pliki'
    return 'plików'
