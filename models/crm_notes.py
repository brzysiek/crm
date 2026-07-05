from database import get_db

VALID_ENTITY_TYPES = ('company', 'contact', 'deal')


def _valid_user_id(user_id: int | None) -> int | None:
    """Zwraca user_id tylko jeśli wciąż istnieje w tabeli users — chroni przed naruszeniem
    FK, gdy sesja przechowuje nieaktualne/usunięte id (np. stara sesja "zapamiętaj mnie")."""
    if not user_id:
        return None
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT id FROM users WHERE id=%s", (user_id,))
        return user_id if cur.fetchone() else None


def add_note(entity_type: str, entity_id: int, user_id: int | None, body: str) -> int:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "INSERT INTO crm_notes (entity_type, entity_id, user_id, body) "
                "VALUES (%s, %s, %s, %s)",
                (entity_type, entity_id, _valid_user_id(user_id), body)
            )
        db.commit()
        return cur.lastrowid
    except Exception:
        db.rollback()
        raise


def get_notes(entity_type: str, entity_id: int) -> list[dict]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT n.*, u.full_name AS user_name
               FROM crm_notes n
               LEFT JOIN users u ON u.id = n.user_id
               WHERE n.entity_type=%s AND n.entity_id=%s
               ORDER BY n.created_at DESC, n.id DESC""",
            (entity_type, entity_id)
        )
        return cur.fetchall()


def delete_note(note_id: int) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("DELETE FROM crm_notes WHERE id=%s", (note_id,))
        db.commit()
    except Exception:
        db.rollback()
        raise


def log_history(entity_type: str, entity_id: int, user_id: int | None,
                 action: str, summary: str) -> int:
    db = get_db()
    try:
        with db.cursor() as cur:
            # Chroni przed zdublowanym wpisem, gdy ten sam zapis trafi do bazy
            # dwa razy (np. podwójny submit formularza) — identyczna
            # akcja/treść w ciągu kilku sekund jest traktowana jako duplikat.
            cur.execute(
                """SELECT id FROM crm_history
                   WHERE entity_type=%s AND entity_id=%s AND action=%s AND summary=%s
                     AND created_at >= NOW() - INTERVAL 10 SECOND
                   ORDER BY id DESC LIMIT 1""",
                (entity_type, entity_id, action, summary)
            )
            existing = cur.fetchone()
            if existing:
                return existing['id']
            cur.execute(
                "INSERT INTO crm_history (entity_type, entity_id, user_id, action, summary) "
                "VALUES (%s, %s, %s, %s, %s)",
                (entity_type, entity_id, _valid_user_id(user_id), action, summary)
            )
            new_id = cur.lastrowid
        db.commit()
        return new_id
    except Exception:
        db.rollback()
        raise


def get_history(entity_type: str, entity_id: int) -> list[dict]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT h.*, u.full_name AS user_name
               FROM crm_history h
               LEFT JOIN users u ON u.id = h.user_id
               WHERE h.entity_type=%s AND h.entity_id=%s
               ORDER BY h.created_at DESC, h.id DESC""",
            (entity_type, entity_id)
        )
        return cur.fetchall()


def build_diff_summary(old: dict, new: dict, field_labels: dict) -> str | None:
    """Porównuje stare i nowe wartości pól, zwraca czytelny opis zmian albo None gdy brak różnic."""
    changes = []
    for field, label in field_labels.items():
        old_val = old.get(field)
        new_val = new.get(field)
        old_str = '' if old_val is None else str(old_val)
        new_str = '' if new_val is None else str(new_val)
        if old_str != new_str:
            old_disp = old_str or '—'
            new_disp = new_str or '—'
            changes.append(f"{label}: '{old_disp}' → '{new_disp}'")
    if not changes:
        return None
    return "Zmieniono: " + "; ".join(changes)
