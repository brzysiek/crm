"""Moduł Finanse v2 — dashboard nad danymi z Fakturowni.

Widok, nie rejestr: dokumentów się tu nie tworzy ani nie edytuje. Źródłem prawdy
jest Fakturownia, CRM trzyma lustro (`fin_documents`) i własne metadane.
"""
import calendar
import json
import re
import unicodedata
from datetime import date
from decimal import Decimal

from flask import (Blueprint, flash, jsonify, redirect, render_template, request,
                   session, url_for)

from models.fin_document import (GOV_STATUS_LABELS, KIND_LABELS, NON_FINANCIAL_KINDS,
                                 STATUS_LABELS, available_months, available_years,
                                 count_documents, count_uncategorized, departments,
                                 get_document, list_documents, open_items, period_totals)
from models.fin_category import (bulk_set_category, category_monthly, category_totals,
                                 clear_document_category, create_category, get_category_by_slug,
                                 list_categories, update_category)
from models.fin_tax import (RATE_LABELS, list_obligations, list_rates, mark_obligation_paid,
                            missing_rates, rate_years, set_rate, unmark_obligation_paid,
                            upcoming_obligations, upsert_obligation, vat_months)
import models.fin_bank as fin_bank_store
from models.fin_bank import STATUS_LABELS as BANK_STATUS_LABELS
from models.settings import get_setting
from database import get_db
from services.fakturownia_api import FakturowniaError
from services.fin_bank import (BANK_LABELS, BankImportError, import_csv, link_payment,
                               suggest_matches, unlink_payment)
from services.fin_invoice import FinWriteError
from services.fin_rules import (FIELD_LABELS, MATCH_FIELDS, MATCH_TYPES, TYPE_LABELS,
                                apply_rules, create_rule, delete_rule, list_rules, toggle_rule)
from services.fin_sync import get_sync_state, sync_documents
from services.fin_tax import OBLIGATION_LABELS, obligation_rows, period_overview

bp = Blueprint('fin', __name__, url_prefix='/fin')

PER_PAGE = 50

BUCKET_LABELS = {
    'overdue': 'Przeterminowane',
    'week': 'Najbliższe 7 dni',
    'month': 'Do 30 dni',
    'later': 'Później',
    'no_date': 'Bez terminu',
}
BUCKET_ORDER = ('overdue', 'week', 'month', 'later', 'no_date')


def _group_by_bucket(rows: list[dict]) -> list[dict]:
    """Nieopłacone dokumenty w kubełkach terminów, w kolejności pilności."""
    grouped = {key: [] for key in BUCKET_ORDER}
    for row in rows:
        grouped.get(row['bucket'], grouped['later']).append(row)
    return [{'key': key, 'label': BUCKET_LABELS[key], 'rows': grouped[key],
             'total': sum(r['amount_left'] for r in grouped[key])}
            for key in BUCKET_ORDER if grouped[key]]


@bp.route('/')
def index():
    today = date.today()
    month = today.strftime('%Y-%m')
    month_end = date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])

    payables = open_items(is_income=False)
    receivables = open_items(is_income=True)

    # Podatki bieżącego rozliczenia: symulacja za ostatni zamknięty miesiąc plus to,
    # co leży niezapłacone w rejestrze z innych okresów. Brak stawek nie może wywalić
    # ekranu, na którym patrzy się głównie na faktury — stąd łagodne ominięcie.
    tax_period = _tax_period()
    tax_rows, tax_warning = [], ''
    try:
        tax_rows = [r for r in obligation_rows(period_overview(tax_period))
                    if not r['paid_at'] and r['amount'] > 0]
    except ValueError as e:
        tax_warning = str(e)
    for entry in upcoming_obligations():
        if entry['period'] != tax_period:
            tax_rows.append({'kind': entry['kind'], 'label': OBLIGATION_LABELS.get(entry['kind'],
                             entry['kind']), 'period': entry['period'], 'amount': entry['amount'],
                             'calculated': entry['amount_calculated'],
                             'declared': entry['amount_declared'],
                             'due_date': entry['due_date'], 'paid_at': None})
    tax_rows.sort(key=lambda r: (r['due_date'] is None, r['due_date']))

    return render_template(
        'fin/dashboard.html',
        active_tab='dashboard',
        today=today,
        month=month,
        payable_groups=_group_by_bucket(payables),
        receivable_groups=_group_by_bucket(receivables),
        payables_total=sum(r['amount_left'] for r in payables),
        receivables_total=sum(r['amount_left'] for r in receivables),
        overdue_payables=sum(r['amount_left'] for r in payables if r['bucket'] == 'overdue'),
        overdue_receivables=sum(r['amount_left'] for r in receivables if r['bucket'] == 'overdue'),
        tax_period=tax_period,
        tax_rows=tax_rows,
        tax_total=sum((r['amount'] for r in tax_rows), Decimal('0')),
        tax_overdue=sum((r['amount'] for r in tax_rows
                         if r['due_date'] and r['due_date'] < today), Decimal('0')),
        tax_warning=tax_warning,
        month_totals=period_totals(f'{month}-01', month_end.isoformat()),
        year_totals=period_totals(f'{today.year}-01-01', f'{today.year}-12-31'),
        uncategorized=count_uncategorized(),
        sync=get_sync_state('documents'),
    )


def _request_filters() -> dict:
    """Filtry z URL-a, przepuszczone przez białą listę wartości."""
    kind = request.args.get('kind', 'cost')
    payment = request.args.get('payment', '')
    ksef = request.args.get('ksef', '')
    return {
        'kind': kind if kind in ('cost', 'income', 'all') else 'cost',
        'payment': payment if payment in ('paid', 'unpaid', 'overdue') else '',
        'ksef': ksef if ksef in ('with', 'without') else '',
        'month': request.args.get('month', '').strip(),
        'category_id': request.args.get('category_id', type=int),
        'uncategorized': request.args.get('uncategorized') == '1',
        'department_id': request.args.get('department_id', type=int),
        'search': request.args.get('search', '').strip(),
        'financial_only': request.args.get('all_kinds') != '1',
    }


@bp.route('/dokumenty')
def documents():
    filters = _request_filters()
    query = dict(filters)
    if query['kind'] == 'all':
        query['kind'] = ''

    sort = request.args.get('sort', 'issue_date')
    direction = request.args.get('dir', 'desc')
    page = max(request.args.get('page', 1, type=int), 1)

    total = count_documents(query)
    rows = list_documents(query, sort=sort, direction=direction,
                          limit=PER_PAGE, offset=(page - 1) * PER_PAGE)

    return render_template(
        'fin/documents.html',
        active_tab='documents',
        rows=rows,
        total=total,
        page=page,
        pages=max((total + PER_PAGE - 1) // PER_PAGE, 1),
        filters=filters,
        sort=sort,
        direction=direction,
        today_date=date.today(),
        months=available_months(),
        department_ids=departments(),
        categories=list_categories(kind='income' if filters['kind'] == 'income' else None),
        kind_labels=KIND_LABELS,
        status_labels=STATUS_LABELS,
        gov_labels=GOV_STATUS_LABELS,
        non_financial=NON_FINANCIAL_KINDS,
        uncategorized=count_uncategorized(),
        sync=get_sync_state('documents'),
    )


def _positions(raw_json) -> list[dict]:
    """Pozycje faktury czytamy z zapisanej odpowiedzi API — nie mają własnej tabeli."""
    if not raw_json:
        return []
    try:
        return json.loads(raw_json).get('positions') or []
    except (ValueError, AttributeError):
        return []


@bp.route('/dokumenty/<int:fakturownia_id>')
def document(fakturownia_id: int):
    row = get_document(fakturownia_id)
    if not row:
        flash('Nie znam takiego dokumentu — może nie został jeszcze zsynchronizowany.', 'error')
        return redirect(url_for('fin.documents'))
    subdomain = get_setting('fakturownia_subdomain', '')
    return render_template(
        'fin/document.html',
        active_tab='documents',
        doc=row,
        today=date.today(),
        categories=list_categories(kind='income' if row['is_income'] else 'cost'),
        positions=_positions(row.get('raw_json')),
        payments=fin_bank_store.links_for_document(fakturownia_id),
        bank_labels=BANK_LABELS,
        fakturownia_url=(f'https://{subdomain}.fakturownia.pl/invoices/{fakturownia_id}'
                         if subdomain else None),
        kind_labels=KIND_LABELS,
        status_labels=STATUS_LABELS,
        gov_labels=GOV_STATUS_LABELS,
        uncategorized=count_uncategorized(),
        sync=get_sync_state('documents'),
    )


@bp.route('/sync', methods=['POST'])
def sync():
    full = request.form.get('full') == '1'
    try:
        result = sync_documents(full=full)
    except FakturowniaError as e:
        flash(f'Synchronizacja nie doszła do końca: {e}', 'error')
    else:
        flash(f"Synchronizacja: {result['seen']} dokumentów, {result['new']} nowych, "
              f"{result['updated']} zaktualizowanych.", 'success')
        for warning in result['warnings'][:3]:
            flash(warning, 'error')
    return redirect(request.form.get('back') or url_for('fin.index'))


@bp.route('/api/sync', methods=['POST'])
def api_sync():
    """Ten sam sync dla crona i MCP."""
    try:
        result = sync_documents(full=request.args.get('full') == '1')
    except FakturowniaError as e:
        return jsonify({'ok': False, 'error': str(e)}), 502
    result['cursor'] = result['cursor'].isoformat() if result['cursor'] else None
    return jsonify({'ok': True, **result})


# ── Kategoryzacja ────────────────────────────────────────────────────────────

@bp.route('/dokumenty/kategoria', methods=['POST'])
def assign_category():
    """Masowe przypisanie kategorii z listy dokumentów."""
    ids = [int(v) for v in request.form.getlist('doc_id') if v.isdigit()]
    raw_category = request.form.get('category_id', '')
    if not ids:
        flash('Nie zaznaczono żadnego dokumentu.', 'error')
    elif raw_category == 'none':
        for fakturownia_id in ids:
            clear_document_category(fakturownia_id)
        flash(f'Usunięto kategorię z {len(ids)} dokumentów.', 'success')
    elif raw_category.isdigit():
        count = bulk_set_category(ids, int(raw_category), source='manual')
        flash(f'Przypisano kategorię do {count} dokumentów.', 'success')
    else:
        flash('Nie wybrano kategorii.', 'error')
    return redirect(request.form.get('back') or url_for('fin.documents'))


@bp.route('/reguly/z-kontrahenta', methods=['POST'])
def rule_from_counterparty():
    """Skrót z listy: „tak mam księgować wszystko od tego kontrahenta”."""
    tax_no = request.form.get('tax_no', '').strip()
    category_id = request.form.get('category_id', '')
    if not tax_no or not category_id.isdigit():
        flash('Potrzebny NIP kontrahenta i kategoria.', 'error')
        return redirect(request.form.get('back') or url_for('fin.documents'))
    create_rule('counterparty_tax_no_norm', 'equals', tax_no, int(category_id), priority=20)
    result = apply_rules()
    flash(f"Reguła dodana, przypisała kategorię {result['assigned']} dokumentom.", 'success')
    return redirect(request.form.get('back') or url_for('fin.documents'))


# ── Analityka ────────────────────────────────────────────────────────────────

def _pivot(rows: list[dict], months: list[str]) -> list[dict]:
    """Wiersze (miesiąc, kategoria, net) → tabela kategoria × miesiąc."""
    by_category: dict = {}
    for row in rows:
        key = row['category_id']
        entry = by_category.setdefault(key, {
            'category_id': key,
            'category_name': row['category_name'] or 'Bez kategorii',
            'months': {m: Decimal('0') for m in months},
            'total': Decimal('0'),
            'documents': 0,
        })
        entry['months'][row['month']] = entry['months'].get(row['month'], Decimal('0')) + row['net']
        entry['total'] += row['net']
        entry['documents'] += row['documents']
    ordered = sorted(by_category.values(), key=lambda e: e['total'], reverse=True)
    for entry in ordered:
        entry['series'] = [entry['months'].get(m, Decimal('0')) for m in months]
    return ordered


@bp.route('/kategorie')
def categories_view():
    is_income = request.args.get('kind') == 'income'
    span = min(max(request.args.get('months', 12, type=int), 3), 36)
    rows = category_monthly(months=span - 1, is_income=is_income)
    months = sorted({r['month'] for r in rows})
    pivot = _pivot(rows, months)
    column_totals = [sum((e['months'].get(m, Decimal('0')) for e in pivot), Decimal('0')) for m in months]

    year = date.today().year
    return render_template(
        'fin/categories.html',
        active_tab='categories',
        is_income=is_income,
        span=span,
        months=months,
        pivot=pivot,
        column_totals=column_totals,
        grand_total=sum(column_totals, Decimal('0')),
        year_rows=category_totals(f'{year}-01-01', f'{year}-12-31', is_income=is_income),
        year=year,
        uncategorized=count_uncategorized(),
        sync=get_sync_state('documents'),
    )


@bp.route('/wynik')
def result_view():
    today = date.today()
    year = min(max(request.args.get('year', today.year, type=int), 2000), today.year + 1)
    months = [f'{year}-{m:02d}' for m in range(1, 13)]

    cost_rows = category_monthly(months=36, is_income=False)
    income_rows = category_monthly(months=36, is_income=True)
    cost_by_month = {m: Decimal('0') for m in months}
    income_by_month = {m: Decimal('0') for m in months}
    for row in cost_rows:
        if row['month'] in cost_by_month:
            cost_by_month[row['month']] += row['net']
    for row in income_rows:
        if row['month'] in income_by_month:
            income_by_month[row['month']] += row['net']

    series, running_income, running_cost = [], Decimal('0'), Decimal('0')
    for month in months:
        income, cost = income_by_month[month], cost_by_month[month]
        running_income += income
        running_cost += cost
        series.append({
            'month': month,
            'income': income,
            'cost': cost,
            'result': income - cost,
            'margin': (income - cost) / income * 100 if income else None,
            'cumulative': running_income - running_cost,
            'is_future': month > today.strftime('%Y-%m'),
        })

    elapsed = len([s for s in series if not s['is_future'] and (s['income'] or s['cost'])])
    return render_template(
        'fin/result.html',
        active_tab='result',
        year=year,
        years=available_years(),
        series=series,
        total_income=running_income,
        total_cost=running_cost,
        total_result=running_income - running_cost,
        total_margin=(running_income - running_cost) / running_income * 100 if running_income else None,
        forecast=(running_income - running_cost) / elapsed * 12 if elapsed else None,
        max_value=max([max(s['income'], s['cost']) for s in series] + [Decimal('1')]),
        uncategorized=count_uncategorized(),
        sync=get_sync_state('documents'),
    )


# ── Podatki ──────────────────────────────────────────────────────────────────

def _tax_period(default_shift: int = 1) -> str:
    """Okres z URL-a albo domyślnie poprzedni miesiąc — ten, który się właśnie płaci."""
    given = request.args.get('period', '').strip()
    if len(given) == 7 and given[4] == '-' and given[:4].isdigit() and given[5:7].isdigit():
        return given
    today = date.today()
    month = today.month - default_shift
    year = today.year
    while month < 1:
        month += 12
        year -= 1
    return f'{year}-{month:02d}'


@bp.route('/podatki')
def taxes_view():
    period = _tax_period()
    year = int(period[:4])
    missing = missing_rates(year)
    if missing:
        flash('Brakuje stawek: ' + ', '.join(RATE_LABELS.get(k, k) for k in missing)
              + '. Uzupełnij je w Ustawieniach — bez nich nie policzę zobowiązań.', 'error')
        return redirect(url_for('fin.settings_view'))

    overview = period_overview(period)
    months = vat_months()
    if period not in months:
        months = sorted(set(months) | {period}, reverse=True)

    return render_template(
        'fin/taxes.html',
        active_tab='taxes',
        period=period,
        periods=months,
        today=date.today(),
        overview=overview,
        rows=obligation_rows(overview),
        history=list_obligations(year=year),
        kind_labels=KIND_LABELS,
        obligation_labels=OBLIGATION_LABELS,
        uncategorized=count_uncategorized(),
        sync=get_sync_state('documents'),
    )


@bp.route('/podatki/zapisz', methods=['POST'])
def save_obligations():
    """Przepisuje symulację okresu do rejestru — dopiero wtedy wchodzi na „Do zapłaty”."""
    period = request.form.get('period', '')[:7]
    try:
        overview = period_overview(period)
    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('fin.taxes_view', period=period))
    for row in obligation_rows(overview):
        upsert_obligation(row['kind'], period, row['calculated'], row['due_date'])
    flash(f'Zobowiązania za {period} zapisane w rejestrze. To nadal symulacja, nie deklaracja.',
          'success')
    return redirect(url_for('fin.taxes_view', period=period))


@bp.route('/podatki/<kind>/<period>/oplacone', methods=['POST'])
def pay_obligation(kind: str, period: str):
    if kind not in OBLIGATION_LABELS:
        flash('Nie znam takiego zobowiązania.', 'error')
        return redirect(url_for('fin.taxes_view'))
    period = period[:7]
    if request.form.get('undo') == '1':
        unmark_obligation_paid(kind, period)
        flash('Zdjąłem oznaczenie zapłaty.', 'success')
        return redirect(request.form.get('back') or url_for('fin.taxes_view', period=period))

    paid_at = request.form.get('paid_at', '').strip() or date.today().isoformat()
    declared = request.form.get('amount', '').replace(' ', '').replace(',', '.')
    try:
        amount = Decimal(declared) if declared else None
    except ArithmeticError:
        flash('Kwota nie wygląda na liczbę — nic nie zapisałem.', 'error')
        return redirect(url_for('fin.taxes_view', period=period))
    mark_obligation_paid(kind, period, paid_at, amount_declared=amount,
                         amount_calculated=amount or 0)
    flash(f'{OBLIGATION_LABELS[kind]} za {period}: zapłacone.', 'success')
    return redirect(request.form.get('back') or url_for('fin.taxes_view', period=period))


@bp.route('/stawki/zapisz', methods=['POST'])
def save_rates():
    """Stawki na rok — jedyne miejsce, gdzie liczby podatkowe w ogóle istnieją."""
    year = request.form.get('year', type=int)
    if not year:
        flash('Podaj rok.', 'error')
        return redirect(url_for('fin.settings_view'))
    saved = 0
    for key in request.form.getlist('rate_key'):
        raw = request.form.get(f'value_{key}', '').replace(' ', '').replace(',', '.')
        if not raw:
            continue
        try:
            value = Decimal(raw)
        except ArithmeticError:
            flash(f'„{RATE_LABELS.get(key, key)}”: {raw} to nie liczba — pominąłem.', 'error')
            continue
        set_rate(year, key, value, note=request.form.get(f'note_{key}', '').strip(),
                 is_confirmed=request.form.get(f'confirmed_{key}') == '1')
        saved += 1
    flash(f'Zapisałem {saved} stawek na {year}.', 'success')
    return redirect(url_for('fin.settings_view', rates_year=year))


# ── Bank ─────────────────────────────────────────────────────────────────────

@bp.route('/bank')
def bank_view():
    """Wyciąg i kolejka dopasowań. Podpowiedzi liczymy na żywo — wyciąg i lustro
    zmieniają się niezależnie, więc zapisany scoring i tak by się zestarzał."""
    status = request.args.get('status', 'pending')
    if status not in ('', 'all', *BANK_STATUS_LABELS):
        status = 'pending'
    filters = {
        'status': '' if status in ('', 'all') else status,
        'bank': request.args.get('bank', ''),
        'month': request.args.get('month', '')[:7],
        'direction': request.args.get('direction', ''),
        'search': request.args.get('q', '').strip(),
    }
    rows = fin_bank_store.list_transactions(**filters, limit=300)
    suggestions = {}
    if status == 'pending':
        # Scoring na 300 wierszach to 300 zapytań — na kolejce do zatwierdzenia
        # ma sens, na całej historii już nie.
        for txn in rows[:60]:
            found = suggest_matches(txn, limit=3)
            if found:
                suggestions[txn['id']] = found
    links = {}
    for txn in rows:
        if txn['link_count']:
            links[txn['id']] = fin_bank_store.links_for_transaction(txn['id'])

    return render_template(
        'fin/bank.html',
        active_tab='bank',
        rows=rows,
        status=status,
        filters=filters,
        suggestions=suggestions,
        links=links,
        counts=fin_bank_store.count_by_status(),
        banks=fin_bank_store.banks(),
        bank_labels=BANK_LABELS,
        status_labels=BANK_STATUS_LABELS,
        uncategorized=count_uncategorized(),
        sync=get_sync_state('documents'),
    )


@bp.route('/bank/import', methods=['POST'])
def bank_import():
    upload = request.files.get('file')
    if not upload or not upload.filename:
        flash('Nie wybrałeś pliku.', 'error')
        return redirect(url_for('fin.bank_view'))
    try:
        result = import_csv(upload.read(), bank=request.form.get('bank', ''))
    except BankImportError as e:
        flash(str(e), 'error')
    except Exception as e:                                  # noqa: BLE001
        flash(f'Nie udało się wczytać wyciągu: {e}', 'error')
    else:
        flash(f"Wyciąg {result['bank_label']} ({result['date_from']} – {result['date_to']}): "
              f"{result['parsed']} operacji, {result['new']} nowych, "
              f"{result['updated'] + result['unchanged']} już znanych.", 'success')
    return redirect(url_for('fin.bank_view'))


@bp.route('/bank/<int:txn_id>/powiaz', methods=['POST'])
def bank_link(txn_id: int):
    fakturownia_id = request.form.get('fakturownia_id', '')
    if not fakturownia_id.isdigit():
        flash('Brak dokumentu do powiązania.', 'error')
        return redirect(request.form.get('back') or url_for('fin.bank_view'))
    amount = (request.form.get('amount') or '').replace(',', '.').strip()
    push = request.form.get('push') != '0'
    try:
        result = link_payment(txn_id, int(fakturownia_id), amount=amount or None,
                              push=push, actor=f'user:{session.get("user_id", "?")}')
    except (BankImportError, FinWriteError) as e:
        flash(str(e), 'error')
    else:
        message = f"Powiązano {result['amount_applied']} zł."
        if result['pushed']:
            doc = result['document']
            message += (f" W Fakturowni: {doc['number']} → {doc['paid_amount']} zł "
                        f"({STATUS_LABELS.get(doc['status'], doc['status'])}).")
        else:
            message += ' Zapłaty w Fakturowni nie dopisywałem.'
        flash(message, 'success')
    return redirect(request.form.get('back') or url_for('fin.bank_view'))


@bp.route('/bank/<int:txn_id>/odwiaz', methods=['POST'])
def bank_unlink(txn_id: int):
    fakturownia_id = request.form.get('fakturownia_id', '')
    if fakturownia_id.isdigit():
        unlink_payment(txn_id, int(fakturownia_id))
        flash('Powiązanie usunięte. Zapłaty w Fakturowni nie cofam — zrób to świadomie, '
              'jeśli trzeba.', 'success')
    return redirect(request.form.get('back') or url_for('fin.bank_view'))


@bp.route('/bank/<int:txn_id>/pomin', methods=['POST'])
def bank_ignore(txn_id: int):
    ignored = request.form.get('undo') != '1'
    fin_bank_store.set_ignored(txn_id, ignored)
    get_db().commit()
    flash('Operacja pominięta — nie będzie już w kolejce.' if ignored
          else 'Operacja wróciła do kolejki.', 'success')
    return redirect(request.form.get('back') or url_for('fin.bank_view'))


@bp.route('/bank/<int:txn_id>/dopasowania')
def bank_matches(txn_id: int):
    """Podpowiedzi dla jednej operacji — dla wiersza rozwijanego na liście."""
    txn = fin_bank_store.get_transaction(txn_id)
    if not txn:
        return jsonify({'ok': False, 'error': 'Nie znam tej operacji.'}), 404
    matches = suggest_matches(txn, limit=8, min_score=0)
    return jsonify({'ok': True, 'matches': [
        {'fakturownia_id': m['fakturownia_id'], 'number': m['number'],
         'counterparty_name': m['counterparty_name'], 'score': m['score'],
         'gross_pln': str(m['gross_pln']), 'amount_left': str(m['amount_left']),
         'status': m['status'], 'reasons': m['reasons'],
         'payment_to': m['payment_to'].isoformat() if m['payment_to'] else None}
        for m in matches]})

# ── Ustawienia modułu ────────────────────────────────────────────────────────

def _rate_form_rows(year: int) -> list[dict]:
    """Wiersze formularza stawek: wszystkie znane klucze, także te jeszcze nieuzupełnione."""
    saved = {r['key']: r for r in list_rates(year)}
    keys = list(RATE_LABELS) + [k for k in saved if k not in RATE_LABELS]
    return [dict(saved.get(key) or {'key': key, 'value': None, 'note': '', 'is_confirmed': 1},
                 label=RATE_LABELS.get(key, key)) for key in keys]


@bp.route('/ustawienia')
def settings_view():
    rates_year = request.args.get('rates_year', type=int) or date.today().year
    return render_template(
        'fin/settings.html',
        active_tab='settings',
        rates_year=rates_year,
        rates=_rate_form_rows(rates_year),
        rate_labels=RATE_LABELS,
        rate_years=sorted(set(rate_years()) | {date.today().year, date.today().year + 1},
                          reverse=True),
        categories=list_categories(include_archived=True),
        rules=list_rules(),
        match_fields=MATCH_FIELDS,
        match_types=MATCH_TYPES,
        field_labels=FIELD_LABELS,
        type_labels=TYPE_LABELS,
        uncategorized=count_uncategorized(),
        sync=get_sync_state('documents'),
    )


@bp.route('/reguly/dodaj', methods=['POST'])
def add_rule():
    try:
        create_rule(
            request.form.get('match_field', ''),
            request.form.get('match_type', ''),
            request.form.get('match_value', '').strip(),
            int(request.form.get('category_id', 0)),
            priority=request.form.get('priority', 100, type=int),
        )
    except (ValueError, re.error) as e:
        flash(f'Nie zapisałem reguły: {e}', 'error')
    else:
        flash('Reguła dodana. Uruchom „Zastosuj reguły”, żeby objęła stare dokumenty.', 'success')
    return redirect(url_for('fin.settings_view'))


@bp.route('/reguly/<int:rule_id>/usun', methods=['POST'])
def remove_rule(rule_id: int):
    delete_rule(rule_id)
    flash('Reguła usunięta. Przypisania, które zdążyła zrobić, zostają.', 'success')
    return redirect(url_for('fin.settings_view'))


@bp.route('/reguly/<int:rule_id>/przelacz', methods=['POST'])
def switch_rule(rule_id: int):
    toggle_rule(rule_id, request.form.get('active') == '1')
    return redirect(url_for('fin.settings_view'))


@bp.route('/reguly/zastosuj', methods=['POST'])
def run_rules():
    recategorize = request.form.get('recategorize') == '1'
    result = apply_rules(recategorize_rule_assigned=recategorize)
    flash(f"Sprawdzono {result['checked']} dokumentów, kategorię dostało {result['assigned']}.",
          'success')
    return redirect(request.form.get('back') or url_for('fin.settings_view'))


@bp.route('/kategorie/dodaj', methods=['POST'])
def add_category():
    name = request.form.get('name', '').strip()
    slug = request.form.get('slug', '').strip() or _slugify(name)
    if not name:
        flash('Kategoria potrzebuje nazwy.', 'error')
    elif get_category_by_slug(slug):
        flash(f'Kategoria o identyfikatorze „{slug}” już istnieje.', 'error')
    else:
        create_category(
            request.form.get('kind', 'cost'), name, slug,
            vat=request.form.get('vat', 100, type=int),
            kup=request.form.get('kup', 100, type=int),
            is_fixed_cost=request.form.get('is_fixed_cost') == '1',
            sort_order=request.form.get('sort_order', 500, type=int))
        flash('Kategoria dodana.', 'success')
    return redirect(url_for('fin.settings_view'))


@bp.route('/kategorie/<int:category_id>/zapisz', methods=['POST'])
def save_category(category_id: int):
    update_category(
        category_id,
        name=request.form.get('name', '').strip(),
        default_vat_deduction=request.form.get('vat', 100, type=int),
        default_tax_deductible=request.form.get('kup', 100, type=int),
        is_fixed_cost=1 if request.form.get('is_fixed_cost') == '1' else 0,
        sort_order=request.form.get('sort_order', 500, type=int))
    flash('Kategoria zapisana. Dokumenty już przypisane zachowują swoje procenty.', 'success')
    return redirect(url_for('fin.settings_view'))


def _slugify(text: str) -> str:
    """Nazwa kategorii → identyfikator: bez ogonków, małe litery, myślniki."""
    ascii_text = unicodedata.normalize('NFKD', text.replace('ł', 'l').replace('Ł', 'L'))
    ascii_text = ascii_text.encode('ascii', 'ignore').decode()
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', ascii_text.lower())).strip('-')[:128]
