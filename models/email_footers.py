from database import get_db


def get_all_footers() -> list[dict]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM email_footers ORDER BY name")
        return cur.fetchall()


def get_footer_by_id(footer_id: int) -> dict | None:
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM email_footers WHERE id=%s", (footer_id,))
        return cur.fetchone()


def create_footer(name: str, html_content: str) -> int:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "INSERT INTO email_footers (name, html_content) VALUES (%s, %s)",
                (name, html_content)
            )
            footer_id = cur.lastrowid
        db.commit()
        return footer_id
    except Exception:
        db.rollback()
        raise


def update_footer(footer_id: int, name: str, html_content: str) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "UPDATE email_footers SET name=%s, html_content=%s WHERE id=%s",
                (name, html_content, footer_id)
            )
        db.commit()
    except Exception:
        db.rollback()
        raise


def delete_footer(footer_id: int) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("DELETE FROM email_footers WHERE id=%s", (footer_id,))
        db.commit()
    except Exception:
        db.rollback()
        raise
