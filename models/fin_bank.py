"""Transakcje bankowe z importu CSV i ich powiązania z dokumentami.

`fin_bank_transactions` to wyciąg: jedna operacja = jeden wiersz, klucz
`external_id` (id z banku albo stabilny hash), więc ten sam plik wgrany dwa razy
nie zrobi duplikatów. `fin_payment_links` łączy operację z dokumentem M:N —
jeden przelew może opłacić kilka faktur, a jedna faktura może być opłacona
w ratach z kilku przelewów. Dlatego kwota siedzi na powiązaniu
(`amount_applied`), a nie na żadnej z tych dwóch stron.

Stan operacji (`status`) liczymy z powiązań, nigdy nie ustawiamy go ręcznie —
poza `ignored`, które jest świadomą decyzją człowieka („to nie zapłata faktury”).
"""
from decimal import Decimal

from database import get_db

TXN_FIELDS = ('external_id', 'bank', 'booked_date', 'amount', 'currency',
              'counterparty_name', 'counterparty_account', 'title', 'raw_data')

STATUS_LABELS = {
    'pending': 'Niedopasowana',
    'partial': 'Częściowo dopasowana',
    'matched': 'Dopasowana',
    'ignored': 'Pominięta',
}

TXN_SORTS = {'booked_date': 'booked_date', 'amount': 'amount', 'bank': 'bank'}


def upsert_transaction(row: dict) -> str:
    """Wstawia operację albo odświeża jej dane. Zwraca 'new' | 'updated' | 'unchanged'.

    Świadomie nie ruszamy `matched_amount` ani `status` — powtórny import tego
    samego wyciągu nie może zdmuchnąć wykonanej wcześniej pracy dopasowania.
    """
    values = tuple(row.get(f) for f in TXN_FIELDS)
    columns = ', '.join(f'`{f}`' for f in TXN_FIELDS)
    marks = ', '.join(['%s'] * len(TXN_FIELDS))
    updates = ', '.join(f'`{f}` = VALUES(`{f}`)' for f in TXN_FIELDS if f != 'external_id')
    with get_db().cursor() as cur:
        cur.execute(f"INSERT INTO fin_bank_transactions ({columns}) VALUES ({marks}) "
                    f"ON DUPLICATE KEY UPDATE {updates}", values)
        return {1: 'new', 2: 'updated'}.get(cur.rowcount, 'unchanged')


def get_transaction(txn_id: int) -> dict | None:
    with get_db().cursor() as cur:
        cur.execute("SELECT * FROM fin_bank_transactions WHERE id = %s", (int(txn_id),))
        row = cur.fetchone()
    return dict(row) if row else None


def list_transactions(status: str = '', bank: str = '', search: str = '',
                      month: str = '', direction: str = '',
                      sort: str = 'booked_date', limit: int = 200) -> list[dict]:
    where, params = ['1=1'], []
    if status:
        where.append('t.status = %s')
        params.append(status)
    if bank:
        where.append('t.bank = %s')
        params.append(bank)
    if month:
        where.append("DATE_FORMAT(t.booked_date, '%%Y-%%m') = %s")
        params.append(month)
    if direction == 'out':
        where.append('t.amount < 0')
    elif direction == 'in':
        where.append('t.amount > 0')
    if search:
        where.append('(t.title LIKE %s OR t.counterparty_name LIKE %s)')
        params += [f'%{search}%'] * 2
    order = TXN_SORTS.get(sort, 'booked_date')
    with get_db().cursor() as cur:
        cur.execute(f"""SELECT t.*, COUNT(l.id) AS link_count
                        FROM fin_bank_transactions t
                        LEFT JOIN fin_payment_links l ON l.transaction_id = t.id
                        WHERE {' AND '.join(where)}
                        GROUP BY t.id
                        ORDER BY t.{order} DESC, t.id DESC LIMIT %s""",
                    tuple(params) + (max(1, min(int(limit), 500)),))
        return [dict(r) for r in cur.fetchall()]


def count_by_status() -> dict:
    with get_db().cursor() as cur:
        cur.execute("SELECT status, COUNT(*) n FROM fin_bank_transactions GROUP BY status")
        return {r['status']: r['n'] for r in cur.fetchall()}


def banks() -> list[str]:
    with get_db().cursor() as cur:
        cur.execute("SELECT DISTINCT bank FROM fin_bank_transactions ORDER BY bank")
        return [r['bank'] for r in cur.fetchall()]


# ── powiązania ───────────────────────────────────────────────────────────────

def links_for_transaction(txn_id: int) -> list[dict]:
    with get_db().cursor() as cur:
        cur.execute("""SELECT l.*, d.number, d.counterparty_name, d.is_income, d.gross_pln,
                              d.paid_amount, d.status AS doc_status, d.payment_to
                       FROM fin_payment_links l
                       LEFT JOIN fin_documents d ON d.fakturownia_id = l.fakturownia_id
                       WHERE l.transaction_id = %s ORDER BY l.id""", (int(txn_id),))
        return [dict(r) for r in cur.fetchall()]


def links_for_document(fakturownia_id: int) -> list[dict]:
    with get_db().cursor() as cur:
        cur.execute("""SELECT l.*, t.booked_date, t.amount, t.bank, t.title, t.counterparty_name
                       FROM fin_payment_links l
                       JOIN fin_bank_transactions t ON t.id = l.transaction_id
                       WHERE l.fakturownia_id = %s ORDER BY t.booked_date""",
                    (int(fakturownia_id),))
        return [dict(r) for r in cur.fetchall()]


def applied_to_document(fakturownia_id: int) -> Decimal:
    with get_db().cursor() as cur:
        cur.execute("""SELECT COALESCE(SUM(amount_applied), 0) s FROM fin_payment_links
                       WHERE fakturownia_id = %s""", (int(fakturownia_id),))
        return Decimal(str(cur.fetchone()['s']))


def add_link(txn_id: int, fakturownia_id: int, amount: Decimal, created_by: str = '') -> int:
    with get_db().cursor() as cur:
        cur.execute("""INSERT INTO fin_payment_links
                           (transaction_id, fakturownia_id, amount_applied, created_by)
                       VALUES (%s, %s, %s, %s)
                       ON DUPLICATE KEY UPDATE amount_applied = VALUES(amount_applied),
                                               created_by = VALUES(created_by)""",
                    (int(txn_id), int(fakturownia_id), amount, (created_by or '')[:64]))
        link_id = cur.lastrowid
    # Stanu nie przeliczamy tutaj: robi to wołający w swojej transakcji, żeby
    # powiązanie i wynikający z niego status commitowały się razem.
    return link_id


def remove_link(txn_id: int, fakturownia_id: int) -> int:
    with get_db().cursor() as cur:
        cur.execute("""DELETE FROM fin_payment_links
                       WHERE transaction_id = %s AND fakturownia_id = %s""",
                    (int(txn_id), int(fakturownia_id)))
        removed = cur.rowcount
    return removed


def refresh_status(txn_id: int) -> str:
    """Przelicza `matched_amount` i `status` z powiązań. `ignored` zostaje —
    to decyzja człowieka, nie wynik arytmetyki."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute("""SELECT t.amount, t.status,
                              COALESCE(SUM(l.amount_applied), 0) AS applied
                       FROM fin_bank_transactions t
                       LEFT JOIN fin_payment_links l ON l.transaction_id = t.id
                       WHERE t.id = %s GROUP BY t.id""", (int(txn_id),))
        row = cur.fetchone()
        if not row:
            return ''
        applied = Decimal(str(row['applied']))
        total = abs(Decimal(str(row['amount'])))
        if row['status'] == 'ignored':
            status = 'ignored'
        elif applied <= 0:
            status = 'pending'
        elif applied + Decimal('0.02') >= total:
            status = 'matched'
        else:
            status = 'partial'
        cur.execute("UPDATE fin_bank_transactions SET matched_amount = %s, status = %s WHERE id = %s",
                    (applied, status, int(txn_id)))
    return status


def set_ignored(txn_id: int, ignored: bool = True) -> str:
    with get_db().cursor() as cur:
        cur.execute("UPDATE fin_bank_transactions SET status = %s WHERE id = %s",
                    ('ignored' if ignored else 'pending', int(txn_id)))
    return refresh_status(txn_id)
