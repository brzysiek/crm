from datetime import date

from database import get_db


def get_event_meta(start_date: date, end_date: date) -> dict:
    """Zwraca event_id -> {'is_done': bool, 'project_id': int|None} dla zakresu dat."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT event_id, done_at, project_id FROM gcal_event_done "
            "WHERE event_date BETWEEN %s AND %s",
            (start_date, end_date)
        )
        return {
            row['event_id']: {'is_done': row['done_at'] is not None, 'project_id': row['project_id']}
            for row in cur.fetchall()
        }


def get_project_id(event_id: str) -> int | None:
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT project_id FROM gcal_event_done WHERE event_id=%s", (event_id,))
        row = cur.fetchone()
        return row['project_id'] if row else None


def mark_done(event_id: str, event_date: str) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                """INSERT INTO gcal_event_done (event_id, event_date, done_at) VALUES (%s, %s, NOW())
                   ON DUPLICATE KEY UPDATE event_date=VALUES(event_date), done_at=NOW()""",
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
            cur.execute("UPDATE gcal_event_done SET done_at=NULL WHERE event_id=%s", (event_id,))
        db.commit()
    except Exception:
        db.rollback()
        raise


def set_project(event_id: str, event_date: str, project_id: int | None) -> None:
    """Przypisuje (lub odpina, gdy project_id=None) wydarzenie z kalendarza do projektu GTD."""
    db = get_db()
    try:
        with db.cursor() as cur:
            if project_id:
                cur.execute(
                    """INSERT INTO gcal_event_done (event_id, event_date, project_id) VALUES (%s, %s, %s)
                       ON DUPLICATE KEY UPDATE event_date=VALUES(event_date), project_id=VALUES(project_id)""",
                    (event_id, event_date, project_id)
                )
            else:
                cur.execute("UPDATE gcal_event_done SET project_id=NULL WHERE event_id=%s", (event_id,))
        db.commit()
    except Exception:
        db.rollback()
        raise
