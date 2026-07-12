from datetime import date, timedelta

from database import get_db

VALID_STATUSES = ('inbox', 'next', 'waiting', 'someday', 'done')

STATUS_LABELS = {
    'inbox': 'Inbox',
    'next': 'Next actions',
    'waiting': 'Czeka na',
    'someday': 'Kiedyś/może',
    'done': 'Zrobione',
}

_LIST_FIELDS = """t.*, ct.name AS context_name,
                  p.title AS project_title"""

_LIST_JOINS = """FROM tasks t
                 LEFT JOIN crm_tags ct ON ct.id = t.context_tag_id
                 LEFT JOIN tasks p ON p.id = t.parent_id"""


def _valid_user_id(user_id: int | None) -> int | None:
    if not user_id:
        return None
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT id FROM users WHERE id=%s", (user_id,))
        return user_id if cur.fetchone() else None


def get_task(task_id: int) -> dict | None:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(f"SELECT {_LIST_FIELDS} {_LIST_JOINS} WHERE t.id=%s", (task_id,))
        return cur.fetchone()


def create_task(title: str, user_id: int | None, is_project: bool = False,
                 status: str = 'inbox', **fields) -> int:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                """INSERT INTO tasks
                   (title, notes, is_project, parent_id, status, context_tag_id, waiting_on,
                    due_date, scheduled_date, scheduled_time, scheduled_duration_min,
                    is_today_priority, is_week_priority, created_by)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    title,
                    fields.get('notes') or None,
                    1 if is_project else 0,
                    fields.get('parent_id') or None,
                    status if status in VALID_STATUSES else 'inbox',
                    fields.get('context_tag_id') or None,
                    fields.get('waiting_on') or None,
                    fields.get('due_date') or None,
                    fields.get('scheduled_date') or None,
                    fields.get('scheduled_time') or None,
                    fields.get('scheduled_duration_min') or None,
                    1 if fields.get('is_today_priority') else 0,
                    1 if fields.get('is_week_priority') else 0,
                    _valid_user_id(user_id),
                )
            )
            new_id = cur.lastrowid
        db.commit()
        return new_id
    except Exception:
        db.rollback()
        raise


def update_task(task_id: int, data: dict) -> None:
    allowed = ('title', 'notes', 'status', 'context_tag_id', 'waiting_on', 'due_date',
               'scheduled_date', 'scheduled_time', 'scheduled_duration_min')
    fields = {k: v for k, v in data.items() if k in allowed}
    if not fields:
        return
    db = get_db()
    try:
        with db.cursor() as cur:
            set_clause = ", ".join(f"{k}=%s" for k in fields)
            cur.execute(
                f"UPDATE tasks SET {set_clause} WHERE id=%s",
                (*fields.values(), task_id)
            )
        db.commit()
    except Exception:
        db.rollback()
        raise


def _sync_project_status(cur, parent_id: int | None) -> None:
    """Projekt kończy się automatycznie, gdy wszystkie jego podzadania są zrobione;
    odnawia się automatycznie, jeśli któreś znów przestanie być zrobione."""
    if not parent_id:
        return
    cur.execute("SELECT is_project, status FROM tasks WHERE id=%s", (parent_id,))
    parent = cur.fetchone()
    if not parent or not parent['is_project']:
        return
    cur.execute(
        "SELECT COUNT(*) AS total, SUM(status='done') AS done FROM tasks WHERE parent_id=%s",
        (parent_id,)
    )
    counts = cur.fetchone()
    total = counts['total'] or 0
    done = counts['done'] or 0
    if total > 0 and done == total and parent['status'] != 'done':
        cur.execute("UPDATE tasks SET status='done', completed_at=NOW() WHERE id=%s", (parent_id,))
    elif parent['status'] == 'done' and done < total:
        cur.execute("UPDATE tasks SET status='next', completed_at=NULL WHERE id=%s", (parent_id,))


def delete_task(task_id: int) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("SELECT parent_id FROM tasks WHERE id=%s", (task_id,))
            row = cur.fetchone()
            parent_id = row['parent_id'] if row else None
            cur.execute("UPDATE tasks SET parent_id=NULL WHERE parent_id=%s", (task_id,))
            cur.execute("DELETE FROM tasks WHERE id=%s", (task_id,))
            _sync_project_status(cur, parent_id)
        db.commit()
    except Exception:
        db.rollback()
        raise


def set_status(task_id: int, status: str) -> None:
    if status not in VALID_STATUSES:
        return
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("SELECT parent_id FROM tasks WHERE id=%s", (task_id,))
            row = cur.fetchone()
            parent_id = row['parent_id'] if row else None
            if status == 'done':
                cur.execute(
                    "UPDATE tasks SET status=%s, completed_at=NOW() WHERE id=%s",
                    (status, task_id)
                )
            else:
                cur.execute(
                    "UPDATE tasks SET status=%s, completed_at=NULL WHERE id=%s",
                    (status, task_id)
                )
            _sync_project_status(cur, parent_id)
        db.commit()
    except Exception:
        db.rollback()
        raise


def toggle_today_priority(task_id: int) -> bool:
    """Przełącza flagę gwiazdki dnia. Zwraca nowy stan (True/False)."""
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("SELECT is_today_priority FROM tasks WHERE id=%s", (task_id,))
            row = cur.fetchone()
            new_val = 0 if (row and row['is_today_priority']) else 1
            cur.execute("UPDATE tasks SET is_today_priority=%s WHERE id=%s", (new_val, task_id))
        db.commit()
        return bool(new_val)
    except Exception:
        db.rollback()
        raise


def toggle_week_priority(task_id: int) -> bool:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("SELECT is_week_priority FROM tasks WHERE id=%s", (task_id,))
            row = cur.fetchone()
            new_val = 0 if (row and row['is_week_priority']) else 1
            cur.execute("UPDATE tasks SET is_week_priority=%s WHERE id=%s", (new_val, task_id))
        db.commit()
        return bool(new_val)
    except Exception:
        db.rollback()
        raise


def schedule_task(task_id: int, scheduled_date: str | None, scheduled_time: str | None = None,
                   scheduled_duration_min: int | None = None) -> None:
    """Ustawia konkretny dzień/godzinę. Zadanie 'wychodzi' z Inbox (status next) i traci
    ewentualne przypisanie do luźnego bloku tygodniowego — dzień jest bardziej konkretny."""
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                """UPDATE tasks SET scheduled_date=%s, scheduled_time=%s, scheduled_duration_min=%s,
                   planned_week=NULL, status=IF(status='inbox','next',status) WHERE id=%s""",
                (scheduled_date or None, scheduled_time or None, scheduled_duration_min or None, task_id)
            )
        db.commit()
    except Exception:
        db.rollback()
        raise


def _monday_of(d: date, week_offset: int) -> date:
    monday = d - timedelta(days=d.weekday())
    return monday + timedelta(weeks=week_offset)


def assign_week(task_id: int, week_offset: int) -> date:
    """Przypisuje zadanie do luźnego bloku tygodniowego (0 = ten tydzień, 1 = przyszły)
    — bez konkretnego dnia. Zadanie wychodzi z Inbox i traci ewentualne zaplanowanie
    na konkretny dzień (blok tygodniowy i konkretny dzień się wykluczają)."""
    monday = _monday_of(date.today(), week_offset)
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                """UPDATE tasks SET planned_week=%s, scheduled_date=NULL, scheduled_time=NULL,
                   scheduled_duration_min=NULL, gcal_event_id=NULL,
                   status=IF(status='inbox','next',status) WHERE id=%s""",
                (monday, task_id)
            )
        db.commit()
        return monday
    except Exception:
        db.rollback()
        raise


def clear_week(task_id: int) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("UPDATE tasks SET planned_week=NULL WHERE id=%s", (task_id,))
        db.commit()
    except Exception:
        db.rollback()
        raise


def unschedule_task(task_id: int) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                """UPDATE tasks SET scheduled_date=NULL, scheduled_time=NULL,
                   scheduled_duration_min=NULL, gcal_event_id=NULL WHERE id=%s""",
                (task_id,)
            )
        db.commit()
    except Exception:
        db.rollback()
        raise


def set_gcal_event_id(task_id: int, event_id: str | None) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("UPDATE tasks SET gcal_event_id=%s WHERE id=%s", (event_id, task_id))
        db.commit()
    except Exception:
        db.rollback()
        raise


def convert_to_project(task_id: int) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "UPDATE tasks SET is_project=1, "
                "status=IF(status='inbox', 'next', status) WHERE id=%s",
                (task_id,)
            )
        db.commit()
    except Exception:
        db.rollback()
        raise


def flatten_project(task_id: int) -> None:
    """Cofa projekt do zwykłego zadania — odpina wszystkie subtaski (zostają samodzielne)."""
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("UPDATE tasks SET parent_id=NULL WHERE parent_id=%s", (task_id,))
            cur.execute("UPDATE tasks SET is_project=0 WHERE id=%s", (task_id,))
        db.commit()
    except Exception:
        db.rollback()
        raise


def get_inbox_tasks() -> list[dict]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            f"SELECT {_LIST_FIELDS} {_LIST_JOINS} WHERE t.status='inbox' "
            f"ORDER BY t.created_at DESC, t.id DESC"
        )
        return cur.fetchall()


def get_next_actions(context_tag_id: int | None = None) -> list[dict]:
    db = get_db()
    sql = f"SELECT {_LIST_FIELDS} {_LIST_JOINS} WHERE t.status='next' AND t.is_project=0"
    params = []
    if context_tag_id:
        sql += " AND t.context_tag_id=%s"
        params.append(context_tag_id)
    sql += " ORDER BY t.due_date IS NULL, t.due_date ASC, t.id DESC"
    with db.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def get_waiting_tasks() -> list[dict]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            f"SELECT {_LIST_FIELDS} {_LIST_JOINS} WHERE t.status='waiting' "
            f"ORDER BY t.updated_at DESC, t.id DESC"
        )
        return cur.fetchall()


def get_someday_tasks() -> list[dict]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            f"SELECT {_LIST_FIELDS} {_LIST_JOINS} WHERE t.status='someday' "
            f"ORDER BY t.created_at DESC, t.id DESC"
        )
        return cur.fetchall()


def get_projects(include_done: bool = False) -> list[dict]:
    db = get_db()
    sql = f"SELECT {_LIST_FIELDS} {_LIST_JOINS} WHERE t.is_project=1"
    if not include_done:
        sql += " AND t.status != 'done'"
    sql += " ORDER BY t.created_at DESC, t.id DESC"
    with db.cursor() as cur:
        cur.execute(sql)
        projects = cur.fetchall()
        for proj in projects:
            cur.execute(
                "SELECT COUNT(*) AS total, SUM(status='done') AS done "
                "FROM tasks WHERE parent_id=%s",
                (proj['id'],)
            )
            counts = cur.fetchone()
            proj['subtask_total'] = counts['total'] or 0
            proj['subtask_done'] = counts['done'] or 0
        return projects


def get_project_subtasks(project_id: int) -> list[dict]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            f"SELECT {_LIST_FIELDS} {_LIST_JOINS} WHERE t.parent_id=%s "
            f"ORDER BY (t.status='done'), t.due_date IS NULL, t.due_date ASC, t.id ASC",
            (project_id,)
        )
        return cur.fetchall()


def get_tasks_for_day(day: date) -> list[dict]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            f"SELECT {_LIST_FIELDS} {_LIST_JOINS} WHERE t.scheduled_date=%s "
            f"ORDER BY t.scheduled_time IS NULL, t.scheduled_time ASC, t.is_today_priority DESC, t.id ASC",
            (day,)
        )
        return cur.fetchall()


def get_unfinished_before(day: date, limit: int = 20) -> list[dict]:
    """Niedokończone zadania zaplanowane na dni przed `day` — do sekcji przeglądu,
    nigdy nie przenoszone automatycznie (zgodnie z filozofią GTD: nic nie dzieje
    się w tle, użytkownik świadomie decyduje co dalej)."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            f"SELECT {_LIST_FIELDS} {_LIST_JOINS} "
            f"WHERE t.scheduled_date < %s AND t.status != 'done' "
            f"ORDER BY t.scheduled_date DESC, t.id DESC LIMIT %s",
            (day, limit)
        )
        return cur.fetchall()


def get_week_priority_tasks() -> list[dict]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            f"SELECT {_LIST_FIELDS} {_LIST_JOINS} WHERE t.is_week_priority=1 AND t.status != 'done' "
            f"ORDER BY t.due_date IS NULL, t.due_date ASC, t.id DESC"
        )
        return cur.fetchall()


def get_week_bucket_tasks(monday: date) -> list[dict]:
    """Zadania przypisane do luźnego bloku tygodniowego (bez konkretnego dnia)."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            f"SELECT {_LIST_FIELDS} {_LIST_JOINS} WHERE t.planned_week=%s AND t.status != 'done' "
            f"ORDER BY t.due_date IS NULL, t.due_date ASC, t.id DESC",
            (monday,)
        )
        return cur.fetchall()


def get_scheduled_tasks_between(start: date, end: date) -> list[dict]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            f"SELECT {_LIST_FIELDS} {_LIST_JOINS} "
            f"WHERE t.scheduled_date BETWEEN %s AND %s "
            f"ORDER BY t.scheduled_date ASC, t.scheduled_time IS NULL, t.scheduled_time ASC",
            (start, end)
        )
        return cur.fetchall()


def count_today_priority(day: date) -> int:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS cnt FROM tasks WHERE scheduled_date=%s AND is_today_priority=1 AND status != 'done'",
            (day,)
        )
        return cur.fetchone()['cnt']


def count_week_priority() -> int:
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS cnt FROM tasks WHERE is_week_priority=1 AND status != 'done'")
        return cur.fetchone()['cnt']


def count_inbox() -> int:
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS cnt FROM tasks WHERE status='inbox'")
        return cur.fetchone()['cnt']
