from database import get_db
import models.gtd_context as gtd_context_model
from models.crm_notes import log_history, build_diff_summary
from models.crm_tags import set_contact_tags
from services.text_utils import format_phone

FIELD_LABELS = {
    'first_name': 'Imię', 'last_name': 'Nazwisko', 'position': 'Stanowisko',
    'email': 'Email', 'phone': 'Telefon',
    'linkedin_url': 'LinkedIn', 'description': 'Opis', 'context_id': 'Kontekst',
}


def get_all_contacts(sort: str = 'last_name', direction: str = 'asc',
                      search: str = None, company_id: int = None,
                      context_ids: list[int] | None = None) -> list[dict]:
    allowed_sort = {'first_name', 'last_name', 'position', 'email', 'phone', 'created_at', 'company_name'}
    if sort not in allowed_sort:
        sort = 'last_name'
    sort_col = 'co.name' if sort == 'company_name' else f'ct.{sort}'
    direction = 'DESC' if str(direction).lower() == 'desc' else 'ASC'

    db = get_db()
    sql = ("SELECT ct.*, co.name AS company_name, co.short_name AS company_short_name, "
           "co.favicon_url AS company_favicon_url, "
           "gc.name AS context_name, gc.badge_color AS context_badge_color, gc.text_color AS context_text_color, "
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
           "LEFT JOIN gtd_contexts gc ON gc.id = ct.context_id "
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
    if context_ids is not None:
        # Sentinel 0 oznacza koszyk „Brak kontekstu” (ct.context_id IS NULL).
        real_ids = [c for c in context_ids if c]
        conds = []
        if real_ids:
            placeholders = ','.join(['%s'] * len(real_ids))
            conds.append(f"ct.context_id IN ({placeholders})")
            params.extend(real_ids)
        if 0 in context_ids:
            conds.append("ct.context_id IS NULL")
        sql += f" AND ({' OR '.join(conds)})" if conds else " AND 1=0"
    sql += f" ORDER BY ct.is_starred DESC, {sort_col} {direction}, ct.id DESC"

    with db.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def get_contact_by_id(contact_id: int) -> dict | None:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT ct.*, co.name AS company_name, co.short_name AS company_short_name,
                      co.website AS company_website,
                      gc.name AS context_name, gc.badge_color AS context_badge_color,
                      gc.text_color AS context_text_color
               FROM crm_contacts ct
               LEFT JOIN crm_companies co ON co.id = ct.company_id
               LEFT JOIN gtd_contexts gc ON gc.id = ct.context_id
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
    sql = ("SELECT ct.id, ct.first_name, ct.last_name, ct.email, ct.company_id, co.name AS company_name "
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


def create_contact(data: dict, user_id: int | None, tags: list[str] = None) -> int:
    data['phone'] = format_phone(data.get('phone'))
    db = get_db()
    if not data.get('context_id') and data.get('company_id'):
        with db.cursor() as cur:
            cur.execute("SELECT context_id FROM crm_companies WHERE id=%s", (data['company_id'],))
            row = cur.fetchone()
            if row:
                data['context_id'] = row['context_id']
    data['context_id'] = data.get('context_id') or gtd_context_model.get_default_context_id()
    try:
        with db.cursor() as cur:
            cur.execute(
                """INSERT INTO crm_contacts
                   (company_id, first_name, last_name, position, email, phone,
                    linkedin_url, description, context_id)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    data.get('company_id') or None, data['first_name'], data['last_name'],
                    data.get('position') or None, data.get('email') or None,
                    data.get('phone') or None,
                    data.get('linkedin_url') or None, data.get('description') or None,
                    data.get('context_id') or None,
                )
            )
        db.commit()
        contact_id = cur.lastrowid
    except Exception:
        db.rollback()
        raise
    if tags is not None:
        set_contact_tags(contact_id, tags)
    if data.get('company_id'):
        gtd_context_model.sync_company_context_group(data['company_id'], data.get('context_id') or None)
    log_history('contact', contact_id, user_id, 'create',
                f"Utworzono kontakt „{data['first_name']} {data['last_name']}”.")
    return contact_id


def update_contact(contact_id: int, data: dict, user_id: int | None, tags: list[str] = None) -> None:
    data['phone'] = format_phone(data.get('phone'))
    old = get_contact_by_id(contact_id)
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                """UPDATE crm_contacts SET
                   company_id=%s, first_name=%s, last_name=%s, position=%s,
                   email=%s, phone=%s, linkedin_url=%s, description=%s, context_id=%s
                   WHERE id=%s""",
                (
                    data.get('company_id') or None, data['first_name'], data['last_name'],
                    data.get('position') or None, data.get('email') or None,
                    data.get('phone') or None,
                    data.get('linkedin_url') or None, data.get('description') or None,
                    data.get('context_id') or None,
                    contact_id,
                )
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    if tags is not None:
        set_contact_tags(contact_id, tags)
    if data.get('company_id') and (not old or old.get('context_id') != data.get('context_id')):
        gtd_context_model.sync_company_context_group(data['company_id'], data.get('context_id') or None)
    if old:
        old_disp = dict(old)
        new_disp = dict(data)
        context_names = {c['id']: c['name'] for c in gtd_context_model.get_all_contexts()}
        old_disp['context_id'] = f"@{context_names[old['context_id']]}" if old.get('context_id') in context_names else None
        new_disp['context_id'] = f"@{context_names[data['context_id']]}" if data.get('context_id') in context_names else None
        summary = build_diff_summary(old_disp, new_disp, FIELD_LABELS)
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


def assign_contacts_to_company(contact_ids: list[int], company_id: int, user_id: int | None) -> None:
    if not contact_ids:
        return
    db = get_db()
    placeholders = ','.join(['%s'] * len(contact_ids))
    try:
        with db.cursor() as cur:
            cur.execute(
                f"UPDATE crm_contacts SET company_id=%s WHERE id IN ({placeholders})",
                [company_id] + contact_ids,
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    for contact_id in contact_ids:
        log_history('contact', contact_id, user_id, 'update', 'Przypisano kontakt do firmy.')


def unassign_contacts_from_company(contact_ids: list[int], user_id: int | None) -> None:
    if not contact_ids:
        return
    db = get_db()
    placeholders = ','.join(['%s'] * len(contact_ids))
    try:
        with db.cursor() as cur:
            cur.execute(
                f"UPDATE crm_contacts SET company_id=NULL WHERE id IN ({placeholders})",
                contact_ids,
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    for contact_id in contact_ids:
        log_history('contact', contact_id, user_id, 'update', 'Odpięto kontakt od firmy.')


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


def bulk_set_context(contact_ids: list[int], context_id: int | None, user_id: int | None) -> int:
    """Ustawia kontekst GTD dla zaznaczonych kontaktów; jeśli kontakt ma
    przypisaną firmę, kaskadowo ujednolica kontekst na całej grupie firma+kontakty."""
    if not contact_ids:
        return 0
    ctx = gtd_context_model.get_context(context_id) if context_id else None
    summary = f'Ustawiono kontekst na @{ctx["name"]}.' if ctx else 'Usunięto kontekst.'
    db = get_db()
    for contact_id in contact_ids:
        contact = get_contact_by_id(contact_id)
        if not contact:
            continue
        if contact.get('company_id'):
            gtd_context_model.sync_company_context_group(contact['company_id'], context_id)
        else:
            try:
                with db.cursor() as cur:
                    cur.execute("UPDATE crm_contacts SET context_id=%s WHERE id=%s", (context_id, contact_id))
                db.commit()
            except Exception:
                db.rollback()
                raise
        log_history('contact', contact_id, user_id, 'update', summary)
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
