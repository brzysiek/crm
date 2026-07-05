/* ── Górne menu: hamburger na urządzeniach mobilnych ──────────────────────────── */
function initNavbarToggle() {
  const navbar = document.querySelector('.navbar');
  const toggle = document.getElementById('navbar-toggle');
  if (!navbar || !toggle) return;

  toggle.addEventListener('click', e => {
    e.stopPropagation();
    const open = navbar.classList.toggle('nav-open');
    toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
  });

  document.addEventListener('click', e => {
    if (navbar.classList.contains('nav-open') && !navbar.contains(e.target)) {
      navbar.classList.remove('nav-open');
      toggle.setAttribute('aria-expanded', 'false');
    }
  });
}
document.addEventListener('DOMContentLoaded', initNavbarToggle);

/* ── VAT calculator ──────────────────────────────────────────────────────────── */
function calcNet() {
  const grossEl = document.getElementById('amount_gross');
  const vatEl   = document.getElementById('vat_rate');
  const netEl   = document.getElementById('amount_net');
  if (!grossEl || !vatEl || !netEl) return;

  const gross = parseFloat(grossEl.value) || 0;
  const vat   = parseFloat(vatEl.value);

  let net;
  if (vat < 0) {        // zw. — net equals gross
    net = gross;
  } else {
    net = gross / (1 + vat / 100);
  }
  netEl.value = gross > 0 ? net.toFixed(2) : '';
}

/* ── Payment percent slider ──────────────────────────────────────────────────── */
function syncSlider(val) {
  const num = document.getElementById('payment_percent');
  if (num) num.value = val;
}

function syncNumber(val) {
  const slider = document.getElementById('payment_slider');
  if (slider) slider.value = Math.min(100, Math.max(0, val));
}

/* ── Invoice ref show/hide ────────────────────────────────────────────────────── */
function toggleInvoiceRef() {
  const radios = document.querySelectorAll('input[name="invoice_status"]');
  const wrap   = document.getElementById('invoice_ref_wrap');
  const label  = document.getElementById('invoice_ref_label');
  if (!wrap) return;

  let val = 'none';
  radios.forEach(r => { if (r.checked) val = r.value; });

  wrap.style.display = val !== 'none' ? 'block' : 'none';
  if (label) label.textContent = val === 'disk' ? 'Ścieżka pliku' : 'Numer KSeF';
}

/* ── Other person toggle ─────────────────────────────────────────────────────── */
function toggleOtherPerson(select) {
  const other = document.getElementById('person_other');
  if (!other) return;
  const show = select.value === '__other__';
  other.style.display = show ? 'block' : 'none';
  if (show) other.focus();
}

/* ── New category toggle ─────────────────────────────────────────────────────── */
function toggleNewCategory(select) {
  const newCat = document.getElementById('category_new');
  if (!newCat) return;
  const show = select.value === '__new__';
  newCat.style.display = show ? 'block' : 'none';
  if (show) newCat.focus();
}

/* ── API key reveal toggle ───────────────────────────────────────────────────── */
function toggleReveal(inputId, btn) {
  const el = document.getElementById(inputId);
  if (!el) return;
  if (el.type === 'password') {
    el.type = 'text';
    btn.textContent = 'Ukryj';
  } else {
    el.type = 'password';
    btn.textContent = 'Pokaż';
  }
}

/* ── Bar chart (Canvas API) ──────────────────────────────────────────────────── */
function fillRoundedTopRect(ctx, x, y, w, h, r) {
  if (h <= 0) return;
  r = Math.min(r, w / 2, h);
  ctx.beginPath();
  ctx.moveTo(x, y + h);
  ctx.lineTo(x, y + r);
  ctx.arcTo(x, y, x + r, y, r);
  ctx.lineTo(x + w - r, y);
  ctx.arcTo(x + w, y, x + w, y + r, r);
  ctx.lineTo(x + w, y + h);
  ctx.closePath();
  ctx.fill();
}

function drawBarChart(canvas, data) {
  if (!canvas || !data || data.length === 0) return;

  const dpr = window.devicePixelRatio || 1;
  const cssW = canvas.clientWidth || canvas.parentElement.clientWidth || 900;
  const cssH = 180;
  canvas.width  = cssW * dpr;
  canvas.height = cssH * dpr;
  canvas.style.width  = cssW + 'px';
  canvas.style.height = cssH + 'px';

  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);

  const padL = 60, padR = 16, padT = 16, padB = 36;
  const W = cssW - padL - padR;
  const H = cssH - padT - padB;

  const maxVal = Math.max(...data, 1);
  const barW   = Math.max(4, W / data.length - 3);
  const step   = W / data.length;

  // Grid lines
  ctx.strokeStyle = '#e5e7eb';
  ctx.lineWidth = 1;
  ctx.setLineDash([3, 3]);
  for (let i = 0; i <= 4; i++) {
    const y = padT + H - (H * i / 4);
    ctx.beginPath();
    ctx.moveTo(padL, y);
    ctx.lineTo(padL + W, y);
    ctx.stroke();
  }
  ctx.setLineDash([]);

  // Y-axis labels
  ctx.fillStyle = '#9ca3af';
  ctx.font = '11px Inter, system-ui, sans-serif';
  ctx.textAlign = 'right';
  for (let i = 0; i <= 4; i++) {
    const val = maxVal * i / 4;
    const y   = padT + H - (H * i / 4);
    ctx.fillText(formatK(val), padL - 6, y + 4);
  }

  // Bars
  const primary = '#3b82f6';

  data.forEach((val, i) => {
    const barH = (val / maxVal) * H;
    const x    = padL + i * step + (step - barW) / 2;
    const y    = padT + H - barH;

    ctx.fillStyle = val > 0 ? primary : '#eaecf0';
    fillRoundedTopRect(ctx, x, y, barW, barH, 3);
  });

  // X-axis day labels (every 5th)
  ctx.fillStyle = '#9ca3af';
  ctx.textAlign = 'center';
  ctx.font = '10px Inter, system-ui, sans-serif';
  data.forEach((_, i) => {
    if ((i + 1) % 5 === 0 || i === 0) {
      const x = padL + i * step + step / 2;
      ctx.fillText(i + 1, x, padT + H + 18);
    }
  });

  // X-axis baseline
  ctx.strokeStyle = '#e5e7eb';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(padL, padT + H);
  ctx.lineTo(padL + W, padT + H);
  ctx.stroke();
}

function formatK(val) {
  if (val >= 1000) return (val / 1000).toFixed(1).replace('.', ',') + 'k';
  return Math.round(val).toString();
}

/* ── Monthly bar chart with explicit labels (CRM Plan) ───────────────────────── */
function drawMonthlyBarChart(canvas, labels, data, currentIndex) {
  if (!canvas || !data || data.length === 0) return;

  const dpr  = window.devicePixelRatio || 1;
  const cssW = canvas.clientWidth || canvas.parentElement.clientWidth || 900;
  const cssH = 200;
  canvas.width  = cssW * dpr;
  canvas.height = cssH * dpr;
  canvas.style.width  = cssW + 'px';
  canvas.style.height = cssH + 'px';

  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);

  const padL = 60, padR = 16, padT = 16, padB = 32;
  const W = cssW - padL - padR;
  const H = cssH - padT - padB;

  const maxVal = Math.max(...data, 1);
  const step   = W / data.length;
  const barW   = Math.max(8, step * 0.55);

  ctx.strokeStyle = '#e5e7eb';
  ctx.lineWidth = 1;
  ctx.setLineDash([3, 3]);
  for (let i = 0; i <= 4; i++) {
    const y = padT + H - (H * i / 4);
    ctx.beginPath();
    ctx.moveTo(padL, y);
    ctx.lineTo(padL + W, y);
    ctx.stroke();
  }
  ctx.setLineDash([]);

  ctx.fillStyle = '#9ca3af';
  ctx.font = '11px Inter, system-ui, sans-serif';
  ctx.textAlign = 'right';
  for (let i = 0; i <= 4; i++) {
    const val = maxVal * i / 4;
    const y   = padT + H - (H * i / 4);
    ctx.fillText(formatK(val), padL - 8, y + 4);
  }

  const indigo    = '#4f46e5';
  const lightBlue = '#93c5fd';

  data.forEach((val, i) => {
    const barH = (val / maxVal) * H;
    const x    = padL + i * step + (step - barW) / 2;
    const y    = padT + H - barH;

    ctx.fillStyle = i === currentIndex ? indigo : lightBlue;
    fillRoundedTopRect(ctx, x, y, barW, barH, 4);

    ctx.fillStyle = i === currentIndex ? '#1f2937' : '#6b7280';
    ctx.font = (i === currentIndex ? '700 ' : '500 ') + '11px Inter, system-ui, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(labels[i] || '', x + barW / 2, padT + H + 18);
  });

  ctx.strokeStyle = '#e5e7eb';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(padL, padT + H);
  ctx.lineTo(padL + W, padT + H);
  ctx.stroke();
}

/* ── KSeF preview modal ──────────────────────────────────────────────────── */
async function showKsefPreview(entityType, entityId) {
  const modal = document.getElementById('ksefPreviewModal');
  if (!modal) return;
  const body = document.getElementById('ksefPreviewBody');
  modal.classList.add('open');
  if (body) body.innerHTML = '<div style="padding:1rem;color:#6b7280">Ładowanie…</div>';

  try {
    const r = await fetch('/api/ksef-preview/' + entityType + '/' + entityId);
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const resp = await r.json();
    if (resp.has_fakturownia_data) {
      const isIncome = resp.invoice_type === 'income';
      body.innerHTML = buildDetailsHTML(resp.data, isIncome);
    } else {
      const num = resp.ksef_number || '—';
      body.innerHTML = '<div class="inv-details">' +
        section('Numer KSeF', [['Numer', num]]) +
        '<p style="margin:1rem;color:#6b7280;font-size:.9rem">Brak szczegółowych danych faktury — numer KSeF zapisany ręcznie.</p>' +
        '</div>';
    }
  } catch (e) {
    if (body) body.innerHTML = '<div style="padding:1rem;color:#b91c1c">Błąd ładowania: ' + e.message + '</div>';
  }
}

/* ── Dysk (GDrive) preview modal ─────────────────────────────────────────── */
async function showDiskPreview(entityType, entityId) {
  const modal = document.getElementById('ksefPreviewModal');
  if (!modal) return;
  const title = document.getElementById('ksefPreviewTitle');
  const body  = document.getElementById('ksefPreviewBody');
  if (title) title.textContent = 'Podgląd faktury z Dysku Google';
  modal.classList.add('open');
  if (body) body.innerHTML = '<div style="padding:1rem;color:#6b7280">Ładowanie…</div>';

  try {
    const r = await fetch('/api/disk-preview/' + entityType + '/' + entityId);
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const d = await r.json();
    if (d.error) throw new Error(d.error);

    const fmt = v => (v !== null && v !== undefined && v !== '') ? v : '—';
    const fmtMoney = v => v !== null && v !== undefined
      ? parseFloat(v).toLocaleString('pl-PL', {minimumFractionDigits:2, maximumFractionDigits:2}) + ' zł'
      : '—';
    const monthPad = m => m ? String(m).padStart(2, '0') : '—';

    const rows = [
      ['Plik',            fmt(d.file_name)],
      ['Rok / miesiąc',   d.gdrive_year ? d.gdrive_year + ' / ' + monthPad(d.gdrive_month) : '—'],
      ['Numer faktury',   fmt(d.invoice_number)],
      ['Kontrahent',      fmt(d.vendor_name)],
      ['NIP',             fmt(d.vendor_nip)],
      ['Data wystawienia',fmt(d.issue_date)],
      ['Typ',             d.invoice_type === 'income' ? 'Przychodowa' : 'Kosztowa'],
      ['Kwota brutto',    fmtMoney(d.amount_gross)],
      ['Kwota netto',     fmtMoney(d.amount_net)],
      ['VAT',             fmtMoney(d.vat_amount)],
    ];

    if (d.ocr && d.ocr.confidence_note) {
      rows.push(['Uwagi OCR', fmt(d.ocr.confidence_note)]);
    }

    const tableRows = rows.map(([label, value]) =>
      `<tr><th style="width:160px;font-weight:600;padding:.4rem .75rem;white-space:nowrap">${label}</th>` +
      `<td style="padding:.4rem .75rem">${String(value).replace(/</g,'&lt;').replace(/>/g,'&gt;')}</td></tr>`
    ).join('');

    body.innerHTML =
      '<div class="inv-details">' +
      '<table class="data-table data-table-sm"><tbody>' + tableRows + '</tbody></table>' +
      '</div>';
  } catch (e) {
    if (body) body.innerHTML = '<div style="padding:1rem;color:#b91c1c">Błąd ładowania: ' + e.message + '</div>';
  }
}

function buildDetailsHTML(d, isIncome) {
  const fmt = (v) => v !== null && v !== undefined && v !== '' ? v : '—';
  const fmtMoney = (v) => v !== null && v !== undefined && v !== '' ?
    parseFloat(v).toLocaleString('pl-PL', {minimumFractionDigits:2, maximumFractionDigits:2}) + ' ' + (d.currency || 'PLN') : '—';

  const STATUS_MAP = { '0': 'Wystawiona', '1': 'Wysłana', '3': 'Opłacona', '5': 'Odrzucona' };
  const PAYMENT_STATUS_MAP = {
    'paid': 'Opłacona', 'unpaid': 'Nieopłacona',
    'partial': 'Częściowo opłacona', 'overdue': 'Przeterminowana'
  };

  let html = '<div class="inv-details">';

  html += section('Podstawowe informacje', [
    ['Numer dokumentu',   fmt(d.number)],
    ['Rodzaj',            fmt(d.kind_text || d.kind)],
    ['Data sprzedaży',    fmt(d.sell_date)],
    ['Data wystawienia',  fmt(d.issue_date)],
    ['Termin płatności',  fmt(d.payment_to)],
    ['Status',            fmt(STATUS_MAP[String(d.status)] || d.status)],
    ['Status płatności',  fmt(PAYMENT_STATUS_MAP[d.payment_status] || d.payment_status)],
    ['Waluta',            fmt(d.currency)],
    ['Numer zamówienia',  fmt(d.oid)],
  ]);

  if (isIncome) {
    html += section('Wystawiający (my)', [
      ['Nazwa',    fmt(d.seller_name)],
      ['NIP',      fmt(d.seller_tax_no)],
      ['Adres',    [d.seller_street, d.seller_post_code, d.seller_city].filter(Boolean).join(', ') || '—'],
      ['Email',    fmt(d.seller_email)],
      ['Telefon',  fmt(d.seller_phone)],
      ['Bank',     fmt(d.seller_bank)],
      ['Nr konta', fmt(d.seller_bank_account)],
    ]);
    html += section('Odbiorca (klient)', [
      ['Nazwa',    fmt(d.buyer_name)],
      ['NIP',      fmt(d.buyer_tax_no)],
      ['Adres',    [d.buyer_street, d.buyer_post_code, d.buyer_city].filter(Boolean).join(', ') || '—'],
      ['Email',    fmt(d.buyer_email)],
      ['Telefon',  fmt(d.buyer_phone)],
    ]);
  } else {
    html += section('Wystawiający (dostawca)', [
      ['Nazwa',    fmt(d.buyer_name)],
      ['NIP',      fmt(d.buyer_tax_no)],
      ['Adres',    [d.buyer_street, d.buyer_post_code, d.buyer_city].filter(Boolean).join(', ') || '—'],
      ['Email',    fmt(d.buyer_email)],
      ['Telefon',  fmt(d.buyer_phone)],
      ['Bank',     fmt(d.buyer_bank)],
      ['Nr konta', fmt(d.buyer_bank_account)],
    ]);
    html += section('Nabywca (my, Arborum)', [
      ['Nazwa',    fmt(d.seller_name)],
      ['NIP',      fmt(d.seller_tax_no)],
      ['Adres',    [d.seller_street, d.seller_post_code, d.seller_city].filter(Boolean).join(', ') || '—'],
      ['Email',    fmt(d.seller_email)],
      ['Telefon',  fmt(d.seller_phone)],
    ]);
  }

  html += section('Kwoty', [
    ['Netto',    fmtMoney(d.price_net)],
    ['VAT',      fmtMoney(d.price_tax)],
    ['Brutto',   '<strong>' + fmtMoney(d.price_gross) + '</strong>'],
    ['Rabat',    d.discount ? fmt(d.discount) + '%' : '—'],
  ]);

  html += section('Płatność', [
    ['Forma płatności', fmt(d.payment_type)],
    ['Opłacono',        fmtMoney(d.paid)],
    ['Data opłacenia',  fmt(d.paid_date)],
    ['Podzielona płatność', d.split_payment ? 'Tak' : 'Nie'],
  ]);

  if (d.ksef_number || d.gov_id || d.gov_status) {
    html += section('KSeF / GOV', [
      ['Numer KSeF',  fmt(d.ksef_number)],
      ['Status KSeF', fmt(d.gov_status)],
      ['GOV ID',      fmt(d.gov_id)],
      ['GOV Kind',    fmt(d.gov_kind)],
    ]);
  }

  let products = d.product_cache;
  let productsStr = null;
  if (typeof products === 'string' && products.trim()) {
    if (products.trim().startsWith('[')) {
      try { products = JSON.parse(products); } catch(e2) { productsStr = products; products = null; }
    } else {
      productsStr = products;
      products = null;
    }
  }
  if (Array.isArray(products) && products.length > 0) {
    let tbl = '<div class="inv-section"><h4>Pozycje na dokumencie</h4>';
    tbl += '<div class="table-wrapper"><table class="data-table data-table-sm">';
    tbl += '<thead><tr><th>Nazwa</th><th>Ilość</th><th>J.m.</th><th class="text-right">Cena netto</th><th class="text-right">VAT</th><th class="text-right">Wartość brutto</th></tr></thead><tbody>';
    products.forEach(p => {
      tbl += '<tr><td>' + fmt(p.name || p.product_name) + '</td><td>' + fmt(p.count || p.quantity) + '</td>';
      tbl += '<td>' + fmt(p.unit || '') + '</td><td class="text-right">' + fmt(p.price_net || p.unit_price_net) + '</td>';
      tbl += '<td class="text-right">' + fmt(p.tax || p.vat) + '</td>';
      tbl += '<td class="text-right"><strong>' + fmt(p.total_price_gross || p.price_gross) + '</strong></td></tr>';
    });
    tbl += '</tbody></table></div></div>';
    html += tbl;
  } else if (productsStr) {
    html += section('Pozycje na dokumencie', [['Produkty', productsStr]]);
  }

  const notes = [
    ['Opis',             d.description],
    ['Opis długi',       d.description_long],
    ['Notatka wewnętrzna', d.internal_note],
    ['Uwaga nabywcy',    d.buyer_note],
    ['Dodatkowe info',   d.additional_info_desc],
  ].filter(([, v]) => v);
  if (notes.length > 0) html += section('Uwagi i notatki', notes);

  html += section('Daty systemowe', [
    ['Utworzono',    fmt(d.created_at)],
    ['Zaktualizowano', fmt(d.updated_at)],
    ['ID w systemie', fmt(d.id)],
    ['Numer GOV',    fmt(d.normalized_number || d.number)],
  ]);

  html += '</div>';
  return html;
}

function section(title, rows) {
  let html = '<div class="inv-section"><h4>' + title + '</h4><dl class="inv-dl">';
  rows.forEach(([label, val]) => {
    html += '<dt>' + label + '</dt><dd>' + (val || '—') + '</dd>';
  });
  html += '</dl></div>';
  return html;
}

/* ── Dual bar chart (income vs expenses, Canvas API) ─────────────────────────── */
function drawDualBarChart(canvas, expData, incData) {
  if (!canvas) return;
  const hasData = expData.some(v => v > 0) || incData.some(v => v > 0);
  if (!hasData) return;

  const dpr  = window.devicePixelRatio || 1;
  const cssW = canvas.clientWidth || canvas.parentElement.clientWidth || 900;
  const cssH = 200;
  canvas.width  = cssW * dpr;
  canvas.height = cssH * dpr;
  canvas.style.width  = cssW + 'px';
  canvas.style.height = cssH + 'px';

  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);

  const padL = 60, padR = 16, padT = 16, padB = 36;
  const W = cssW - padL - padR;
  const H = cssH - padT - padB;
  const n = expData.length;
  const maxVal = Math.max(...expData, ...incData, 1);
  const slotW  = W / n;
  const barW   = Math.max(2, Math.floor(slotW * 0.38));

  // Grid lines
  ctx.strokeStyle = '#e5e7eb';
  ctx.lineWidth = 1;
  ctx.setLineDash([3, 3]);
  for (let i = 0; i <= 4; i++) {
    const y = padT + H - (H * i / 4);
    ctx.beginPath();
    ctx.moveTo(padL, y);
    ctx.lineTo(padL + W, y);
    ctx.stroke();
  }
  ctx.setLineDash([]);

  // Y-axis labels
  ctx.fillStyle = '#9ca3af';
  ctx.font = '11px Inter, system-ui, sans-serif';
  ctx.textAlign = 'right';
  for (let i = 0; i <= 4; i++) {
    const val = maxVal * i / 4;
    const y   = padT + H - (H * i / 4);
    ctx.fillText(formatK(val), padL - 6, y + 4);
  }

  // Grouped bars: income (green) left, expense (red) right
  expData.forEach((exp, i) => {
    const inc = incData[i] || 0;
    const cx  = padL + i * slotW + slotW / 2;
    const gap = 1;

    if (inc > 0) {
      const h = (inc / maxVal) * H;
      ctx.fillStyle = '#22c55e';
      fillRoundedTopRect(ctx, cx - barW - gap, padT + H - h, barW, h, 3);
    }
    if (exp > 0) {
      const h = (exp / maxVal) * H;
      ctx.fillStyle = '#f87171';
      fillRoundedTopRect(ctx, cx + gap, padT + H - h, barW, h, 3);
    }
  });

  // X-axis day labels (1, every 5th)
  ctx.fillStyle = '#9ca3af';
  ctx.textAlign = 'center';
  ctx.font = '10px Inter, system-ui, sans-serif';
  expData.forEach((_, i) => {
    if ((i + 1) % 5 === 0 || i === 0) {
      ctx.fillText(i + 1, padL + i * slotW + slotW / 2, padT + H + 18);
    }
  });

  // Baseline
  ctx.strokeStyle = '#e5e7eb';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(padL, padT + H);
  ctx.lineTo(padL + W, padT + H);
  ctx.stroke();
}

/* ── Operation progress bar ──────────────────────────────────────────────────── */
/**
 * Renders a progress bar inside an api-result element.
 * current/total = 0/0 → indeterminate (animated slide)
 * current/total > 0   → determinate with % label
 */
function opProgress(el, label, current, total) {
  const pct = (total > 0) ? Math.round(current / total * 100) : 0;
  const determinate = total > 0;
  el.style.display = 'block';
  el.className = 'api-result api-loading';
  el.innerHTML =
    '<div class="op-progress-header">' +
      '<span>' + label + '</span>' +
      (determinate ? '<span class="op-progress-pct">' + pct + '%</span>' : '') +
    '</div>' +
    '<div class="op-progress-track">' +
      '<div class="op-progress-fill' + (determinate ? '' : ' indeterminate') + '"' +
           (determinate ? ' style="width:' + pct + '%"' : '') + '></div>' +
    '</div>';
}

/* ── Auto-submit filter form on select change ─────────────────────────────────── */
document.addEventListener('DOMContentLoaded', function () {
  const filterBar = document.querySelector('.filter-bar');
  if (filterBar) {
    filterBar.querySelectorAll('select').forEach(sel => {
      sel.addEventListener('change', () => filterBar.submit());
    });
  }
});

/* ── CRM: zwijane menu boczne (Firmy / Kontakty / Interesy) ────────────────────
 * Stan (zwinięte/rozwinięte) zapamiętany w localStorage, wspólny dla wszystkich
 * podstron CRM. Bezpiecznie no-op, jeśli #crm-layout nie istnieje na stronie.
 */
function initCrmSidebar() {
  const layout = document.getElementById('crm-layout');
  const btn = document.getElementById('crm-sidebar-toggle');
  if (!layout || !btn) return;

  const STORAGE_KEY = 'crm_sidebar_collapsed';
  let collapsed = localStorage.getItem(STORAGE_KEY) === '1';

  function apply() {
    layout.classList.toggle('collapsed', collapsed);
    btn.title = collapsed ? 'Rozwiń menu' : 'Zwiń menu';
  }
  apply();

  btn.addEventListener('click', () => {
    collapsed = !collapsed;
    localStorage.setItem(STORAGE_KEY, collapsed ? '1' : '0');
    apply();
  });
}
document.addEventListener('DOMContentLoaded', initCrmSidebar);

/* ── CRM: helpers ─────────────────────────────────────────────────────────────── */
function crmEsc(s) {
  return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function crmSetStatus(el, text, color) {
  if (!el) return;
  el.textContent = text;
  el.style.color = color || '';
}

/* ── CRM: usuwanie (archiwizacja) firmy z pytaniem o powiązane kontakty ────────── */
function crmConfirmDeleteCompany(form, contactsCount) {
  if (!confirm('Usunąć tę firmę?')) return false;
  if (contactsCount > 0) {
    const wantsContacts = confirm(
      `Ta firma ma ${contactsCount} powiązanych kontaktów. Czy usunąć (zarchiwizować) je również?`
    );
    const hidden = form.querySelector('input[name="archive_contacts"]');
    if (hidden) hidden.value = wantsContacts ? '1' : '0';
  }
  return true;
}

/* ── CRM: usuwanie (archiwizacja) kontaktu z pytaniem o powiązaną firmę ────────── */
function crmConfirmDeleteContact(form, hasCompany) {
  if (!confirm('Usunąć ten kontakt?')) return false;
  if (hasCompany) {
    const wantsCompany = confirm('Czy usunąć (zarchiwizować) też powiązaną firmę?');
    const hidden = form.querySelector('input[name="archive_company"]');
    if (hidden) hidden.value = wantsCompany ? '1' : '0';
  }
  return true;
}

/* ── CRM: pobieranie danych firmy po NIP/KRS (formularz Firmy) ────────────────── */
async function crmLookupCompany(kind) {
  const input = document.getElementById(kind);
  const statusEl = document.getElementById('lookup-status');
  const value = input ? input.value.trim() : '';
  if (!value) {
    crmSetStatus(statusEl, 'Wpisz najpierw ' + (kind === 'nip' ? 'NIP' : 'numer KRS') + '.', 'var(--danger)');
    return;
  }
  crmSetStatus(statusEl, 'Pobieranie danych…', 'var(--slate-mid)');
  try {
    const resp = await fetch(window.API_BASE + '/api/crm/company-lookup?' + new URLSearchParams({ [kind]: value }));
    const result = await resp.json();
    if (!result.ok) {
      crmSetStatus(statusEl, result.error || 'Nie udało się pobrać danych.', 'var(--danger)');
      return;
    }
    const d = result.data;
    const set = (id, val) => { const el = document.getElementById(id); if (el && val) el.value = val; };
    set('name', d.name);
    set('country', d.country);
    set('city', d.city);
    set('street', d.street);
    set('house_number', d.house_number);
    set('flat_number', d.flat_number);
    set('postal_code', d.postal_code);
    set('nip', d.nip);
    set('krs', d.krs);
    crmSetStatus(statusEl, 'Dane uzupełnione' + (d.name ? ' (' + d.name + ').' : '.'), 'var(--success)');
  } catch (e) {
    crmSetStatus(statusEl, 'Błąd połączenia podczas pobierania danych.', 'var(--danger)');
  }
}

/* ── CRM: pobranie profilu firmy ze strony WWW (scraping + AI) ─────────────────
 * Uzupełnia opis (zawsze) oraz puste pola kontaktowe/adresowe i branże
 * (poprzez wrap.tagInputAdd z initTagInput), bez nadpisywania już wypełnionych pól.
 */
async function crmScrapeWebsite() {
  const input = document.getElementById('website');
  const statusEl = document.getElementById('website-status');
  const url = input ? input.value.trim() : '';
  if (!url) {
    crmSetStatus(statusEl, 'Wpisz najpierw adres strony WWW.', 'var(--danger)');
    return;
  }
  crmSetStatus(statusEl, 'Pobieranie strony i analiza AI… (może potrwać kilka sekund)', 'var(--slate-mid)');
  try {
    const resp = await fetch(window.API_BASE + '/api/crm/companies/scrape-website', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    });
    const result = await resp.json();
    if (!result.ok) {
      crmSetStatus(statusEl, result.error || 'Nie udało się pobrać informacji ze strony.', 'var(--danger)');
      return;
    }
    const d = result.data;
    const setIfEmpty = (id, val) => {
      const el = document.getElementById(id);
      if (el && val && !el.value.trim()) el.value = val;
    };
    const descEl = document.getElementById('description');
    if (descEl && d.description) descEl.value = d.description;
    setIfEmpty('email', d.email);
    setIfEmpty('phone', d.phone);
    setIfEmpty('nip', d.nip);
    setIfEmpty('city', d.city);
    setIfEmpty('street', d.street);
    setIfEmpty('house_number', d.house_number);
    setIfEmpty('flat_number', d.flat_number);
    setIfEmpty('postal_code', d.postal_code);

    const industriesWrap = document.getElementById('industries-wrap');
    if (industriesWrap && industriesWrap.tagInputAdd && Array.isArray(d.industries)) {
      d.industries.forEach(ind => industriesWrap.tagInputAdd(ind));
    }
    crmSetStatus(statusEl, 'Dane uzupełnione na podstawie strony WWW.', 'var(--success)');
  } catch (e) {
    crmSetStatus(statusEl, 'Błąd połączenia podczas pobierania danych ze strony.', 'var(--danger)');
  }
}

/* ── CRM: tag/branża chip-input ────────────────────────────────────────────────
 * Wymaga w DOM: <div id="{wrapId}"> z <input id="{inputId}"> oraz
 * <div id="{suggestId}" class="tag-suggestions">. Tworzy chipy + hidden inputy
 * name="tags[]" / "industries[]" zależnie od `kind`.
 */
function initTagInput(wrapId, inputId, suggestId, kind, initialValues) {
  const wrap = document.getElementById(wrapId);
  const input = document.getElementById(inputId);
  const suggestBox = document.getElementById(suggestId);
  if (!wrap || !input || !suggestBox) return;

  const TAG_FIELD_NAMES = { tag: 'tags[]', industry: 'industries[]', source: 'sources[]' };
  const fieldName = TAG_FIELD_NAMES[kind] || 'tags[]';
  let values = Array.isArray(initialValues) ? [...initialValues] : [];

  function render() {
    wrap.querySelectorAll('.tag-chip, input[type=hidden]').forEach(el => el.remove());
    values.forEach(v => {
      const chip = document.createElement('span');
      chip.className = 'tag-chip';
      chip.appendChild(document.createTextNode(v));
      const rm = document.createElement('button');
      rm.type = 'button';
      rm.className = 'tag-chip-remove';
      rm.textContent = '✕';
      rm.onclick = () => { values = values.filter(x => x !== v); render(); };
      chip.appendChild(rm);
      wrap.insertBefore(chip, input);

      const hidden = document.createElement('input');
      hidden.type = 'hidden';
      hidden.name = fieldName;
      hidden.value = v;
      wrap.appendChild(hidden);
    });
  }

  function closeSuggestions() {
    suggestBox.classList.remove('open');
    suggestBox.innerHTML = '';
  }

  function addValue(raw) {
    const v = raw.trim().replace(/,+$/, '');
    if (!v || values.includes(v)) { input.value = ''; closeSuggestions(); return; }
    values.push(v);
    input.value = '';
    closeSuggestions();
    render();
  }

  input.addEventListener('keydown', e => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      addValue(input.value);
    } else if (e.key === 'Backspace' && !input.value && values.length) {
      values.pop();
      render();
    }
  });

  let timer = null;
  input.addEventListener('input', () => {
    clearTimeout(timer);
    const q = input.value.trim();
    timer = setTimeout(async () => {
      try {
        const resp = await fetch(window.API_BASE + '/api/crm/suggest?type=' + kind + '&q=' + encodeURIComponent(q));
        const items = (await resp.json()).filter(it => !values.includes(it));
        if (items.length === 0) { closeSuggestions(); return; }
        suggestBox.innerHTML = items.map(it =>
          '<div class="tag-suggestion-item">' + crmEsc(it) + '</div>'
        ).join('');
        suggestBox.classList.add('open');
        suggestBox.querySelectorAll('.tag-suggestion-item').forEach((el, i) => {
          el.onclick = () => addValue(items[i]);
        });
      } catch (_) { closeSuggestions(); }
    }, 250);
  });

  document.addEventListener('click', e => {
    if (!wrap.contains(e.target)) closeSuggestions();
  });

  wrap.tagInputAdd = addValue;
  render();
}

/* ── CRM: podpowiedzi dla pojedynczego pola tekstowego (np. wartość w edycji
 * zbiorczej firm) — te same podpowiedzi co w initTagInput, ale bez chipów,
 * kliknięcie podpowiedzi po prostu wpisuje wartość do pola. `kindFn` zwraca
 * aktualny rodzaj ('tag'/'industry'/'source'); dla innych wartości podpowiedzi
 * są wyłączone. */
function initSuggestInput(inputId, suggestId, kindFn) {
  const input = document.getElementById(inputId);
  const suggestBox = document.getElementById(suggestId);
  if (!input || !suggestBox) return;

  function closeSuggestions() {
    suggestBox.classList.remove('open');
    suggestBox.innerHTML = '';
  }

  let timer = null;
  input.addEventListener('input', () => {
    clearTimeout(timer);
    const kind = kindFn();
    if (!['tag', 'industry', 'source'].includes(kind)) { closeSuggestions(); return; }
    const q = input.value.trim();
    timer = setTimeout(async () => {
      try {
        const resp = await fetch(window.API_BASE + '/api/crm/suggest?type=' + kind + '&q=' + encodeURIComponent(q));
        const items = await resp.json();
        if (items.length === 0) { closeSuggestions(); return; }
        suggestBox.innerHTML = items.map(it =>
          '<div class="tag-suggestion-item">' + crmEsc(it) + '</div>'
        ).join('');
        suggestBox.classList.add('open');
        suggestBox.querySelectorAll('.tag-suggestion-item').forEach((el, i) => {
          el.onclick = () => { input.value = items[i]; closeSuggestions(); input.focus(); };
        });
      } catch (_) { closeSuggestions(); }
    }, 250);
  });

  document.addEventListener('click', e => {
    if (!input.contains(e.target) && !suggestBox.contains(e.target)) closeSuggestions();
  });
}

/* ── CRM: szybkie utworzenie firmy po NIP/KRS (formularz Kontaktu) ─────────────
 * Wymaga elementów o id: company-quick-create-fields, quick-nip, quick-krs,
 * quick-create-status, oraz entity-pickera 'company-picker' do podpięcia wyniku.
 */
function toggleQuickCreateCompany(e) {
  e.preventDefault();
  const fields = document.getElementById('company-quick-create-fields');
  if (fields) fields.classList.toggle('hidden');
}

async function quickCreateCompany() {
  const nip = document.getElementById('quick-nip')?.value.trim() || '';
  const krs = document.getElementById('quick-krs')?.value.trim() || '';
  const statusEl = document.getElementById('quick-create-status');
  if (!nip && !krs) {
    crmSetStatus(statusEl, 'Podaj NIP lub KRS.', 'var(--danger)');
    return;
  }
  crmSetStatus(statusEl, 'Pobieranie danych…', 'var(--slate-mid)');
  try {
    const resp = await fetch(window.API_BASE + '/api/crm/companies/quick-create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nip, krs }),
    });
    const result = await resp.json();
    if (!result.ok) {
      crmSetStatus(statusEl, result.error || 'Nie udało się utworzyć firmy.', 'var(--danger)');
      return;
    }
    selectEntityPicker('company-picker', result.id, result.name);
    document.getElementById('company-quick-create-fields')?.classList.add('hidden');
    crmSetStatus(statusEl, result.created ? 'Firma utworzona i przypisana.' : 'Znaleziono istniejącą firmę i przypisano.', 'var(--success)');
  } catch (e) {
    crmSetStatus(statusEl, 'Błąd połączenia.', 'var(--danger)');
  }
}

/* ── CRM: wyszukiwarka firmy / kontaktu (combobox) ─────────────────────────────
 * Wymaga w DOM: <div id="{pickerId}"> zawierający
 * <input id="{pickerId}-input">, <div id="{pickerId}-results">,
 * <input type="hidden" id="{pickerId}-hidden"> i opcjonalnie
 * <div id="{pickerId}-selected"> (gdy wartość już wybrana).
 */
function initEntityPicker(pickerId, searchUrl) {
  const root = document.getElementById(pickerId);
  const input = document.getElementById(pickerId + '-input');
  const results = document.getElementById(pickerId + '-results');
  const hidden = document.getElementById(pickerId + '-hidden');
  if (!root || !input || !results || !hidden) return;

  let timer = null;
  let lastItems = [];

  input.addEventListener('input', () => {
    clearTimeout(timer);
    timer = setTimeout(async () => {
      const q = input.value.trim();
      const sep = searchUrl.includes('?') ? '&' : '?';
      try {
        const resp = await fetch(window.API_BASE + searchUrl + sep + 'q=' + encodeURIComponent(q));
        lastItems = await resp.json();
      } catch (_) { lastItems = []; }
      if (lastItems.length === 0) {
        results.innerHTML = '<div class="entity-picker-result-item text-muted">Brak wyników</div>';
        results.classList.add('open');
        return;
      }
      results.innerHTML = lastItems.map((it, i) => {
        const label = it.name || ((it.first_name || '') + ' ' + (it.last_name || '')).trim();
        const sub = it.company_name || it.city || it.nip || '';
        return '<div class="entity-picker-result-item" data-i="' + i + '">'
          + '<div>' + crmEsc(label) + '</div>'
          + (sub ? '<div class="entity-picker-result-sub">' + crmEsc(sub) + '</div>' : '')
          + '</div>';
      }).join('');
      results.classList.add('open');
      results.querySelectorAll('.entity-picker-result-item[data-i]').forEach(el => {
        el.onclick = () => {
          const it = lastItems[parseInt(el.dataset.i, 10)];
          const label = it.name || ((it.first_name || '') + ' ' + (it.last_name || '')).trim();
          selectEntityPicker(pickerId, it.id, label);
        };
      });
    }, 250);
  });

  document.addEventListener('click', e => {
    if (!root.contains(e.target)) results.classList.remove('open');
  });
}

function selectEntityPicker(pickerId, id, label) {
  document.getElementById(pickerId + '-hidden').value = id;
  const input = document.getElementById(pickerId + '-input');
  input.value = '';
  input.style.display = 'none';
  const results = document.getElementById(pickerId + '-results');
  results.classList.remove('open');
  results.innerHTML = '';

  let selected = document.getElementById(pickerId + '-selected');
  if (!selected) {
    selected = document.createElement('div');
    selected.className = 'entity-picker-selected';
    selected.id = pickerId + '-selected';
    input.parentNode.insertBefore(selected, input);
  }
  selected.innerHTML = '<span class="entity-picker-selected-name">' + crmEsc(label) + '</span>'
    + '<button type="button" class="entity-picker-clear">✕</button>';
  selected.querySelector('.entity-picker-clear').onclick = () => clearEntityPicker(pickerId);
}

function clearEntityPicker(pickerId) {
  document.getElementById(pickerId + '-hidden').value = '';
  const selected = document.getElementById(pickerId + '-selected');
  if (selected) selected.remove();
  const input = document.getElementById(pickerId + '-input');
  input.style.display = '';
  input.focus();
}

/* ── CRM: widoczność kolumn listy (zapamiętana w localStorage + per użytkownik) ──
 * Checkboxy w menu muszą mieć data-col="<nazwa>" odpowiadającą atrybutom
 * data-col="<nazwa>" na <th>/<td> w tabeli. `defaultHidden` to kolumny domyślnie
 * schowane, zanim użytkownik cokolwiek wybierze (brak zapisanego ustawienia —
 * odróżniane od "zapisano puste [] / wszystko widoczne" przez null z localStorage).
 */
function initColumnToggle(tableId, storageKey, btnId, menuId, defaultHidden) {
  const table = document.getElementById(tableId);
  const menu = document.getElementById(menuId);
  const btn = document.getElementById(btnId);
  if (!table || !menu || !btn) return;

  const items = Array.from(menu.querySelectorAll('.col-toggle-item[data-col]'));
  const defaultOrder = items.map(it => it.dataset.col);
  let hidden = [];
  let order = defaultOrder.slice();

  /* Format zapisany w localStorage/serwerze to { hidden: [...], order: [...] }.
     Stary format (sama tablica) oznaczał tylko `hidden` — zachowujemy wsteczną
     kompatybilność, żeby nie zgubić ustawień zapisanych przed dodaniem reorderu. */
  function parseStored(raw) {
    if (raw == null) return null;
    try {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) return { hidden: parsed, order: null };
      if (parsed && typeof parsed === 'object') return { hidden: parsed.hidden || [], order: parsed.order || null };
    } catch (_) {}
    return null;
  }

  const localParsed = parseStored(localStorage.getItem(storageKey));
  if (localParsed) {
    hidden = localParsed.hidden;
    if (localParsed.order) order = reconcileOrder(localParsed.order);
  } else {
    hidden = defaultHidden ? defaultHidden.slice() : [];
  }

  function reconcileOrder(savedOrder) {
    const known = new Set(defaultOrder);
    const cleaned = savedOrder.filter(c => known.has(c));
    defaultOrder.forEach(c => { if (!cleaned.includes(c)) cleaned.push(c); });
    return cleaned;
  }

  function applyOrder() {
    // Kolumny data-col są w markupie ciągłym blokiem (między kolumnami stałymi
    // typu favicon/akcje) — usuwamy je i wstawiamy z powrotem w zadanej kolejności
    // w miejscu, gdzie zaczynał się ten blok.
    table.querySelectorAll('tr').forEach(row => {
      const cells = {};
      let anchor = null;
      let anchorIndex = -1;
      Array.from(row.children).forEach((cell, idx) => {
        const col = cell.dataset.col;
        if (col && order.includes(col)) {
          cells[col] = cell;
          if (anchorIndex === -1) anchorIndex = idx;
        }
      });
      if (anchorIndex === -1) return;
      anchor = row.children[anchorIndex] || null;
      order.forEach(col => {
        const cell = cells[col];
        if (cell) row.insertBefore(cell, anchor);
      });
    });

    // Ta sama kolejność w menu (żeby drag handle odzwierciedlał aktualny stan).
    order.forEach(col => {
      const item = items.find(it => it.dataset.col === col);
      if (item) menu.appendChild(item);
    });
  }

  function applyVisibility() {
    items.forEach(item => {
      const col = item.dataset.col;
      const cb = item.querySelector('input[type=checkbox]');
      const isHidden = hidden.includes(col);
      cb.checked = !isHidden;
      table.querySelectorAll('[data-col="' + col + '"]').forEach(el => {
        el.style.display = isHidden ? 'none' : '';
      });
    });
  }

  function persist() {
    const value = JSON.stringify({ hidden, order });
    localStorage.setItem(storageKey, value);
    fetch(window.API_BASE + '/api/user-settings/' + storageKey, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ value }),
    }).catch(() => {});
  }

  items.forEach(item => {
    const cb = item.querySelector('input[type=checkbox]');
    cb.addEventListener('change', () => {
      const col = item.dataset.col;
      hidden = cb.checked ? hidden.filter(c => c !== col) : [...hidden, col];
      persist();
      applyVisibility();
    });
  });

  let dragged = null;
  items.forEach(item => {
    item.addEventListener('dragstart', () => {
      dragged = item;
      item.classList.add('dragging');
    });
    item.addEventListener('dragend', () => {
      item.classList.remove('dragging');
      items.forEach(it => it.classList.remove('drag-over'));
    });
    item.addEventListener('dragover', e => {
      e.preventDefault();
      if (item !== dragged) item.classList.add('drag-over');
    });
    item.addEventListener('dragleave', () => item.classList.remove('drag-over'));
    item.addEventListener('drop', e => {
      e.preventDefault();
      item.classList.remove('drag-over');
      if (!dragged || dragged === item) return;
      const before = Array.from(menu.children).indexOf(item) < Array.from(menu.children).indexOf(dragged);
      menu.insertBefore(dragged, before ? item : item.nextSibling);
      order = Array.from(menu.querySelectorAll('.col-toggle-item[data-col]')).map(it => it.dataset.col);
      applyOrder();
      persist();
    });
  });

  btn.addEventListener('click', e => {
    e.stopPropagation();
    menu.classList.toggle('open');
  });
  document.addEventListener('click', e => {
    if (!menu.contains(e.target) && e.target !== btn) menu.classList.remove('open');
  });

  applyOrder();
  applyVisibility();

  /* Serwer jest źródłem prawdy między urządzeniami — localStorage to tylko
     natychmiastowy cache na czas wczytywania strony. */
  fetch(window.API_BASE + '/api/user-settings/' + storageKey)
    .then(r => r.ok ? r.json() : null)
    .then(data => {
      if (data && data.value) {
        const parsed = parseStored(data.value);
        if (parsed) {
          hidden = parsed.hidden;
          if (parsed.order) order = reconcileOrder(parsed.order);
          localStorage.setItem(storageKey, data.value);
          applyOrder();
          applyVisibility();
        }
      }
    })
    .catch(() => {});
}

/* ── CRM: przełącznik widoku Lista/Kanban na liście interesów (zapamiętany w localStorage) ── */
function initDealsViewToggle() {
  const listBtn = document.getElementById('deals-view-list');
  const kanbanBtn = document.getElementById('deals-view-kanban');
  const listView = document.getElementById('deals-list-view');
  const kanbanView = document.getElementById('deals-kanban-view');
  if (!listBtn || !kanbanBtn || !listView || !kanbanView) return;

  const STORAGE_KEY = 'crm_deals_view';

  function apply(view) {
    listView.style.display = view === 'kanban' ? 'none' : '';
    kanbanView.style.display = view === 'kanban' ? '' : 'none';
    listBtn.classList.toggle('btn-primary', view !== 'kanban');
    listBtn.classList.toggle('btn-outline', view === 'kanban');
    kanbanBtn.classList.toggle('btn-primary', view === 'kanban');
    kanbanBtn.classList.toggle('btn-outline', view !== 'kanban');
  }

  listBtn.addEventListener('click', () => {
    localStorage.setItem(STORAGE_KEY, 'list');
    apply('list');
  });
  kanbanBtn.addEventListener('click', () => {
    localStorage.setItem(STORAGE_KEY, 'kanban');
    apply('kanban');
  });

  apply(localStorage.getItem(STORAGE_KEY) === 'kanban' ? 'kanban' : 'list');
}
