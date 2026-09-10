from database import get_db


def get_all_contexts() -> list[dict]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM gtd_contexts ORDER BY name")
        return cur.fetchall()


def get_context(context_id: int) -> dict | None:
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM gtd_contexts WHERE id=%s", (context_id,))
        return cur.fetchone()


def create_context(name: str, badge_color: str, text_color: str) -> int:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "INSERT INTO gtd_contexts (name, badge_color, text_color) VALUES (%s,%s,%s)",
                (name, badge_color, text_color)
            )
            new_id = cur.lastrowid
        db.commit()
        return new_id
    except Exception:
        db.rollback()
        raise


def update_context(context_id: int, name: str, badge_color: str, text_color: str) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "UPDATE gtd_contexts SET name=%s, badge_color=%s, text_color=%s WHERE id=%s",
                (name, badge_color, text_color, context_id)
            )
        db.commit()
    except Exception:
        db.rollback()
        raise


def delete_context(context_id: int) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("DELETE FROM gtd_contexts WHERE id=%s", (context_id,))
        db.commit()
    except Exception:
        db.rollback()
        raise


def get_default_context() -> dict | None:
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM gtd_contexts WHERE is_default=1 LIMIT 1")
        return cur.fetchone()


def get_default_context_id() -> int | None:
    ctx = get_default_context()
    return ctx['id'] if ctx else None


def set_default_context(context_id: int | None) -> None:
    """Ustawia dany kontekst jako domyślny, zdejmując flagę z pozostałych.
    `context_id=None` czyści domyślny kontekst całkowicie."""
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("UPDATE gtd_contexts SET is_default=0")
            if context_id:
                cur.execute("UPDATE gtd_contexts SET is_default=1 WHERE id=%s", (context_id,))
        db.commit()
    except Exception:
        db.rollback()
        raise


def sync_company_context_group(company_id: int, context_id: int | None) -> None:
    """Utrzymuje spójny kontekst GTD w obrębie firmy i jej kontaktów — gdy
    kontekst zmienia się na firmie lub na dowolnym jej kontakcie, ujednolica
    go na całej grupie (firma + wszyscy jej kontakci)."""
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("UPDATE crm_companies SET context_id=%s WHERE id=%s", (context_id, company_id))
            cur.execute("UPDATE crm_contacts SET context_id=%s WHERE company_id=%s", (context_id, company_id))
        db.commit()
    except Exception:
        db.rollback()
        raise
