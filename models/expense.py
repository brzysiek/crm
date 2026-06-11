from database import get_db


def get_all_expenses(month: str = None, category: str = None,
                     invoice_status: str = None, payment_filter: str = None,
                     search: str = None) -> list[dict]:
    db = get_db()
    sql = "SELECT * FROM expenses WHERE 1=1"
    params = []

    if month:
        sql += " AND DATE_FORMAT(date, '%%Y-%%m') = %s"
        params.append(month)
    if category:
        sql += " AND category = %s"
        params.append(category)
    if invoice_status:
        sql += " AND invoice_status = %s"
        params.append(invoice_status)
    if payment_filter == 'full':
        sql += " AND payment_percent = 100"
    elif payment_filter == 'partial':
        sql += " AND payment_percent > 0 AND payment_percent < 100"
    elif payment_filter == 'none':
        sql += " AND payment_percent = 0"
    if search:
        sql += " AND (description LIKE %s OR responsible_person LIKE %s)"
        like = f"%{search}%"
        params.extend([like, like])

    sql += " ORDER BY date DESC, id DESC"
    with db.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def get_expense_by_id(expense_id: int) -> dict | None:
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM expenses WHERE id = %s", (expense_id,))
        return cur.fetchone()


def get_categories() -> list[str]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT DISTINCT category FROM expenses "
            "WHERE category IS NOT NULL AND category != '' ORDER BY category"
        )
        return [r['category'] for r in cur.fetchall()]


def create_expense(data: dict) -> int:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                """INSERT INTO expenses
                   (date, responsible_person, contractor_name, contractor_nip,
                    invoice_number, description, amount_gross, vat_rate,
                    amount_net, payment_percent, invoice_status, invoice_ref,
                    paid_by, payment_method, is_recurring, category, notes)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    data['date'], data['responsible_person'],
                    data.get('contractor_name') or None,
                    data.get('contractor_nip') or None,
                    data.get('invoice_number') or None,
                    data['description'],
                    data['amount_gross'], data['vat_rate'], data['amount_net'],
                    data.get('payment_percent', 0),
                    data.get('invoice_status', 'none'),
                    data.get('invoice_ref') or None,
                    data.get('paid_by') or None,
                    data.get('payment_method') or None,
                    1 if data.get('is_recurring') else 0,
                    data.get('category') or None,
                    data.get('notes') or None,
                )
            )
        db.commit()
        return cur.lastrowid
    except Exception:
        db.rollback()
        raise


def update_expense(expense_id: int, data: dict) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                """UPDATE expenses SET
                   date=%s, responsible_person=%s,
                   contractor_name=%s, contractor_nip=%s, invoice_number=%s,
                   description=%s, amount_gross=%s, vat_rate=%s, amount_net=%s,
                   payment_percent=%s, invoice_status=%s, invoice_ref=%s,
                   paid_by=%s, payment_method=%s, is_recurring=%s,
                   category=%s, notes=%s
                   WHERE id = %s""",
                (
                    data['date'], data['responsible_person'],
                    data.get('contractor_name') or None,
                    data.get('contractor_nip') or None,
                    data.get('invoice_number') or None,
                    data['description'],
                    data['amount_gross'], data['vat_rate'], data['amount_net'],
                    data.get('payment_percent', 0),
                    data.get('invoice_status', 'none'),
                    data.get('invoice_ref') or None,
                    data.get('paid_by') or None,
                    data.get('payment_method') or None,
                    1 if data.get('is_recurring') else 0,
                    data.get('category') or None,
                    data.get('notes') or None,
                    expense_id,
                )
            )
        db.commit()
    except Exception:
        db.rollback()
        raise


def delete_expense(expense_id: int) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("DELETE FROM expenses WHERE id = %s", (expense_id,))
        db.commit()
    except Exception:
        db.rollback()
        raise


def get_monthly_kpi(month: str) -> dict:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT
               COALESCE(SUM(amount_gross), 0)                              AS total_gross,
               COALESCE(SUM(CASE WHEN payment_percent=100 THEN amount_gross ELSE 0 END), 0) AS paid,
               COALESCE(SUM(CASE WHEN payment_percent<100  THEN amount_gross ELSE 0 END), 0) AS pending
               FROM expenses WHERE DATE_FORMAT(date, '%%Y-%%m') = %s""",
            (month,)
        )
        return cur.fetchone()


def get_expense_transactions(expense_id: int) -> list[dict]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT bt.*, et.id AS link_id
               FROM expense_transactions et
               JOIN bank_transactions bt ON et.bank_txn_id = bt.id
               WHERE et.expense_id = %s
               ORDER BY bt.date DESC, bt.id DESC""",
            (expense_id,)
        )
        return cur.fetchall()


def _recalc_payment_percent(cur, expense_id: int) -> int:
    cur.execute(
        """SELECT COALESCE(SUM(ABS(bt.amount)), 0) AS total
           FROM expense_transactions et
           JOIN bank_transactions bt ON et.bank_txn_id = bt.id
           WHERE et.expense_id = %s""",
        (expense_id,)
    )
    total = float(cur.fetchone()['total'])
    cur.execute("SELECT amount_gross FROM expenses WHERE id = %s", (expense_id,))
    row = cur.fetchone()
    gross = float(row['amount_gross']) if row else 0
    pct = min(100, round(total / gross * 100)) if gross else 0
    cur.execute("UPDATE expenses SET payment_percent = %s WHERE id = %s", (pct, expense_id))
    return pct


def link_transaction(expense_id: int, bank_txn_id: int) -> dict:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "SELECT id FROM expense_transactions WHERE expense_id=%s AND bank_txn_id=%s",
                (expense_id, bank_txn_id)
            )
            if cur.fetchone():
                return {'status': 'already_linked'}
            cur.execute(
                "INSERT INTO expense_transactions (expense_id, bank_txn_id) VALUES (%s, %s)",
                (expense_id, bank_txn_id)
            )
            cur.execute(
                "UPDATE bank_transactions SET status='accepted' WHERE id=%s AND status='pending'",
                (bank_txn_id,)
            )
            pct = _recalc_payment_percent(cur, expense_id)
        db.commit()
        return {'status': 'ok', 'payment_percent': pct}
    except Exception:
        db.rollback()
        raise


def unlink_transaction(expense_id: int, bank_txn_id: int) -> dict:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "DELETE FROM expense_transactions WHERE expense_id=%s AND bank_txn_id=%s",
                (expense_id, bank_txn_id)
            )
            # Wróć do pending tylko jeśli transakcja nie jest już przypięta do innego wydatku
            cur.execute(
                "SELECT COUNT(*) AS cnt FROM expense_transactions WHERE bank_txn_id=%s",
                (bank_txn_id,)
            )
            if cur.fetchone()['cnt'] == 0:
                cur.execute(
                    "UPDATE bank_transactions SET status='pending' WHERE id=%s AND status='accepted'",
                    (bank_txn_id,)
                )
            pct = _recalc_payment_percent(cur, expense_id)
        db.commit()
        return {'status': 'ok', 'payment_percent': pct}
    except Exception:
        db.rollback()
        raise


def get_daily_totals(month: str) -> list[dict]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT DAY(date) AS day, SUM(amount_gross) AS total
               FROM expenses WHERE DATE_FORMAT(date, '%%Y-%%m') = %s
               GROUP BY DAY(date) ORDER BY day""",
            (month,)
        )
        return cur.fetchall()
