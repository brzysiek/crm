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
  ctx.strokeStyle = '#e8e8e6';
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
  ctx.fillStyle = '#878782';
  ctx.font = '11px Work Sans, system-ui, sans-serif';
  ctx.textAlign = 'right';
  for (let i = 0; i <= 4; i++) {
    const val = maxVal * i / 4;
    const y   = padT + H - (H * i / 4);
    ctx.fillText(formatK(val), padL - 6, y + 4);
  }

  // Bars
  const lime        = '#B5E619';
  const bottleGreen = '#1C4B40';

  data.forEach((val, i) => {
    const barH = (val / maxVal) * H;
    const x    = padL + i * step + (step - barW) / 2;
    const y    = padT + H - barH;

    ctx.fillStyle = val > 0 ? bottleGreen : '#e0e0de';
    ctx.fillRect(x, y, barW, barH);
  });

  // X-axis day labels (every 5th)
  ctx.fillStyle = '#878782';
  ctx.textAlign = 'center';
  ctx.font = '10px Work Sans, system-ui, sans-serif';
  data.forEach((_, i) => {
    if ((i + 1) % 5 === 0 || i === 0) {
      const x = padL + i * step + step / 2;
      ctx.fillText(i + 1, x, padT + H + 18);
    }
  });

  // X-axis baseline
  ctx.strokeStyle = '#cdcdc8';
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

/* ── KSeF preview modal ──────────────────────────────────────────────────── */
async function showKsefPreview(entityType, entityId) {
  const modal = document.getElementById('ksefPreviewModal');
  if (!modal) return;
  const body = document.getElementById('ksefPreviewBody');
  modal.classList.add('open');
  if (body) body.innerHTML = '<div style="padding:1rem;color:#666">Ładowanie…</div>';

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
        '<p style="margin:1rem;color:#666;font-size:.9rem">Brak szczegółowych danych faktury — numer KSeF zapisany ręcznie.</p>' +
        '</div>';
    }
  } catch (e) {
    if (body) body.innerHTML = '<div style="padding:1rem;color:#c00">Błąd ładowania: ' + e.message + '</div>';
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
  if (body) body.innerHTML = '<div style="padding:1rem;color:#666">Ładowanie…</div>';

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
    if (body) body.innerHTML = '<div style="padding:1rem;color:#c00">Błąd ładowania: ' + e.message + '</div>';
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
  ctx.strokeStyle = '#e8e8e6';
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
  ctx.fillStyle = '#878782';
  ctx.font = '11px Work Sans, system-ui, sans-serif';
  ctx.textAlign = 'right';
  for (let i = 0; i <= 4; i++) {
    const val = maxVal * i / 4;
    const y   = padT + H - (H * i / 4);
    ctx.fillText(formatK(val), padL - 6, y + 4);
  }

  // Grouped bars: income (lime) left, expense (bottle-green) right
  expData.forEach((exp, i) => {
    const inc = incData[i] || 0;
    const cx  = padL + i * slotW + slotW / 2;
    const gap = 1;

    if (inc > 0) {
      const h = (inc / maxVal) * H;
      ctx.fillStyle = '#B5E619';
      ctx.fillRect(cx - barW - gap, padT + H - h, barW, h);
    }
    if (exp > 0) {
      const h = (exp / maxVal) * H;
      ctx.fillStyle = '#1C4B40';
      ctx.fillRect(cx + gap, padT + H - h, barW, h);
    }
  });

  // X-axis day labels (1, every 5th)
  ctx.fillStyle = '#878782';
  ctx.textAlign = 'center';
  ctx.font = '10px Work Sans, system-ui, sans-serif';
  expData.forEach((_, i) => {
    if ((i + 1) % 5 === 0 || i === 0) {
      ctx.fillText(i + 1, padL + i * slotW + slotW / 2, padT + H + 18);
    }
  });

  // Baseline
  ctx.strokeStyle = '#cdcdc8';
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
