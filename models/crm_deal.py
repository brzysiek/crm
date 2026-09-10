from database import get_db
from models.crm_notes import log_history, build_diff_summary
import models.gtd_context as gtd_context_model

STAGE_LABELS = {
    'new': 'Lead', 'in_progress': 'Kwalifikacja', 'won': 'Wygrany', 'in_delivery': 'W toku projektu',
    'completed': 'Zakończony', 'someday': 'Kiedyś', 'lost': 'Przegrany', 'unqualified': 'Niekwalifikowany',
}

# Kolejność etapów w pipeline — używana do sortowania listy dealów po etapie.
STAGE_ORDER = list(STAGE_LABELS.keys())

STAGE_BADGE_CLASSES = {
    'new': 'badge-yellow', 'in_progress': 'badge-blue', 'won': 'badge-green', 'in_delivery': 'badge-purple',
    'completed': 'badge-lime', 'someday': 'badge-gray', 'lost': 'badge-red', 'unqualified': 'badge-orange',
}

KANBAN_DEFAULT_HIDDEN_STAGES = ['completed', 'lost', 'unqualified', 'someday']

PROBABILITY_CHOICES = [5, 20, 40, 60, 80, 100]

# Etapy, dla których prawdopodobieństwo jest wymuszone i niezależne od wyboru użytkownika.
FORCED_PROBABILITY_BY_STAGE = {'won': 100, 'in_delivery': 100, 'completed': 100, 'lost': 0}

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
    'deal_type': 'Typ', 'probability': 'Prawdopodobieństwo',
    'start_date': 'Data rozpoczęcia', 'end_date': 'Data zakończenia', 'context_id': 'Kontekst',
}


def resolve_probability(stage: str, probability: int | None) -> int | None:
    """Dla wygranych/zakończonych/w toku wymusza 100%, dla przegranych 0% —
    niezależnie od tego, co wybrał użytkownik."""
    return FORCED_PROBABILITY_BY_STAGE.get(stage, probability)


def probability_row_class(stage: str, probability: int | None) -> str:
    """Klasa CSS pastelowego tła rzędu/kafelka: czerwień (0%) → zieleń (100%),
    fiolet dla nieustawionej wartości, ciemny bordowy dla przegranych."""
    if stage == 'lost':
        return 'prob-lost'
    if probability is None:
        return 'prob-none'
    nearest = min(PROBABILITY_CHOICES, key=lambda x: abs(x - probability))
    return f'prob-{nearest}'


def get_all_deals(sort: str = 'created_at', direction: str = 'desc',
                   search: str = None, stage: str | list[str] = None, deal_type: str = None,
                   company_id: int = None, contact_id: int = None,
                   context_ids: list[int] | None = None) -> list[dict]:
    allowed_sort = {'name', 'amount', 'stage', 'probability', 'start_date', 'end_date', 'created_at'}
    if sort not in allowed_sort:
        sort = 'created_at'
    direction = 'DESC' if str(direction).lower() == 'desc' else 'ASC'

    db = get_db()
    sql = ("SELECT d.*, co.name AS company_name, co.short_name AS company_short_name, "
           "ct.first_name AS contact_first_name, ct.last_name AS contact_last_name, "
           "gc.name AS context_name, gc.badge_color AS context_badge_color, gc.text_color AS context_text_color "
           "FROM crm_deals d "
           "LEFT JOIN crm_companies co ON co.id = d.company_id "
           "LEFT JOIN crm_contacts ct ON ct.id = d.contact_id "
           "LEFT JOIN gtd_contexts gc ON gc.id = d.context_id WHERE 1=1")
    params = []
    if stage:
        stages = [stage] if isinstance(stage, str) else list(stage)
        placeholders = ','.join(['%s'] * len(stages))
        sql += f" AND d.stage IN ({placeholders})"
        params.extend(stages)
    if deal_type:
        sql += " AND d.deal_type = %s"
        params.append(deal_type)
    if company_id:
        sql += " AND d.company_id = %s"
        params.append(company_id)
    if contact_id:
        sql += " AND d.contact_id = %s"
        params.append(contact_id)
    if context_ids is not None:
        # Sentinel 0 oznacza koszyk „Brak kontekstu” (d.context_id IS NULL).
        real_ids = [c for c in context_ids if c]
        conds = []
        if real_ids:
            placeholders = ','.join(['%s'] * len(real_ids))
            conds.append(f"d.context_id IN ({placeholders})")
            params.extend(real_ids)
        if 0 in context_ids:
            conds.append("d.context_id IS NULL")
        sql += f" AND ({' OR '.join(conds)})" if conds else " AND 1=0"
    if search:
        sql += " AND (d.name LIKE %s OR d.description LIKE %s OR co.name LIKE %s)"
        like = f"%{search}%"
        params.extend([like, like, like])

    if sort == 'stage':
        # Sortowanie po etapie w kolejności pipeline'u, w drugiej kolejności zawsze
        # po malejącym prawdopodobieństwie (niezależnie od kierunku sortowania etapu).
        stage_placeholders = ','.join(['%s'] * len(STAGE_ORDER))
        sql += f" ORDER BY FIELD(d.stage, {stage_placeholders}) {direction}, d.probability DESC, d.id DESC"
        params.extend(STAGE_ORDER)
    else:
        sql += f" ORDER BY d.{sort} {direction}, d.id DESC"

    with db.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def get_deal_by_id(deal_id: int) -> dict | None:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT d.*, co.name AS company_name, co.short_name AS company_short_name,
                      ct.first_name AS contact_first_name, ct.last_name AS contact_last_name,
                      gc.name AS context_name, gc.badge_color AS context_badge_color,
                      gc.text_color AS context_text_color
               FROM crm_deals d
               LEFT JOIN crm_companies co ON co.id = d.company_id
               LEFT JOIN crm_contacts ct ON ct.id = d.contact_id
               LEFT JOIN gtd_contexts gc ON gc.id = d.context_id
               WHERE d.id=%s""",
            (deal_id,)
        )
        return cur.fetchone()


def get_deals_by_ids(ids: list[int]) -> dict[int, dict]:
    if not ids:
        return {}
    db = get_db()
    placeholders = ','.join(['%s'] * len(ids))
    with db.cursor() as cur:
        cur.execute(
            f"""SELECT d.id, d.context_id, d.contact_id, d.company_id,
                      co.name AS company_name, co.short_name AS company_short_name,
                      ct.first_name AS contact_first_name, ct.last_name AS contact_last_name,
                      gc.name AS context_name, gc.badge_color AS context_badge_color,
                      gc.text_color AS context_text_color
               FROM crm_deals d
               LEFT JOIN crm_companies co ON co.id = d.company_id
               LEFT JOIN crm_contacts ct ON ct.id = d.contact_id
               LEFT JOIN gtd_contexts gc ON gc.id = d.context_id
               WHERE d.id IN ({placeholders})""",
            tuple(ids)
        )
        return {row['id']: row for row in cur.fetchall()}


def create_deal(data: dict, user_id: int | None) -> int:
    stage = data.get('stage', 'new')
    probability = resolve_probability(stage, data.get('probability'))
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                """INSERT INTO crm_deals
                   (name, description, amount, company_id, contact_id, stage, probability, deal_type,
                    start_date, end_date, owner_user_id, context_id)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    data['name'], data.get('description') or None, data.get('amount') or None,
                    data.get('company_id') or None, data.get('contact_id') or None,
                    stage, probability, data.get('deal_type', 'inne'), data.get('start_date') or None,
                    data.get('end_date') or None, data.get('owner_user_id') or None,
                    data.get('context_id') or None,
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
    stage = data.get('stage', 'new')
    probability = resolve_probability(stage, data.get('probability'))
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                """UPDATE crm_deals SET
                   name=%s, description=%s, amount=%s, company_id=%s, contact_id=%s,
                   stage=%s, probability=%s, deal_type=%s, start_date=%s, end_date=%s, owner_user_id=%s,
                   context_id=%s
                   WHERE id=%s""",
                (
                    data['name'], data.get('description') or None, data.get('amount') or None,
                    data.get('company_id') or None, data.get('contact_id') or None,
                    stage, probability, data.get('deal_type', 'inne'), data.get('start_date') or None,
                    data.get('end_date') or None, data.get('owner_user_id') or None,
                    data.get('context_id') or None,
                    deal_id,
                )
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    if old:
        context_names = {c['id']: c['name'] for c in gtd_context_model.get_all_contexts()}
        old_disp = dict(old)
        new_disp = dict(data)
        new_disp['probability'] = probability
        old_disp['stage'] = STAGE_LABELS.get(old.get('stage'), old.get('stage'))
        new_disp['stage'] = STAGE_LABELS.get(data.get('stage'), data.get('stage'))
        old_disp['deal_type'] = DEAL_TYPE_LABELS.get(old.get('deal_type'), old.get('deal_type'))
        new_disp['deal_type'] = DEAL_TYPE_LABELS.get(data.get('deal_type'), data.get('deal_type'))
        old_disp['probability'] = f"{old.get('probability')}%" if old.get('probability') is not None else None
        new_disp['probability'] = f"{probability}%" if probability is not None else None
        old_disp['context_id'] = f"@{context_names[old['context_id']]}" if old.get('context_id') in context_names else None
        new_disp['context_id'] = f"@{context_names[data['context_id']]}" if data.get('context_id') in context_names else None
        summary = build_diff_summary(old_disp, new_disp, FIELD_LABELS)
        if summary:
            log_history('deal', deal_id, user_id, 'update', summary)


def update_deal_probability(deal_id: int, probability: int | None, user_id: int | None) -> int | None:
    old = get_deal_by_id(deal_id)
    if not old:
        return None
    if old.get('stage') in FORCED_PROBABILITY_BY_STAGE:
        return old.get('probability')
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("UPDATE crm_deals SET probability=%s WHERE id=%s", (probability, deal_id))
        db.commit()
    except Exception:
        db.rollback()
        raise
    if old.get('probability') != probability:
        old_label = f"{old.get('probability')}%" if old.get('probability') is not None else '—'
        new_label = f"{probability}%" if probability is not None else '—'
        log_history('deal', deal_id, user_id, 'update',
                     f"Prawdopodobieństwo: „{old_label}” → „{new_label}”.")
    return probability


def update_deal_stage(deal_id: int, stage: str, user_id: int | None) -> int | None:
    old = get_deal_by_id(deal_id)
    if not old:
        return None
    probability = resolve_probability(stage, old.get('probability'))
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("UPDATE crm_deals SET stage=%s, probability=%s WHERE id=%s", (stage, probability, deal_id))
        db.commit()
    except Exception:
        db.rollback()
        raise
    if old.get('stage') != stage:
        log_history('deal', deal_id, user_id, 'update',
                     f"Etap: „{STAGE_LABELS.get(old.get('stage'), old.get('stage'))}” → „{STAGE_LABELS.get(stage, stage)}”.")
    return probability


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
