from datetime import date, datetime, timedelta

from database import get_db

VALID_STATUSES = ('inbox', 'next', 'waiting', 'someday', 'done')

STATUS_LABELS = {
    'inbox': 'Inbox',
    'next': 'Next actions',
    'waiting': 'Czeka na',
    'someday': 'Kiedyś/może',
    'done': 'Zrobione',
}

_LIST_FIELDS = """t.*, p.title AS project_title,
                  cc.first_name AS crm_contact_first_name, cc.last_name AS crm_contact_last_name,
                  cco.name AS crm_company_name, cco.short_name AS crm_company_short_name"""

_LIST_JOINS = """FROM tasks t
                 LEFT JOIN tasks p ON p.id = t.parent_id
                 LEFT JOIN crm_contacts cc ON cc.id = t.crm_contact_id
                 LEFT JOIN crm_companies cco ON cco.id = t.crm_company_id"""


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
                   (title, notes, is_project, parent_id, status, waiting_on,
                    due_date, scheduled_date, scheduled_time, scheduled_duration_min,
                    is_today_priority, is_week_priority, created_by)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    title,
                    fields.get('notes') or None,
                    1 if is_project else 0,
                    fields.get('parent_id') or None,
                    status if status in VALID_STATUSES else 'inbox',
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
    allowed = ('title', 'notes', 'status', 'waiting_on', 'due_date',
               'scheduled_date', 'scheduled_time', 'scheduled_duration_min',
               'parent_id', 'crm_contact_id', 'crm_company_id')
    fields = {k: v for k, v in data.items() if k in allowed}
    if not fields:
        return
    if 'parent_id' in fields:
        fields['parent_id'] = fields['parent_id'] or None
    if 'crm_contact_id' in fields:
        fields['crm_contact_id'] = fields['crm_contact_id'] or None
    if 'crm_company_id' in fields:
        fields['crm_company_id'] = fields['crm_company_id'] or None
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


def close_project(project_id: int, close_subtasks: bool = False) -> bool:
    """Ręcznie zamyka projekt — projekty nigdy nie zamykają się automatycznie.
    Zwraca False, jeśli projekt ma przypisane niezakończone spotkanie z kalendarza
    (wtedy zamknięcie jest zablokowane, dopóki spotkanie nie zostanie oznaczone
    jako zrobione albo odpięte od projektu). Gdy close_subtasks=True, wszystkie
    wciąż otwarte podzadania zostają zamknięte razem z projektem."""
    db = get_db()
    try:
        with db.cursor() as cur:
            try:
                cur.execute(
                    "SELECT 1 FROM gcal_event_done WHERE project_id=%s AND done_at IS NULL LIMIT 1",
                    (project_id,)
                )
                if cur.fetchone() is not None:
                    return False
            except Exception:
                pass
            if close_subtasks:
                cur.execute(
                    "UPDATE tasks SET status='done', completed_at=NOW() "
                    "WHERE parent_id=%s AND deleted_at IS NULL AND status != 'done'",
                    (project_id,)
                )
            cur.execute(
                "UPDATE tasks SET status='done', completed_at=NOW() WHERE id=%s",
                (project_id,)
            )
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise


def reopen_project(project_id: int) -> None:
    """Ręcznie otwiera ponownie zamknięty projekt (nie dotyka statusu podzadań)."""
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "UPDATE tasks SET status='next', completed_at=NULL WHERE id=%s",
                (project_id,)
            )
        db.commit()
    except Exception:
        db.rollback()
        raise


def get_open_subtasks(project_id: int) -> list[dict]:
    """Otwarte (nieukończone, nieusunięte) podzadania projektu — do okna
    potwierdzenia przy zamykaniu projektu."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT id, title FROM tasks WHERE parent_id=%s AND deleted_at IS NULL "
            "AND status != 'done' ORDER BY created_at",
            (project_id,)
        )
        return cur.fetchall()


def delete_task(task_id: int) -> None:
    """Miękkie usunięcie — zadanie trafia do Archiwum → Usunięte, skąd można je
    przywrócić lub skasować trwale. Podzadania projektu zostają odłączone (jak dawniej),
    nie są usuwane razem z nim."""
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("UPDATE tasks SET parent_id=NULL WHERE parent_id=%s", (task_id,))
            cur.execute("UPDATE tasks SET deleted_at=NOW() WHERE id=%s", (task_id,))
        db.commit()
    except Exception:
        db.rollback()
        raise


def restore_task(task_id: int) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("UPDATE tasks SET deleted_at=NULL WHERE id=%s", (task_id,))
        db.commit()
    except Exception:
        db.rollback()
        raise


def permanently_delete_task(task_id: int) -> None:
    """Trwałe skasowanie — dozwolone tylko dla pozycji już miękko usuniętych."""
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("DELETE FROM tasks WHERE id=%s AND deleted_at IS NOT NULL", (task_id,))
        db.commit()
    except Exception:
        db.rollback()
        raise


def set_status(task_id: int, status: str) -> bool:
    """Ustawia status zwykłego zadania. Do zamykania/otwierania projektów służą
    dedykowane close_project()/reopen_project() (uwzględniają otwarte podzadania
    i przypisane spotkania z kalendarza)."""
    if status not in VALID_STATUSES:
        return False
    db = get_db()
    try:
        with db.cursor() as cur:
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
        db.commit()
        return True
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
            f"SELECT {_LIST_FIELDS} {_LIST_JOINS} WHERE t.status='inbox' AND t.deleted_at IS NULL "
            f"ORDER BY t.created_at DESC, t.id DESC"
        )
        return cur.fetchall()


def get_next_actions(project_id: int | None = None) -> list[dict]:
    db = get_db()
    sql = f"SELECT {_LIST_FIELDS} {_LIST_JOINS} WHERE t.status='next' AND t.is_project=0 AND t.deleted_at IS NULL"
    params = []
    if project_id:
        sql += " AND t.parent_id=%s"
        params.append(project_id)
    sql += " ORDER BY t.due_date IS NULL, t.due_date ASC, t.id DESC"
    with db.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def get_waiting_tasks() -> list[dict]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            f"SELECT {_LIST_FIELDS} {_LIST_JOINS} WHERE t.status='waiting' AND t.deleted_at IS NULL "
            f"ORDER BY t.updated_at DESC, t.id DESC"
        )
        return cur.fetchall()


def get_someday_tasks() -> list[dict]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            f"SELECT {_LIST_FIELDS} {_LIST_JOINS} WHERE t.status='someday' AND t.deleted_at IS NULL "
            f"ORDER BY t.created_at DESC, t.id DESC"
        )
        return cur.fetchall()


def get_projects(include_done: bool = False) -> list[dict]:
    db = get_db()
    sql = f"SELECT {_LIST_FIELDS} {_LIST_JOINS} WHERE t.is_project=1 AND t.deleted_at IS NULL"
    if not include_done:
        sql += " AND t.status != 'done'"
    sql += " ORDER BY t.created_at DESC, t.id DESC"
    with db.cursor() as cur:
        cur.execute(sql)
        projects = cur.fetchall()
        for proj in projects:
            cur.execute(
                "SELECT COUNT(*) AS total, SUM(status='done') AS done "
                "FROM tasks WHERE parent_id=%s AND deleted_at IS NULL",
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
            f"SELECT {_LIST_FIELDS} {_LIST_JOINS} WHERE t.parent_id=%s AND t.deleted_at IS NULL "
            f"ORDER BY (t.status='done'), t.due_date IS NULL, t.due_date ASC, t.id ASC",
            (project_id,)
        )
        return cur.fetchall()


def get_tasks_for_day(day: date) -> list[dict]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            f"SELECT {_LIST_FIELDS} {_LIST_JOINS} WHERE t.scheduled_date=%s AND t.deleted_at IS NULL "
            f"ORDER BY t.scheduled_time IS NULL, t.scheduled_time ASC, "
            f"t.day_order ASC, t.is_today_priority DESC, t.id ASC",
            (day,)
        )
        return cur.fetchall()


def move_task_in_day(task_id: int, day: date, direction: str) -> None:
    """Zamienia miejscami zadanie z sąsiadem na liście zadań bez konkretnej
    godziny w danym dniu (ręczna kolejność, `day_order` normalizowany do 0..n-1
    przy każdym przesunięciu)."""
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "SELECT id FROM tasks WHERE scheduled_date=%s AND scheduled_time IS NULL "
                "AND deleted_at IS NULL ORDER BY day_order ASC, is_today_priority DESC, id ASC",
                (day,)
            )
            ids = [row['id'] for row in cur.fetchall()]
            if task_id not in ids:
                return
            idx = ids.index(task_id)
            swap_idx = idx - 1 if direction == 'up' else idx + 1
            if swap_idx < 0 or swap_idx >= len(ids):
                return
            ids[idx], ids[swap_idx] = ids[swap_idx], ids[idx]
            for i, tid in enumerate(ids):
                cur.execute("UPDATE tasks SET day_order=%s WHERE id=%s", (i, tid))
        db.commit()
    except Exception:
        db.rollback()
        raise


def get_unfinished_before(day: date, limit: int = 20) -> list[dict]:
    """Niedokończone zadania zaplanowane na dni przed `day` — do sekcji przeglądu,
    nigdy nie przenoszone automatycznie (zgodnie z filozofią GTD: nic nie dzieje
    się w tle, użytkownik świadomie decyduje co dalej)."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            f"SELECT {_LIST_FIELDS} {_LIST_JOINS} "
            f"WHERE t.scheduled_date < %s AND t.status != 'done' AND t.deleted_at IS NULL "
            f"ORDER BY t.scheduled_date DESC, t.id DESC LIMIT %s",
            (day, limit)
        )
        return cur.fetchall()


def get_week_priority_tasks(monday: date, sunday: date, include_unassigned: bool = False) -> list[dict]:
    """Priorytety tygodnia (gwiazdka) należące do danego tygodnia (blok tygodniowy lub
    konkretny dzień mieszczący się w zakresie) — zadania zrobione zostają widoczne.
    `include_unassigned` dokłada priorytety bez żadnego przypisania do tygodnia/dnia
    (domyślnie lądują w widoku 'Ten tydzień')."""
    db = get_db()
    with db.cursor() as cur:
        clause = "(t.planned_week=%s OR (t.scheduled_date BETWEEN %s AND %s))"
        params = [monday, monday, sunday]
        if include_unassigned:
            clause = f"({clause} OR (t.planned_week IS NULL AND t.scheduled_date IS NULL))"
        cur.execute(
            f"SELECT {_LIST_FIELDS} {_LIST_JOINS} WHERE t.is_week_priority=1 AND t.deleted_at IS NULL AND {clause} "
            f"ORDER BY (t.status='done'), t.due_date IS NULL, t.due_date ASC, t.id DESC",
            tuple(params)
        )
        return cur.fetchall()


def get_unfinished_weeks_before(monday: date, limit: int = 20) -> list[dict]:
    """Zadania z blokiem tygodniowym sprzed `monday`, wciąż nieukończone — do sekcji
    przeglądu na stronie 'Ten tydzień', nigdy nie przenoszone automatycznie (jak przy dniach)."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            f"SELECT {_LIST_FIELDS} {_LIST_JOINS} "
            f"WHERE t.planned_week < %s AND t.status != 'done' AND t.deleted_at IS NULL "
            f"ORDER BY t.planned_week DESC, t.id DESC LIMIT %s",
            (monday, limit)
        )
        return cur.fetchall()


def get_week_bucket_tasks(monday: date) -> list[dict]:
    """Zadania przypisane do luźnego bloku tygodniowego (bez konkretnego dnia).
    Zadania zrobione zostają widoczne (nie znikają z widoku tygodnia)."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            f"SELECT {_LIST_FIELDS} {_LIST_JOINS} WHERE t.planned_week=%s AND t.deleted_at IS NULL "
            f"ORDER BY (t.status='done'), t.due_date IS NULL, t.due_date ASC, t.id DESC",
            (monday,)
        )
        return cur.fetchall()


def get_archive_completed(limit: int = 300) -> list[dict]:
    """Lista dla Archiwum → Zakończone: samodzielne ukończone zadania oraz projekty.
    Projekt trafia tu tylko, gdy jest ręcznie/automatycznie oznaczony jako 'done'
    (wtedy pokazuje się na zielono), albo ma co najmniej jedno ukończone podzadanie
    (wtedy na biało, w trakcie). Puste projekty (bez podzadań) i te z samymi
    nieukończonymi zadaniami nie trafiają tu, chyba że są oznaczone jako 'done'.
    Wszystko posortowane razem po ostatniej aktywności (data ukończenia zadania /
    projektu, albo — dla projektów w trakcie — data ukończenia ich najnowszego
    podzadania)."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            f"SELECT {_LIST_FIELDS} {_LIST_JOINS} WHERE t.is_project=0 AND t.parent_id IS NULL "
            f"AND t.status='done' AND t.deleted_at IS NULL "
            f"ORDER BY t.completed_at DESC, t.id DESC LIMIT %s",
            (limit,)
        )
        tasks = cur.fetchall()

        cur.execute(
            f"SELECT {_LIST_FIELDS} {_LIST_JOINS} WHERE t.is_project=1 AND t.deleted_at IS NULL "
            f"ORDER BY t.created_at DESC, t.id DESC"
        )
        all_projects = cur.fetchall()
        projects = []
        for proj in all_projects:
            cur.execute(
                "SELECT COUNT(*) AS total, SUM(status='done') AS done, MAX(completed_at) AS last_done "
                "FROM tasks WHERE parent_id=%s AND deleted_at IS NULL",
                (proj['id'],)
            )
            counts = cur.fetchone()
            total = counts['total'] or 0
            done = counts['done'] or 0
            if proj['status'] != 'done' and done == 0:
                continue  # ani ukończony ręcznie/automatycznie, ani ma ukończone podzadania — pomijamy
            proj['subtask_total'] = total
            proj['subtask_done'] = done
            proj['sort_key'] = counts['last_done'] or proj['completed_at'] or proj['created_at']
            if done:
                cur.execute(
                    f"SELECT {_LIST_FIELDS} {_LIST_JOINS} WHERE t.parent_id=%s AND t.status='done' "
                    f"AND t.deleted_at IS NULL ORDER BY t.completed_at DESC, t.id DESC",
                    (proj['id'],)
                )
                proj['completed_subtasks'] = cur.fetchall()
            else:
                proj['completed_subtasks'] = []
            projects.append(proj)

        items = [{'kind': 'task', 'sort_key': t['completed_at'], 'task': t} for t in tasks]
        items += [{'kind': 'project', 'sort_key': p['sort_key'], 'project': p} for p in projects]
        items.sort(key=lambda x: x['sort_key'] or datetime.min, reverse=True)
        return items[:limit]


def get_deleted_tasks(limit: int = 300) -> list[dict]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            f"SELECT {_LIST_FIELDS} {_LIST_JOINS} WHERE t.deleted_at IS NOT NULL "
            f"ORDER BY t.deleted_at DESC, t.id DESC LIMIT %s",
            (limit,)
        )
        return cur.fetchall()


def get_scheduled_tasks_between(start: date, end: date) -> list[dict]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            f"SELECT {_LIST_FIELDS} {_LIST_JOINS} "
            f"WHERE t.scheduled_date BETWEEN %s AND %s AND t.deleted_at IS NULL "
            f"ORDER BY t.scheduled_date ASC, t.scheduled_time IS NULL, t.scheduled_time ASC",
            (start, end)
        )
        return cur.fetchall()


def get_today_priority_tasks(day: date) -> list[dict]:
    """Priorytety dnia (gwiazdka) zaplanowane na dany dzień — zadania zrobione
    zostają widoczne (nie znikają z listy)."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            f"SELECT {_LIST_FIELDS} {_LIST_JOINS} "
            f"WHERE t.is_today_priority=1 AND t.scheduled_date=%s AND t.deleted_at IS NULL "
            f"ORDER BY (t.status='done'), t.scheduled_time IS NULL, t.scheduled_time ASC, t.id DESC",
            (day,)
        )
        return cur.fetchall()


def count_today_priority(day: date) -> int:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS cnt FROM tasks WHERE scheduled_date=%s AND is_today_priority=1 "
            "AND status != 'done' AND deleted_at IS NULL",
            (day,)
        )
        return cur.fetchone()['cnt']


def count_week_priority(monday: date, sunday: date, include_unassigned: bool = False) -> int:
    db = get_db()
    with db.cursor() as cur:
        clause = "(planned_week=%s OR (scheduled_date BETWEEN %s AND %s))"
        params = [monday, monday, sunday]
        if include_unassigned:
            clause = f"({clause} OR (planned_week IS NULL AND scheduled_date IS NULL))"
        cur.execute(
            f"SELECT COUNT(*) AS cnt FROM tasks WHERE is_week_priority=1 AND status != 'done' "
            f"AND deleted_at IS NULL AND {clause}",
            tuple(params)
        )
        return cur.fetchone()['cnt']


def count_inbox() -> int:
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS cnt FROM tasks WHERE status='inbox' AND deleted_at IS NULL")
        return cur.fetchone()['cnt']


def get_tasks_for_crm(contact_id: int | None = None, company_id: int | None = None) -> list[dict]:
    """Zadania/projekty przypisane do kontaktu lub firmy CRM — do sekcji
    „Zadania/Projekty/Spotkania” na karcie kontaktu/firmy."""
    if not contact_id and not company_id:
        return []
    db = get_db()
    with db.cursor() as cur:
        if contact_id:
            cur.execute(
                "SELECT id, title, is_project, status, due_date, completed_at, created_at "
                "FROM tasks WHERE crm_contact_id=%s AND deleted_at IS NULL ORDER BY created_at DESC",
                (contact_id,)
            )
        else:
            cur.execute(
                "SELECT id, title, is_project, status, due_date, completed_at, created_at "
                "FROM tasks WHERE crm_company_id=%s AND deleted_at IS NULL ORDER BY created_at DESC",
                (company_id,)
            )
        return cur.fetchall()


def get_titles_by_ids(ids: list[int]) -> dict[int, str]:
    if not ids:
        return {}
    db = get_db()
    with db.cursor() as cur:
        placeholders = ','.join(['%s'] * len(ids))
        cur.execute(f"SELECT id, title FROM tasks WHERE id IN ({placeholders})", tuple(ids))
        return {row['id']: row['title'] for row in cur.fetchall()}
