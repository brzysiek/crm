from database import get_db
from models.crm_notes import log_history, build_diff_summary
from services.text_utils import format_phone

FIELD_LABELS = {
    'name': 'Nazwa', 'short_name': 'Nazwa skrócona',
    'country': 'Kraj', 'city': 'Miasto', 'voivodeship': 'Województwo', 'street': 'Ulica',
    'house_number': 'Nr domu', 'flat_number': 'Nr lokalu', 'postal_code': 'Kod pocztowy',
    'email': 'Email', 'phone': 'Telefon', 'nip': 'NIP', 'krs': 'KRS', 'website': 'Strona WWW',
    'linkedin_url': 'LinkedIn', 'description': 'Opis', 'short_description': 'Krótki opis',
}


def _filters(search: str = None) -> tuple[list, list]:
    where = ["c.archived_at IS NULL"]
    params = []
    if search:
        where.append("(c.name LIKE %s OR c.short_name LIKE %s OR c.email LIKE %s "
                      "OR c.nip LIKE %s OR c.city LIKE %s)")
        like = f"%{search}%"
        params.extend([like, like, like, like, like])
    return where, params


def get_all_mna_companies(sort: str = 'name', direction: str = 'asc', search: str = None) -> list[dict]:
    allowed_sort = {'name', 'short_name', 'city', 'email', 'phone', 'nip', 'created_at'}
    if sort not in allowed_sort:
        sort = 'name'
    direction = 'DESC' if str(direction).lower() == 'desc' else 'ASC'
    where, params = _filters(search)
    db = get_db()
    sql = f"""SELECT c.*,
        (SELECT COUNT(*) FROM mna_contacts ct WHERE ct.company_id=c.id AND ct.archived_at IS NULL) AS contacts_count,
        (SELECT COUNT(*) FROM mna_deal_targets dt WHERE dt.company_id=c.id) AS deals_count
        FROM mna_companies c WHERE {' AND '.join(where)}
        ORDER BY c.is_starred DESC, c.{sort} {direction}, c.id DESC"""
    with db.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def get_mna_company_by_id(company_id: int) -> dict | None:
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM mna_companies WHERE id=%s AND archived_at IS NULL", (company_id,))
        return cur.fetchone()


def search_mna_companies(q: str, limit: int = 20) -> list[dict]:
    db = get_db()
    sql = "SELECT id, name, short_name, city, nip FROM mna_companies WHERE archived_at IS NULL"
    params = []
    if q:
        sql += " AND (name LIKE %s OR short_name LIKE %s OR nip LIKE %s)"
        like = f"%{q}%"
        params.extend([like, like, like])
    sql += " ORDER BY name LIMIT %s"
    params.append(limit)
    with db.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def set_starred(company_id: int, starred: bool) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("UPDATE mna_companies SET is_starred=%s WHERE id=%s", (1 if starred else 0, company_id))
        db.commit()
    except Exception:
        db.rollback()
        raise


def _insert(data: dict) -> int:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """INSERT INTO mna_companies
               (name, short_name, country, city, voivodeship, street, house_number,
                flat_number, postal_code, email, phone, nip, krs, website, linkedin_url,
                description, short_description, owner_user_id)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                data['name'], data.get('short_name') or None,
                data.get('country') or 'Polska', data.get('city') or None, data.get('voivodeship') or None,
                data.get('street') or None, data.get('house_number') or None, data.get('flat_number') or None,
                data.get('postal_code') or None, data.get('email') or None, data.get('phone') or None,
                data.get('nip') or None, data.get('krs') or None, data.get('website') or None,
                data.get('linkedin_url') or None, data.get('description') or None,
                data.get('short_description') or None, data.get('owner_user_id') or None,
            )
        )
        return cur.lastrowid


def create_mna_company(data: dict, user_id: int | None) -> int:
    data['phone'] = format_phone(data.get('phone'))
    db = get_db()
    try:
        company_id = _insert(data)
        db.commit()
    except Exception:
        db.rollback()
        raise
    log_history('mna_company', company_id, user_id, 'create', f"Utworzono firmę „{data['name']}”.")
    return company_id


def update_mna_company(company_id: int, data: dict, user_id: int | None) -> None:
    data['phone'] = format_phone(data.get('phone'))
    old = get_mna_company_by_id(company_id)
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                """UPDATE mna_companies SET
                   name=%s, short_name=%s, country=%s, city=%s, voivodeship=%s, street=%s,
                   house_number=%s, flat_number=%s, postal_code=%s, email=%s, phone=%s,
                   nip=%s, krs=%s, website=%s, linkedin_url=%s, description=%s, short_description=%s,
                   owner_user_id=%s
                   WHERE id=%s""",
                (
                    data['name'], data.get('short_name') or None,
                    data.get('country') or 'Polska', data.get('city') or None, data.get('voivodeship') or None,
                    data.get('street') or None, data.get('house_number') or None, data.get('flat_number') or None,
                    data.get('postal_code') or None, data.get('email') or None, data.get('phone') or None,
                    data.get('nip') or None, data.get('krs') or None, data.get('website') or None,
                    data.get('linkedin_url') or None, data.get('description') or None,
                    data.get('short_description') or None, data.get('owner_user_id') or None,
                    company_id,
                )
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    if old:
        summary = build_diff_summary(old, data, FIELD_LABELS)
        if summary:
            log_history('mna_company', company_id, user_id, 'update', summary)


def delete_mna_company(company_id: int, user_id: int | None) -> None:
    company = get_mna_company_by_id(company_id)
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("UPDATE mna_companies SET archived_at=NOW() WHERE id=%s", (company_id,))
        db.commit()
    except Exception:
        db.rollback()
        raise
    if company:
        log_history('mna_company', company_id, user_id, 'archive', f"Zarchiwizowano firmę „{company['name']}”.")


def get_mna_company_by_id_any(company_id: int) -> dict | None:
    """Jak get_mna_company_by_id, ale zwraca firmę niezależnie od tego, czy jest zarchiwizowana."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM mna_companies WHERE id=%s", (company_id,))
        return cur.fetchone()


def restore_mna_company(company_id: int, user_id: int | None) -> None:
    company = get_mna_company_by_id_any(company_id)
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("UPDATE mna_companies SET archived_at=NULL WHERE id=%s", (company_id,))
        db.commit()
    except Exception:
        db.rollback()
        raise
    if company:
        log_history('mna_company', company_id, user_id, 'restore', f"Przywrócono firmę „{company['name']}” z archiwum.")
