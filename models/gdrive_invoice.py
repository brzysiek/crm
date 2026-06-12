"""DB operations for gdrive_invoices table."""
import json as _json

from database import get_db


def get_pending_gdrive_invoices(invoice_type: str = None) -> list[dict]:
    db = get_db()
    sql = "SELECT * FROM gdrive_invoices WHERE status = 'pending'"
    params = []
    if invoice_type in ('income', 'expense'):
        sql += " AND invoice_type = %s"
        params.append(invoice_type)
    sql += " ORDER BY gdrive_year DESC, gdrive_month DESC, issue_date DESC"
    with db.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def get_gdrive_invoice_by_id(inv_id: int) -> dict | None:
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM gdrive_invoices WHERE id = %s", (inv_id,))
        return cur.fetchone()


def upsert_gdrive_invoice(data: dict) -> bool:
    """INSERT or UPDATE a gdrive invoice record.

    Returns True if a new record was created (status set to 'pending').
    """
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "SELECT id, status FROM gdrive_invoices WHERE gdrive_file_id = %s",
                (data['gdrive_file_id'],)
            )
            existing = cur.fetchone()

            if existing:
                cur.execute(
                    """UPDATE gdrive_invoices
                       SET file_name=%s, file_modified_at=%s,
                           gdrive_year=%s, gdrive_month=%s,
                           invoice_number=%s, vendor_name=%s, vendor_nip=%s,
                           issue_date=%s, amount_gross=%s, amount_net=%s,
                           vat_amount=%s, invoice_type=%s, ocr_raw=%s
                       WHERE gdrive_file_id=%s""",
                    (
                        data.get('file_name'),
                        data.get('file_modified_at'),
                        data.get('gdrive_year'),
                        data.get('gdrive_month'),
                        data.get('invoice_number'),
                        data.get('vendor_name'),
                        data.get('vendor_nip'),
                        data.get('issue_date') or None,
                        data.get('amount_gross'),
                        data.get('amount_net'),
                        data.get('vat_amount'),
                        data.get('invoice_type', 'expense'),
                        data.get('ocr_raw'),
                        data['gdrive_file_id'],
                    )
                )
                db.commit()
                return False

            cur.execute(
                """INSERT INTO gdrive_invoices
                   (gdrive_file_id, file_name, file_modified_at,
                    gdrive_year, gdrive_month,
                    invoice_number, vendor_name, vendor_nip,
                    issue_date, amount_gross, amount_net, vat_amount,
                    invoice_type, ocr_raw, status)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'pending')""",
                (
                    data['gdrive_file_id'],
                    data.get('file_name', ''),
                    data.get('file_modified_at'),
                    data.get('gdrive_year'),
                    data.get('gdrive_month'),
                    data.get('invoice_number'),
                    data.get('vendor_name'),
                    data.get('vendor_nip'),
                    data.get('issue_date') or None,
                    data.get('amount_gross'),
                    data.get('amount_net'),
                    data.get('vat_amount'),
                    data.get('invoice_type', 'expense'),
                    data.get('ocr_raw'),
                )
            )
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise


def get_gdrive_pending_count() -> int:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS cnt FROM gdrive_invoices WHERE status = 'pending'"
        )
        return cur.fetchone()['cnt']


def reject_gdrive_invoice(inv_id: int) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "UPDATE gdrive_invoices SET status='rejected' WHERE id = %s",
                (inv_id,)
            )
        db.commit()
    except Exception:
        db.rollback()
        raise


def bulk_reject_gdrive(ids: list[int]) -> int:
    if not ids:
        return 0
    db = get_db()
    try:
        placeholders = ','.join(['%s'] * len(ids))
        with db.cursor() as cur:
            cur.execute(
                f"UPDATE gdrive_invoices SET status='rejected' "
                f"WHERE id IN ({placeholders}) AND status='pending'",
                ids,
            )
            affected = cur.rowcount
        db.commit()
        return affected
    except Exception:
        db.rollback()
        raise


def assign_gdrive_invoice(inv_id: int, record_id: int) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "UPDATE gdrive_invoices SET status='assigned', assigned_record_id=%s "
                "WHERE id = %s",
                (record_id, inv_id)
            )
        db.commit()
    except Exception:
        db.rollback()
        raise


def get_gdrive_invoices_by_ids(ids: list[int]) -> list[dict]:
    if not ids:
        return []
    db = get_db()
    placeholders = ','.join(['%s'] * len(ids))
    with db.cursor() as cur:
        cur.execute(
            f"SELECT * FROM gdrive_invoices WHERE id IN ({placeholders})", ids
        )
        return cur.fetchall()


def get_processed_file_ids() -> set[str]:
    """Return gdrive_file_id values for records that are not rejected (pending or assigned)."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT gdrive_file_id FROM gdrive_invoices WHERE status != 'rejected'"
        )
        return {row['gdrive_file_id'] for row in cur.fetchall()}
