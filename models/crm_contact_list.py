"""Listy kontaktów — nazwane grupy definiowane w Ustawieniach.

Kontakt może być na wielu listach naraz (M:N przez crm_contact_list_members),
w odróżnieniu od kontekstu GTD, którego kontakt ma najwyżej jeden. Każde
dopisanie i wypisanie trafia do historii kontaktu — tak samo jak przy tagach
email, bo to zmiana przynależności, którą trzeba móc odtworzyć.
"""
from database import get_db
from models.crm_notes import log_history

DEFAULT_BADGE_COLOR = '#3B82F6'
DEFAULT_TEXT_COLOR = '#1F2937'


def get_all_lists(with_counts: bool = False) -> list[dict]:
    """Listy w kolejności ręcznej (sort_order), potem alfabetycznie.

    `with_counts=True` dokłada `member_count` — używane w Ustawieniach i w menu
    bocznym, gdzie liczba obok nazwy mówi, czy lista w ogóle jest zapełniona.
    Liczone są tylko kontakty nieprzeniesione do archiwum.
    """
    count_col = (", (SELECT COUNT(*) FROM crm_contact_list_members m "
                 "   JOIN crm_contacts ct ON ct.id = m.contact_id "
                 "   WHERE m.list_id = l.id AND ct.archived_at IS NULL) AS member_count"
                 ) if with_counts else ""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(f"SELECT l.*{count_col} FROM crm_contact_lists l ORDER BY l.sort_order, l.name")
        return cur.fetchall()


def get_list(list_id: int) -> dict | None:
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM crm_contact_lists WHERE id=%s", (list_id,))
        return cur.fetchone()


def create_list(name: str, badge_color: str = DEFAULT_BADGE_COLOR,
                 text_color: str = DEFAULT_TEXT_COLOR, description: str = None,
                 sort_order: int = 0) -> int:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                """INSERT INTO crm_contact_lists (name, badge_color, text_color, description, sort_order)
                   VALUES (%s,%s,%s,%s,%s)""",
                (name, badge_color, text_color, description or None, sort_order)
            )
            new_id = cur.lastrowid
        db.commit()
        return new_id
    except Exception:
        db.rollback()
        raise


def update_list(list_id: int, name: str, badge_color: str, text_color: str,
                 description: str = None, sort_order: int = 0) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                """UPDATE crm_contact_lists
                      SET name=%s, badge_color=%s, text_color=%s, description=%s, sort_order=%s
                    WHERE id=%s""",
                (name, badge_color, text_color, description or None, sort_order, list_id)
            )
        db.commit()
    except Exception:
        db.rollback()
        raise


def delete_list(list_id: int) -> None:
    """Usuwa listę; przynależności znikają kaskadą, same kontakty zostają."""
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("DELETE FROM crm_contact_lists WHERE id=%s", (list_id,))
        db.commit()
    except Exception:
        db.rollback()
        raise


def get_contact_lists(contact_id: int) -> list[dict]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT l.* FROM crm_contact_lists l
               JOIN crm_contact_list_members m ON m.list_id = l.id
               WHERE m.contact_id=%s ORDER BY l.sort_order, l.name""",
            (contact_id,)
        )
        return cur.fetchall()


def get_contact_list_ids(contact_id: int) -> list[int]:
    return [row['id'] for row in get_contact_lists(contact_id)]


def get_lists_for_contacts(contact_ids: list[int]) -> dict[int, list[dict]]:
    """Listy dla wielu kontaktów naraz — jedno zapytanie zamiast N na widoku listy."""
    if not contact_ids:
        return {}
    placeholders = ','.join(['%s'] * len(contact_ids))
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            f"""SELECT m.contact_id, l.id, l.name, l.badge_color, l.text_color
                  FROM crm_contact_list_members m
                  JOIN crm_contact_lists l ON l.id = m.list_id
                 WHERE m.contact_id IN ({placeholders})
                 ORDER BY l.sort_order, l.name""",
            contact_ids
        )
        rows = cur.fetchall()
    result: dict[int, list[dict]] = {}
    for row in rows:
        result.setdefault(row['contact_id'], []).append(row)
    return result


def set_contact_lists(contact_id: int, list_ids: list[int], user_id: int | None) -> None:
    """Ustawia komplet list kontaktu — to, czego nie ma na liście, zostaje odpięte."""
    wanted = {int(i) for i in list_ids if str(i).isdigit() or isinstance(i, int)}
    current = {row['id']: row['name'] for row in get_contact_lists(contact_id)}
    if wanted == set(current):
        return

    names = {row['id']: row['name'] for row in get_all_lists()}
    wanted = {i for i in wanted if i in names}          # ignoruj listy, które zniknęły
    added = wanted - set(current)
    removed = set(current) - wanted

    db = get_db()
    try:
        with db.cursor() as cur:
            if removed:
                placeholders = ','.join(['%s'] * len(removed))
                cur.execute(
                    f"DELETE FROM crm_contact_list_members WHERE contact_id=%s "
                    f"AND list_id IN ({placeholders})",
                    [contact_id] + sorted(removed)
                )
            for list_id in sorted(added):
                cur.execute(
                    "INSERT IGNORE INTO crm_contact_list_members (list_id, contact_id) VALUES (%s,%s)",
                    (list_id, contact_id)
                )
        db.commit()
    except Exception:
        db.rollback()
        raise

    for list_id in sorted(added):
        log_history('contact', contact_id, user_id, 'update',
                     f'Dodano do listy „{names[list_id]}”.', entry_type='list_add')
    for list_id in sorted(removed):
        log_history('contact', contact_id, user_id, 'update',
                     f'Usunięto z listy „{current[list_id]}”.', entry_type='list_remove')


def add_contacts_to_list(list_id: int, contact_ids: list[int], user_id: int | None) -> int:
    """Hurtowe dopisanie zaznaczonych kontaktów do listy. Zwraca liczbę faktycznie
    dodanych — kontakty już będące na liście nie są liczone ani logowane drugi raz."""
    target = get_list(list_id)
    if not target or not contact_ids:
        return 0
    db = get_db()
    added = []
    try:
        with db.cursor() as cur:
            for contact_id in contact_ids:
                cur.execute(
                    "INSERT IGNORE INTO crm_contact_list_members (list_id, contact_id) VALUES (%s,%s)",
                    (list_id, contact_id)
                )
                if cur.rowcount:
                    added.append(contact_id)
        db.commit()
    except Exception:
        db.rollback()
        raise
    for contact_id in added:
        log_history('contact', contact_id, user_id, 'update',
                     f'Dodano do listy „{target["name"]}”.', entry_type='list_add')
    return len(added)


def remove_contacts_from_list(list_id: int, contact_ids: list[int], user_id: int | None) -> int:
    target = get_list(list_id)
    if not target or not contact_ids:
        return 0
    placeholders = ','.join(['%s'] * len(contact_ids))
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                f"SELECT contact_id FROM crm_contact_list_members "
                f"WHERE list_id=%s AND contact_id IN ({placeholders})",
                [list_id] + list(contact_ids)
            )
            removed = [row['contact_id'] for row in cur.fetchall()]
            if removed:
                cur.execute(
                    f"DELETE FROM crm_contact_list_members WHERE list_id=%s "
                    f"AND contact_id IN ({placeholders})",
                    [list_id] + list(contact_ids)
                )
        db.commit()
    except Exception:
        db.rollback()
        raise
    for contact_id in removed:
        log_history('contact', contact_id, user_id, 'update',
                     f'Usunięto z listy „{target["name"]}”.', entry_type='list_remove')
    return len(removed)


def merge_list_memberships(primary_id: int, secondary_id: int) -> None:
    """Przy scalaniu duplikatów kontakt docelowy przejmuje listy duplikatu.
    INSERT IGNORE, bo obie strony mogą już być na tej samej liście."""
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                """INSERT IGNORE INTO crm_contact_list_members (list_id, contact_id)
                   SELECT list_id, %s FROM crm_contact_list_members WHERE contact_id=%s""",
                (primary_id, secondary_id)
            )
            cur.execute("DELETE FROM crm_contact_list_members WHERE contact_id=%s", (secondary_id,))
        db.commit()
    except Exception:
        db.rollback()
        raise
