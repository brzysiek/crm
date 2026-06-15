import json as _json

from database import get_db


def _fix_counterparty(row: dict) -> dict:
    """Nadpisuje vendor_name/vendor_nip danymi z raw_json.
    Fakturownia dla kosztowych: buyer_* = dostawca (wystawiający), seller_* = my.
    Dla przychodowych: buyer_* = klient (odbiorca), seller_* = my.
    W obu przypadkach kontrahent to buyer_*.
    """
    try:
        raw = _json.loads(row['raw_json']) if row.get('raw_json') else {}
        name = raw.get('buyer_name') or raw.get('seller_name') or ''
        nip  = raw.get('buyer_tax_no') or raw.get('seller_tax_no') or ''
        if name:
            row['vendor_name'] = name
        if nip:
            row['vendor_nip'] = nip
    except Exception:
        pass
    return row


def get_pending_invoices(invoice_type: str = None) -> list[dict]:
    db = get_db()
    sql = "SELECT * FROM fakturownia_invoices WHERE status = 'pending'"
    params = []
    if invoice_type in ('income', 'expense'):
        sql += " AND invoice_type = %s"
        params.append(invoice_type)
    sql += " ORDER BY issue_date DESC"
    with db.cursor() as cur:
        cur.execute(sql, params)
        return [_fix_counterparty(row) for row in cur.fetchall()]


def get_pending_count() -> int:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS cnt FROM fakturownia_invoices WHERE status = 'pending'"
        )
        return cur.fetchone()['cnt']


def get_invoice_by_id(invoice_id: int) -> dict | None:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT * FROM fakturownia_invoices WHERE id = %s", (invoice_id,)
        )
        return cur.fetchone()


def upsert_invoice(data: dict) -> bool:
    """INSERT nowej faktury lub UPDATE danych kontrahenta jeśli już istnieje.
    Zwraca True jeśli nowa (status=pending ustawiony po raz pierwszy)."""
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "SELECT id, status FROM fakturownia_invoices WHERE fakturownia_id = %s",
                (data['fakturownia_id'],)
            )
            existing = cur.fetchone()
            if existing:
                cur.execute(
                    """UPDATE fakturownia_invoices
                       SET vendor_name=%s, vendor_nip=%s, invoice_type=%s,
                           amount_gross=%s, amount_net=%s, vat_amount=%s,
                           payment_to=%s, raw_json=%s,
                           currency=%s, orig_amount=%s, exchange_rate=%s
                       WHERE fakturownia_id=%s""",
                    (
                        data.get('vendor_name'), data.get('vendor_nip'),
                        data.get('invoice_type', 'expense'),
                        data.get('amount_gross'), data.get('amount_net'),
                        data.get('vat_amount'),
                        data.get('payment_to') or None,
                        data.get('raw_json'),
                        data.get('currency', 'PLN'),
                        data.get('orig_amount') or None,
                        data.get('exchange_rate') or None,
                        data['fakturownia_id'],
                    )
                )
                db.commit()
                return False
            cur.execute(
                """INSERT INTO fakturownia_invoices
                   (fakturownia_id, invoice_number, vendor_name, vendor_nip,
                    issue_date, payment_to, amount_gross, amount_net, vat_amount,
                    ksef_number, invoice_type, currency, orig_amount, exchange_rate,
                    raw_json, status)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'pending')""",
                (
                    data['fakturownia_id'], data['invoice_number'],
                    data.get('vendor_name'), data.get('vendor_nip'),
                    data.get('issue_date'),
                    data.get('payment_to') or None,
                    data.get('amount_gross'),
                    data.get('amount_net'), data.get('vat_amount'),
                    data.get('ksef_number'),
                    data.get('invoice_type', 'expense'),
                    data.get('currency', 'PLN'),
                    data.get('orig_amount') or None,
                    data.get('exchange_rate') or None,
                    data.get('raw_json'),
                )
            )
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise


def assign_invoice(invoice_id: int, expense_id: int) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "UPDATE fakturownia_invoices SET status='assigned', assigned_expense_id=%s "
                "WHERE id = %s",
                (expense_id, invoice_id)
            )
        db.commit()
    except Exception:
        db.rollback()
        raise


def reject_invoice(invoice_id: int) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "UPDATE fakturownia_invoices SET status='rejected' WHERE id = %s",
                (invoice_id,)
            )
        db.commit()
    except Exception:
        db.rollback()
        raise


def get_invoices_by_ids(ids: list[int]) -> list[dict]:
    if not ids:
        return []
    db = get_db()
    placeholders = ','.join(['%s'] * len(ids))
    with db.cursor() as cur:
        cur.execute(
            f"SELECT * FROM fakturownia_invoices WHERE id IN ({placeholders})", ids
        )
        return cur.fetchall()


def bulk_reject(ids: list[int]) -> int:
    if not ids:
        return 0
    db = get_db()
    try:
        placeholders = ','.join(['%s'] * len(ids))
        with db.cursor() as cur:
            cur.execute(
                f"UPDATE fakturownia_invoices SET status='rejected' "
                f"WHERE id IN ({placeholders}) AND status='pending'",
                ids,
            )
            affected = cur.rowcount
        db.commit()
        return affected
    except Exception:
        db.rollback()
        raise


def get_sync_log(limit: int = 10) -> list[dict]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT * FROM sync_log ORDER BY synced_at DESC LIMIT %s", (limit,)
        )
        return cur.fetchall()


def add_sync_log(fetched: int, new: int, pending: int,
                 status: str, message: str = None) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                """INSERT INTO sync_log
                   (invoices_fetched, invoices_new, invoices_pending, status, message)
                   VALUES (%s,%s,%s,%s,%s)""",
                (fetched, new, pending, status, message)
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
