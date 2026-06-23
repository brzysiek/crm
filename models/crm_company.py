import re

from database import get_db
from models.crm_notes import log_history, build_diff_summary
from models.crm_tags import get_or_create_tag_ids
from services.text_utils import format_phone

RELATION_LABELS = {'lead': 'Lead', 'client': 'Klient', 'partner': 'Partner'}

FIELD_LABELS = {
    'name': 'Nazwa', 'short_name': 'Nazwa skrócona', 'relation_type': 'Relacja',
    'country': 'Kraj', 'city': 'Miasto', 'street': 'Ulica',
    'house_number': 'Nr domu', 'flat_number': 'Nr lokalu', 'postal_code': 'Kod pocztowy',
    'email': 'Email', 'phone': 'Telefon', 'nip': 'NIP', 'krs': 'KRS', 'website': 'Strona WWW',
    'description': 'Opis', 'source': 'Źródło',
}

# Sufiksy odmian nazw spółek, usuwane przy automatycznym tworzeniu nazwy skróconej
# (case-insensitive, z opcjonalnym przecinkiem/spacją przed sufiksem).
_SUFFIXES = [
    'SPÓŁKA Z OGRANICZONĄ ODPOWIEDZIALNOŚCIĄ',
    r'SP\.\s*Z\s*O\.\s*O\.?',
    'SPÓŁKA KOMANDYTOWA',
    r'SP\.\s*KOM\.?',
    'SPÓŁKA CYWILNA',
    r'S\.\s*C\.?',
]
_SUFFIX_RE = re.compile(
    r'\s*,?\s*(' + '|'.join(_SUFFIXES) + r')\s*$', re.IGNORECASE
)


def derive_short_name(name: str) -> str:
    if not name:
        return ''
    short = _SUFFIX_RE.sub('', name).strip()
    return short or name.strip()


def get_all_companies(sort: str = 'name', direction: str = 'asc',
                       search: str = None, relation_type: str = None,
                       tag: str = None, industry: str = None) -> list[dict]:
    allowed_sort = {
        'name', 'short_name', 'relation_type', 'city', 'email', 'phone',
        'nip', 'source', 'created_at',
    }
    if sort not in allowed_sort:
        sort = 'name'
    direction = 'DESC' if str(direction).lower() == 'desc' else 'ASC'

    db = get_db()
    params = []
    joins = []
    where = ["1=1"]

    if tag:
        joins.append("JOIN crm_company_tags ct ON ct.company_id=c.id "
                     "JOIN crm_tags t ON t.id=ct.tag_id AND t.kind='tag'")
        where.append("t.name = %s")
        params.append(tag)
    if industry:
        joins.append("JOIN crm_company_tags ci ON ci.company_id=c.id "
                     "JOIN crm_tags i ON i.id=ci.tag_id AND i.kind='industry'")
        where.append("i.name = %s")
        params.append(industry)
    if relation_type:
        where.append("c.relation_type = %s")
        params.append(relation_type)
    if search:
        where.append("(c.name LIKE %s OR c.short_name LIKE %s OR c.email LIKE %s "
                      "OR c.nip LIKE %s OR c.city LIKE %s)")
        like = f"%{search}%"
        params.extend([like, like, like, like, like])

    sql = f"""SELECT DISTINCT c.*,
        (SELECT GROUP_CONCAT(t.name ORDER BY t.name SEPARATOR ', ')
           FROM crm_company_tags ct JOIN crm_tags t ON t.id=ct.tag_id
           WHERE ct.company_id=c.id AND t.kind='tag') AS tags_list,
        (SELECT GROUP_CONCAT(t.name ORDER BY t.name SEPARATOR ', ')
           FROM crm_company_tags ct JOIN crm_tags t ON t.id=ct.tag_id
           WHERE ct.company_id=c.id AND t.kind='industry') AS industries_list
        FROM crm_companies c {' '.join(joins)} WHERE {' AND '.join(where)}"""
    sql += f" ORDER BY c.{sort} {direction}, c.id DESC"

    with db.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def get_company_by_id(company_id: int) -> dict | None:
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM crm_companies WHERE id=%s", (company_id,))
        return cur.fetchone()


def get_company_by_nip(nip: str) -> dict | None:
    if not nip:
        return None
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM crm_companies WHERE nip=%s LIMIT 1", (nip,))
        return cur.fetchone()


def search_companies(q: str, limit: int = 20) -> list[dict]:
    db = get_db()
    sql = "SELECT id, name, short_name, city, nip FROM crm_companies WHERE 1=1"
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


def get_company_tags(company_id: int, kind: str) -> list[str]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT t.name FROM crm_tags t
               JOIN crm_company_tags ct ON ct.tag_id=t.id
               WHERE ct.company_id=%s AND t.kind=%s ORDER BY t.name""",
            (company_id, kind)
        )
        return [r['name'] for r in cur.fetchall()]


def set_company_tags(company_id: int, kind: str, names: list[str]) -> None:
    tag_ids = get_or_create_tag_ids(kind, names)
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                """DELETE ct FROM crm_company_tags ct
                   JOIN crm_tags t ON t.id = ct.tag_id
                   WHERE ct.company_id=%s AND t.kind=%s""",
                (company_id, kind)
            )
            for tag_id in tag_ids:
                cur.execute(
                    "INSERT IGNORE INTO crm_company_tags (company_id, tag_id) VALUES (%s, %s)",
                    (company_id, tag_id)
                )
        db.commit()
    except Exception:
        db.rollback()
        raise


def _insert(data: dict) -> int:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """INSERT INTO crm_companies
               (name, short_name, relation_type, country, city, street, house_number,
                flat_number, postal_code, email, phone, nip, krs, website, description, source, owner_user_id)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                data['name'], data.get('short_name') or None, data.get('relation_type', 'lead'),
                data.get('country') or 'Polska', data.get('city') or None, data.get('street') or None,
                data.get('house_number') or None, data.get('flat_number') or None,
                data.get('postal_code') or None, data.get('email') or None, data.get('phone') or None,
                data.get('nip') or None, data.get('krs') or None, data.get('website') or None,
                data.get('description') or None, data.get('source') or None, data.get('owner_user_id') or None,
            )
        )
        return cur.lastrowid


def create_company(data: dict, user_id: int | None,
                    tags: list[str] = None, industries: list[str] = None) -> int:
    data['phone'] = format_phone(data.get('phone'))
    db = get_db()
    try:
        company_id = _insert(data)
        db.commit()
    except Exception:
        db.rollback()
        raise
    if tags is not None:
        set_company_tags(company_id, 'tag', tags)
    if industries is not None:
        set_company_tags(company_id, 'industry', industries)
    log_history('company', company_id, user_id, 'create',
                f"Utworzono firmę „{data['name']}”.")
    return company_id


def update_company(company_id: int, data: dict, user_id: int | None,
                    tags: list[str] = None, industries: list[str] = None) -> None:
    data['phone'] = format_phone(data.get('phone'))
    old = get_company_by_id(company_id)
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                """UPDATE crm_companies SET
                   name=%s, short_name=%s, relation_type=%s, country=%s, city=%s, street=%s,
                   house_number=%s, flat_number=%s, postal_code=%s, email=%s, phone=%s,
                   nip=%s, krs=%s, website=%s, description=%s, source=%s, owner_user_id=%s
                   WHERE id=%s""",
                (
                    data['name'], data.get('short_name') or None, data.get('relation_type', 'lead'),
                    data.get('country') or 'Polska', data.get('city') or None, data.get('street') or None,
                    data.get('house_number') or None, data.get('flat_number') or None,
                    data.get('postal_code') or None, data.get('email') or None, data.get('phone') or None,
                    data.get('nip') or None, data.get('krs') or None, data.get('website') or None,
                    data.get('description') or None, data.get('source') or None, data.get('owner_user_id') or None,
                    company_id,
                )
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    if tags is not None:
        set_company_tags(company_id, 'tag', tags)
    if industries is not None:
        set_company_tags(company_id, 'industry', industries)
    if old:
        old_disp = dict(old)
        new_disp = dict(data)
        old_disp['relation_type'] = RELATION_LABELS.get(old.get('relation_type'), old.get('relation_type'))
        new_disp['relation_type'] = RELATION_LABELS.get(data.get('relation_type'), data.get('relation_type'))
        summary = build_diff_summary(old_disp, new_disp, FIELD_LABELS)
        if summary:
            log_history('company', company_id, user_id, 'update', summary)


def delete_company(company_id: int, user_id: int | None) -> None:
    company = get_company_by_id(company_id)
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("DELETE FROM crm_companies WHERE id=%s", (company_id,))
        db.commit()
    except Exception:
        db.rollback()
        raise
    if company:
        log_history('company', company_id, user_id, 'delete',
                     f"Usunięto firmę „{company['name']}”.")
