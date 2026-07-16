from database import get_db
from models.crm_notes import log_history, build_diff_summary
from services.text_utils import format_phone

FIELD_LABELS = {
    'first_name': 'Imię', 'last_name': 'Nazwisko', 'position': 'Stanowisko',
    'email': 'Email', 'phone': 'Telefon',
    'linkedin_url': 'LinkedIn', 'description': 'Opis',
}


def get_all_contacts(sort: str = 'last_name', direction: str = 'asc',
                      search: str = None, company_id: int = None) -> list[dict]:
    allowed_sort = {'first_name', 'last_name', 'position', 'email', 'phone', 'created_at', 'company_name'}
    if sort not in allowed_sort:
        sort = 'last_name'
    sort_col = 'co.name' if sort == 'company_name' else f'ct.{sort}'
    direction = 'DESC' if str(direction).lower() == 'desc' else 'ASC'

    db = get_db()
    sql = ("SELECT ct.*, co.name AS company_name, co.short_name AS company_short_name, "
           "co.favicon_url AS company_favicon_url, "
           "(SELECT GROUP_CONCAT(t.name ORDER BY t.name SEPARATOR ', ') "
           "   FROM crm_company_tags cct JOIN crm_tags t ON t.id=cct.tag_id "
           "   WHERE cct.company_id=co.id AND t.kind='tag') AS company_tags_list, "
           "(SELECT GROUP_CONCAT(t.name ORDER BY t.name SEPARATOR ', ') "
           "   FROM crm_company_tags cct JOIN crm_tags t ON t.id=cct.tag_id "
           "   WHERE cct.company_id=co.id AND t.kind='industry') AS company_industries_list, "
           "(SELECT f.id FROM crm_files f WHERE f.contact_id=ct.id AND f.category='business_card' "
           "   ORDER BY f.id DESC LIMIT 1) AS business_card_file_id, "
           "(SELECT f.mime_type FROM crm_files f WHERE f.contact_id=ct.id AND f.category='business_card' "
           "   ORDER BY f.id DESC LIMIT 1) AS business_card_mime_type "
           "FROM crm_contacts ct LEFT JOIN crm_companies co ON co.id = ct.company_id "
           "WHERE ct.archived_at IS NULL")
    params = []
    if company_id:
        sql += " AND ct.company_id = %s"
        params.append(company_id)
    if search:
        sql += (" AND (ct.first_name LIKE %s OR ct.last_name LIKE %s OR ct.email LIKE %s "
                 "OR ct.phone LIKE %s OR co.name LIKE %s)")
        like = f"%{search}%"
        params.extend([like, like, like, like, like])
    sql += f" ORDER BY ct.is_starred DESC, {sort_col} {direction}, ct.id DESC"

    with db.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def get_contact_by_id(contact_id: int) -> dict | None:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT ct.*, co.name AS company_name, co.short_name AS company_short_name,
                      co.website AS company_website
               FROM crm_contacts ct LEFT JOIN crm_companies co ON co.id = ct.company_id
               WHERE ct.id=%s AND ct.archived_at IS NULL""",
            (contact_id,)
        )
        return cur.fetchone()


def get_names_by_ids(ids: list[int]) -> dict[int, str]:
    if not ids:
        return {}
    db = get_db()
    with db.cursor() as cur:
        placeholders = ','.join(['%s'] * len(ids))
        cur.execute(
            f"SELECT id, first_name, last_name FROM crm_contacts WHERE id IN ({placeholders})",
            tuple(ids)
        )
        return {row['id']: f"{row['first_name']} {row['last_name']}".strip() for row in cur.fetchall()}


def search_contacts(q: str, company_id: int = None, limit: int = 20) -> list[dict]:
    db = get_db()
    sql = ("SELECT ct.id, ct.first_name, ct.last_name, ct.email, co.name AS company_name "
           "FROM crm_contacts ct LEFT JOIN crm_companies co ON co.id = ct.company_id "
           "WHERE ct.archived_at IS NULL")
    params = []
    if company_id:
        sql += " AND ct.company_id = %s"
        params.append(company_id)
    if q:
        sql += " AND (ct.first_name LIKE %s OR ct.last_name LIKE %s OR ct.email LIKE %s)"
        like = f"%{q}%"
        params.extend([like, like, like])
    sql += " ORDER BY ct.last_name LIMIT %s"
    params.append(limit)
    with db.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def create_contact(data: dict, user_id: int | None) -> int:
    data['phone'] = format_phone(data.get('phone'))
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                """INSERT INTO crm_contacts
                   (company_id, first_name, last_name, position, email, phone,
                    linkedin_url, description)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    data.get('company_id') or None, data['first_name'], data['last_name'],
                    data.get('position') or None, data.get('email') or None,
                    data.get('phone') or None,
                    data.get('linkedin_url') or None, data.get('description') or None,
                )
            )
        db.commit()
        contact_id = cur.lastrowid
    except Exception:
        db.rollback()
        raise
    log_history('contact', contact_id, user_id, 'create',
                f"Utworzono kontakt „{data['first_name']} {data['last_name']}”.")
    return contact_id


def update_contact(contact_id: int, data: dict, user_id: int | None) -> None:
    data['phone'] = format_phone(data.get('phone'))
    old = get_contact_by_id(contact_id)
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                """UPDATE crm_contacts SET
                   company_id=%s, first_name=%s, last_name=%s, position=%s,
                   email=%s, phone=%s, linkedin_url=%s, description=%s
                   WHERE id=%s""",
                (
                    data.get('company_id') or None, data['first_name'], data['last_name'],
                    data.get('position') or None, data.get('email') or None,
                    data.get('phone') or None,
                    data.get('linkedin_url') or None, data.get('description') or None,
                    contact_id,
                )
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    if old:
        summary = build_diff_summary(old, data, FIELD_LABELS)
        if summary:
            log_history('contact', contact_id, user_id, 'update', summary)


def set_starred(contact_id: int, starred: bool) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("UPDATE crm_contacts SET is_starred=%s WHERE id=%s", (1 if starred else 0, contact_id))
        db.commit()
    except Exception:
        db.rollback()
        raise


def bulk_set_starred(contact_ids: list[int], starred: bool) -> int:
    if not contact_ids:
        return 0
    db = get_db()
    placeholders = ','.join(['%s'] * len(contact_ids))
    try:
        with db.cursor() as cur:
            cur.execute(
                f"UPDATE crm_contacts SET is_starred=%s WHERE id IN ({placeholders})",
                [1 if starred else 0] + contact_ids,
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return len(contact_ids)


def bulk_delete_contacts(contact_ids: list[int], user_id: int | None) -> int:
    affected = 0
    for contact_id in contact_ids:
        delete_contact(contact_id, user_id, archive_company=False)
        affected += 1
    return affected


def delete_contact(contact_id: int, user_id: int | None, archive_company: bool = False) -> None:
    contact = get_contact_by_id(contact_id)
    db = get_db()
    company_archived = False
    try:
        with db.cursor() as cur:
            cur.execute("UPDATE crm_contacts SET archived_at=NOW() WHERE id=%s", (contact_id,))
            if archive_company and contact and contact.get('company_id'):
                cur.execute(
                    "UPDATE crm_companies SET archived_at=NOW() WHERE id=%s AND archived_at IS NULL",
                    (contact['company_id'],)
                )
                company_archived = cur.rowcount > 0
        db.commit()
    except Exception:
        db.rollback()
        raise
    if contact:
        summary = f"Zarchiwizowano kontakt „{contact['first_name']} {contact['last_name']}”."
        if company_archived:
            summary += f" Zarchiwizowano też firmę „{contact.get('company_name')}”."
        log_history('contact', contact_id, user_id, 'delete', summary)
        if company_archived:
            log_history('company', contact['company_id'], user_id, 'delete',
                         f"Zarchiwizowano firmę „{contact.get('company_name')}” (usunięto kontakt "
                         f"„{contact['first_name']} {contact['last_name']}”).")
