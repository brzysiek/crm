import re

from database import get_db
from models.crm_notes import log_history


def _normalize_word(word: str) -> str:
    letters = [c for c in word if c.isalpha()]
    if not letters:
        return word
    if all(c.isupper() for c in letters):
        return word
    out, capitalized = [], False
    for c in word:
        if not c.isalpha():
            out.append(c)
        elif not capitalized:
            out.append(c.upper())
            capitalized = True
        else:
            out.append(c.lower())
    return ''.join(out)


def normalize_tag_name(name: str) -> str:
    """Ujednolica zapis tagu do formatu Tytułowego: każde słowo z wielkiej litery
    (np. "fundusz inwestycyjny" -> "Fundusz Inwestycyjny"). Słowa zapisane w
    całości wielkimi literami zostają bez zmian, żeby nie niszczyć akronimów
    (IT, BNI, CRM, M&A, B2B). Dzieli też złożenia typu "IT/Edukacja" czy
    "e-commerce" po / i -, żeby capitalizacja działała po obu stronach separatora."""
    def norm_compound(token: str) -> str:
        parts = re.split(r'([/-])', token)
        return ''.join(p if p in ('/', '-') else _normalize_word(p) for p in parts)
    return ' '.join(norm_compound(w) for w in name.split())


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
    name = normalize_tag_name(name.strip())
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


def get_contact_email_tags(contact_id: int) -> list[str]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT t.name FROM crm_tags t
               JOIN crm_contact_tags ct ON ct.tag_id=t.id
               WHERE ct.contact_id=%s AND t.kind='email' ORDER BY t.name""",
            (contact_id,)
        )
        return [r['name'] for r in cur.fetchall()]


def _replace_contact_tags_of_kind(contact_id: int, kind: str, tag_ids: list[int]) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                """DELETE ct FROM crm_contact_tags ct
                   JOIN crm_tags t ON t.id = ct.tag_id
                   WHERE ct.contact_id=%s AND t.kind=%s""",
                (contact_id, kind)
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


def set_contact_email_tags(contact_id: int, names: list[str], user_id: int | None) -> None:
    """Nadanie/odebranie tagu email jest jednocześnie udzieleniem/wycofaniem zgody
    marketingowej na dany cel komunikacji — każda zmiana trafia do historii kontaktu."""
    names = [normalize_tag_name(n.strip()) for n in names if n and n.strip()]
    current = get_contact_email_tags(contact_id)
    added = [n for n in names if n not in current]
    removed = [n for n in current if n not in names]
    tag_ids = get_or_create_tag_ids('email', names)
    _replace_contact_tags_of_kind(contact_id, 'email', tag_ids)
    for name in added:
        log_history('contact', contact_id, user_id, 'update',
                     f'Dodano tag email „{name}” (zgoda marketingowa).', entry_type='tag_add')
    for name in removed:
        log_history('contact', contact_id, user_id, 'update',
                     f'Usunięto tag email „{name}” (wycofanie zgody).', entry_type='tag_remove')


def remove_all_contact_email_tags(contact_id: int, user_id: int | None = None,
                                   reason: str = 'Wypisano z newslettera (link unsubscribe).') -> None:
    current = get_contact_email_tags(contact_id)
    if not current:
        return
    _replace_contact_tags_of_kind(contact_id, 'email', [])
    for name in current:
        log_history('contact', contact_id, user_id, 'update',
                     f'Usunięto tag email „{name}” ({reason})', entry_type='tag_remove')


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
                name = normalize_tag_name(raw_name.strip())
                if not name:
                    continue
                cur.execute(
                    "SELECT id, name FROM crm_tags WHERE kind=%s AND name=%s",
                    (kind, name)
                )
                row = cur.fetchone()
                if row:
                    if row['name'] != name:
                        cur.execute("UPDATE crm_tags SET name=%s WHERE id=%s", (name, row['id']))
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
