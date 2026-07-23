from database import get_db
from models.crm_notes import log_history, build_diff_summary

STAGE_LABELS = {
    'new': 'Lead', 'in_progress': 'Kwalifikacja', 'won': 'Wygrany', 'in_delivery': 'W toku projektu',
    'completed': 'Zakończony', 'someday': 'Kiedyś', 'lost': 'Przegrany', 'unqualified': 'Niekwalifikowany',
}

STAGE_BADGE_CLASSES = {
    'new': 'badge-yellow', 'in_progress': 'badge-blue', 'won': 'badge-green', 'in_delivery': 'badge-purple',
    'completed': 'badge-lime', 'someday': 'badge-gray', 'lost': 'badge-red', 'unqualified': 'badge-orange',
}

KANBAN_DEFAULT_HIDDEN_STAGES = ['completed', 'lost', 'unqualified']

DEAL_TYPE_LABELS = {
    'szkolenie': 'Szkolenie', 'ma': 'M&A', 'warsztaty': 'Warsztaty',
    'prowizja': 'Prowizja', 'partnerstwo': 'Partnerstwo', 'inne': 'Inne',
}

DEAL_TYPE_BADGE_CLASSES = {
    'szkolenie': 'badge-blue', 'ma': 'badge-purple', 'warsztaty': 'badge-green',
    'prowizja': 'badge-yellow', 'partnerstwo': 'badge-lime', 'inne': 'badge-gray',
}

FIELD_LABELS = {
    'name': 'Nazwa', 'description': 'Opis', 'amount': 'Kwota', 'stage': 'Etap',
    'deal_type': 'Typ', 'start_date': 'Data rozpoczęcia', 'end_date': 'Data zakończenia',
}


def get_all_deals(sort: str = 'created_at', direction: str = 'desc',
                   search: str = None, stage: str = None, deal_type: str = None,
                   company_id: int = None, contact_id: int = None) -> list[dict]:
    allowed_sort = {'name', 'amount', 'stage', 'start_date', 'end_date', 'created_at'}
    if sort not in allowed_sort:
        sort = 'created_at'
    direction = 'DESC' if str(direction).lower() == 'desc' else 'ASC'

    db = get_db()
    sql = ("SELECT d.*, co.name AS company_name, co.short_name AS company_short_name, "
           "ct.first_name AS contact_first_name, ct.last_name AS contact_last_name "
           "FROM crm_deals d "
           "LEFT JOIN crm_companies co ON co.id = d.company_id "
           "LEFT JOIN crm_contacts ct ON ct.id = d.contact_id WHERE 1=1")
    params = []
    if stage:
        sql += " AND d.stage = %s"
        params.append(stage)
    if deal_type:
        sql += " AND d.deal_type = %s"
        params.append(deal_type)
    if company_id:
        sql += " AND d.company_id = %s"
        params.append(company_id)
    if contact_id:
        sql += " AND d.contact_id = %s"
        params.append(contact_id)
    if search:
        sql += " AND (d.name LIKE %s OR d.description LIKE %s OR co.name LIKE %s)"
        like = f"%{search}%"
        params.extend([like, like, like])
    sql += f" ORDER BY d.{sort} {direction}, d.id DESC"

    with db.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def get_deal_by_id(deal_id: int) -> dict | None:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT d.*, co.name AS company_name, co.short_name AS company_short_name,
                      ct.first_name AS contact_first_name, ct.last_name AS contact_last_name
               FROM crm_deals d
               LEFT JOIN crm_companies co ON co.id = d.company_id
               LEFT JOIN crm_contacts ct ON ct.id = d.contact_id
               WHERE d.id=%s""",
            (deal_id,)
        )
        return cur.fetchone()


def create_deal(data: dict, user_id: int | None) -> int:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                """INSERT INTO crm_deals
                   (name, description, amount, company_id, contact_id, stage, deal_type,
                    start_date, end_date, owner_user_id)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    data['name'], data.get('description') or None, data.get('amount') or None,
                    data.get('company_id') or None, data.get('contact_id') or None,
                    data.get('stage', 'new'), data.get('deal_type', 'inne'), data.get('start_date') or None,
                    data.get('end_date') or None, data.get('owner_user_id') or None,
                )
            )
        db.commit()
        deal_id = cur.lastrowid
    except Exception:
        db.rollback()
        raise
    log_history('deal', deal_id, user_id, 'create', f"Utworzono deal „{data['name']}”.")
    return deal_id


def update_deal(deal_id: int, data: dict, user_id: int | None) -> None:
    old = get_deal_by_id(deal_id)
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                """UPDATE crm_deals SET
                   name=%s, description=%s, amount=%s, company_id=%s, contact_id=%s,
                   stage=%s, deal_type=%s, start_date=%s, end_date=%s, owner_user_id=%s
                   WHERE id=%s""",
                (
                    data['name'], data.get('description') or None, data.get('amount') or None,
                    data.get('company_id') or None, data.get('contact_id') or None,
                    data.get('stage', 'new'), data.get('deal_type', 'inne'), data.get('start_date') or None,
                    data.get('end_date') or None, data.get('owner_user_id') or None,
                    deal_id,
                )
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    if old:
        old_disp = dict(old)
        new_disp = dict(data)
        old_disp['stage'] = STAGE_LABELS.get(old.get('stage'), old.get('stage'))
        new_disp['stage'] = STAGE_LABELS.get(data.get('stage'), data.get('stage'))
        old_disp['deal_type'] = DEAL_TYPE_LABELS.get(old.get('deal_type'), old.get('deal_type'))
        new_disp['deal_type'] = DEAL_TYPE_LABELS.get(data.get('deal_type'), data.get('deal_type'))
        summary = build_diff_summary(old_disp, new_disp, FIELD_LABELS)
        if summary:
            log_history('deal', deal_id, user_id, 'update', summary)


def delete_deal(deal_id: int, user_id: int | None) -> None:
    deal = get_deal_by_id(deal_id)
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("DELETE FROM crm_deals WHERE id=%s", (deal_id,))
        db.commit()
    except Exception:
        db.rollback()
        raise
    if deal:
        log_history('deal', deal_id, user_id, 'delete', f"Usunięto deal „{deal['name']}”.")
