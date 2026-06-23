from database import get_db


def suggest_tags(kind: str, q: str = '', limit: int = 20) -> list[str]:
    """kind: 'tag' lub 'industry' — podpowiedzi istniejących nazw do tag-inputa."""
    db = get_db()
    sql = "SELECT name FROM crm_tags WHERE kind=%s"
    params = [kind]
    if q:
        sql += " AND name LIKE %s"
        params.append(f"%{q}%")
    sql += " ORDER BY name LIMIT %s"
    params.append(limit)
    with db.cursor() as cur:
        cur.execute(sql, params)
        return [r['name'] for r in cur.fetchall()]


def suggest_sources(q: str = '', limit: int = 20) -> list[str]:
    """Podpowiedzi 'źródła' z istniejących, już użytych wartości w crm_companies.source."""
    db = get_db()
    sql = ("SELECT DISTINCT source FROM crm_companies "
           "WHERE source IS NOT NULL AND source != ''")
    params = []
    if q:
        sql += " AND source LIKE %s"
        params.append(f"%{q}%")
    sql += " ORDER BY source LIMIT %s"
    params.append(limit)
    with db.cursor() as cur:
        cur.execute(sql, params)
        return [r['source'] for r in cur.fetchall()]


def get_or_create_tag_ids(kind: str, names: list[str]) -> list[int]:
    db = get_db()
    ids = []
    try:
        with db.cursor() as cur:
            for raw_name in names:
                name = raw_name.strip()
                if not name:
                    continue
                cur.execute(
                    "SELECT id FROM crm_tags WHERE kind=%s AND name=%s",
                    (kind, name)
                )
                row = cur.fetchone()
                if row:
                    ids.append(row['id'])
                else:
                    cur.execute(
                        "INSERT INTO crm_tags (kind, name) VALUES (%s, %s)",
                        (kind, name)
                    )
                    ids.append(cur.lastrowid)
        db.commit()
        return ids
    except Exception:
        db.rollback()
        raise
