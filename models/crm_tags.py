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


def suggest_sources(q: str = '', limit: int = 20) -> list[dict]:
    """Podpowiedzi dla pola źródła: łączy istniejące wartości źródeł (crm_tags)
    z kontaktami pasującymi do zapytania, żeby można było wskazać osobę polecającą.
    Zwraca listę {'value': str, 'contact_id': int|None}."""
    db = get_db()
    tag_sql = "SELECT name FROM crm_tags WHERE kind='source'"
    tag_params = []
    if q:
        tag_sql += " AND name LIKE %s"
        tag_params.append(f"%{q}%")
    tag_sql += " ORDER BY name LIMIT %s"
    tag_params.append(limit)

    contact_sql = "SELECT id, first_name, last_name FROM crm_contacts WHERE archived_at IS NULL"
    contact_params = []
    if q:
        contact_sql += " AND (first_name LIKE %s OR last_name LIKE %s OR CONCAT(first_name,' ',last_name) LIKE %s)"
        like = f"%{q}%"
        contact_params.extend([like, like, like])
    contact_sql += " ORDER BY last_name, first_name LIMIT %s"
    contact_params.append(limit)

    with db.cursor() as cur:
        cur.execute(tag_sql, tag_params)
        tag_names = [r['name'] for r in cur.fetchall()]
        cur.execute(contact_sql, contact_params)
        contacts = cur.fetchall()

    results = [
        {'value': f"{c['first_name']} {c['last_name']}", 'contact_id': c['id']}
        for c in contacts
    ]
    contact_names_lower = {r['value'].lower() for r in results}
    for name in tag_names:
        if name.lower() not in contact_names_lower:
            results.append({'value': name, 'contact_id': None})

    results.sort(key=lambda r: r['value'].lower())
    return results[:limit]


def get_tags(kind: str) -> list[dict]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT id, name FROM crm_tags WHERE kind=%s ORDER BY name", (kind,)
        )
        return cur.fetchall()


def add_tag(kind: str, name: str) -> int:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "INSERT INTO crm_tags (kind, name) VALUES (%s, %s)", (kind, name)
            )
            new_id = cur.lastrowid
        db.commit()
        return new_id
    except Exception:
        db.rollback()
        raise


def delete_tag(tag_id: int) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("DELETE FROM crm_tags WHERE id=%s", (tag_id,))
        db.commit()
    except Exception:
        db.rollback()
        raise


def get_contact_tags(contact_id: int) -> list[str]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT t.name FROM crm_tags t
               JOIN crm_contact_tags ct ON ct.tag_id=t.id
               WHERE ct.contact_id=%s AND t.kind='tag' ORDER BY t.name""",
            (contact_id,)
        )
        return [r['name'] for r in cur.fetchall()]


def set_contact_tags(contact_id: int, names: list[str]) -> None:
    tag_ids = get_or_create_tag_ids('tag', names)
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                """DELETE ct FROM crm_contact_tags ct
                   JOIN crm_tags t ON t.id = ct.tag_id
                   WHERE ct.contact_id=%s AND t.kind='tag'""",
                (contact_id,)
            )
            for tag_id in tag_ids:
                cur.execute(
                    "INSERT IGNORE INTO crm_contact_tags (contact_id, tag_id) VALUES (%s, %s)",
                    (contact_id, tag_id)
                )
        db.commit()
    except Exception:
        db.rollback()
        raise


def get_tag_ids_by_names(kind: str, names: list[str]) -> list[int]:
    """Jak get_or_create_tag_ids, ale nie tworzy nowych tagów — do podglądu
    (np. liczby odbiorców kampanii) zanim formularz zostanie zapisany."""
    names = [n.strip() for n in names if n and n.strip()]
    if not names:
        return []
    db = get_db()
    placeholders = ','.join(['%s'] * len(names))
    with db.cursor() as cur:
        cur.execute(
            f"SELECT id FROM crm_tags WHERE kind=%s AND name IN ({placeholders})",
            [kind] + names
        )
        return [r['id'] for r in cur.fetchall()]


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
