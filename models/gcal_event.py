from datetime import date, datetime
from zoneinfo import ZoneInfo

from database import get_db

WARSAW_TZ = ZoneInfo('Europe/Warsaw')


def parse_raw_event(e: dict) -> dict | None:
    """Wyciąga datę/godzinę/czas trwania/status odrzucenia/tytuł z surowego
    wydarzenia Google Calendar — współdzielone między widokiem dnia/tygodnia/
    miesiąca, harmonogramem projektu i sekcjami CRM."""
    start_info = e.get('start', {})
    end_info = e.get('end', {})
    duration_min = None
    if start_info.get('dateTime'):
        dt = datetime.fromisoformat(start_info['dateTime'].replace('Z', '+00:00')).astimezone(WARSAW_TZ)
        d = dt.date()
        time_label = dt.strftime('%H:%M')
        if end_info.get('dateTime'):
            end_dt = datetime.fromisoformat(end_info['dateTime'].replace('Z', '+00:00')).astimezone(WARSAW_TZ)
            duration_min = max(0, int((end_dt - dt).total_seconds()) // 60)
    elif start_info.get('date'):
        d = datetime.strptime(start_info['date'], '%Y-%m-%d').date()
        time_label = None
    else:
        return None
    self_attendee = next((a for a in e.get('attendees') or [] if a.get('self')), None)
    is_declined = e.get('status') == 'cancelled' or (self_attendee is not None and self_attendee.get('responseStatus') == 'declined')
    return {
        'date': d,
        'time': time_label,
        'duration_min': duration_min,
        'is_declined': is_declined,
        'title': e.get('summary') or ('🔒 Wydarzenie prywatne' if e.get('visibility') == 'private' else '(bez tytułu)'),
    }


def cache_snapshot(event_id: str, event_date: str, title: str, event_time: str | None,
                    duration_min: int | None, is_declined: bool) -> None:
    """Zapisuje lokalną kopię tytułu/godziny/czasu trwania wydarzenia właśnie
    pobranego z Google Calendar — żeby dało się je później pokazać (np. na
    listach GTD) bez ponownego zapytania do API."""
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                """INSERT INTO gcal_event_done (event_id, event_date, title, event_time, duration_min, is_declined)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   ON DUPLICATE KEY UPDATE event_date=VALUES(event_date), title=VALUES(title),
                   event_time=VALUES(event_time), duration_min=VALUES(duration_min), is_declined=VALUES(is_declined)""",
                (event_id, event_date, title, event_time, duration_min, int(is_declined))
            )
        db.commit()
    except Exception:
        db.rollback()
        raise


def parse_and_cache(raw_event: dict) -> dict | None:
    """Parsuje surowe wydarzenie Google Calendar i od razu zapisuje jego
    tytuł/godzinę/czas trwania do lokalnego cache (patrz cache_snapshot)."""
    parsed = parse_raw_event(raw_event)
    if not parsed:
        return None
    cache_snapshot(raw_event.get('id'), parsed['date'].isoformat(), parsed['title'],
                    parsed['time'], parsed['duration_min'], parsed['is_declined'])
    return parsed


def get_cached_past_events(context_ids: list[int] | None = None, project_id: int | None = None,
                            limit: int = 200) -> list[dict]:
    """Przeszłe wydarzenia z kalendarza, których tytuł mamy już zapisany
    lokalnie (patrz cache_snapshot) — pozwala pokazać je na listach GTD
    (Wszystkie zadania, Wg kontekstu) bez odpytywania Google Calendar."""
    db = get_db()
    sql = ("SELECT event_id, event_date, title, event_time, duration_min, is_declined, "
           "done_at, is_today_priority, project_id, crm_contact_id, crm_company_id, context_id "
           "FROM gcal_event_done WHERE title IS NOT NULL AND event_date < CURDATE()")
    params: list = []
    if context_ids:
        ctx_placeholders = ','.join(['%s'] * len(context_ids))
        clause = f"context_id IN ({ctx_placeholders})"
        if 0 in context_ids:
            clause = f"({clause} OR context_id IS NULL)"
        sql += f" AND {clause}"
        params.extend(context_ids)
    if project_id:
        sql += " AND project_id=%s"
        params.append(project_id)
    sql += " ORDER BY event_date DESC, event_time DESC LIMIT %s"
    params.append(limit)
    with db.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def get_backfill_candidates() -> list[str]:
    """event_id-y wpisów z metadanymi (projekt/kontekst/kontakt/firma) sprzed
    wprowadzenia cache'owania tytułu/godziny — zapisanych, zanim gcal_event_done
    zyskała te kolumny, więc title jest u nich puste mimo powiązania z GTD/CRM."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT event_id FROM gcal_event_done WHERE title IS NULL "
            "AND (project_id IS NOT NULL OR context_id IS NOT NULL "
            "OR crm_contact_id IS NOT NULL OR crm_company_id IS NOT NULL)"
        )
        return [r['event_id'] for r in cur.fetchall()]


def get_event_meta(start_date: date, end_date: date) -> dict:
    """Zwraca event_id -> {'is_done', 'is_today_priority', 'project_id',
    'crm_contact_id', 'crm_company_id', 'context_id'} dla zakresu dat."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT event_id, done_at, is_today_priority, project_id, crm_contact_id, crm_company_id, context_id "
            "FROM gcal_event_done WHERE event_date BETWEEN %s AND %s",
            (start_date, end_date)
        )
        return {
            row['event_id']: {
                'is_done': row['done_at'] is not None,
                'is_today_priority': bool(row['is_today_priority']),
                'project_id': row['project_id'],
                'crm_contact_id': row['crm_contact_id'],
                'crm_company_id': row['crm_company_id'],
                'context_id': row['context_id'],
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


def toggle_today_priority(event_id: str, event_date: str) -> bool:
    """Przełącza gwiazdkę „priorytet dnia” dla wydarzenia z kalendarza. Zwraca nowy stan."""
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("SELECT is_today_priority FROM gcal_event_done WHERE event_id=%s", (event_id,))
            row = cur.fetchone()
            new_val = 0 if (row and row['is_today_priority']) else 1
            cur.execute(
                """INSERT INTO gcal_event_done (event_id, event_date, is_today_priority) VALUES (%s, %s, %s)
                   ON DUPLICATE KEY UPDATE event_date=VALUES(event_date), is_today_priority=VALUES(is_today_priority)""",
                (event_id, event_date, new_val)
            )
        db.commit()
        return bool(new_val)
    except Exception:
        db.rollback()
        raise


def count_today_priority(day: date) -> int:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS cnt FROM gcal_event_done WHERE event_date=%s AND is_today_priority=1",
            (day,)
        )
        return cur.fetchone()['cnt']


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


def set_context(event_id: str, event_date: str, context_id: int | None) -> None:
    """Przypisuje (lub odpina, gdy context_id=None) wydarzenie z kalendarza do kontekstu GTD."""
    db = get_db()
    try:
        with db.cursor() as cur:
            if context_id:
                cur.execute(
                    """INSERT INTO gcal_event_done (event_id, event_date, context_id) VALUES (%s, %s, %s)
                       ON DUPLICATE KEY UPDATE event_date=VALUES(event_date), context_id=VALUES(context_id)""",
                    (event_id, event_date, context_id)
                )
            else:
                cur.execute("UPDATE gcal_event_done SET context_id=NULL WHERE event_id=%s", (event_id,))
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


def get_events_for_project(project_id: int) -> list[dict]:
    """Metadane wydarzeń kalendarza przypisanych do projektu GTD — do zbudowania
    edytowalnego harmonogramu na stronie projektu (patrz routes.gtd._project_gcal_day_groups)."""
    if not project_id:
        return []
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT event_id, event_date, done_at, is_today_priority, "
            "crm_contact_id, crm_company_id, context_id FROM gcal_event_done "
            "WHERE project_id=%s ORDER BY event_date DESC",
            (project_id,)
        )
        return cur.fetchall()


def enrich_with_titles(events: list[dict]) -> list[dict]:
    """Dogrywa tytuł wydarzenia z Google Calendar, zapisując go od razu do
    lokalnego cache (patrz parse_and_cache) — do sekcji „Zadania/Projekty/
    Spotkania” na karcie kontaktu/firmy. Ciche pominięcie błędu per-wydarzenie
    (np. usunięte w kalendarzu), żeby jedno zepsute wydarzenie nie wywaliło całej sekcji."""
    if not events:
        return events
    from models.settings import get_setting
    from services.google_calendar import GoogleCalendarClient, parse_calendar_ids

    token = get_setting('google_drive_api_token', '')
    calendar_ids = parse_calendar_ids(get_setting('gtd_gcal_read_calendar_id', ''))
    if not token or not calendar_ids:
        for e in events:
            e['title'] = None
        return events
    client = GoogleCalendarClient(token)
    for e in events:
        try:
            _, ev = client.get_event_any(calendar_ids, e['event_id'])
            parsed = parse_and_cache(ev)
            e['title'] = parsed['title'] if parsed else (ev.get('summary') or '(bez tytułu)')
        except Exception:
            e['title'] = None
    return events
