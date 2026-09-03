/* ── Odświeżenie treści strony GTD bez przeładowania (po dodaniu zadania) ──
   Pobiera aktualny widok przez fetch, podmienia #gtdContent świeżo wyrenderowaną
   treścią z serwera (ta sama logika co przy zwykłym GET, więc listy/liczniki
   zostają poprawnie przeliczone) i, jeśli podano, ustawia focus z powrotem
   w polu dodawania, żeby można było od razu wpisać kolejne zadanie. */
function gtdRefreshContent(focusInputId) {
  const container = document.getElementById('gtdContent');
  if (!container) { location.reload(); return; }
  fetch(window.location.href)
    .then(r => r.text())
    .then(html => {
      const fresh = new DOMParser().parseFromString(html, 'text/html').getElementById('gtdContent');
      if (!fresh) { location.reload(); return; }
      container.innerHTML = fresh.innerHTML;
      if (focusInputId) {
        const input = document.getElementById(focusInputId);
        if (input) input.focus();
      }
    })
    .catch(() => location.reload());
}

/* ── Akcje na zadaniach (używane przez onclick w widokach listy) ── */
function gtdToggleDone(taskId, checked, prevStatus) {
  const status = checked ? 'done' : prevStatus;
  fetch(window.API_BASE + '/api/gtd/tasks/' + taskId + '/status', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  })
    .then(r => r.json())
    .then(data => { if (data.status === 'ok') location.reload(); else alert(data.message || 'Błąd.'); })
    .catch(() => alert('Błąd sieci.'));
}

function gtdToggleGcalDone(eventId, eventDate, done) {
  fetch(window.API_BASE + '/api/gtd/gcal_events/' + encodeURIComponent(eventId) + '/done', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ event_date: eventDate, done }),
  })
    .then(r => r.json())
    .then(data => { if (data.status === 'ok') location.reload(); else alert(data.message || 'Błąd.'); })
    .catch(() => alert('Błąd sieci.'));
}

function gtdToggleGcalStar(eventId, eventDate) {
  fetch(window.API_BASE + '/api/gtd/gcal_events/' + encodeURIComponent(eventId) + '/toggle_today', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ event_date: eventDate }),
  })
    .then(r => r.json())
    .then(data => { if (data.status === 'ok') location.reload(); else alert(data.message || 'Błąd.'); })
    .catch(() => alert('Błąd sieci.'));
}

function gtdToggleStar(taskId, urlSuffix) {
  fetch(window.API_BASE + '/api/gtd/tasks/' + taskId + '/' + urlSuffix, { method: 'POST' })
    .then(r => r.json())
    .then(data => { if (data.status === 'ok') location.reload(); else alert(data.message || 'Błąd.'); })
    .catch(() => alert('Błąd sieci.'));
}

function gtdSetStatus(taskId, status) {
  fetch(window.API_BASE + '/api/gtd/tasks/' + taskId + '/status', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  })
    .then(r => r.json())
    .then(data => { if (data.status === 'ok') location.reload(); else alert(data.message || 'Błąd.'); })
    .catch(() => alert('Błąd sieci.'));
}

function gtdSetWaiting(taskId) {
  const waitingOn = window.prompt('Na co/kogo czekasz?', '');
  if (waitingOn === null) return;
  fetch(window.API_BASE + '/api/gtd/tasks/' + taskId, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status: 'waiting', waiting_on: waitingOn }),
  })
    .then(r => r.json())
    .then(data => { if (data.status === 'ok') location.reload(); else alert(data.message || 'Błąd.'); })
    .catch(() => alert('Błąd sieci.'));
}

function gtdUnwait(taskId) {
  fetch(window.API_BASE + '/api/gtd/tasks/' + taskId, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status: 'next', waiting_on: null }),
  })
    .then(r => r.json())
    .then(data => { if (data.status === 'ok') location.reload(); else alert(data.message || 'Błąd.'); })
    .catch(() => alert('Błąd sieci.'));
}

function gtdScheduleToday(taskId) {
  const today = new Date().toISOString().slice(0, 10);
  fetch(window.API_BASE + '/api/gtd/tasks/' + taskId + '/schedule', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scheduled_date: today }),
  })
    .then(r => r.json())
    .then(data => { if (data.status === 'ok') location.reload(); else alert(data.message || 'Błąd.'); })
    .catch(() => alert('Błąd sieci.'));
}

function gtdScheduleDay(taskId, dayIso) {
  fetch(window.API_BASE + '/api/gtd/tasks/' + taskId + '/schedule', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scheduled_date: dayIso }),
  })
    .then(r => r.json())
    .then(data => { if (data.status === 'ok') location.reload(); else alert(data.message || 'Błąd.'); })
    .catch(() => alert('Błąd sieci.'));
}

function gtdScheduleTomorrow(taskId) {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  const tomorrow = d.toISOString().slice(0, 10);
  fetch(window.API_BASE + '/api/gtd/tasks/' + taskId + '/schedule', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scheduled_date: tomorrow }),
  })
    .then(r => r.json())
    .then(data => { if (data.status === 'ok') location.reload(); else alert(data.message || 'Błąd.'); })
    .catch(() => alert('Błąd sieci.'));
}

function gtdAssignWeek(taskId, weekOrMonday) {
  const isDate = /^\d{4}-\d{2}-\d{2}$/.test(weekOrMonday);
  fetch(window.API_BASE + '/api/gtd/tasks/' + taskId + '/assign_week', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(isDate ? { monday: weekOrMonday } : { week: weekOrMonday }),
  })
    .then(r => r.json())
    .then(data => { if (data.status === 'ok') location.reload(); else alert(data.message || 'Błąd.'); })
    .catch(() => alert('Błąd sieci.'));
}

function gtdClearWeek(taskId) {
  fetch(window.API_BASE + '/api/gtd/tasks/' + taskId + '/clear_week', { method: 'POST' })
    .then(r => r.json())
    .then(data => { if (data.status === 'ok') location.reload(); else alert(data.message || 'Błąd.'); })
    .catch(() => alert('Błąd sieci.'));
}

function gtdAssignMonth(taskId, monthStart) {
  fetch(window.API_BASE + '/api/gtd/tasks/' + taskId + '/assign_month', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ month: monthStart }),
  })
    .then(r => r.json())
    .then(data => { if (data.status === 'ok') location.reload(); else alert(data.message || 'Błąd.'); })
    .catch(() => alert('Błąd sieci.'));
}

function gtdClearMonth(taskId) {
  fetch(window.API_BASE + '/api/gtd/tasks/' + taskId + '/clear_month', { method: 'POST' })
    .then(r => r.json())
    .then(data => { if (data.status === 'ok') location.reload(); else alert(data.message || 'Błąd.'); })
    .catch(() => alert('Błąd sieci.'));
}

function gtdUnschedule(taskId) {
  fetch(window.API_BASE + '/api/gtd/tasks/' + taskId + '/unschedule', { method: 'POST' })
    .then(r => r.json())
    .then(data => { if (data.status === 'ok') location.reload(); else alert(data.message || 'Błąd.'); })
    .catch(() => alert('Błąd sieci.'));
}

function gtdMoveTask(taskId, day, direction) {
  fetch(window.API_BASE + '/api/gtd/tasks/' + taskId + '/move', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ day, direction }),
  })
    .then(r => r.json())
    .then(data => { if (data.status === 'ok') location.reload(); else alert(data.message || 'Błąd.'); })
    .catch(() => alert('Błąd sieci.'));
}

function gtdConvertToProject(taskId) {
  if (!confirm('Zamienić to zadanie w projekt?')) return;
  fetch(window.API_BASE + '/api/gtd/tasks/' + taskId + '/convert_project', { method: 'POST' })
    .then(r => r.json())
    .then(data => { if (data.status === 'ok') location.reload(); else alert(data.message || 'Błąd.'); })
    .catch(() => alert('Błąd sieci.'));
}

function gtdFlattenProject(taskId) {
  if (!confirm('Cofnąć projekt do zwykłego zadania? Podzadania zostaną odpięte, ale nie usunięte.')) return;
  fetch(window.API_BASE + '/api/gtd/tasks/' + taskId + '/flatten_project', { method: 'POST' })
    .then(r => r.json())
    .then(data => { if (data.status === 'ok') location.reload(); else alert(data.message || 'Błąd.'); })
    .catch(() => alert('Błąd sieci.'));
}

function gtdDeleteTask(taskId) {
  if (!confirm('Zarchiwizować to zadanie? Trafi do Archiwum, skąd można je przywrócić.')) return;
  fetch(window.API_BASE + '/api/gtd/tasks/' + taskId, { method: 'DELETE' })
    .then(r => r.json())
    .then(data => { if (data.status === 'ok') location.reload(); else alert(data.message || 'Błąd.'); })
    .catch(() => alert('Błąd sieci.'));
}

function gtdRestoreTask(taskId) {
  fetch(window.API_BASE + '/api/gtd/tasks/' + taskId + '/restore', { method: 'POST' })
    .then(r => r.json())
    .then(data => { if (data.status === 'ok') location.reload(); else alert(data.message || 'Błąd.'); })
    .catch(() => alert('Błąd sieci.'));
}

function gtdPermanentlyDeleteTask(taskId) {
  if (!confirm('Usunąć trwale? Tej operacji nie można cofnąć.')) return;
  fetch(window.API_BASE + '/api/gtd/tasks/' + taskId + '/permanent', { method: 'DELETE' })
    .then(r => r.json())
    .then(data => { if (data.status === 'ok') location.reload(); else alert(data.message || 'Błąd.'); })
    .catch(() => alert('Błąd sieci.'));
}

function gtdToggleArchiveProject(projectId) {
  const row = document.querySelector('.gtd-archive-project-row[data-project-id="' + projectId + '"]');
  if (row) row.classList.toggle('gtd-archive-expanded');
  document.querySelectorAll('.gtd-archive-subrow[data-project-id="' + projectId + '"]').forEach(function (tr) {
    tr.classList.toggle('gtd-archive-visible');
  });
}

function gtdAddProject(inputId) {
  const input = document.getElementById(inputId);
  const title = input.value.trim();
  if (!title) return;
  fetch(window.API_BASE + '/api/gtd/tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, is_project: true, status: 'next' }),
  })
    .then(r => r.json())
    .then(data => { if (data.status === 'ok') gtdRefreshContent(inputId); else alert(data.message || 'Błąd.'); })
    .catch(() => alert('Błąd sieci.'));
}

function gtdRenameProject(taskId, currentTitle) {
  const title = window.prompt('Nowa nazwa projektu:', currentTitle || '');
  if (title === null) return;
  const trimmed = title.trim();
  if (!trimmed) return;
  fetch(window.API_BASE + '/api/gtd/tasks/' + taskId, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title: trimmed }),
  })
    .then(r => r.json())
    .then(data => { if (data.status === 'ok') location.reload(); else alert(data.message || 'Błąd.'); })
    .catch(() => alert('Błąd sieci.'));
}

function gtdArchiveProject(taskId) {
  if (!confirm('Zarchiwizować ten projekt? Trafi do Archiwum, skąd można go przywrócić. Podzadania zostaną zachowane, ale odłączone od projektu.')) return;
  fetch(window.API_BASE + '/api/gtd/tasks/' + taskId, { method: 'DELETE' })
    .then(r => r.json())
    .then(data => { if (data.status === 'ok') location.href = window.API_BASE + '/gtd/projekty'; else alert(data.message || 'Błąd.'); })
    .catch(() => alert('Błąd sieci.'));
}

function gtdPermanentlyDeleteProject(taskId) {
  if (!confirm('Usunąć ten projekt trwale? Tej operacji nie można cofnąć. Podzadania zostaną zachowane, ale odłączone od projektu.')) return;
  fetch(window.API_BASE + '/api/gtd/tasks/' + taskId + '/permanent', { method: 'DELETE' })
    .then(r => r.json())
    .then(data => { if (data.status === 'ok') location.href = window.API_BASE + '/gtd/projekty'; else alert(data.message || 'Błąd.'); })
    .catch(() => alert('Błąd sieci.'));
}

function gtdAddSubtask(projectId, inputId) {
  const input = document.getElementById(inputId);
  const title = input.value.trim();
  if (!title) return;
  fetch(window.API_BASE + '/api/gtd/tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, parent_id: projectId, status: 'next' }),
  })
    .then(r => r.json())
    .then(data => { if (data.status === 'ok') gtdRefreshContent(inputId); else alert(data.message || 'Błąd.'); })
    .catch(() => alert('Błąd sieci.'));
}

function gtdAddToDay(dayIso, inputId) {
  const input = document.getElementById(inputId);
  const title = input.value.trim();
  if (!title) return;
  fetch(window.API_BASE + '/api/gtd/tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, status: 'next', scheduled_date: dayIso }),
  })
    .then(r => r.json())
    .then(data => { if (data.status === 'ok') gtdRefreshContent(inputId); else alert(data.message || 'Błąd.'); })
    .catch(() => alert('Błąd sieci.'));
}

function gtdAddToWeek(monday, inputId) {
  const input = document.getElementById(inputId);
  const title = input.value.trim();
  if (!title) return;
  fetch(window.API_BASE + '/api/gtd/tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, status: 'next' }),
  })
    .then(r => r.json())
    .then(data => {
      if (data.status !== 'ok') { alert(data.message || 'Błąd.'); return null; }
      return fetch(window.API_BASE + '/api/gtd/tasks/' + data.task.id + '/assign_week', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ monday }),
      }).then(r => r.json());
    })
    .then(result => {
      if (!result) return;
      if (result.status === 'ok') gtdRefreshContent(inputId);
      else alert(result.message || 'Błąd.');
    })
    .catch(() => alert('Błąd sieci.'));
}

function gtdAddToMonth(monthStart, inputId) {
  const input = document.getElementById(inputId);
  const title = input.value.trim();
  if (!title) return;
  fetch(window.API_BASE + '/api/gtd/tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, status: 'next' }),
  })
    .then(r => r.json())
    .then(data => {
      if (data.status !== 'ok') { alert(data.message || 'Błąd.'); return null; }
      return fetch(window.API_BASE + '/api/gtd/tasks/' + data.task.id + '/assign_month', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ month: monthStart }),
      }).then(r => r.json());
    })
    .then(result => {
      if (!result) return;
      if (result.status === 'ok') gtdRefreshContent(inputId);
      else alert(result.message || 'Błąd.');
    })
    .catch(() => alert('Błąd sieci.'));
}

function gtdAddToInbox(inputId) {
  const input = document.getElementById(inputId);
  const title = input.value.trim();
  if (!title) return;
  fetch(window.API_BASE + '/api/gtd/tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, status: 'inbox' }),
  })
    .then(r => r.json())
    .then(data => { if (data.status === 'ok') gtdRefreshContent(inputId); else alert(data.message || 'Błąd.'); })
    .catch(() => alert('Błąd sieci.'));
}

function gtdAddToNext(inputId, projectId) {
  const input = document.getElementById(inputId);
  const title = input.value.trim();
  if (!title) return;
  fetch(window.API_BASE + '/api/gtd/tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, status: 'next', parent_id: projectId || null }),
  })
    .then(r => r.json())
    .then(data => { if (data.status === 'ok') gtdRefreshContent(inputId); else alert(data.message || 'Błąd.'); })
    .catch(() => alert('Błąd sieci.'));
}

function gtdAddToWaiting(inputId) {
  const input = document.getElementById(inputId);
  const title = input.value.trim();
  if (!title) return;
  const waitingOn = window.prompt('Na co/kogo czekasz?', '');
  if (waitingOn === null) return;
  fetch(window.API_BASE + '/api/gtd/tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, status: 'waiting', waiting_on: waitingOn }),
  })
    .then(r => r.json())
    .then(data => { if (data.status === 'ok') gtdRefreshContent(inputId); else alert(data.message || 'Błąd.'); })
    .catch(() => alert('Błąd sieci.'));
}

function gtdAddToSomeday(inputId) {
  const input = document.getElementById(inputId);
  const title = input.value.trim();
  if (!title) return;
  fetch(window.API_BASE + '/api/gtd/tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, status: 'someday' }),
  })
    .then(r => r.json())
    .then(data => { if (data.status === 'ok') gtdRefreshContent(inputId); else alert(data.message || 'Błąd.'); })
    .catch(() => alert('Błąd sieci.'));
}

/* ── Filtry widoku "Wszystkie zadania" (aktualizują URL i odświeżają listę bez przeładowania) ── */
function gtdNextApplyFilter(param, value, focusId) {
  const url = new URL(window.location.href);
  if (value) url.searchParams.set(param, value); else url.searchParams.delete(param);
  window.history.replaceState(null, '', url);
  gtdRefreshContent(focusId);
}

let gtdNextSearchTimer = null;
function gtdNextSearchInput(el) {
  clearTimeout(gtdNextSearchTimer);
  const val = el.value.trim();
  if (val.length > 0 && val.length < 3) return;
  gtdNextSearchTimer = setTimeout(() => gtdNextApplyFilter('q', val, el.id), 400);
}

function gtdGcalPush(taskId) {
  fetch(window.API_BASE + '/api/gtd/tasks/' + taskId + '/gcal_push', { method: 'POST' })
    .then(r => r.json())
    .then(data => { if (data.status === 'ok') location.reload(); else alert(data.message || 'Błąd.'); })
    .catch(() => alert('Błąd sieci.'));
}

/* ── Modal blokowania czasu ── */
function gtdOpenTimeBlock(taskId, currentDate, currentTime, currentDuration) {
  document.getElementById('gtdTimeBlockTaskId').value = taskId;
  document.getElementById('gtdTimeBlockDate').value = currentDate || new Date().toISOString().slice(0, 10);
  document.getElementById('gtdTimeBlockTime').value = currentTime || '09:00';
  document.getElementById('gtdTimeBlockDuration').value = currentDuration || 30;
  document.getElementById('gtdTimeBlockModal').classList.add('open');
}

function gtdSubmitTimeBlock() {
  const taskId = document.getElementById('gtdTimeBlockTaskId').value;
  const scheduled_date = document.getElementById('gtdTimeBlockDate').value;
  const scheduled_time = document.getElementById('gtdTimeBlockTime').value;
  const scheduled_duration_min = parseInt(document.getElementById('gtdTimeBlockDuration').value, 10) || 30;
  fetch(window.API_BASE + '/api/gtd/tasks/' + taskId + '/schedule', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scheduled_date, scheduled_time, scheduled_duration_min }),
  })
    .then(r => r.json())
    .then(data => { if (data.status === 'ok') location.reload(); else alert(data.message || 'Błąd.'); })
    .catch(() => alert('Błąd sieci.'));
}

/* ── Modal edycji terminu ── */
let _gtdProjectsCache = null;

function _gtdFillProjectSelect(taskId, currentParentId, selectId) {
  const select = document.getElementById(selectId || 'gtdEditTaskProject');
  const render = (projects) => {
    select.innerHTML = '<option value="">— brak —</option>';
    projects
      .filter(p => p.id !== taskId)
      .forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.textContent = p.title;
        if (currentParentId && p.id === currentParentId) opt.selected = true;
        select.appendChild(opt);
      });
  };
  if (_gtdProjectsCache) {
    render(_gtdProjectsCache);
    return;
  }
  fetch(window.API_BASE + '/api/gtd/projects')
    .then(r => r.json())
    .then(projects => { _gtdProjectsCache = projects; render(projects); })
    .catch(() => {});
}

let _gtdContactsCache = null;
let _gtdCompaniesCache = null;

/* ── Wyszukiwarki kontaktu/firmy CRM w modalach GTD (entity-picker z app.js) ──
   Same widget as CRM's own contact/company search — resolves the currently
   assigned id to a display name (from a cached full list) to prefill the
   "selected" chip when a modal reopens; actual search-as-you-type hits the
   existing CRM search endpoints via initEntityPicker itself. */
function _gtdSetCrmPickers(currentContactId, currentCompanyId, contactPickerId, companyPickerId) {
  if (!currentContactId) {
    clearEntityPicker(contactPickerId);
  } else {
    const apply = (contacts) => {
      const item = contacts.find(c => c.id === currentContactId);
      selectEntityPicker(contactPickerId, currentContactId, item ? item.name : ('Kontakt #' + currentContactId));
    };
    if (_gtdContactsCache) {
      apply(_gtdContactsCache);
    } else {
      fetch(window.API_BASE + '/api/gtd/crm_contacts')
        .then(r => r.json())
        .then(contacts => { _gtdContactsCache = contacts; apply(contacts); })
        .catch(() => {});
    }
  }
  if (!currentCompanyId) {
    clearEntityPicker(companyPickerId);
  } else {
    const apply = (companies) => {
      const item = companies.find(c => c.id === currentCompanyId);
      selectEntityPicker(companyPickerId, currentCompanyId, item ? item.name : ('Firma #' + currentCompanyId));
    };
    if (_gtdCompaniesCache) {
      apply(_gtdCompaniesCache);
    } else {
      fetch(window.API_BASE + '/api/gtd/crm_companies')
        .then(r => r.json())
        .then(companies => { _gtdCompaniesCache = companies; apply(companies); })
        .catch(() => {});
    }
  }
}

function gtdOpenEditTask(taskId, currentDue, currentParentId, currentTitle, currentContactId, currentCompanyId, currentScheduled, currentWeek, currentDealId, currentDealName) {
  document.getElementById('gtdEditTaskId').value = taskId;
  document.getElementById('gtdEditTaskTitle').value = currentTitle || '';
  document.getElementById('gtdEditTaskDue').value = currentDue || '';
  document.getElementById('gtdEditTaskScheduled').value = currentScheduled || '';
  document.getElementById('gtdEditTaskWeek').value = currentWeek || '';
  _gtdFillProjectSelect(taskId, currentParentId || null);
  _gtdSetCrmPickers(currentContactId || null, currentCompanyId || null, 'gtdEditTaskContactPicker', 'gtdEditTaskCompanyPicker');
  if (currentDealId) {
    selectEntityPicker('gtdEditTaskDealPicker', currentDealId, currentDealName || ('Deal #' + currentDealId));
  } else {
    clearEntityPicker('gtdEditTaskDealPicker');
  }
  document.getElementById('gtdEditTaskModal').classList.add('open');
}

function gtdSubmitEditTask() {
  const taskId = document.getElementById('gtdEditTaskId').value;
  const title = document.getElementById('gtdEditTaskTitle').value.trim();
  if (!title) { alert('Nazwa zadania nie może być pusta.'); return; }
  const due_date = document.getElementById('gtdEditTaskDue').value || null;
  const scheduled_date = document.getElementById('gtdEditTaskScheduled').value || null;
  const week = document.getElementById('gtdEditTaskWeek').value || null;
  const parentValue = document.getElementById('gtdEditTaskProject').value;
  const parent_id = parentValue ? parseInt(parentValue, 10) : null;
  const contactValue = document.getElementById('gtdEditTaskContactPicker-hidden').value;
  const crm_contact_id = contactValue ? parseInt(contactValue, 10) : null;
  const companyValue = document.getElementById('gtdEditTaskCompanyPicker-hidden').value;
  const crm_company_id = companyValue ? parseInt(companyValue, 10) : null;
  const dealValue = document.getElementById('gtdEditTaskDealPicker-hidden').value;
  const crm_deal_id = dealValue ? parseInt(dealValue, 10) : null;
  fetch(window.API_BASE + '/api/gtd/tasks/' + taskId, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, due_date, scheduled_date, parent_id, crm_contact_id, crm_company_id, crm_deal_id }),
  })
    .then(r => r.json())
    .then(data => {
      if (data.status !== 'ok') { alert(data.message || 'Błąd.'); return; }
      const weekReq = week
        ? fetch(window.API_BASE + '/api/gtd/tasks/' + taskId + '/assign_week', {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ monday: week }),
          })
        : fetch(window.API_BASE + '/api/gtd/tasks/' + taskId + '/clear_week', { method: 'POST' });
      return weekReq.then(() => location.reload());
    })
    .catch(() => alert('Błąd sieci.'));
}

/* ── Modal nowego zadania (follow-up z pierwotnego zadania, albo zaawansowane
   dodawanie z widoku Dziś/Tydzień/Miesiąc — presetScheduled/presetWeek/presetMonth
   wstępnie wypełniają termin z kontekstu widoku, z którego modal został otwarty) ── */
function gtdOpenFollowUp(currentParentId, currentContactId, currentCompanyId, currentDealId, currentDealName,
                          presetScheduled, presetWeek, presetMonth, presetTitle, presetStatus) {
  document.getElementById('gtdFollowUpTitle').value = presetTitle || '';
  document.getElementById('gtdFollowUpDue').value = '';
  document.getElementById('gtdFollowUpScheduled').value = presetScheduled || '';
  document.getElementById('gtdFollowUpWeek').value = presetWeek || '';
  document.getElementById('gtdFollowUpMonth').value = presetMonth || '';
  document.getElementById('gtdFollowUpStatus').value = presetStatus || 'next';
  _gtdFillProjectSelect(null, currentParentId || null, 'gtdFollowUpProject');
  _gtdSetCrmPickers(currentContactId || null, currentCompanyId || null, 'gtdFollowUpContactPicker', 'gtdFollowUpCompanyPicker');
  if (currentDealId) {
    selectEntityPicker('gtdFollowUpDealPicker', currentDealId, currentDealName || ('Deal #' + currentDealId));
  } else {
    clearEntityPicker('gtdFollowUpDealPicker');
  }
  document.getElementById('gtdFollowUpModal').classList.add('open');
  document.getElementById('gtdFollowUpTitle').focus();
}

function gtdSubmitFollowUp() {
  const title = document.getElementById('gtdFollowUpTitle').value.trim();
  if (!title) { alert('Nazwa zadania nie może być pusta.'); return; }
  const due_date = document.getElementById('gtdFollowUpDue').value || null;
  const scheduled_date = document.getElementById('gtdFollowUpScheduled').value || null;
  const week = document.getElementById('gtdFollowUpWeek').value || null;
  const month = document.getElementById('gtdFollowUpMonth').value || null;
  const parentValue = document.getElementById('gtdFollowUpProject').value;
  const parent_id = parentValue ? parseInt(parentValue, 10) : null;
  const contactValue = document.getElementById('gtdFollowUpContactPicker-hidden').value;
  const crm_contact_id = contactValue ? parseInt(contactValue, 10) : null;
  const companyValue = document.getElementById('gtdFollowUpCompanyPicker-hidden').value;
  const crm_company_id = companyValue ? parseInt(companyValue, 10) : null;
  const dealValue = document.getElementById('gtdFollowUpDealPicker-hidden').value;
  const crm_deal_id = dealValue ? parseInt(dealValue, 10) : null;
  const status = document.getElementById('gtdFollowUpStatus').value || 'next';
  fetch(window.API_BASE + '/api/gtd/tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, due_date, scheduled_date, parent_id, status }),
  })
    .then(r => r.json())
    .then(data => {
      if (data.status !== 'ok') { alert(data.message || 'Błąd.'); return; }
      const taskId = data.task.id;
      const steps = [];
      if (crm_contact_id || crm_company_id || crm_deal_id) {
        steps.push(() => fetch(window.API_BASE + '/api/gtd/tasks/' + taskId, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ crm_contact_id, crm_company_id, crm_deal_id }),
        }));
      }
      if (week) {
        steps.push(() => fetch(window.API_BASE + '/api/gtd/tasks/' + taskId + '/assign_week', {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ monday: week }),
        }));
      } else if (month) {
        steps.push(() => fetch(window.API_BASE + '/api/gtd/tasks/' + taskId + '/assign_month', {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ month }),
        }));
      }
      return steps.reduce((p, step) => p.then(step), Promise.resolve()).then(() => location.reload());
    })
    .catch(() => alert('Błąd sieci.'));
}

function gtdCloseProject(projectId) {
  fetch(window.API_BASE + '/api/gtd/tasks/' + projectId + '/open_subtasks')
    .then(r => r.json())
    .then(data => {
      const openTasks = data.tasks || [];
      let closeSubtasks = false;
      if (openTasks.length) {
        const list = openTasks.map(t => '- ' + t.title).join('\n');
        closeSubtasks = confirm(
          'Projekt ma otwarte zadania:\n\n' + list + '\n\nCzy zamknąć je automatycznie razem z projektem?'
        );
      }
      return fetch(window.API_BASE + '/api/gtd/tasks/' + projectId + '/close_project', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ close_subtasks: closeSubtasks }),
      });
    })
    .then(r => r.json())
    .then(data => { if (data.status === 'ok') location.reload(); else alert(data.message || 'Błąd.'); })
    .catch(() => alert('Błąd sieci.'));
}

function gtdReopenProject(projectId) {
  fetch(window.API_BASE + '/api/gtd/tasks/' + projectId + '/reopen_project', { method: 'POST' })
    .then(r => r.json())
    .then(data => { if (data.status === 'ok') location.reload(); else alert(data.message || 'Błąd.'); })
    .catch(() => alert('Błąd sieci.'));
}

function gtdOpenGcalProject(eventId, eventDate, currentProjectId, currentContactId, currentCompanyId) {
  document.getElementById('gtdGcalProjectEventId').value = eventId;
  document.getElementById('gtdGcalProjectEventDate').value = eventDate;
  _gtdFillProjectSelect(null, currentProjectId || null, 'gtdGcalProjectSelect');
  _gtdSetCrmPickers(currentContactId || null, currentCompanyId || null, 'gtdGcalProjectContactPicker', 'gtdGcalProjectCompanyPicker');
  document.getElementById('gtdGcalProjectModal').classList.add('open');
}

function gtdSubmitGcalProject() {
  const eventId = document.getElementById('gtdGcalProjectEventId').value;
  const eventDate = document.getElementById('gtdGcalProjectEventDate').value;
  const projectValue = document.getElementById('gtdGcalProjectSelect').value;
  const project_id = projectValue ? parseInt(projectValue, 10) : null;
  const contactValue = document.getElementById('gtdGcalProjectContactPicker-hidden').value;
  const crm_contact_id = contactValue ? parseInt(contactValue, 10) : null;
  const companyValue = document.getElementById('gtdGcalProjectCompanyPicker-hidden').value;
  const crm_company_id = companyValue ? parseInt(companyValue, 10) : null;
  Promise.all([
    fetch(window.API_BASE + '/api/gtd/gcal_events/' + encodeURIComponent(eventId) + '/project', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ event_date: eventDate, project_id }),
    }),
    fetch(window.API_BASE + '/api/gtd/gcal_events/' + encodeURIComponent(eventId) + '/crm_link', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ event_date: eventDate, crm_contact_id, crm_company_id }),
    }),
  ])
    .then(() => location.reload())
    .catch(() => alert('Błąd sieci.'));
}

/* ── Przypisanie zadania do konkretnego dnia tygodnia (hover-picker w widoku tygodnia) ── */
function gtdSetWeekday(taskId, weekStartIso, dayIndex) {
  const [y, m, d] = weekStartIso.split('-').map(Number);
  const start = new Date(y, m - 1, d);
  start.setDate(start.getDate() + dayIndex);
  const dayIso = start.getFullYear() + '-'
    + String(start.getMonth() + 1).padStart(2, '0') + '-'
    + String(start.getDate()).padStart(2, '0');
  fetch(window.API_BASE + '/api/gtd/tasks/' + taskId + '/schedule', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scheduled_date: dayIso }),
  })
    .then(r => r.json())
    .then(data => { if (data.status === 'ok') location.reload(); else alert(data.message || 'Błąd.'); })
    .catch(() => alert('Błąd sieci.'));
}

/* Po wybraniu kontaktu w pickerze, jeśli kontakt ma przypisaną firmę, automatycznie
   uzupełnij też picker firmy — kontakt i klient mają iść w parze. */
function _gtdAutoFillCompanyFromContact(contact, companyPickerId) {
  if (contact.company_id) {
    selectEntityPicker(companyPickerId, contact.company_id, contact.company_name || ('Firma #' + contact.company_id));
  }
}

/* ── Init wyszukiwarek CRM w modalach GTD (elementy z _layout.html, obecne na
   każdej stronie GTD) — initEntityPicker pochodzi z app.js, ładowanego wcześniej. */
if (document.getElementById('gtdEditTaskContactPicker')) {
  initEntityPicker('gtdEditTaskContactPicker', '/api/crm/contacts/search',
    it => _gtdAutoFillCompanyFromContact(it, 'gtdEditTaskCompanyPicker'));
  initEntityPicker('gtdEditTaskCompanyPicker', '/api/crm/companies/search');
  initEntityPicker('gtdEditTaskDealPicker', '/api/crm/deals/search');
  initEntityPicker('gtdGcalProjectContactPicker', '/api/crm/contacts/search',
    it => _gtdAutoFillCompanyFromContact(it, 'gtdGcalProjectCompanyPicker'));
  initEntityPicker('gtdGcalProjectCompanyPicker', '/api/crm/companies/search');
  initEntityPicker('gtdFollowUpContactPicker', '/api/crm/contacts/search',
    it => _gtdAutoFillCompanyFromContact(it, 'gtdFollowUpCompanyPicker'));
  initEntityPicker('gtdFollowUpCompanyPicker', '/api/crm/companies/search');
  initEntityPicker('gtdFollowUpDealPicker', '/api/crm/deals/search');
}
