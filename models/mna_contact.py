from database import get_db
from models.crm_notes import log_history, build_diff_summary
from models.mna_tags import set_contact_tags
from services.text_utils import format_phone

FIELD_LABELS = {
    'first_name': 'Imię', 'last_name': 'Nazwisko', 'position': 'Stanowisko',
    'email': 'Email', 'phone': 'Telefon', 'linkedin_url': 'LinkedIn', 'description': 'Opis',
    'company_id': 'Firma',
}


def get_all_mna_contacts(sort: str = 'last_name', direction: str = 'asc',
                          search: str = None, company_id: int = None) -> list[dict]:
    allowed_sort = {'first_name', 'last_name', 'position', 'email', 'phone', 'created_at'}
    if sort not in allowed_sort:
        sort = 'last_name'
    direction = 'DESC' if str(direction).lower() == 'desc' else 'ASC'
    where = ["ct.archived_at IS NULL"]
    params = []
    if search:
        where.append("(ct.first_name LIKE %s OR ct.last_name LIKE %s OR ct.email LIKE %s)")
        like = f"%{search}%"
        params.extend([like, like, like])
    if company_id:
        where.append("ct.company_id = %s")
        params.append(company_id)
    db = get_db()
    sql = f"""SELECT ct.*, co.name AS company_name, co.short_name AS company_short_name,
        (SELECT COUNT(*) FROM mna_deal_targets dt WHERE dt.contact_id=ct.id) AS deals_count
        FROM mna_contacts ct
        LEFT JOIN mna_companies co ON co.id = ct.company_id
        WHERE {' AND '.join(where)}
        ORDER BY ct.is_starred DESC, ct.{sort} {direction}, ct.id DESC"""
    with db.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def get_mna_contact_by_id(contact_id: int) -> dict | None:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT ct.*, co.name AS company_name, co.short_name AS company_short_name
               FROM mna_contacts ct
               LEFT JOIN mna_companies co ON co.id = ct.company_id
               WHERE ct.id=%s AND ct.archived_at IS NULL""",
            (contact_id,)
        )
        return cur.fetchone()


def search_mna_contacts(q: str, limit: int = 20) -> list[dict]:
    db = get_db()
    sql = """SELECT ct.id, ct.first_name, ct.last_name, ct.email, co.name AS company_name
             FROM mna_contacts ct LEFT JOIN mna_companies co ON co.id = ct.company_id
             WHERE ct.archived_at IS NULL"""
    params = []
    if q:
        sql += " AND (ct.first_name LIKE %s OR ct.last_name LIKE %s OR ct.email LIKE %s)"
        like = f"%{q}%"
        params.extend([like, like, like])
    sql += " ORDER BY ct.last_name LIMIT %s"
    params.append(limit)
    with db.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def set_starred(contact_id: int, starred: bool) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("UPDATE mna_contacts SET is_starred=%s WHERE id=%s", (1 if starred else 0, contact_id))
        db.commit()
    except Exception:
        db.rollback()
        raise


def _insert(data: dict) -> int:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """INSERT INTO mna_contacts
               (company_id, first_name, last_name, position, email, phone, linkedin_url, description)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                data.get('company_id') or None, data['first_name'], data['last_name'],
                data.get('position') or None, data.get('email') or None, data.get('phone') or None,
                data.get('linkedin_url') or None, data.get('description') or None,
            )
        )
        return cur.lastrowid


def create_mna_contact(data: dict, user_id: int | None, tags: list[str] = None) -> int:
    data['phone'] = format_phone(data.get('phone'))
    db = get_db()
    try:
        contact_id = _insert(data)
        db.commit()
    except Exception:
        db.rollback()
        raise
    if tags is not None:
        set_contact_tags(contact_id, tags)
    log_history('mna_contact', contact_id, user_id, 'create',
                f"Utworzono kontakt „{data['first_name']} {data['last_name']}”.")
    return contact_id


def update_mna_contact(contact_id: int, data: dict, user_id: int | None, tags: list[str] = None) -> None:
    data['phone'] = format_phone(data.get('phone'))
    old = get_mna_contact_by_id(contact_id)
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                """UPDATE mna_contacts SET
                   company_id=%s, first_name=%s, last_name=%s, position=%s, email=%s, phone=%s,
                   linkedin_url=%s, description=%s
                   WHERE id=%s""",
                (
                    data.get('company_id') or None, data['first_name'], data['last_name'],
                    data.get('position') or None, data.get('email') or None, data.get('phone') or None,
                    data.get('linkedin_url') or None, data.get('description') or None,
                    contact_id,
                )
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    if tags is not None:
        set_contact_tags(contact_id, tags)
    if old:
        summary = build_diff_summary(old, data, FIELD_LABELS)
        if summary:
            log_history('mna_contact', contact_id, user_id, 'update', summary)


def delete_mna_contact(contact_id: int, user_id: int | None) -> None:
    contact = get_mna_contact_by_id(contact_id)
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("UPDATE mna_contacts SET archived_at=NOW() WHERE id=%s", (contact_id,))
        db.commit()
    except Exception:
        db.rollback()
        raise
    if contact:
        log_history('mna_contact', contact_id, user_id, 'archive',
                    f"Zarchiwizowano kontakt „{contact['first_name']} {contact['last_name']}”.")


def get_mna_contact_by_id_any(contact_id: int) -> dict | None:
    """Jak get_mna_contact_by_id, ale zwraca kontakt niezależnie od tego, czy jest zarchiwizowany."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT ct.*, co.name AS company_name, co.short_name AS company_short_name
               FROM mna_contacts ct
               LEFT JOIN mna_companies co ON co.id = ct.company_id
               WHERE ct.id=%s""",
            (contact_id,)
        )
        return cur.fetchone()


def restore_mna_contact(contact_id: int, user_id: int | None) -> None:
    contact = get_mna_contact_by_id_any(contact_id)
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("UPDATE mna_contacts SET archived_at=NULL WHERE id=%s", (contact_id,))
        db.commit()
    except Exception:
        db.rollback()
        raise
    if contact:
        log_history('mna_contact', contact_id, user_id, 'restore',
                    f"Przywrócono kontakt „{contact['first_name']} {contact['last_name']}” z archiwum.")
