import calendar
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, session, url_for

import models.task as task_model
import models.gcal_event as gcal_event_model
import models.crm_contact as crm_contact_model
import models.crm_company as crm_company_model

bp = Blueprint('gtd', __name__)

MONTHS_PL = {
    1: 'stycznia', 2: 'lutego', 3: 'marca', 4: 'kwietnia', 5: 'maja', 6: 'czerwca',
    7: 'lipca', 8: 'sierpnia', 9: 'września', 10: 'października', 11: 'listopada', 12: 'grudnia',
}
WEEKDAYS_PL = ('poniedziałek', 'wtorek', 'środa', 'czwartek', 'piątek', 'sobota', 'niedziela')


def _parse_date(value: str | None, fallback: date) -> date:
    if value:
        try:
            return datetime.strptime(value, '%Y-%m-%d').date()
        except ValueError:
            pass
    return fallback


def _day_label(d: date) -> str:
    return f"{WEEKDAYS_PL[d.weekday()].capitalize()}, {d.day} {MONTHS_PL[d.month]} {d.year}"


def _week_range(d: date) -> tuple[date, date]:
    monday = d - timedelta(days=d.weekday())
    return monday, monday + timedelta(days=6)


def _month_range(d: date) -> tuple[date, date]:
    start = d.replace(day=1)
    last_day = calendar.monthrange(start.year, start.month)[1]
    return start, start.replace(day=last_day)


def _add_months(d: date, n: int) -> date:
    month_index = d.month - 1 + n
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1)


def _build_timeline(tasks: list[dict], gcal_events: list[dict]) -> list[dict]:
    """Łączy wydarzenia z kalendarza i zadania zaplanowane godzinowo w jeden
    chronologiczny harmonogram (posortowany po godzinie, brak godziny na końcu
    zostawiamy tylko dla wydarzeń całodniowych)."""
    timeline = (
        [{'kind': 'gcal', 'time': e['time'], 'duration_min': e['duration_min'], 'event': e} for e in gcal_events]
        + [{'kind': 'task', 'time': _format_time(t['scheduled_time']), 'duration_min': t.get('scheduled_duration_min') or 30,
            'task': t} for t in tasks if t.get('scheduled_time')]
    )
    timeline.sort(key=lambda x: (x['time'] is None, x['time'] or ''))
    return timeline


def _day_groups(week_start: date, week_end: date, gcal_by_day: dict | None = None,
                 exclude_from_timeline: set | None = None) -> list[dict]:
    """Dzieli zadania zaplanowane na konkretne dni w danym tygodniu (plus wydarzenia
    z Google Calendar, jeśli podano) na sekcje dzień-po-dniu — tylko dni, na które
    faktycznie coś zaplanowano lub coś jest w kalendarzu. Każdy dzień dostaje wspólny
    harmonogram godzinowy (`timeline`) i listę zadań bez konkretnej godziny (`unscheduled`).
    `exclude_from_timeline` pomija zarówno w harmonogramie, jak i w liście „bez
    godziny” zadania, które są już pokazane w sekcji „Priorytety tygodnia”
    (żeby nie dublować widoku)."""
    gcal_by_day = gcal_by_day or {}
    exclude_from_timeline = exclude_from_timeline or set()
    scheduled = task_model.get_scheduled_tasks_between(week_start, week_end)
    groups = []
    d = week_start
    while d <= week_end:
        day_tasks = [t for t in scheduled if t['scheduled_date'] == d]
        day_events = gcal_by_day.get(d, [])
        if day_tasks or day_events:
            done_count = sum(1 for t in day_tasks if t['status'] == 'done') + sum(1 for e in day_events if e['is_done'])
            groups.append({
                'date': d,
                'label': _day_label(d),
                'done_count': done_count,
                'total_count': len(day_tasks) + len(day_events),
                'timeline': _build_timeline(
                    [t for t in day_tasks if t['id'] not in exclude_from_timeline], day_events),
                'unscheduled': [t for t in day_tasks
                                if not t.get('scheduled_time') and t['id'] not in exclude_from_timeline],
            })
        d += timedelta(days=1)
    return groups


WARSAW_TZ = ZoneInfo('Europe/Warsaw')


def _gcal_events_by_day(start: date, end: date) -> tuple[dict, str | None]:
    """Read-only: wydarzenia z Google Calendar w przedziale [start, end] (włącznie),
    pogrupowane po dniu. Zwraca ({}, None) jeśli integracja nie jest skonfigurowana.
    Błąd API nie ma prawa wywalić widoku dnia/tygodnia, więc jest przechwytywany —
    ale zwracany jako komunikat, żeby dało się go zobaczyć wprost w interfejsie
    zamiast szukać w logach serwera."""
    client, calendar_id = _gcal_read_client_and_calendar()
    if not client:
        return {}, None
    try:
        raw = client.get_events(calendar_id, start, end + timedelta(days=1))
    except Exception as e:
        current_app.logger.exception('GTD: błąd pobierania wydarzeń z Google Calendar (calendar_id=%s)', calendar_id)
        return {}, str(e)
    try:
        event_meta = gcal_event_model.get_event_meta(start, end)
    except Exception:
        current_app.logger.exception('GTD: błąd odczytu lokalnych metadanych wydarzeń kalendarza')
        event_meta = {}
    project_ids = {m['project_id'] for m in event_meta.values() if m.get('project_id')}
    project_titles = task_model.get_titles_by_ids(list(project_ids)) if project_ids else {}
    contact_ids = {m['crm_contact_id'] for m in event_meta.values() if m.get('crm_contact_id')}
    company_ids = {m['crm_company_id'] for m in event_meta.values() if m.get('crm_company_id')}
    contact_names = crm_contact_model.get_names_by_ids(list(contact_ids)) if contact_ids else {}
    company_names = crm_company_model.get_names_by_ids(list(company_ids)) if company_ids else {}
    by_day: dict = {}
    for e in raw:
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
            continue
        event_id = e.get('id')
        meta = event_meta.get(event_id, {})
        project_id = meta.get('project_id')
        crm_contact_id = meta.get('crm_contact_id')
        crm_company_id = meta.get('crm_company_id')
        by_day.setdefault(d, []).append({
            'id': event_id,
            'date': d.isoformat(),
            'title': e.get('summary') or '(bez tytułu)',
            'time': time_label,
            'duration_min': duration_min,
            'is_done': meta.get('is_done', False),
            'project_id': project_id,
            'project_title': project_titles.get(project_id) if project_id else None,
            'crm_contact_id': crm_contact_id,
            'crm_contact_name': contact_names.get(crm_contact_id) if crm_contact_id else None,
            'crm_company_id': crm_company_id,
            'crm_company_name': company_names.get(crm_company_id) if crm_company_id else None,
        })
    for events in by_day.values():
        events.sort(key=lambda e: (e['time'] is None, e['time'] or ''))
    return by_day, None


def _format_time(value) -> str:
    """pymysql zwraca kolumny TIME jako timedelta, nie time — ujednolica do 'HH:MM'."""
    if value is None:
        return ''
    if hasattr(value, 'strftime'):
        return value.strftime('%H:%M')
    if hasattr(value, 'total_seconds'):
        total_min = int(value.total_seconds()) // 60
        return f"{total_min // 60:02d}:{total_min % 60:02d}"
    return str(value)[:5]


# ── Widok dnia ───────────────────────────────────────────────────────────────

@bp.route('/gtd/dzis')
def day():
    day_arg = request.args.get('d')
    today = date.today()
    current = _parse_date(day_arg, today)

    tasks = task_model.get_tasks_for_day(current)
    unfinished = task_model.get_unfinished_before(current) if current == today else []
    gcal_by_day, gcal_error = _gcal_events_by_day(current, current)
    gcal_events = gcal_by_day.get(current, [])

    priority_tasks = task_model.get_today_priority_tasks(current)
    priority_ids = {t['id'] for t in priority_tasks}
    unscheduled = [t for t in tasks if not t.get('scheduled_time') and t['id'] not in priority_ids]
    timeline = _build_timeline([t for t in tasks if t['id'] not in priority_ids], gcal_events)

    return render_template(
        'gtd/day.html',
        active_tab=('jutro' if current == today + timedelta(days=1) else 'dzis'),
        current_day=current,
        current_day_label=_day_label(current),
        is_today=(current == today),
        prev_day=(current - timedelta(days=1)).isoformat(),
        next_day=(current + timedelta(days=1)).isoformat(),
        today=today,
        today_iso=today.isoformat(),
        tasks=tasks,
        unscheduled=unscheduled,
        unfinished=unfinished,
        priority_tasks=priority_tasks,
        today_star_count=task_model.count_today_priority(current),
        timeline=timeline,
        gcal_error=gcal_error,
    )


# ── Widok tygodnia ───────────────────────────────────────────────────────────

@bp.route('/gtd/tydzien')
def week():
    today = date.today()
    ref_day = _parse_date(request.args.get('start'), today)
    week_start, week_end = _week_range(ref_day)
    current_week_start = _week_range(today)[0]
    is_current_week = (week_start == current_week_start)

    priority_tasks = task_model.get_week_priority_tasks(week_start, week_end, include_unassigned=is_current_week)
    bucket_tasks = task_model.get_week_bucket_tasks(week_start)
    unfinished_weeks = task_model.get_unfinished_weeks_before(week_start)
    gcal_by_day, gcal_error = _gcal_events_by_day(week_start, week_end)
    day_groups = _day_groups(week_start, week_end, gcal_by_day,
                              exclude_from_timeline={t['id'] for t in priority_tasks})

    return render_template(
        'gtd/week.html',
        active_tab='tydzien',
        today=today,
        week_start=week_start,
        week_end=week_end,
        is_current_week=is_current_week,
        prev_week_start=(week_start - timedelta(days=7)).isoformat(),
        next_week_start=(week_start + timedelta(days=7)).isoformat(),
        current_week_start_iso=current_week_start.isoformat(),
        week_label=f"{week_start.day} {MONTHS_PL[week_start.month]} – {week_end.day} {MONTHS_PL[week_end.month]} {week_end.year}",
        priority_tasks=priority_tasks,
        bucket_tasks=bucket_tasks,
        unfinished_weeks=unfinished_weeks,
        day_groups=day_groups,
        week_star_count=task_model.count_week_priority(week_start, week_end, include_unassigned=is_current_week),
        gcal_error=gcal_error,
    )


# ── Widok miesiąca ───────────────────────────────────────────────────────────

@bp.route('/gtd/miesiac')
def month():
    today = date.today()
    ref_day = _parse_date(request.args.get('start'), today)
    month_start, month_end = _month_range(ref_day)
    current_month_start = _month_range(today)[0]
    is_current_month = (month_start == current_month_start)

    priority_tasks = task_model.get_month_priority_tasks(month_start, month_end, include_unassigned=is_current_month)
    bucket_tasks = task_model.get_month_bucket_tasks(month_start)
    unfinished_months = task_model.get_unfinished_months_before(month_start)
    gcal_by_day, gcal_error = _gcal_events_by_day(month_start, month_end)
    day_groups = _day_groups(month_start, month_end, gcal_by_day,
                              exclude_from_timeline={t['id'] for t in priority_tasks})

    return render_template(
        'gtd/month.html',
        active_tab='miesiac',
        today=today,
        month_start=month_start,
        month_end=month_end,
        is_current_month=is_current_month,
        prev_month_start=_add_months(month_start, -1).isoformat(),
        next_month_start=_add_months(month_start, 1).isoformat(),
        current_month_start_iso=current_month_start.isoformat(),
        month_label=f"{MONTHS_PL[month_start.month].capitalize()} {month_start.year}",
        priority_tasks=priority_tasks,
        bucket_tasks=bucket_tasks,
        unfinished_months=unfinished_months,
        day_groups=day_groups,
        month_star_count=task_model.count_month_priority(month_start, month_end, include_unassigned=is_current_month),
        gcal_error=gcal_error,
    )


# ── Inbox ────────────────────────────────────────────────────────────────────

@bp.route('/gtd/inbox')
def inbox():
    return render_template(
        'gtd/inbox.html', active_tab='inbox',
        tasks=task_model.get_inbox_tasks(),
    )


# ── Next actions ─────────────────────────────────────────────────────────────

@bp.route('/gtd/next')
def next_actions():
    project_id = request.args.get('project', type=int)
    return render_template(
        'gtd/next_actions.html', active_tab='next',
        tasks=task_model.get_next_actions(project_id),
        projects=task_model.get_projects(include_done=True),
        selected_project=project_id,
    )


# ── Czeka na ─────────────────────────────────────────────────────────────────

@bp.route('/gtd/czeka-na')
def waiting():
    return render_template('gtd/waiting.html', active_tab='waiting',
                            tasks=task_model.get_waiting_tasks())


# ── Archiwum ─────────────────────────────────────────────────────────────────

@bp.route('/gtd/archiwum')
def archive():
    return render_template(
        'gtd/archive.html', active_tab='archiwum',
        completed_items=task_model.get_archive_completed(),
        deleted_tasks=task_model.get_deleted_tasks(),
    )


# ── Kiedyś/może ──────────────────────────────────────────────────────────────

@bp.route('/gtd/kiedys-moze')
def someday():
    return render_template('gtd/someday.html', active_tab='someday',
                            tasks=task_model.get_someday_tasks())


# ── Projekty ─────────────────────────────────────────────────────────────────

@bp.route('/gtd/projekty')
def projects():
    return render_template('gtd/projects.html', active_tab='projekty',
                            projects=task_model.get_projects())


@bp.route('/gtd/projekty/<int:project_id>')
def project_detail(project_id):
    project = task_model.get_task(project_id)
    if not project or not project['is_project']:
        return redirect(url_for('gtd.projects'))
    return render_template(
        'gtd/project_detail.html', active_tab='projekty',
        project=project, subtasks=task_model.get_project_subtasks(project_id),
    )


# ── API: szybkie dodawanie ───────────────────────────────────────────────────

@bp.route('/api/gtd/quick_add', methods=['POST'])
def api_quick_add():
    data = request.get_json(silent=True) or {}
    title = (data.get('text') or '').strip()
    if not title:
        return jsonify({'status': 'error', 'message': 'Brak treści zadania.'})
    task_id = task_model.create_task(title, session.get('user_id'), status='inbox')
    return jsonify({'status': 'ok', 'task': task_model.get_task(task_id)})


@bp.route('/api/gtd/voice_add', methods=['POST'])
def api_voice_add():
    from models.settings import get_setting
    from services.gtd_agent import parse_task_text

    data = request.get_json(silent=True) or {}
    text = (data.get('text') or '').strip()
    if not text:
        return jsonify({'status': 'error', 'message': 'Brak transkrypcji.'})

    api_key = get_setting('gemini_api_key', '')
    model = get_setting('gemini_model', 'gemini-2.5-flash')
    if not api_key:
        return jsonify({'status': 'error', 'message': 'Brak klucza API Gemini (Ustawienia → Integracje).'})

    parsed = parse_task_text(text, api_key, date.today(), model=model)
    if 'error' in parsed:
        return jsonify({'status': 'error', 'message': parsed['error']})

    task_id = task_model.create_task(
        parsed['title'], session.get('user_id'), is_project=parsed['is_project'],
        status='inbox', due_date=parsed['due_date'] or None,
    )
    return jsonify({'status': 'ok', 'task': task_model.get_task(task_id)})


# ── API: pełny formularz dodawania (np. podzadanie projektu) ────────────────

@bp.route('/api/gtd/tasks', methods=['POST'])
def api_create_task():
    data = request.get_json(silent=True) or {}
    title = (data.get('title') or '').strip()
    if not title:
        return jsonify({'status': 'error', 'message': 'Tytuł jest wymagany.'})
    task_id = task_model.create_task(
        title, session.get('user_id'),
        is_project=bool(data.get('is_project')),
        status=data.get('status', 'inbox'),
        notes=data.get('notes'),
        parent_id=data.get('parent_id'),
        due_date=data.get('due_date') or None,
        scheduled_date=data.get('scheduled_date') or None,
        scheduled_time=data.get('scheduled_time') or None,
        scheduled_duration_min=data.get('scheduled_duration_min') or None,
        is_today_priority=data.get('is_today_priority'),
    )
    return jsonify({'status': 'ok', 'task': task_model.get_task(task_id)})


@bp.route('/api/gtd/projects')
def api_projects():
    projects = task_model.get_projects()
    return jsonify([{'id': p['id'], 'title': p['title']} for p in projects])


@bp.route('/api/gtd/tasks/<int:task_id>', methods=['PATCH'])
def api_update_task(task_id):
    data = request.get_json(silent=True) or {}
    task_model.update_task(task_id, data)
    return jsonify({'status': 'ok', 'task': task_model.get_task(task_id)})


@bp.route('/api/gtd/tasks/<int:task_id>', methods=['DELETE'])
def api_delete_task(task_id):
    task_model.delete_task(task_id)
    return jsonify({'status': 'ok'})


@bp.route('/api/gtd/tasks/<int:task_id>/restore', methods=['POST'])
def api_restore_task(task_id):
    task_model.restore_task(task_id)
    return jsonify({'status': 'ok'})


@bp.route('/api/gtd/tasks/<int:task_id>/permanent', methods=['DELETE'])
def api_permanently_delete_task(task_id):
    task_model.permanently_delete_task(task_id)
    return jsonify({'status': 'ok'})


@bp.route('/api/gtd/tasks/<int:task_id>/status', methods=['POST'])
def api_set_status(task_id):
    data = request.get_json(silent=True) or {}
    status = data.get('status', '')
    if status not in task_model.VALID_STATUSES:
        return jsonify({'status': 'error', 'message': 'Nieprawidłowy status.'})
    task_model.set_status(task_id, status)
    return jsonify({'status': 'ok', 'task': task_model.get_task(task_id)})


@bp.route('/api/gtd/gcal_events/<event_id>/done', methods=['POST'])
def api_gcal_event_done(event_id):
    data = request.get_json(silent=True) or {}
    done = bool(data.get('done'))
    if done:
        event_date = data.get('event_date')
        if not event_date:
            return jsonify({'status': 'error', 'message': 'Brak daty wydarzenia.'})
        gcal_event_model.mark_done(event_id, event_date)
    else:
        gcal_event_model.mark_undone(event_id)
    return jsonify({'status': 'ok'})


@bp.route('/api/gtd/gcal_events/<event_id>/project', methods=['POST'])
def api_gcal_event_project(event_id):
    data = request.get_json(silent=True) or {}
    event_date = data.get('event_date')
    if not event_date:
        return jsonify({'status': 'error', 'message': 'Brak daty wydarzenia.'})
    project_id = data.get('project_id') or None
    gcal_event_model.set_project(event_id, event_date, project_id)
    return jsonify({'status': 'ok'})


@bp.route('/api/gtd/gcal_events/<event_id>/crm_link', methods=['POST'])
def api_gcal_event_crm_link(event_id):
    data = request.get_json(silent=True) or {}
    event_date = data.get('event_date')
    if not event_date:
        return jsonify({'status': 'error', 'message': 'Brak daty wydarzenia.'})
    contact_id = data.get('crm_contact_id') or None
    company_id = data.get('crm_company_id') or None
    gcal_event_model.set_crm_link(event_id, event_date, contact_id, company_id)
    return jsonify({'status': 'ok'})


@bp.route('/api/gtd/crm_contacts')
def api_gtd_crm_contacts():
    contacts = crm_contact_model.get_all_contacts()
    return jsonify([
        {'id': c['id'], 'name': f"{c['first_name']} {c['last_name']}".strip()}
        for c in contacts
    ])


@bp.route('/api/gtd/crm_companies')
def api_gtd_crm_companies():
    companies = crm_company_model.get_all_companies()
    return jsonify([
        {'id': c['id'], 'name': c.get('short_name') or c['name']}
        for c in companies
    ])


@bp.route('/api/gtd/tasks/<int:project_id>/open_subtasks')
def api_open_subtasks(project_id):
    tasks = task_model.get_open_subtasks(project_id)
    return jsonify({'status': 'ok', 'tasks': tasks})


@bp.route('/api/gtd/tasks/<int:project_id>/close_project', methods=['POST'])
def api_close_project(project_id):
    data = request.get_json(silent=True) or {}
    close_subtasks = bool(data.get('close_subtasks'))
    ok = task_model.close_project(project_id, close_subtasks)
    if not ok:
        return jsonify({
            'status': 'error',
            'message': 'Projekt ma przypisane niezakończone spotkanie z kalendarza — najpierw oznacz je jako zrobione albo odepnij od projektu.',
        })
    return jsonify({'status': 'ok'})


@bp.route('/api/gtd/tasks/<int:project_id>/reopen_project', methods=['POST'])
def api_reopen_project(project_id):
    task_model.reopen_project(project_id)
    return jsonify({'status': 'ok'})


@bp.route('/api/gtd/tasks/<int:task_id>/toggle_today', methods=['POST'])
def api_toggle_today(task_id):
    new_val = task_model.toggle_today_priority(task_id)
    return jsonify({'status': 'ok', 'is_today_priority': new_val})


@bp.route('/api/gtd/tasks/<int:task_id>/toggle_week', methods=['POST'])
def api_toggle_week(task_id):
    new_val = task_model.toggle_week_priority(task_id)
    return jsonify({'status': 'ok', 'is_week_priority': new_val})


@bp.route('/api/gtd/tasks/<int:task_id>/toggle_important', methods=['POST'])
def api_toggle_important(task_id):
    new_val = task_model.toggle_project_important(task_id)
    return jsonify({'status': 'ok', 'is_important': new_val})


@bp.route('/api/gtd/tasks/<int:task_id>/schedule', methods=['POST'])
def api_schedule(task_id):
    data = request.get_json(silent=True) or {}
    scheduled_date = data.get('scheduled_date')
    if not scheduled_date:
        return jsonify({'status': 'error', 'message': 'Brak daty.'})
    task_model.schedule_task(
        task_id, scheduled_date, data.get('scheduled_time') or None,
        data.get('scheduled_duration_min') or None,
    )
    return jsonify({'status': 'ok', 'task': task_model.get_task(task_id)})


@bp.route('/api/gtd/tasks/<int:task_id>/unschedule', methods=['POST'])
def api_unschedule(task_id):
    task = task_model.get_task(task_id)
    if task and task.get('gcal_event_id'):
        _try_gcal_delete(task)
    task_model.unschedule_task(task_id)
    return jsonify({'status': 'ok'})


@bp.route('/api/gtd/tasks/<int:task_id>/move', methods=['POST'])
def api_move_task(task_id):
    data = request.get_json(silent=True) or {}
    day = _parse_date(data.get('day'), date.today())
    direction = data.get('direction')
    if direction not in ('up', 'down'):
        return jsonify({'status': 'error', 'message': 'Nieprawidłowy kierunek.'}), 400
    task_model.move_task_in_day(task_id, day, direction)
    return jsonify({'status': 'ok'})


@bp.route('/api/gtd/tasks/<int:task_id>/assign_week', methods=['POST'])
def api_assign_week(task_id):
    data = request.get_json(silent=True) or {}
    monday_str = data.get('monday')
    week = data.get('week')
    if monday_str:
        try:
            monday = _week_range(datetime.strptime(monday_str, '%Y-%m-%d').date())[0]
        except ValueError:
            return jsonify({'status': 'error', 'message': 'Nieprawidłowa data.'})
    elif week in ('this', 'next'):
        base = _week_range(date.today())[0]
        monday = base + (timedelta(weeks=1) if week == 'next' else timedelta())
    else:
        return jsonify({'status': 'error', 'message': 'Nieprawidłowy tydzień.'})
    task = task_model.get_task(task_id)
    if task and task.get('gcal_event_id'):
        _try_gcal_delete(task)
    task_model.assign_week(task_id, monday)
    return jsonify({'status': 'ok', 'task': task_model.get_task(task_id)})


@bp.route('/api/gtd/tasks/<int:task_id>/clear_week', methods=['POST'])
def api_clear_week(task_id):
    task_model.clear_week(task_id)
    return jsonify({'status': 'ok'})


@bp.route('/api/gtd/tasks/<int:task_id>/assign_month', methods=['POST'])
def api_assign_month(task_id):
    data = request.get_json(silent=True) or {}
    month_str = data.get('month')
    if not month_str:
        return jsonify({'status': 'error', 'message': 'Brak miesiąca.'})
    try:
        month_start = _month_range(datetime.strptime(month_str, '%Y-%m-%d').date())[0]
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Nieprawidłowa data.'})
    task = task_model.get_task(task_id)
    if task and task.get('gcal_event_id'):
        _try_gcal_delete(task)
    task_model.assign_month(task_id, month_start)
    return jsonify({'status': 'ok', 'task': task_model.get_task(task_id)})


@bp.route('/api/gtd/tasks/<int:task_id>/clear_month', methods=['POST'])
def api_clear_month(task_id):
    task_model.clear_month(task_id)
    return jsonify({'status': 'ok'})


@bp.route('/api/gtd/tasks/<int:task_id>/convert_project', methods=['POST'])
def api_convert_project(task_id):
    task_model.convert_to_project(task_id)
    return jsonify({'status': 'ok', 'task': task_model.get_task(task_id)})


@bp.route('/api/gtd/tasks/<int:task_id>/flatten_project', methods=['POST'])
def api_flatten_project(task_id):
    task_model.flatten_project(task_id)
    return jsonify({'status': 'ok'})


# ── API: integracja z Google Calendar (jednokierunkowy push zablokowanego czasu) ──

def _gcal_client_and_calendar():
    from models.settings import get_setting
    from services.google_calendar import GoogleCalendarClient

    token = get_setting('google_drive_api_token', '')
    calendar_id = get_setting('gtd_gcal_calendar_id', '')
    if not token or not calendar_id:
        return None, None
    return GoogleCalendarClient(token), calendar_id


def _gcal_read_client_and_calendar():
    """Osobny, tylko-do-odczytu kalendarz (np. Twój główny kalendarz udostępniony
    kontu usługi) — celowo inny niż kalendarz „Zadania” używany do zapisu."""
    from models.settings import get_setting
    from services.google_calendar import GoogleCalendarClient

    token = get_setting('google_drive_api_token', '')
    calendar_id = get_setting('gtd_gcal_read_calendar_id', '')
    if not token or not calendar_id:
        return None, None
    return GoogleCalendarClient(token), calendar_id


def _try_gcal_delete(task: dict) -> None:
    client, calendar_id = _gcal_client_and_calendar()
    if not client or not task.get('gcal_event_id'):
        return
    try:
        client.delete_task_event(calendar_id, task['gcal_event_id'])
    except Exception:
        pass


@bp.route('/api/gtd/tasks/<int:task_id>/gcal_push', methods=['POST'])
def api_gcal_push(task_id):
    task = task_model.get_task(task_id)
    if not task or not task.get('scheduled_date') or not task.get('scheduled_time'):
        return jsonify({'status': 'error', 'message': 'Zadanie musi mieć zaplanowaną datę i godzinę.'})

    client, calendar_id = _gcal_client_and_calendar()
    if not client:
        return jsonify({'status': 'error', 'message':
                         'Skonfiguruj Google Calendar w Ustawieniach → Integracje.'})

    duration = task.get('scheduled_duration_min') or 30
    time_str = _format_time(task['scheduled_time'])
    sched_date = task['scheduled_date']

    try:
        event = client.upsert_task_event(
            calendar_id, task.get('gcal_event_id'), task['title'],
            sched_date, time_str, duration, task.get('notes') or '',
        )
        task_model.set_gcal_event_id(task_id, event.get('id'))
        return jsonify({'status': 'ok', 'task': task_model.get_task(task_id)})
    except Exception as exc:
        return jsonify({'status': 'error', 'message': f'Błąd Google Calendar: {exc}'})


@bp.route('/api/gtd/day/<day_iso>/busy', methods=['GET'])
def api_day_busy(day_iso):
    client, _ = _gcal_client_and_calendar()
    if not client:
        return jsonify({'status': 'ok', 'events': []})
    try:
        d = datetime.strptime(day_iso, '%Y-%m-%d').date()
        events = client.get_busy_events('primary', d)
        simplified = [{
            'title': e.get('summary', '(bez tytułu)'),
            'start': e.get('start', {}).get('dateTime') or e.get('start', {}).get('date'),
            'end': e.get('end', {}).get('dateTime') or e.get('end', {}).get('date'),
        } for e in events]
        return jsonify({'status': 'ok', 'events': simplified})
    except Exception:
        return jsonify({'status': 'ok', 'events': []})
