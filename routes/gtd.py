from datetime import date, datetime, timedelta

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

import models.task as task_model

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


def _day_groups(week_start: date, week_end: date) -> list[dict]:
    """Dzieli zadania zaplanowane na konkretne dni w danym tygodniu na sekcje
    dzień-po-dniu — tylko dni, na które faktycznie coś zaplanowano."""
    scheduled = task_model.get_scheduled_tasks_between(week_start, week_end)
    groups = []
    d = week_start
    while d <= week_end:
        day_tasks = [t for t in scheduled if t['scheduled_date'] == d]
        if day_tasks:
            groups.append({'date': d, 'label': _day_label(d), 'tasks': day_tasks})
        d += timedelta(days=1)
    return groups


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

    return render_template(
        'gtd/day.html',
        active_tab='dzis',
        current_day=current,
        current_day_label=_day_label(current),
        is_today=(current == today),
        prev_day=(current - timedelta(days=1)).isoformat(),
        next_day=(current + timedelta(days=1)).isoformat(),
        today=today,
        today_iso=today.isoformat(),
        tasks=tasks,
        unfinished=unfinished,
        today_star_count=task_model.count_today_priority(current),
    )


# ── Widok tygodnia ───────────────────────────────────────────────────────────

@bp.route('/gtd/tydzien')
def week():
    today = date.today()
    week_start, week_end = _week_range(today)
    priority_tasks = task_model.get_week_priority_tasks()
    bucket_tasks = task_model.get_week_bucket_tasks(week_start)
    unfinished_weeks = task_model.get_unfinished_weeks_before(week_start)
    day_groups = _day_groups(week_start, week_end)

    return render_template(
        'gtd/week.html',
        active_tab='tydzien',
        week_start=week_start,
        week_end=week_end,
        week_label=f"{week_start.day} {MONTHS_PL[week_start.month]} – {week_end.day} {MONTHS_PL[week_end.month]} {week_end.year}",
        priority_tasks=priority_tasks,
        bucket_tasks=bucket_tasks,
        unfinished_weeks=unfinished_weeks,
        day_groups=day_groups,
        week_star_count=task_model.count_week_priority(),
    )


@bp.route('/gtd/przyszly-tydzien')
def next_week():
    next_monday = _week_range(date.today())[0] + timedelta(days=7)
    week_end = next_monday + timedelta(days=6)
    bucket_tasks = task_model.get_week_bucket_tasks(next_monday)
    day_groups = _day_groups(next_monday, week_end)

    return render_template(
        'gtd/next_week.html',
        active_tab='przyszly_tydzien',
        week_start=next_monday,
        week_end=week_end,
        week_label=f"{next_monday.day} {MONTHS_PL[next_monday.month]} – {week_end.day} {MONTHS_PL[week_end.month]} {week_end.year}",
        bucket_tasks=bucket_tasks,
        day_groups=day_groups,
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


# ── Ukończone ────────────────────────────────────────────────────────────────

@bp.route('/gtd/ukonczone')
def completed():
    return render_template('gtd/completed.html', active_tab='ukonczone',
                            tasks=task_model.get_completed_tasks())


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


@bp.route('/api/gtd/tasks/<int:task_id>', methods=['PATCH'])
def api_update_task(task_id):
    data = request.get_json(silent=True) or {}
    task_model.update_task(task_id, data)
    return jsonify({'status': 'ok', 'task': task_model.get_task(task_id)})


@bp.route('/api/gtd/tasks/<int:task_id>', methods=['DELETE'])
def api_delete_task(task_id):
    task_model.delete_task(task_id)
    return jsonify({'status': 'ok'})


@bp.route('/api/gtd/tasks/<int:task_id>/status', methods=['POST'])
def api_set_status(task_id):
    data = request.get_json(silent=True) or {}
    status = data.get('status', '')
    if status not in task_model.VALID_STATUSES:
        return jsonify({'status': 'error', 'message': 'Nieprawidłowy status.'})
    task_model.set_status(task_id, status)
    return jsonify({'status': 'ok', 'task': task_model.get_task(task_id)})


@bp.route('/api/gtd/tasks/<int:task_id>/toggle_today', methods=['POST'])
def api_toggle_today(task_id):
    new_val = task_model.toggle_today_priority(task_id)
    return jsonify({'status': 'ok', 'is_today_priority': new_val})


@bp.route('/api/gtd/tasks/<int:task_id>/toggle_week', methods=['POST'])
def api_toggle_week(task_id):
    new_val = task_model.toggle_week_priority(task_id)
    return jsonify({'status': 'ok', 'is_week_priority': new_val})


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


@bp.route('/api/gtd/tasks/<int:task_id>/assign_week', methods=['POST'])
def api_assign_week(task_id):
    data = request.get_json(silent=True) or {}
    week = data.get('week')
    if week not in ('this', 'next'):
        return jsonify({'status': 'error', 'message': 'Nieprawidłowy tydzień.'})
    task = task_model.get_task(task_id)
    if task and task.get('gcal_event_id'):
        _try_gcal_delete(task)
    task_model.assign_week(task_id, 0 if week == 'this' else 1)
    return jsonify({'status': 'ok', 'task': task_model.get_task(task_id)})


@bp.route('/api/gtd/tasks/<int:task_id>/clear_week', methods=['POST'])
def api_clear_week(task_id):
    task_model.clear_week(task_id)
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
