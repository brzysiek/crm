from database import get_db
from services.voice_notes import AUDIO_MIME_BY_EXT

# Nagrania jako załącznik: te same formaty co w notatkach głosowych, żeby plik
# wgrywalny do notatki nie odbijał się od sekcji Pliki. Bez .mp4 — ten kontener
# to prawie zawsze wideo, a podawanie go jako audio dałoby odtwarzacz bez obrazu.
AUDIO_EXTENSIONS = {ext: mime for ext, mime in AUDIO_MIME_BY_EXT.items() if ext != 'mp4'}

IMAGE_EXTENSIONS = {
    'jpg':  'image/jpeg',
    'jpeg': 'image/jpeg',
    'png':  'image/png',
    'heic': 'image/heic',
}

ALLOWED_EXTENSIONS = {
    'pdf':  'application/pdf',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'xml':  'application/xml',
    **IMAGE_EXTENSIONS,
    **AUDIO_EXTENSIONS,
}

# Aliasy tego samego formatu — w komunikacie dla użytkownika wystarczy jeden.
_EXT_ALIASES = {'jpeg': 'jpg', 'oga': 'ogg', 'aif': 'aiff'}


def formats_label() -> str:
    """Lista obsługiwanych formatów do komunikatów o błędzie.

    Generowana, a nie zapisana ręcznie: trzy zahardkodowane kopie tej listy
    rozjechały się z tym słownikiem i użytkownik dostawał komunikat wymieniający
    formaty, których wcale nie było w zestawie (i odwrotnie).
    """
    shown = set(ALLOWED_EXTENSIONS) - set(_EXT_ALIASES)
    return ', '.join(sorted(shown)).upper()


# Rozszerzenia renderowalne bezpośrednio w przeglądarce w popupie podglądu.
# Audio leci inline, bo przeglądarka odtwarza je w <audio> — załącznik zmusiłby
# do pobrania pliku, żeby odsłuchać nagranie z dyktafonu.
INLINE_PREVIEW_MIMES = {'application/pdf', 'image/jpeg', 'image/png'} | set(AUDIO_EXTENSIONS.values())


def _valid_user_id(user_id: int | None) -> int | None:
    if not user_id:
        return None
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT id FROM users WHERE id=%s", (user_id,))
        return user_id if cur.fetchone() else None


def add_file(company_id: int | None, contact_id: int | None, file_name: str, drive_file_id: str,
             mime_type: str, file_size: int, user_id: int | None, category: str = 'file',
             mna_deal_id: int | None = None, mna_offer_id: int | None = None) -> int:
    """Plik należy do firmy CRM (company_id), do deala M&A (mna_deal_id) albo do oferty M&A
    (mna_offer_id) — dokładnie jednego z nich."""
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                """INSERT INTO crm_files
                   (company_id, contact_id, mna_deal_id, mna_offer_id, category, file_name,
                    drive_file_id, mime_type, file_size, user_id)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (company_id or None, contact_id, mna_deal_id or None, mna_offer_id or None,
                 category, file_name, drive_file_id, mime_type, file_size, _valid_user_id(user_id))
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
               WHERE f.company_id=%s AND f.category='file'
               ORDER BY f.created_at DESC, f.id DESC""",
            (company_id,)
        )
        return cur.fetchall()


def get_files_for_mna_deal(mna_deal_id: int) -> list[dict]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT f.*, u.full_name AS user_name
               FROM crm_files f
               LEFT JOIN users u ON u.id = f.user_id
               WHERE f.mna_deal_id=%s AND f.category='file'
               ORDER BY f.created_at DESC, f.id DESC""",
            (mna_deal_id,)
        )
        return cur.fetchall()


def get_files_for_mna_offer(mna_offer_id: int) -> list[dict]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT f.*, u.full_name AS user_name
               FROM crm_files f
               LEFT JOIN users u ON u.id = f.user_id
               WHERE f.mna_offer_id=%s AND f.category='file'
               ORDER BY f.created_at DESC, f.id DESC""",
            (mna_offer_id,)
        )
        return cur.fetchall()


def rename_file(file_id: int, file_name: str) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("UPDATE crm_files SET file_name=%s WHERE id=%s", (file_name, file_id))
        db.commit()
    except Exception:
        db.rollback()
        raise


def get_business_card(contact_id: int) -> dict | None:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT f.*, u.full_name AS user_name
               FROM crm_files f
               LEFT JOIN users u ON u.id = f.user_id
               WHERE f.contact_id=%s AND f.category='business_card'
               ORDER BY f.id DESC LIMIT 1""",
            (contact_id,)
        )
        return cur.fetchone()


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
