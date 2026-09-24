"""Dokumenty finansowe — lustro faktur z Fakturowni.

Tabela `fin_documents` jest tylko kopią: niczego tu nie tworzymy ręcznie,
wszystko przychodzi z synchronizacji (services/fin_sync.py).
"""
from database import get_db

# Dokumenty, które nie są zdarzeniem finansowym — nie wchodzą do sum ani do
# zestawienia „do zapłaty”, ale zostają widoczne na liście z flagą.
NON_FINANCIAL_KINDS = ('proforma', 'estimate', 'client_order', 'correction_note',
                       'accounting_note', 'kp', 'kw', 'inbox', 'dw')

FINANCIAL_CLAUSE = "d.kind NOT IN %s"

KIND_LABELS = {
    'vat': 'Faktura VAT', 'correction': 'Korekta', 'proforma': 'Proforma', 'bill': 'Rachunek',
    'receipt': 'Paragon', 'advance': 'Zaliczkowa', 'final': 'Końcowa', 'vat_mp': 'VAT MP',
    'vat_margin': 'VAT marża', 'wdt': 'WDT', 'wnt': 'WNT', 'export_products': 'Eksport towarów',
    'import_products': 'Import towarów', 'import_service': 'Import usług',
    'import_service_eu': 'Import usług UE', 'estimate': 'Wycena', 'client_order': 'Zamówienie',
    'correction_note': 'Nota korygująca', 'accounting_note': 'Nota księgowa', 'kp': 'KP', 'kw': 'KW',
    'invoice_other': 'Inny dokument', 'dw': 'Dokument wewnętrzny', 'inbox': 'Bez numeru',
}

# `received` i `not_approved` są w danych, choć nie ma ich w dokumentacji API —
# stąd pełne pokrycie tego, co faktycznie przychodzi z konta.
STATUS_LABELS = {
    'issued': 'Wystawiona', 'sent': 'Wysłana', 'paid': 'Opłacona',
    'partial': 'Częściowo opłacona', 'rejected': 'Odrzucona',
    'received': 'Otrzymana', 'not_approved': 'Niezatwierdzona',
}

GOV_STATUS_LABELS = {
    'ok': 'W KSeF', 'demo_ok': 'KSeF (demo)', 'processing': 'Wysyłanie…',
    'demo_processing': 'Wysyłanie… (demo)', 'send_error': 'Błąd wysyłki',
    'server_error': 'Błąd serwera KSeF', 'status_check_error': 'Błąd sprawdzenia statusu',
    'offline': 'Tryb offline', 'offline_error': 'Błąd trybu offline',
    'duplicate_error': 'Duplikat w KSeF', 'blocked_403_error': 'Odmowa (403)',
    'not_applicable': 'Poza KSeF', 'not_connected': 'KSeF niepodłączony',
}

DOC_SORTS = {
    'issue_date': 'd.issue_date',
    'payment_to': 'd.payment_to',
    'gross': 'd.gross_pln',
    'counterparty': 'd.counterparty_name',
    'number': 'd.number',
}

UPSERT_FIELDS = (
    'fakturownia_id', 'department_id', 'kind', 'is_income', 'number', 'issue_date', 'sell_date',
    'delivery_date', 'payment_to', 'paid_date', 'status', 'currency', 'exchange_rate',
    'price_net', 'price_tax', 'price_gross', 'paid_amount', 'net_pln', 'tax_pln', 'gross_pln',
    'counterparty_name', 'counterparty_tax_no', 'accounting_kind', 'fakturownia_category_id',
    'gov_id', 'gov_status', 'gov_send_date', 'description', 'oid', 'raw_json',
    'fakturownia_updated_at',
)


def upsert_document(data: dict) -> str:
    """Wstawia albo aktualizuje dokument. Zwraca 'new' | 'updated' | 'unchanged'."""
    db = get_db()
    values = tuple(data.get(f) for f in UPSERT_FIELDS)
    marks = ', '.join(['%s'] * len(UPSERT_FIELDS))
    columns = ', '.join(f'`{f}`' for f in UPSERT_FIELDS)
    updates = ', '.join(f'`{f}` = VALUES(`{f}`)' for f in UPSERT_FIELDS if f != 'fakturownia_id')
    with db.cursor() as cur:
        cur.execute(f"INSERT INTO fin_documents ({columns}) VALUES ({marks}) "
                    f"ON DUPLICATE KEY UPDATE {updates}", values)
        # pymysql: 1 = wstawiono, 2 = zaktualizowano, 0 = nic się nie zmieniło
        affected = cur.rowcount
    return {1: 'new', 2: 'updated'}.get(affected, 'unchanged')


def _filters_sql(filters: dict) -> tuple[str, list]:
    """Buduje WHERE z białej listy — nic z URL-a nie trafia do SQL-a wprost."""
    where = ["1=1"]
    params: list = []

    kind = filters.get('kind')
    if kind == 'cost':
        where.append("d.is_income = 0")
    elif kind == 'income':
        where.append("d.is_income = 1")

    if filters.get('financial_only'):
        where.append(FINANCIAL_CLAUSE)
        params.append(NON_FINANCIAL_KINDS)

    payment = filters.get('payment')
    if payment == 'paid':
        where.append("d.status = 'paid'")
    elif payment == 'unpaid':
        where.append("d.status <> 'paid'")
    elif payment == 'overdue':
        where.append("d.status <> 'paid' AND d.payment_to IS NOT NULL AND d.payment_to < CURDATE()")

    if filters.get('month'):
        where.append("DATE_FORMAT(d.issue_date, '%%Y-%%m') = %s")
        params.append(filters['month'])
    if filters.get('year'):
        where.append("YEAR(d.issue_date) = %s")
        params.append(filters['year'])

    if filters.get('category_id'):
        where.append("m.category_id = %s")
        params.append(filters['category_id'])
    elif filters.get('uncategorized'):
        where.append("m.category_id IS NULL")

    ksef = filters.get('ksef')
    if ksef == 'with':
        where.append("d.gov_id <> ''")
    elif ksef == 'without':
        where.append("d.gov_id = ''")

    if filters.get('department_id'):
        where.append("d.department_id = %s")
        params.append(filters['department_id'])

    if filters.get('search'):
        like = f"%{filters['search']}%"
        where.append("(d.number LIKE %s OR d.counterparty_name LIKE %s"
                     " OR d.counterparty_tax_no LIKE %s OR d.description LIKE %s OR d.gov_id LIKE %s)")
        params.extend([like] * 5)

    return ' AND '.join(where), params


def _order_by(sort: str, direction: str) -> str:
    column = DOC_SORTS.get(sort, DOC_SORTS['issue_date'])
    dir_sql = 'ASC' if str(direction).lower() == 'asc' else 'DESC'
    return f" ORDER BY {column} {dir_sql}, d.id DESC"


def list_documents(filters: dict = None, sort: str = 'issue_date', direction: str = 'desc',
                   limit: int = 100, offset: int = 0) -> list[dict]:
    where, params = _filters_sql(filters or {})
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            f"""SELECT d.*, m.category_id, m.vat_deduction_percent, m.tax_deductible_percent,
                       m.source AS category_source, c.name AS category_name, c.slug AS category_slug
                FROM fin_documents d
                LEFT JOIN fin_document_meta m ON m.fakturownia_id = d.fakturownia_id
                LEFT JOIN fin_categories c ON c.id = m.category_id
                WHERE {where}{_order_by(sort, direction)}
                LIMIT %s OFFSET %s""",
            tuple(params) + (int(limit), int(offset)))
        return [dict(r) for r in cur.fetchall()]


def count_documents(filters: dict = None) -> int:
    where, params = _filters_sql(filters or {})
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            f"""SELECT COUNT(*) AS n FROM fin_documents d
                LEFT JOIN fin_document_meta m ON m.fakturownia_id = d.fakturownia_id
                WHERE {where}""", tuple(params))
        return cur.fetchone()['n']


def get_document(fakturownia_id: int) -> dict | None:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT d.*, m.category_id, m.vat_deduction_percent, m.tax_deductible_percent,
                      m.note AS meta_note, m.source AS category_source, c.name AS category_name
               FROM fin_documents d
               LEFT JOIN fin_document_meta m ON m.fakturownia_id = d.fakturownia_id
               LEFT JOIN fin_categories c ON c.id = m.category_id
               WHERE d.fakturownia_id = %s""", (fakturownia_id,))
        row = cur.fetchone()
    return dict(row) if row else None


def open_items(is_income: bool, limit: int = 200) -> list[dict]:
    """Nieopłacone dokumenty z kubełkiem terminu — rdzeń ekranu „Do zapłaty”."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            f"""SELECT d.*, c.name AS category_name,
                       DATEDIFF(d.payment_to, CURDATE()) AS days_left,
                       (d.gross_pln - d.paid_amount) AS amount_left,
                       CASE
                           WHEN d.payment_to IS NULL THEN 'no_date'
                           WHEN d.payment_to < CURDATE() THEN 'overdue'
                           WHEN d.payment_to <= DATE_ADD(CURDATE(), INTERVAL 7 DAY) THEN 'week'
                           WHEN d.payment_to <= DATE_ADD(CURDATE(), INTERVAL 30 DAY) THEN 'month'
                           ELSE 'later'
                       END AS bucket
                FROM fin_documents d
                LEFT JOIN fin_document_meta m ON m.fakturownia_id = d.fakturownia_id
                LEFT JOIN fin_categories c ON c.id = m.category_id
                WHERE d.is_income = %s AND d.status <> 'paid' AND {FINANCIAL_CLAUSE}
                ORDER BY d.payment_to IS NULL, d.payment_to ASC
                LIMIT %s""",
            (1 if is_income else 0, NON_FINANCIAL_KINDS, int(limit)))
        return [dict(r) for r in cur.fetchall()]


def period_totals(date_from: str, date_to: str) -> dict:
    """Sumy netto/VAT/brutto w oknie dat, osobno koszty i przychody."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            f"""SELECT d.is_income,
                       COUNT(*) AS documents,
                       COALESCE(SUM(d.net_pln), 0)   AS net,
                       COALESCE(SUM(d.tax_pln), 0)   AS tax,
                       COALESCE(SUM(d.gross_pln), 0) AS gross,
                       COALESCE(SUM(CASE WHEN d.status <> 'paid' THEN d.gross_pln - d.paid_amount END), 0) AS open_amount
                FROM fin_documents d
                WHERE d.issue_date BETWEEN %s AND %s AND {FINANCIAL_CLAUSE}
                GROUP BY d.is_income""",
            (date_from, date_to, NON_FINANCIAL_KINDS))
        rows = {int(r['is_income']): dict(r) for r in cur.fetchall()}
    empty = {'documents': 0, 'net': 0, 'tax': 0, 'gross': 0, 'open_amount': 0}
    return {'cost': rows.get(0, dict(empty)), 'income': rows.get(1, dict(empty))}


def monthly_totals(months: int = 12) -> list[dict]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            f"""SELECT DATE_FORMAT(d.issue_date, '%%Y-%%m') AS month, d.is_income,
                       COALESCE(SUM(d.net_pln), 0) AS net, COALESCE(SUM(d.tax_pln), 0) AS tax
                FROM fin_documents d
                WHERE d.issue_date >= DATE_SUB(DATE_FORMAT(CURDATE(), '%%Y-%%m-01'), INTERVAL %s MONTH)
                  AND {FINANCIAL_CLAUSE}
                GROUP BY month, d.is_income
                ORDER BY month""",
            (int(months), NON_FINANCIAL_KINDS))
        return [dict(r) for r in cur.fetchall()]


def count_uncategorized() -> int:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            f"""SELECT COUNT(*) AS n FROM fin_documents d
                LEFT JOIN fin_document_meta m ON m.fakturownia_id = d.fakturownia_id
                WHERE m.category_id IS NULL AND {FINANCIAL_CLAUSE}""", (NON_FINANCIAL_KINDS,))
        return cur.fetchone()['n']


def available_months() -> list[str]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute("""SELECT DISTINCT DATE_FORMAT(issue_date, '%Y-%m') AS month
                       FROM fin_documents WHERE issue_date IS NOT NULL
                       ORDER BY month DESC LIMIT 36""")
        return [r['month'] for r in cur.fetchall()]


def departments() -> list[int]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT DISTINCT department_id FROM fin_documents WHERE department_id IS NOT NULL")
        return [r['department_id'] for r in cur.fetchall()]
