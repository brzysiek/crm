/* ── GTD: szybkie dodawanie (tekst + głos), akcje na zadaniach ── */
(function () {
  const quickInput = document.getElementById('gtdQuickInput');
  const quickBtn = document.getElementById('gtdQuickAddBtn');
  const voiceBtn = document.getElementById('gtdVoiceBtn');
  const statusEl = document.getElementById('gtdQuickAddStatus');

  if (!quickInput) return;

  function showStatus(text, isError) {
    statusEl.textContent = text;
    statusEl.style.color = isError ? 'var(--error-text)' : '';
    if (text) setTimeout(() => { if (statusEl.textContent === text) statusEl.textContent = ''; }, 3000);
  }

  function afterAdd() {
    quickInput.value = '';
    quickInput.focus();
    if (document.getElementById('gtdInboxList')) {
      location.reload();
    } else {
      showStatus('Dodano do Inbox ✓', false);
    }
  }

  function submitQuickAdd() {
    const text = quickInput.value.trim();
    if (!text) return;
    quickBtn.disabled = true;
    fetch(window.API_BASE + '/api/gtd/quick_add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    })
      .then(r => r.json())
      .then(data => {
        quickBtn.disabled = false;
        if (data.status === 'ok') afterAdd();
        else showStatus(data.message || 'Błąd dodawania.', true);
      })
      .catch(() => { quickBtn.disabled = false; showStatus('Błąd sieci.', true); });
  }

  quickBtn.addEventListener('click', submitQuickAdd);
  quickInput.addEventListener('keydown', e => { if (e.key === 'Enter') submitQuickAdd(); });

  // ── Dodawanie głosowe: nagranie -> transkrypcja (reużywa /api/agent/transcribe) -> parsowanie GTD ──
  let mediaRecorder = null;
  let audioChunks = [];
  let recording = false;

  async function startRecording() {
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err) {
      alert('Brak dostępu do mikrofonu: ' + err.message);
      return;
    }
    const candidates = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg'];
    const mimeType = candidates.find(t => window.MediaRecorder && MediaRecorder.isTypeSupported(t)) || '';
    try {
      mediaRecorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
    } catch (err) {
      alert('Nagrywanie audio nie jest wspierane w tej przeglądarce.');
      stream.getTracks().forEach(t => t.stop());
      return;
    }
    audioChunks = [];
    mediaRecorder.ondataavailable = e => { if (e.data.size > 0) audioChunks.push(e.data); };
    mediaRecorder.onstop = () => {
      stream.getTracks().forEach(t => t.stop());
      const blob = new Blob(audioChunks, { type: mediaRecorder.mimeType || mimeType || 'audio/webm' });
      uploadRecording(blob);
    };
    mediaRecorder.start();
    recording = true;
    voiceBtn.classList.add('recording');
    showStatus('Nagrywanie… kliknij 🎙 ponownie, żeby zakończyć', false);
  }

  function stopRecording() {
    if (mediaRecorder && recording) {
      mediaRecorder.stop();
      recording = false;
      voiceBtn.classList.remove('recording');
    }
  }

  function uploadRecording(blob) {
    showStatus('Transkrybowanie…', false);
    voiceBtn.disabled = true;
    const ext = (blob.type.includes('mp4') || blob.type.includes('m4a')) ? 'm4a'
      : blob.type.includes('ogg') ? 'ogg' : 'webm';
    const form = new FormData();
    form.append('audio', blob, 'zadanie.' + ext);
    fetch(window.API_BASE + '/api/agent/transcribe', { method: 'POST', body: form })
      .then(r => r.json())
      .then(data => {
        if (data.status !== 'ok') {
          voiceBtn.disabled = false;
          showStatus(data.message || 'Nie udało się przetranskrybować.', true);
          return;
        }
        showStatus('Analizuję zadanie…', false);
        return fetch(window.API_BASE + '/api/gtd/voice_add', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: data.text }),
        }).then(r => r.json()).then(result => {
          voiceBtn.disabled = false;
          if (result.status === 'ok') afterAdd();
          else showStatus(result.message || 'Nie udało się dodać zadania.', true);
        });
      })
      .catch(() => { voiceBtn.disabled = false; showStatus('Błąd sieci.', true); });
  }

  voiceBtn.addEventListener('click', () => {
    if (!recording) startRecording(); else stopRecording();
  });
})();

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

function gtdAssignWeek(taskId, week) {
  fetch(window.API_BASE + '/api/gtd/tasks/' + taskId + '/assign_week', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ week }),
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
  if (!confirm('Usunąć to zadanie?')) return;
  fetch(window.API_BASE + '/api/gtd/tasks/' + taskId, { method: 'DELETE' })
    .then(r => r.json())
    .then(data => { if (data.status === 'ok') location.reload(); else alert(data.message || 'Błąd.'); })
    .catch(() => alert('Błąd sieci.'));
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
    .then(data => { if (data.status === 'ok') location.reload(); else alert(data.message || 'Błąd.'); })
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

function gtdDeleteProject(taskId) {
  if (!confirm('Usunąć ten projekt? Zadania w nim zostaną zachowane, ale odłączone od projektu.')) return;
  fetch(window.API_BASE + '/api/gtd/tasks/' + taskId, { method: 'DELETE' })
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
    .then(data => { if (data.status === 'ok') location.reload(); else alert(data.message || 'Błąd.'); })
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
    .then(data => { if (data.status === 'ok') location.reload(); else alert(data.message || 'Błąd.'); })
    .catch(() => alert('Błąd sieci.'));
}

function gtdAddToWeek(week, inputId) {
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
        body: JSON.stringify({ week }),
      }).then(r => r.json());
    })
    .then(result => {
      if (!result) return;
      if (result.status === 'ok') location.reload();
      else alert(result.message || 'Błąd.');
    })
    .catch(() => alert('Błąd sieci.'));
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

function _gtdFillProjectSelect(taskId, currentParentId) {
  const select = document.getElementById('gtdEditTaskProject');
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

function gtdOpenEditTask(taskId, currentDue, currentParentId) {
  document.getElementById('gtdEditTaskId').value = taskId;
  document.getElementById('gtdEditTaskDue').value = currentDue || '';
  _gtdFillProjectSelect(taskId, currentParentId || null);
  document.getElementById('gtdEditTaskModal').classList.add('open');
}

function gtdSubmitEditTask() {
  const taskId = document.getElementById('gtdEditTaskId').value;
  const due_date = document.getElementById('gtdEditTaskDue').value || null;
  const parentValue = document.getElementById('gtdEditTaskProject').value;
  const parent_id = parentValue ? parseInt(parentValue, 10) : null;
  fetch(window.API_BASE + '/api/gtd/tasks/' + taskId, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ due_date, parent_id }),
  })
    .then(r => r.json())
    .then(data => { if (data.status === 'ok') location.reload(); else alert(data.message || 'Błąd.'); })
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
