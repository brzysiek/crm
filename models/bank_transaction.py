from database import get_db


def get_pending_bank_transactions(bank: str = None,
                                  txn_type: str = None) -> list[dict]:
    db = get_db()
    sql = "SELECT * FROM bank_transactions WHERE status='pending'"
    params = []
    if bank in ('mbank', 'unicredit'):
        sql += " AND bank = %s"
        params.append(bank)
    if txn_type == 'expense':
        sql += " AND amount < 0"
    elif txn_type == 'income':
        sql += " AND amount > 0"
    sql += " ORDER BY date DESC, id DESC"
    with db.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def get_pending_bank_count() -> int:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS cnt FROM bank_transactions WHERE status='pending'"
        )
        return cur.fetchone()['cnt']


def get_bank_transaction_by_id(txn_id: int) -> dict | None:
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM bank_transactions WHERE id = %s", (txn_id,))
        return cur.fetchone()


def upsert_bank_transaction(data: dict) -> bool:
    """Wstawia nową transakcję; jeśli transaction_id istnieje — pomija. Zwraca True jeśli nowa."""
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "SELECT id FROM bank_transactions WHERE transaction_id = %s",
                (data['transaction_id'],)
            )
            if cur.fetchone():
                return False
            cur.execute(
                """INSERT INTO bank_transactions
                   (bank, transaction_id, date, description, counterparty,
                    amount, currency, category, balance, raw_data, status)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'pending')""",
                (
                    data['bank'], data['transaction_id'], data['date'],
                    data.get('description'), data.get('counterparty'),
                    data['amount'], data.get('currency', 'PLN'),
                    data.get('category', ''), data.get('balance'),
                    data.get('raw_data'),
                )
            )
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise


def reject_bank_transaction(txn_id: int) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "UPDATE bank_transactions SET status='rejected' WHERE id = %s",
                (txn_id,)
            )
        db.commit()
    except Exception:
        db.rollback()
        raise


def search_bank_transactions(q: str = None, bank: str = None,
                              min_amount: float = None, max_amount: float = None,
                              for_expense_id: int = None,
                              for_income_id: int = None) -> list[dict]:
    db = get_db()
    sql = "SELECT * FROM bank_transactions WHERE status != 'rejected'"
    params = []
    if bank in ('mbank', 'unicredit'):
        sql += " AND bank = %s"
        params.append(bank)
    if q:
        sql += " AND (description LIKE %s OR counterparty LIKE %s)"
        like = f"%{q}%"
        params.extend([like, like])
    if min_amount is not None:
        sql += " AND ABS(amount) >= %s"
        params.append(min_amount)
    if max_amount is not None:
        sql += " AND ABS(amount) <= %s"
        params.append(max_amount)
    sql += " ORDER BY date DESC, id DESC LIMIT 100"
    with db.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

    linked_ids = set()
    if for_expense_id:
        with db.cursor() as cur:
            cur.execute(
                "SELECT bank_txn_id FROM expense_transactions WHERE expense_id = %s",
                (for_expense_id,)
            )
            linked_ids = {r['bank_txn_id'] for r in cur.fetchall()}
    elif for_income_id:
        with db.cursor() as cur:
            cur.execute(
                "SELECT bank_txn_id FROM income_transactions WHERE income_id = %s",
                (for_income_id,)
            )
            linked_ids = {r['bank_txn_id'] for r in cur.fetchall()}

    for row in rows:
        row['linked_to_this'] = row['id'] in linked_ids

    return rows


def bulk_reject_bank(ids: list[int]) -> int:
    if not ids:
        return 0
    db = get_db()
    placeholders = ','.join(['%s'] * len(ids))
    try:
        with db.cursor() as cur:
            cur.execute(
                f"UPDATE bank_transactions SET status='rejected' "
                f"WHERE id IN ({placeholders}) AND status='pending'",
                ids,
            )
            affected = cur.rowcount
        db.commit()
        return affected
    except Exception:
        db.rollback()
        raise
