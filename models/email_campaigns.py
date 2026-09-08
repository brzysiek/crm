import base64
import secrets

from database import get_db


def get_all_campaigns() -> list[dict]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT c.*,
                      (SELECT COUNT(*) FROM email_campaign_recipients r WHERE r.campaign_id=c.id) AS recipient_count,
                      (SELECT COUNT(*) FROM email_campaign_recipients r WHERE r.campaign_id=c.id AND r.status='sent') AS sent_count,
                      (SELECT COUNT(*) FROM email_campaign_recipients r WHERE r.campaign_id=c.id AND r.status='failed') AS failed_count
               FROM email_campaigns c ORDER BY c.created_at DESC"""
        )
        return cur.fetchall()


def get_campaign_by_id(campaign_id: int) -> dict | None:
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM email_campaigns WHERE id=%s", (campaign_id,))
        return cur.fetchone()


def get_campaign_tag_ids(campaign_id: int) -> list[int]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT tag_id FROM email_campaign_tags WHERE campaign_id=%s", (campaign_id,))
        return [r['tag_id'] for r in cur.fetchall()]


def get_campaign_tag_names(campaign_id: int) -> list[str]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT t.name FROM crm_tags t
               JOIN email_campaign_tags ect ON ect.tag_id = t.id
               WHERE ect.campaign_id=%s ORDER BY t.name""",
            (campaign_id,)
        )
        return [r['name'] for r in cur.fetchall()]


def get_campaign_recipients(campaign_id: int) -> list[dict]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT r.*, c.first_name, c.last_name
               FROM email_campaign_recipients r
               LEFT JOIN crm_contacts c ON c.id = r.contact_id
               WHERE r.campaign_id=%s ORDER BY r.id""",
            (campaign_id,)
        )
        return cur.fetchall()


def create_campaign(name: str, subject: str, body_html: str, tag_ids: list[int], created_by: int | None) -> int:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "INSERT INTO email_campaigns (name, subject, body_html, created_by) VALUES (%s,%s,%s,%s)",
                (name, subject, body_html, created_by)
            )
            campaign_id = cur.lastrowid
            for tag_id in tag_ids:
                cur.execute(
                    "INSERT IGNORE INTO email_campaign_tags (campaign_id, tag_id) VALUES (%s, %s)",
                    (campaign_id, tag_id)
                )
        db.commit()
        return campaign_id
    except Exception:
        db.rollback()
        raise


def add_campaign_attachment(campaign_id: int, filename: str, mime_type: str, data: bytes) -> int:
    db = get_db()
    encoded = base64.b64encode(data).decode('ascii')
    try:
        with db.cursor() as cur:
            cur.execute(
                """INSERT INTO email_campaign_attachments
                   (campaign_id, filename, mime_type, size_bytes, data_base64)
                   VALUES (%s,%s,%s,%s,%s)""",
                (campaign_id, filename, mime_type, len(data), encoded)
            )
            attachment_id = cur.lastrowid
        db.commit()
        return attachment_id
    except Exception:
        db.rollback()
        raise


def get_campaign_attachments(campaign_id: int) -> list[dict]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT id, campaign_id, filename, mime_type, size_bytes, data_base64
               FROM email_campaign_attachments WHERE campaign_id=%s ORDER BY id""",
            (campaign_id,)
        )
        rows = cur.fetchall()
    for row in rows:
        row['data'] = base64.b64decode(row.pop('data_base64'))
    return rows


def resolve_recipient_contacts(tag_ids: list[int]) -> list[dict]:
    """Kontakty pasujące do dowolnego z tagów (ANY), z aktywną zgodą marketingową,
    nie zarchiwizowane, z adresem email, nieobecne na globalnej liście wypisań."""
    if not tag_ids:
        return []
    db = get_db()
    placeholders = ','.join(['%s'] * len(tag_ids))
    with db.cursor() as cur:
        cur.execute(
            f"""SELECT DISTINCT c.id, c.email FROM crm_contacts c
                JOIN crm_contact_tags ct ON ct.contact_id = c.id
                WHERE ct.tag_id IN ({placeholders})
                  AND c.archived_at IS NULL
                  AND c.email IS NOT NULL AND c.email != ''
                  AND c.marketing_consent_at IS NOT NULL
                  AND c.email NOT IN (SELECT email FROM email_unsubscribes)""",
            tag_ids
        )
        return cur.fetchall()


def freeze_recipients(campaign_id: int) -> int:
    """Zamraża listę odbiorców w momencie wysyłki (statyczna grupa) i przełącza
    kampanię w tryb 'sending'. Zwraca liczbę zamrożonych odbiorców."""
    tag_ids = get_campaign_tag_ids(campaign_id)
    contacts = resolve_recipient_contacts(tag_ids)
    db = get_db()
    try:
        with db.cursor() as cur:
            for contact in contacts:
                cur.execute(
                    """INSERT INTO email_campaign_recipients
                       (campaign_id, contact_id, email, unsubscribe_token)
                       VALUES (%s,%s,%s,%s)""",
                    (campaign_id, contact['id'], contact['email'], secrets.token_urlsafe(32))
                )
            cur.execute("UPDATE email_campaigns SET status='sending' WHERE id=%s", (campaign_id,))
        db.commit()
        return len(contacts)
    except Exception:
        db.rollback()
        raise


def get_pending_batch(limit: int) -> list[dict]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT r.* FROM email_campaign_recipients r
               JOIN email_campaigns c ON c.id = r.campaign_id
               WHERE r.status='pending' AND c.status='sending'
               ORDER BY r.id LIMIT %s""",
            (limit,)
        )
        return cur.fetchall()


def is_unsubscribed(email: str) -> bool:
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT 1 FROM email_unsubscribes WHERE email=%s", (email,))
        return cur.fetchone() is not None


def mark_sent(recipient_id: int, gmail_message_id: str) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "UPDATE email_campaign_recipients SET status='sent', gmail_message_id=%s, sent_at=NOW() WHERE id=%s",
                (gmail_message_id, recipient_id)
            )
        db.commit()
    except Exception:
        db.rollback()
        raise


def mark_failed(recipient_id: int, error_message: str) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "UPDATE email_campaign_recipients SET status='failed', error_message=%s WHERE id=%s",
                (error_message[:2000], recipient_id)
            )
        db.commit()
    except Exception:
        db.rollback()
        raise


def mark_skipped_unsubscribed(recipient_id: int) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "UPDATE email_campaign_recipients SET status='skipped_unsubscribed' WHERE id=%s",
                (recipient_id,)
            )
        db.commit()
    except Exception:
        db.rollback()
        raise


def count_sent_today() -> int:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS n FROM email_campaign_recipients WHERE status='sent' AND DATE(sent_at) = CURDATE()"
        )
        return cur.fetchone()['n']


def add_unsubscribe(email: str, campaign_id: int | None) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "INSERT IGNORE INTO email_unsubscribes (email, campaign_id) VALUES (%s, %s)",
                (email, campaign_id)
            )
        db.commit()
    except Exception:
        db.rollback()
        raise


def get_recipient_by_token(token: str) -> dict | None:
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM email_campaign_recipients WHERE unsubscribe_token=%s", (token,))
        return cur.fetchone()


def maybe_complete_campaign(campaign_id: int) -> None:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS n FROM email_campaign_recipients WHERE campaign_id=%s AND status='pending'",
            (campaign_id,)
        )
        pending = cur.fetchone()['n']
    if pending == 0:
        try:
            with db.cursor() as cur:
                cur.execute(
                    "UPDATE email_campaigns SET status='sent', sent_at=NOW() WHERE id=%s AND status='sending'",
                    (campaign_id,)
                )
            db.commit()
        except Exception:
            db.rollback()
            raise
