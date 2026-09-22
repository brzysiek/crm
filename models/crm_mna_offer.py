from datetime import date

from database import get_db
from models.crm_notes import log_history, build_diff_summary

REF_PREFIX = 'Ref: '

OFFER_TYPE_LABELS = {
    'for_sale': 'Na sprzedaż',
    'wanted': 'Poszukiwana',
}

OFFER_TYPE_BADGE_CLASSES = {
    'for_sale': 'badge-green',
    'wanted': 'badge-blue',
}

FIELD_LABELS = {
    'name': 'Nazwa', 'ref_number': 'Numer oferty', 'description': 'Opis', 'industry': 'Branża',
    'revenue': 'Obroty', 'ebitda': 'EBITDA', 'offer_type': 'Typ oferty',
    'added_date': 'Data dodania',
}

_SELECT_JOINS = (
    "SELECT o.*, "
    "tc.first_name AS target_contact_first_name, tc.last_name AS target_contact_last_name, "
    "tco.name AS target_company_name, tco.short_name AS target_company_short_name, "
    "sc.first_name AS source_contact_first_name, sc.last_name AS source_contact_last_name, "
    "sco.name AS source_company_name, sco.short_name AS source_company_short_name "
    "FROM crm_mna_offers o "
    "LEFT JOIN crm_contacts tc ON tc.id = o.target_contact_id "
    "LEFT JOIN crm_companies tco ON tco.id = o.target_company_id "
    "LEFT JOIN crm_contacts sc ON sc.id = o.source_contact_id "
    "LEFT JOIN crm_companies sco ON sco.id = o.source_company_id "
)


def get_all_mna_offers(offer_type: str = None, sort: str = 'created_at', direction: str = 'desc',
                        search: str = None) -> list[dict]:
    allowed_sort = {'name', 'industry', 'revenue', 'ebitda', 'created_at'}
    if sort not in allowed_sort:
        sort = 'created_at'
    direction = 'DESC' if str(direction).lower() == 'desc' else 'ASC'

    db = get_db()
    sql = _SELECT_JOINS + "WHERE o.deleted_at IS NULL"
    params = []
    if offer_type:
        sql += " AND o.offer_type = %s"
        params.append(offer_type)
    if search:
        sql += " AND (o.name LIKE %s OR o.ref_number LIKE %s OR o.description LIKE %s OR o.industry LIKE %s)"
        like = f"%{search}%"
        params.extend([like, like, like, like])
    sql += f" ORDER BY o.{sort} {direction}, o.id DESC"

    with db.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def get_mna_offer_by_id(offer_id: int) -> dict | None:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(_SELECT_JOINS + "WHERE o.id=%s", (offer_id,))
        return cur.fetchone()


def get_mna_offers_by_ids(ids: list[int]) -> dict[int, dict]:
    if not ids:
        return {}
    db = get_db()
    placeholders = ','.join(['%s'] * len(ids))
    with db.cursor() as cur:
        cur.execute(
            f"""SELECT o.id, o.name, o.offer_type,
                      (SELECT COUNT(*) FROM tasks t WHERE t.crm_mna_offer_id = o.id AND t.deleted_at IS NULL) AS task_total,
                      (SELECT COUNT(*) FROM tasks t WHERE t.crm_mna_offer_id = o.id AND t.deleted_at IS NULL AND t.status = 'done') AS task_done
               FROM crm_mna_offers o
               WHERE o.id IN ({placeholders})""",
            tuple(ids)
        )
        return {row['id']: row for row in cur.fetchall()}


def next_mna_offer_ref(on_date: date | None = None) -> str:
    """Kolejny numer oferty w formacie „Ref: <nr w miesiącu>/<miesiąc>/<rok>”.

    Numeracja zaczyna się od 1 w każdym miesiącu. Pod uwagę bierzemy również oferty
    zarchiwizowane, żeby ten sam numer nie został wydany dwa razy.
    """
    today = on_date or date.today()
    suffix = f"/{today.month:02d}/{today.year}"

    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT ref_number FROM crm_mna_offers WHERE ref_number LIKE %s", (f"%{suffix}",))
        rows = cur.fetchall()

    used = []
    for row in rows:
        head = row['ref_number'][:-len(suffix)].removeprefix(REF_PREFIX).strip()
        if head.isdigit():
            used.append(int(head))
    return f"{REF_PREFIX}{max(used) + 1 if used else 1}{suffix}"


def create_mna_offer(data: dict, user_id: int | None) -> int:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                """INSERT INTO crm_mna_offers
                   (name, ref_number, description, industry, revenue, ebitda, offer_type, added_date,
                    target_contact_id, target_company_id, source_contact_id, source_company_id, owner_user_id)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    data['name'], (data.get('ref_number') or '').strip() or next_mna_offer_ref(),
                    data.get('description') or None, data.get('industry') or None,
                    data.get('revenue') or None, data.get('ebitda') or None,
                    data.get('offer_type', 'for_sale'), data.get('added_date') or None,
                    data.get('target_contact_id') or None, data.get('target_company_id') or None,
                    data.get('source_contact_id') or None, data.get('source_company_id') or None,
                    data.get('owner_user_id') or None,
                )
            )
        db.commit()
        offer_id = cur.lastrowid
    except Exception:
        db.rollback()
        raise
    log_history('mna_offer', offer_id, user_id, 'create', f"Utworzono ofertę M&A „{data['name']}”.")
    return offer_id


def update_mna_offer(offer_id: int, data: dict, user_id: int | None) -> None:
    old = get_mna_offer_by_id(offer_id)
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                """UPDATE crm_mna_offers SET
                   name=%s, ref_number=%s, description=%s, industry=%s, revenue=%s, ebitda=%s,
                   offer_type=%s, added_date=%s,
                   target_contact_id=%s, target_company_id=%s, source_contact_id=%s, source_company_id=%s,
                   owner_user_id=%s
                   WHERE id=%s""",
                (
                    data['name'], (data.get('ref_number') or '').strip() or None,
                    data.get('description') or None, data.get('industry') or None,
                    data.get('revenue') or None, data.get('ebitda') or None,
                    data.get('offer_type', 'for_sale'), data.get('added_date') or None,
                    data.get('target_contact_id') or None, data.get('target_company_id') or None,
                    data.get('source_contact_id') or None, data.get('source_company_id') or None,
                    data.get('owner_user_id') or None,
                    offer_id,
                )
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    if old:
        old_disp = dict(old)
        new_disp = dict(data)
        old_disp['offer_type'] = OFFER_TYPE_LABELS.get(old.get('offer_type'), old.get('offer_type'))
        new_disp['offer_type'] = OFFER_TYPE_LABELS.get(data.get('offer_type'), data.get('offer_type'))
        summary = build_diff_summary(old_disp, new_disp, FIELD_LABELS)
        if summary:
            log_history('mna_offer', offer_id, user_id, 'update', summary)


def delete_mna_offer(offer_id: int, user_id: int | None) -> None:
    """Miękkie usunięcie — oferta trafia do Archiwum, skąd można ją przywrócić lub skasować trwale."""
    offer = get_mna_offer_by_id(offer_id)
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("UPDATE crm_mna_offers SET deleted_at=NOW() WHERE id=%s", (offer_id,))
        db.commit()
    except Exception:
        db.rollback()
        raise
    if offer:
        log_history('mna_offer', offer_id, user_id, 'archive', f"Zarchiwizowano ofertę M&A „{offer['name']}”.")


def restore_mna_offer(offer_id: int, user_id: int | None) -> None:
    offer = get_mna_offer_by_id(offer_id)
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("UPDATE crm_mna_offers SET deleted_at=NULL WHERE id=%s", (offer_id,))
        db.commit()
    except Exception:
        db.rollback()
        raise
    if offer:
        log_history('mna_offer', offer_id, user_id, 'restore', f"Przywrócono ofertę M&A „{offer['name']}” z archiwum.")


def permanently_delete_mna_offer(offer_id: int, user_id: int | None) -> None:
    """Trwałe skasowanie — działa niezależnie od tego, czy oferta była wcześniej zarchiwizowana."""
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("DELETE FROM crm_mna_offers WHERE id=%s", (offer_id,))
        db.commit()
    except Exception:
        db.rollback()
        raise


def get_deleted_mna_offers(limit: int = 300) -> list[dict]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            _SELECT_JOINS + "WHERE o.deleted_at IS NOT NULL ORDER BY o.deleted_at DESC, o.id DESC LIMIT %s",
            (limit,)
        )
        return cur.fetchall()
