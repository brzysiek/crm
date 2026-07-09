/* ── Agent AI: nagrywanie/transkrypcja, parsowanie intencji, podsumowanie, wykonanie ── */
(function () {
  const recordBtn = document.getElementById('agentRecordBtn');
  const recordStatus = document.getElementById('agentRecordStatus');
  const textArea = document.getElementById('agentText');
  const submitBtn = document.getElementById('agentSubmitBtn');
  const clearBtn = document.getElementById('agentClearBtn');
  const parseStatus = document.getElementById('agentParseStatus');
  const inputArea = document.getElementById('agentInputArea');
  const confirmBox = document.getElementById('agentConfirm');
  const doneBox = document.getElementById('agentDone');

  if (!recordBtn) return;

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
    recordBtn.classList.add('recording');
    recordBtn.querySelector('.agent-record-label').textContent = 'Zatrzymaj';
    recordStatus.textContent = 'Nagrywanie…';
  }

  function stopRecording() {
    if (mediaRecorder && recording) {
      mediaRecorder.stop();
      recording = false;
      recordBtn.classList.remove('recording');
      recordBtn.querySelector('.agent-record-label').textContent = 'Nagrywaj';
    }
  }

  function uploadRecording(blob) {
    recordStatus.textContent = 'Transkrybowanie…';
    recordBtn.disabled = true;
    const ext = (blob.type.includes('mp4') || blob.type.includes('m4a')) ? 'm4a'
      : blob.type.includes('ogg') ? 'ogg' : 'webm';
    const form = new FormData();
    form.append('audio', blob, 'polecenie.' + ext);
    fetch(window.API_BASE + '/api/agent/transcribe', { method: 'POST', body: form })
      .then(r => r.json())
      .then(data => {
        recordBtn.disabled = false;
        if (data.status === 'ok') {
          textArea.value = data.text;
          recordStatus.textContent = 'Transkrypcja gotowa.';
        } else {
          recordStatus.textContent = '';
          alert(data.message || 'Nie udało się przetranskrybować nagrania.');
        }
      })
      .catch(() => {
        recordBtn.disabled = false;
        recordStatus.textContent = '';
        alert('Błąd sieci przy transkrypcji.');
      });
  }

  recordBtn.addEventListener('click', () => {
    if (!recording) startRecording(); else stopRecording();
  });

  clearBtn.addEventListener('click', () => {
    textArea.value = '';
    parseStatus.textContent = '';
    textArea.focus();
  });

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, c => (
      { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
    ));
  }

  const ENTITY_LABEL = { company: 'Klient', contact: 'Kontakt', deal: 'Interes' };
  const SEARCH_URL = {
    company: '/api/crm/companies/search',
    contact: '/api/crm/contacts/search',
    deal: '/api/crm/deals/search',
  };

  function taskLabel(intent, entityType) {
    if (intent === 'note') return 'Notatka';
    if (entityType === 'company') return 'Dodanie klienta';
    if (entityType === 'contact') return 'Dodanie kontaktu';
    return 'Dodanie interesu';
  }

  function pickerHtml(pickerId, selected, placeholder) {
    const sel = selected ? (
      '<div class="entity-picker-selected" id="' + pickerId + '-selected">'
      + (selected.favicon_url ? '<img src="' + esc(selected.favicon_url) + '" class="favicon-img-sm" alt="">' : '')
      + '<span class="entity-picker-selected-name">' + esc(selected.name) + '</span>'
      + '<button type="button" class="entity-picker-clear" data-clear-picker="' + pickerId + '">✕</button>'
      + '</div>'
    ) : '';
    return (
      '<div class="entity-picker" id="' + pickerId + '">' + sel
      + '<input type="text" id="' + pickerId + '-input" class="filter-input" style="width:100%' + (selected ? ';display:none' : '') + '"'
      + ' placeholder="' + esc(placeholder) + '" autocomplete="off">'
      + '<div id="' + pickerId + '-results" class="entity-picker-results"></div>'
      + '<input type="hidden" id="' + pickerId + '-hidden" value="' + (selected ? selected.id : '') + '">'
      + '</div>'
    );
  }

  function fieldRow(field, label, value, multiline) {
    const tag = multiline
      ? '<textarea class="agent-field" data-field="' + field + '" rows="3">' + esc(value) + '</textarea>'
      : '<input type="text" class="agent-field" data-field="' + field + '" value="' + esc(value) + '">';
    return '<div class="agent-confirm-row"><label>' + esc(label) + '</label>' + tag + '</div>';
  }

  function pickerRow(label, pickerId, selected, hint, placeholder) {
    return '<div class="agent-confirm-row"><label>' + esc(label) + '</label>'
      + pickerHtml(pickerId, selected, placeholder)
      + (!selected && hint ? '<div class="text-muted" style="margin-top:.3rem;font-size:.8rem">Nie znaleziono automatycznie — wyszukaj i wybierz: „' + esc(hint) + '”</div>' : '')
      + '</div>';
  }

  function staticRow(label, value) {
    return '<div class="agent-confirm-row"><label>' + esc(label) + '</label>'
      + '<div class="agent-confirm-static">' + esc(value) + '</div></div>';
  }

  let currentResult = null;

  function renderConfirmation(result) {
    currentResult = result;
    const { intent, entity_type: entityType, fields } = result;
    let rows = '';

    if (intent === 'note') {
      const pickerId = 'agent-target-picker';
      rows += pickerRow(ENTITY_LABEL[entityType], pickerId, result.target, result.target_hint,
        'Szukaj: ' + ENTITY_LABEL[entityType].toLowerCase() + '…');
      if (result.context_company_name) rows += staticRow('Firma', result.context_company_name);
      if (result.context_contact_name) rows += staticRow('Kontakt', result.context_contact_name);
      rows += fieldRow('note_body', 'Notatka', fields.note_body, true);
    } else if (entityType === 'company') {
      rows += fieldRow('company_name', 'Nazwa firmy', fields.company_name, false);
      rows += fieldRow('first_name', 'Imię', fields.first_name, false);
      rows += fieldRow('last_name', 'Nazwisko', fields.last_name, false);
      rows += fieldRow('email', 'Email', fields.email, false);
      rows += fieldRow('phone', 'Telefon', fields.phone, false);
      rows += fieldRow('city', 'Miasto', fields.city, false);
      rows += fieldRow('website', 'Strona www', fields.website, false);
      rows += fieldRow('nip', 'NIP', fields.nip, false);
      rows += fieldRow('source', 'Źródło', fields.source, false);
      rows += fieldRow('description', 'Opis', fields.description, true);
    } else if (entityType === 'contact') {
      rows += pickerRow('Klient', 'agent-link-company-picker', result.link_company, result.link_company_hint, 'Szukaj firmy…');
      rows += fieldRow('first_name', 'Imię', fields.first_name, false);
      rows += fieldRow('last_name', 'Nazwisko', fields.last_name, false);
      rows += fieldRow('position', 'Stanowisko', fields.position, false);
      rows += fieldRow('email', 'Email', fields.email, false);
      rows += fieldRow('phone', 'Telefon', fields.phone, false);
      rows += fieldRow('description', 'Opis', fields.description, true);
    } else {
      rows += pickerRow('Klient', 'agent-link-company-picker', result.link_company, result.link_company_hint, 'Szukaj firmy…');
      rows += pickerRow('Kontakt', 'agent-link-contact-picker', result.link_contact, result.link_contact_hint, 'Szukaj kontaktu…');
      rows += fieldRow('deal_name', 'Nazwa interesu', fields.deal_name, false);
      rows += fieldRow('amount', 'Kwota', fields.amount, false);
      rows += fieldRow('description', 'Opis', fields.description, true);
    }

    confirmBox.innerHTML = (
      '<div class="agent-confirm-title">Zadanie: ' + esc(taskLabel(intent, entityType)) + '</div>'
      + rows
      + '<div class="agent-confirm-actions">'
      + '<button type="button" id="agentConfirmBtn" class="btn btn-primary btn-lg">ZATWIERDŹ</button>'
      + '<button type="button" id="agentCancelBtn" class="btn btn-ghost agent-confirm-cancel">Anuluj</button>'
      + '</div>'
    );
    confirmBox.style.display = '';
    inputArea.style.display = 'none';
    doneBox.style.display = 'none';

    if (intent === 'note') {
      initEntityPicker('agent-target-picker', SEARCH_URL[entityType]);
    } else if (entityType === 'contact') {
      initEntityPicker('agent-link-company-picker', SEARCH_URL.company);
    } else if (entityType === 'deal') {
      initEntityPicker('agent-link-company-picker', SEARCH_URL.company);
      initEntityPicker('agent-link-contact-picker', SEARCH_URL.contact);
    }
    confirmBox.querySelectorAll('[data-clear-picker]').forEach(btn => {
      btn.addEventListener('click', () => clearEntityPicker(btn.dataset.clearPicker));
    });

    document.getElementById('agentCancelBtn').addEventListener('click', resetToInput);
    document.getElementById('agentConfirmBtn').addEventListener('click', submitExecute);
  }

  function resetToInput() {
    confirmBox.style.display = 'none';
    doneBox.style.display = 'none';
    inputArea.style.display = '';
    currentResult = null;
  }

  function collectFields() {
    const fields = {};
    confirmBox.querySelectorAll('.agent-field').forEach(el => {
      fields[el.dataset.field] = el.value.trim();
    });
    return fields;
  }

  function hiddenVal(pickerId) {
    const el = document.getElementById(pickerId + '-hidden');
    return el && el.value ? el.value : null;
  }

  function submitExecute() {
    const btn = document.getElementById('agentConfirmBtn');
    btn.disabled = true;
    btn.textContent = 'Zapisywanie…';

    const payload = {
      intent: currentResult.intent,
      entity_type: currentResult.entity_type,
      fields: collectFields(),
      input_text: currentResult.input_text,
    };
    if (currentResult.intent === 'note') {
      payload.target_id = hiddenVal('agent-target-picker');
    } else if (currentResult.entity_type === 'contact') {
      payload.link_company_id = hiddenVal('agent-link-company-picker');
    } else if (currentResult.entity_type === 'deal') {
      payload.link_company_id = hiddenVal('agent-link-company-picker');
      payload.link_contact_id = hiddenVal('agent-link-contact-picker');
    }

    fetch(window.API_BASE + '/api/agent/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
      .then(r => r.json())
      .then(data => {
        if (data.status === 'ok') {
          confirmBox.style.display = 'none';
          doneBox.innerHTML = '<div>' + esc(data.summary) + '</div>'
            + '<button type="button" id="agentNewTaskBtn" class="btn btn-outline">Nowe polecenie</button>';
          doneBox.style.display = '';
          document.getElementById('agentNewTaskBtn').addEventListener('click', () => {
            textArea.value = '';
            resetToInput();
          });
        } else {
          btn.disabled = false;
          btn.textContent = 'ZATWIERDŹ';
          alert(data.message || 'Nie udało się wykonać polecenia.');
        }
      })
      .catch(() => {
        btn.disabled = false;
        btn.textContent = 'ZATWIERDŹ';
        alert('Błąd sieci przy wykonywaniu polecenia.');
      });
  }

  submitBtn.addEventListener('click', () => {
    const text = textArea.value.trim();
    if (!text) { textArea.focus(); return; }
    submitBtn.disabled = true;
    parseStatus.textContent = 'Analizuję polecenie…';
    fetch(window.API_BASE + '/api/agent/parse', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    })
      .then(r => r.json())
      .then(data => {
        submitBtn.disabled = false;
        parseStatus.textContent = '';
        if (data.status === 'ok') {
          renderConfirmation(data.result);
        } else {
          alert(data.message || 'Nie udało się zrozumieć polecenia.');
        }
      })
      .catch(() => {
        submitBtn.disabled = false;
        parseStatus.textContent = '';
        alert('Błąd sieci przy analizie polecenia.');
      });
  });
})();
