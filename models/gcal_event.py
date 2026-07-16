from datetime import date

from database import get_db


def get_event_meta(start_date: date, end_date: date) -> dict:
    """Zwraca event_id -> {'is_done', 'project_id', 'crm_contact_id', 'crm_company_id'}
    dla zakresu dat."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT event_id, done_at, project_id, crm_contact_id, crm_company_id "
            "FROM gcal_event_done WHERE event_date BETWEEN %s AND %s",
            (start_date, end_date)
        )
        return {
            row['event_id']: {
                'is_done': row['done_at'] is not None,
                'project_id': row['project_id'],
                'crm_contact_id': row['crm_contact_id'],
                'crm_company_id': row['crm_company_id'],
            }
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


def set_crm_link(event_id: str, event_date: str, contact_id: int | None, company_id: int | None) -> None:
    """Przypisuje (lub odpina, gdy oba None) wydarzenie z kalendarza do kontaktu/firmy CRM."""
    db = get_db()
    try:
        with db.cursor() as cur:
            if contact_id or company_id:
                cur.execute(
                    """INSERT INTO gcal_event_done (event_id, event_date, crm_contact_id, crm_company_id)
                       VALUES (%s, %s, %s, %s)
                       ON DUPLICATE KEY UPDATE event_date=VALUES(event_date),
                       crm_contact_id=VALUES(crm_contact_id), crm_company_id=VALUES(crm_company_id)""",
                    (event_id, event_date, contact_id, company_id)
                )
            else:
                cur.execute(
                    "UPDATE gcal_event_done SET crm_contact_id=NULL, crm_company_id=NULL WHERE event_id=%s",
                    (event_id,)
                )
        db.commit()
    except Exception:
        db.rollback()
        raise


def get_events_for_crm(contact_id: int | None = None, company_id: int | None = None) -> list[dict]:
    """Surowe metadane wydarzeń kalendarza przypisanych do kontaktu/firmy CRM (bez
    tytułu — patrz enrich_with_titles) — do sekcji „Zadania/Projekty/Spotkania”."""
    if not contact_id and not company_id:
        return []
    db = get_db()
    with db.cursor() as cur:
        if contact_id:
            cur.execute(
                "SELECT event_id, event_date, done_at FROM gcal_event_done "
                "WHERE crm_contact_id=%s ORDER BY event_date DESC",
                (contact_id,)
            )
        else:
            cur.execute(
                "SELECT event_id, event_date, done_at FROM gcal_event_done "
                "WHERE crm_company_id=%s ORDER BY event_date DESC",
                (company_id,)
            )
        return cur.fetchall()


def enrich_with_titles(events: list[dict]) -> list[dict]:
    """Dogrywa tytuł wydarzenia z Google Calendar — nie przechowujemy go lokalnie,
    tylko metadane (patrz nagłówek modułu). Ciche pominięcie błędu per-wydarzenie
    (np. usunięte w kalendarzu), żeby jedno zepsute wydarzenie nie wywaliło całej sekcji."""
    if not events:
        return events
    from models.settings import get_setting
    from services.google_calendar import GoogleCalendarClient

    token = get_setting('google_drive_api_token', '')
    calendar_id = get_setting('gtd_gcal_read_calendar_id', '')
    if not token or not calendar_id:
        for e in events:
            e['title'] = None
        return events
    client = GoogleCalendarClient(token)
    for e in events:
        try:
            ev = client.get_event(calendar_id, e['event_id'])
            e['title'] = ev.get('summary') or '(bez tytułu)'
        except Exception:
            e['title'] = None
    return events
