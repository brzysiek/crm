"""Moduł Finanse v2 — dashboard nad danymi z Fakturowni.

Widok, nie rejestr: dokumentów się tu nie tworzy ani nie edytuje. Źródłem prawdy
jest Fakturownia, CRM trzyma lustro (`fin_documents`) i własne metadane.
"""
import calendar
import json
from datetime import date

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from models.fin_document import (GOV_STATUS_LABELS, KIND_LABELS, NON_FINANCIAL_KINDS,
                                 STATUS_LABELS, available_months, count_documents,
                                 count_uncategorized, departments, get_document, list_documents,
                                 open_items, period_totals)
from models.settings import get_setting
from services.fakturownia_api import FakturowniaError
from services.fin_sync import get_sync_state, sync_documents

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
        positions=_positions(row.get('raw_json')),
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
