from database import get_db


def _default_accounting_month(data: dict) -> str:
    """Miesiąc księgowy domyślnie zgodny z miesiącem pola `date`, jeśli nie podano jawnie."""
    given = (data.get('accounting_month') or '').strip()
    if given:
        return given[:7]
    d = data.get('date')
    if hasattr(d, 'strftime'):
        return d.strftime('%Y-%m')
    return str(d or '')[:7]


def get_all_expenses(month: str = None, category: str = None,
                     invoice_status: str = None, payment_filter: str = None,
                     search: str = None) -> list[dict]:
    db = get_db()
    sql = "SELECT * FROM expenses WHERE 1=1"
    params = []

    if month:
        sql += " AND accounting_month = %s"
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
                   (date, accounting_month, payment_due_date, responsible_person, contractor_name, contractor_nip,
                    invoice_number, description, amount_gross, vat_rate,
                    amount_net, orig_amount, orig_currency,
                    payment_percent, invoice_status, invoice_ref,
                    paid_by, payment_method, is_recurring, category, notes, source)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    data['date'],
                    _default_accounting_month(data),
                    data.get('payment_due_date') or None,
                    data['responsible_person'],
                    data.get('contractor_name') or None,
                    data.get('contractor_nip') or None,
                    data.get('invoice_number') or None,
                    data['description'],
                    data['amount_gross'], data['vat_rate'], data['amount_net'],
                    data.get('orig_amount') or None,
                    data.get('orig_currency') or None,
                    data.get('payment_percent', 0),
                    data.get('invoice_status', 'none'),
                    data.get('invoice_ref') or None,
                    data.get('paid_by') or None,
                    data.get('payment_method') or None,
                    1 if data.get('is_recurring') else 0,
                    data.get('category') or None,
                    data.get('notes') or None,
                    data.get('source') or None,
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
                   date=%s, accounting_month=%s, payment_due_date=%s, responsible_person=%s,
                   contractor_name=%s, contractor_nip=%s, invoice_number=%s,
                   description=%s, amount_gross=%s, vat_rate=%s, amount_net=%s,
                   orig_amount=%s, orig_currency=%s,
                   payment_percent=%s, invoice_status=%s, invoice_ref=%s,
                   paid_by=%s, payment_method=%s, is_recurring=%s,
                   category=%s, notes=%s, source=%s
                   WHERE id = %s""",
                (
                    data['date'],
                    _default_accounting_month(data),
                    data.get('payment_due_date') or None,
                    data['responsible_person'],
                    data.get('contractor_name') or None,
                    data.get('contractor_nip') or None,
                    data.get('invoice_number') or None,
                    data['description'],
                    data['amount_gross'], data['vat_rate'], data['amount_net'],
                    data.get('orig_amount') or None,
                    data.get('orig_currency') or None,
                    data.get('payment_percent', 0),
                    data.get('invoice_status', 'none'),
                    data.get('invoice_ref') or None,
                    data.get('paid_by') or None,
                    data.get('payment_method') or None,
                    1 if data.get('is_recurring') else 0,
                    data.get('category') or None,
                    data.get('notes') or None,
                    data.get('source') or None,
                    expense_id,
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
                f"UPDATE expenses SET category=%s WHERE id IN ({placeholders})",
                [category or None] + ids,
            )
            affected = cur.rowcount
        db.commit()
        return affected
    except Exception:
        db.rollback()
        raise


def bulk_set_description(ids: list[int], description: str) -> int:
    if not ids:
        return 0
    db = get_db()
    placeholders = ','.join(['%s'] * len(ids))
    try:
        with db.cursor() as cur:
            cur.execute(
                f"UPDATE expenses SET description=%s WHERE id IN ({placeholders})",
                [description] + ids,
            )
            affected = cur.rowcount
        db.commit()
        return affected
    except Exception:
        db.rollback()
        raise


def bulk_set_responsible_person(ids: list[int], person: str | None) -> int:
    if not ids:
        return 0
    db = get_db()
    placeholders = ','.join(['%s'] * len(ids))
    try:
        with db.cursor() as cur:
            cur.execute(
                f"UPDATE expenses SET responsible_person=%s WHERE id IN ({placeholders})",
                [person or None] + ids,
            )
            affected = cur.rowcount
        db.commit()
        return affected
    except Exception:
        db.rollback()
        raise


def bulk_set_payment_percent(ids: list[int], pct: int) -> int:
    """Ręcznie nadpisuje procent opłacenia (100=opłacone, 50=częściowo, 0=nieopłacone).

    Wartość zostanie ponownie przeliczona automatycznie, jeśli później zostanie
    dopięta/odpięta transakcja bankowa (patrz _recalc_payment_percent).
    """
    if not ids:
        return 0
    db = get_db()
    placeholders = ','.join(['%s'] * len(ids))
    try:
        with db.cursor() as cur:
            cur.execute(
                f"UPDATE expenses SET payment_percent=%s WHERE id IN ({placeholders})",
                [pct] + ids,
            )
            affected = cur.rowcount
        db.commit()
        return affected
    except Exception:
        db.rollback()
        raise


def _revert_expense_links(cur, expense_id: int) -> None:
    """Odpina transakcje bankowe i faktury powiązane z wydatkiem, przywracając
    je do stanu oczekującego (pending), zanim wydatek zostanie usunięty."""
    cur.execute(
        "SELECT bank_txn_id FROM expense_transactions WHERE expense_id=%s",
        (expense_id,)
    )
    txn_ids = [r['bank_txn_id'] for r in cur.fetchall()]
    cur.execute("DELETE FROM expense_transactions WHERE expense_id=%s", (expense_id,))
    for txn_id in txn_ids:
        cur.execute(
            "SELECT (SELECT COUNT(*) FROM expense_transactions WHERE bank_txn_id=%s) "
            "+ (SELECT COUNT(*) FROM income_transactions WHERE bank_txn_id=%s) AS cnt",
            (txn_id, txn_id)
        )
        if cur.fetchone()['cnt'] == 0:
            cur.execute(
                "UPDATE bank_transactions SET status='pending' WHERE id=%s AND status='accepted'",
                (txn_id,)
            )
    cur.execute(
        "UPDATE fakturownia_invoices SET status='pending', assigned_expense_id=NULL "
        "WHERE assigned_expense_id=%s AND status='assigned' AND invoice_type='expense'",
        (expense_id,)
    )
    cur.execute(
        "UPDATE gdrive_invoices SET status='pending', assigned_record_id=NULL "
        "WHERE assigned_record_id=%s AND status='assigned' AND invoice_type='expense'",
        (expense_id,)
    )


def delete_expense(expense_id: int) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            _revert_expense_links(cur, expense_id)
            cur.execute("DELETE FROM expenses WHERE id = %s", (expense_id,))
        db.commit()
    except Exception:
        db.rollback()
        raise


def bulk_delete_expenses(ids: list[int]) -> int:
    if not ids:
        return 0
    db = get_db()
    affected = 0
    try:
        with db.cursor() as cur:
            for expense_id in ids:
                _revert_expense_links(cur, expense_id)
                cur.execute("DELETE FROM expenses WHERE id=%s", (expense_id,))
                affected += cur.rowcount
        db.commit()
        return affected
    except Exception:
        db.rollback()
        raise


def get_monthly_kpi(month: str, exclude_categories: list[str] = None) -> dict:
    db = get_db()
    sql = """SELECT
               COALESCE(SUM(amount_gross), 0) AS total_gross,
               COALESCE(SUM(amount_net), 0) AS total_net,
               COALESCE(SUM(amount_gross - amount_net), 0) AS total_vat,
               COALESCE(SUM(CASE WHEN payment_percent = 100 THEN amount_gross ELSE 0 END), 0) AS paid,
               COALESCE(SUM(CASE WHEN payment_percent = 0   THEN amount_gross ELSE 0 END), 0) AS unpaid,
               COALESCE(SUM(CASE WHEN payment_percent > 0
                                  AND payment_percent < 100 THEN amount_gross ELSE 0 END), 0) AS partial
               FROM expenses WHERE accounting_month = %s"""
    params = [month]
    if exclude_categories:
        placeholders = ','.join(['%s'] * len(exclude_categories))
        sql += f" AND (category IS NULL OR category NOT IN ({placeholders}))"
        params.extend(exclude_categories)
    with db.cursor() as cur:
        cur.execute(sql, params)
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


def get_daily_totals(month: str, exclude_categories: list[str] = None) -> list[dict]:
    db = get_db()
    sql = """SELECT DAY(date) AS day, SUM(amount_gross) AS total
               FROM expenses WHERE accounting_month = %s"""
    params = [month]
    if exclude_categories:
        placeholders = ','.join(['%s'] * len(exclude_categories))
        sql += f" AND (category IS NULL OR category NOT IN ({placeholders}))"
        params.extend(exclude_categories)
    sql += " GROUP BY DAY(date) ORDER BY day"
    with db.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def get_unpaid_expenses(limit: int = 20) -> list[dict]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT id, date, contractor_name, invoice_number,
                      description, amount_gross, payment_percent
               FROM expenses
               WHERE payment_percent < 100
               ORDER BY date ASC, id DESC
               LIMIT %s""",
            (limit,)
        )
        return cur.fetchall()
