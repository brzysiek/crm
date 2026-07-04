from database import get_db


def get_all_incomes(month: str = None, category: str = None,
                    payment_status: str = None, search: str = None) -> list[dict]:
    db = get_db()
    sql = "SELECT * FROM incomes WHERE 1=1"
    params = []

    if month:
        sql += " AND DATE_FORMAT(date, '%%Y-%%m') = %s"
        params.append(month)
    if category:
        sql += " AND category = %s"
        params.append(category)
    if payment_status:
        sql += " AND payment_status = %s"
        params.append(payment_status)
    if search:
        sql += " AND (description LIKE %s OR client_name LIKE %s OR invoice_number LIKE %s)"
        like = f"%{search}%"
        params.extend([like, like, like])

    sql += " ORDER BY date DESC, id DESC"
    with db.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def get_income_by_id(income_id: int) -> dict | None:
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM incomes WHERE id = %s", (income_id,))
        return cur.fetchone()


def get_income_categories() -> list[str]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT DISTINCT category FROM incomes "
            "WHERE category IS NOT NULL AND category != '' ORDER BY category"
        )
        return [r['category'] for r in cur.fetchall()]


def create_income(data: dict) -> int:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                """INSERT INTO incomes
                   (date, payment_due_date, client_name, client_nip, description, invoice_number,
                    amount_gross, vat_rate, amount_net, orig_amount, orig_currency,
                    invoice_status, invoice_ref, payment_method, payment_status,
                    category, fakturownia_id, notes, paid_by, source)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    data['date'],
                    data.get('payment_due_date') or None,
                    data.get('client_name') or None,
                    data.get('client_nip') or None,
                    data['description'],
                    data.get('invoice_number') or None,
                    data['amount_gross'],
                    data['vat_rate'],
                    data['amount_net'],
                    data.get('orig_amount') or None,
                    data.get('orig_currency') or None,
                    data.get('invoice_status', 'none'),
                    data.get('invoice_ref') or None,
                    data.get('payment_method') or None,
                    data.get('payment_status', 'unpaid'),
                    data.get('category') or None,
                    data.get('fakturownia_id') or None,
                    data.get('notes') or None,
                    data.get('paid_by') or None,
                    data.get('source') or None,
                )
            )
        db.commit()
        return cur.lastrowid
    except Exception:
        db.rollback()
        raise


def update_income(income_id: int, data: dict) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                """UPDATE incomes SET
                   date=%s, payment_due_date=%s, client_name=%s, client_nip=%s, description=%s,
                   invoice_number=%s, amount_gross=%s, vat_rate=%s, amount_net=%s,
                   orig_amount=%s, orig_currency=%s,
                   invoice_status=%s, invoice_ref=%s, payment_method=%s,
                   payment_status=%s, category=%s, notes=%s, paid_by=%s, source=%s
                   WHERE id = %s""",
                (
                    data['date'],
                    data.get('payment_due_date') or None,
                    data.get('client_name') or None,
                    data.get('client_nip') or None,
                    data['description'],
                    data.get('invoice_number') or None,
                    data['amount_gross'],
                    data['vat_rate'],
                    data['amount_net'],
                    data.get('orig_amount') or None,
                    data.get('orig_currency') or None,
                    data.get('invoice_status', 'none'),
                    data.get('invoice_ref') or None,
                    data.get('payment_method') or None,
                    data.get('payment_status', 'unpaid'),
                    data.get('category') or None,
                    data.get('notes') or None,
                    data.get('paid_by') or None,
                    data.get('source') or None,
                    income_id,
                )
            )
        db.commit()
    except Exception:
        db.rollback()
        raise


def bulk_set_category(ids: list[int], category: str | None) -> int:
    if not ids:
        return 0
    db = get_db()
    placeholders = ','.join(['%s'] * len(ids))
    try:
        with db.cursor() as cur:
            cur.execute(
                f"UPDATE incomes SET category=%s WHERE id IN ({placeholders})",
                [category or None] + ids,
            )
            affected = cur.rowcount
        db.commit()
        return affected
    except Exception:
        db.rollback()
        raise


def bulk_set_paid_by(ids: list[int], person: str | None) -> int:
    if not ids:
        return 0
    db = get_db()
    placeholders = ','.join(['%s'] * len(ids))
    try:
        with db.cursor() as cur:
            cur.execute(
                f"UPDATE incomes SET paid_by=%s WHERE id IN ({placeholders})",
                [person or None] + ids,
            )
            affected = cur.rowcount
        db.commit()
        return affected
    except Exception:
        db.rollback()
        raise


def delete_income(income_id: int) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("DELETE FROM incomes WHERE id = %s", (income_id,))
        db.commit()
    except Exception:
        db.rollback()
        raise


def get_income_transactions(income_id: int) -> list[dict]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT bt.*, it.id AS link_id
               FROM income_transactions it
               JOIN bank_transactions bt ON it.bank_txn_id = bt.id
               WHERE it.income_id = %s
               ORDER BY bt.date DESC, bt.id DESC""",
            (income_id,)
        )
        return cur.fetchall()


def link_income_transaction(income_id: int, bank_txn_id: int) -> dict:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "SELECT id FROM income_transactions WHERE income_id=%s AND bank_txn_id=%s",
                (income_id, bank_txn_id)
            )
            if cur.fetchone():
                return {'status': 'already_linked'}
            cur.execute(
                "INSERT INTO income_transactions (income_id, bank_txn_id) VALUES (%s, %s)",
                (income_id, bank_txn_id)
            )
            cur.execute(
                "UPDATE bank_transactions SET status='accepted' WHERE id=%s AND status='pending'",
                (bank_txn_id,)
            )
        db.commit()
        return {'status': 'ok'}
    except Exception:
        db.rollback()
        raise


def unlink_income_transaction(income_id: int, bank_txn_id: int) -> dict:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "DELETE FROM income_transactions WHERE income_id=%s AND bank_txn_id=%s",
                (income_id, bank_txn_id)
            )
            # Wróć do pending tylko gdy nie przypięta nigdzie indziej
            cur.execute(
                "SELECT COUNT(*) AS cnt FROM income_transactions WHERE bank_txn_id=%s",
                (bank_txn_id,)
            )
            if cur.fetchone()['cnt'] == 0:
                cur.execute(
                    "SELECT COUNT(*) AS cnt FROM expense_transactions WHERE bank_txn_id=%s",
                    (bank_txn_id,)
                )
                if cur.fetchone()['cnt'] == 0:
                    cur.execute(
                        "UPDATE bank_transactions SET status='pending' WHERE id=%s AND status='accepted'",
                        (bank_txn_id,)
                    )
        db.commit()
        return {'status': 'ok'}
    except Exception:
        db.rollback()
        raise


def get_unpaid_incomes(limit: int = 20) -> list[dict]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT id, date, client_name, invoice_number,
                      description, amount_gross, payment_status
               FROM incomes
               WHERE payment_status != 'paid'
               ORDER BY date ASC, id DESC
               LIMIT %s""",
            (limit,)
        )
        return cur.fetchall()


def get_income_daily_totals(month: str) -> list[dict]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT DAY(date) AS day, SUM(amount_gross) AS total
               FROM incomes WHERE DATE_FORMAT(date, '%%Y-%%m') = %s
               GROUP BY DAY(date) ORDER BY day""",
            (month,)
        )
        return cur.fetchall()


def get_monthly_income_kpi(month: str) -> dict:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT
               COALESCE(SUM(amount_gross), 0) AS total_gross,
               COALESCE(SUM(CASE WHEN payment_status='paid'    THEN amount_gross ELSE 0 END), 0) AS paid,
               COALESCE(SUM(CASE WHEN payment_status='unpaid'  THEN amount_gross ELSE 0 END), 0) AS unpaid,
               COALESCE(SUM(CASE WHEN payment_status='partial' THEN amount_gross ELSE 0 END), 0) AS partial
               FROM incomes WHERE DATE_FORMAT(date, '%%Y-%%m') = %s""",
            (month,)
        )
        return cur.fetchone()
