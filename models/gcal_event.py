from datetime import date

from database import get_db


def get_done_event_ids(start_date: date, end_date: date) -> set:
    """Zwraca zbiór event_id oznaczonych jako done w danym zakresie dat."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT event_id FROM gcal_event_done WHERE event_date BETWEEN %s AND %s",
            (start_date, end_date)
        )
        return {row['event_id'] for row in cur.fetchall()}


def mark_done(event_id: str, event_date: str) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                """INSERT INTO gcal_event_done (event_id, event_date) VALUES (%s, %s)
                   ON DUPLICATE KEY UPDATE event_date=VALUES(event_date)""",
                (event_id, event_date)
            )
        db.commit()
    except Exception:
        db.rollback()
        raise


def mark_undone(event_id: str) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("DELETE FROM gcal_event_done WHERE event_id=%s", (event_id,))
        db.commit()
    except Exception:
        db.rollback()
        raise
