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


def create_context(name: str, badge_color: str) -> int:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("INSERT INTO gtd_contexts (name, badge_color) VALUES (%s,%s)", (name, badge_color))
            new_id = cur.lastrowid
        db.commit()
        return new_id
    except Exception:
        db.rollback()
        raise


def update_context(context_id: int, name: str, badge_color: str) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("UPDATE gtd_contexts SET name=%s, badge_color=%s WHERE id=%s", (name, badge_color, context_id))
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
