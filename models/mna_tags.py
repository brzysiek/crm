from database import get_db
from models.crm_tags import normalize_tag_name


def suggest_tags(q: str = '', limit: int = 20) -> list[str]:
    db = get_db()
    sql = "SELECT name FROM mna_tags"
    params = []
    if q:
        sql += " WHERE name LIKE %s"
        params.append(f"%{q}%")
    sql += " ORDER BY name LIMIT %s"
    params.append(limit)
    with db.cursor() as cur:
        cur.execute(sql, params)
        return [r['name'] for r in cur.fetchall()]


def get_company_tags(company_id: int) -> list[str]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT t.name FROM mna_tags t
               JOIN mna_company_tags ct ON ct.tag_id=t.id
               WHERE ct.company_id=%s ORDER BY t.name""",
            (company_id,)
        )
        return [r['name'] for r in cur.fetchall()]


def get_contact_tags(contact_id: int) -> list[str]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT t.name FROM mna_tags t
               JOIN mna_contact_tags ct ON ct.tag_id=t.id
               WHERE ct.contact_id=%s ORDER BY t.name""",
            (contact_id,)
        )
        return [r['name'] for r in cur.fetchall()]


def _get_or_create_tag_ids(names: list[str]) -> list[int]:
    db = get_db()
    ids = []
    with db.cursor() as cur:
        for raw_name in names:
            name = normalize_tag_name(raw_name.strip())
            if not name:
                continue
            cur.execute("SELECT id, name FROM mna_tags WHERE name=%s", (name,))
            row = cur.fetchone()
            if row:
                ids.append(row['id'])
            else:
                cur.execute("INSERT INTO mna_tags (name) VALUES (%s)", (name,))
                ids.append(cur.lastrowid)
    return ids


def set_company_tags(company_id: int, names: list[str]) -> None:
    db = get_db()
    try:
        tag_ids = _get_or_create_tag_ids(names)
        with db.cursor() as cur:
            cur.execute("DELETE FROM mna_company_tags WHERE company_id=%s", (company_id,))
            for tag_id in tag_ids:
                cur.execute(
                    "INSERT IGNORE INTO mna_company_tags (company_id, tag_id) VALUES (%s, %s)",
                    (company_id, tag_id)
                )
        db.commit()
    except Exception:
        db.rollback()
        raise


def set_contact_tags(contact_id: int, names: list[str]) -> None:
    db = get_db()
    try:
        tag_ids = _get_or_create_tag_ids(names)
        with db.cursor() as cur:
            cur.execute("DELETE FROM mna_contact_tags WHERE contact_id=%s", (contact_id,))
            for tag_id in tag_ids:
                cur.execute(
                    "INSERT IGNORE INTO mna_contact_tags (contact_id, tag_id) VALUES (%s, %s)",
                    (contact_id, tag_id)
                )
        db.commit()
    except Exception:
        db.rollback()
        raise
