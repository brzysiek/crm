from database import get_db
from models.crm_notes import log_history, build_diff_summary

STAGE_LABELS = {
    'long_list': 'Long lista', 'short_list': 'Short lista', 'kontakt_nawiazany': 'Kontakt nawiązany',
    'nda': 'NDA', 'ioi': 'IOI', 'due_diligence': 'Due diligence', 'loi': 'LOI',
    'zamkniety': 'Zamknięty', 'przegrany': 'Przegrany',
}

STAGE_ORDER = list(STAGE_LABELS.keys())

STAGE_BADGE_CLASSES = {
    'long_list': 'badge-gray', 'short_list': 'badge-blue', 'kontakt_nawiazany': 'badge-yellow',
    'nda': 'badge-purple', 'ioi': 'badge-lime', 'due_diligence': 'badge-orange',
    'loi': 'badge-blue', 'zamkniety': 'badge-green', 'przegrany': 'badge-red',
}

LIST_TYPE_LABELS = {'long_list': 'Long lista', 'short_list': 'Short lista'}

INTEREST_STATUS_LABELS = {
    'unknown': 'Nieznany', 'interested': 'Zainteresowany', 'not_interested': 'Niezainteresowany',
}

FIELD_LABELS = {
    'name': 'Nazwa', 'description': 'Opis', 'stage': 'Etap', 'amount': 'Kwota',
    'start_date': 'Data rozpoczęcia', 'end_date': 'Data zakończenia', 'offer_id': 'Oferta M&A',
}


def get_all_mna_deals(sort: str = 'created_at', direction: str = 'desc',
                       search: str = None, stage: str | list[str] = None) -> list[dict]:
    allowed_sort = {'name', 'amount', 'stage', 'start_date', 'end_date', 'created_at'}
    if sort not in allowed_sort:
        sort = 'created_at'
    direction = 'DESC' if str(direction).lower() == 'desc' else 'ASC'

    db = get_db()
    sql = ("SELECT d.*, o.name AS offer_name, "
           "(SELECT COUNT(*) FROM mna_deal_targets dt WHERE dt.deal_id=d.id AND dt.list_type='long_list') AS long_list_count, "
           "(SELECT COUNT(*) FROM mna_deal_targets dt WHERE dt.deal_id=d.id AND dt.list_type='short_list') AS short_list_count "
           "FROM mna_deals d LEFT JOIN crm_mna_offers o ON o.id = d.offer_id "
           "WHERE d.archived_at IS NULL")
    params = []
    if stage:
        stages = [stage] if isinstance(stage, str) else list(stage)
        placeholders = ','.join(['%s'] * len(stages))
        sql += f" AND d.stage IN ({placeholders})"
        params.extend(stages)
    if search:
        sql += " AND (d.name LIKE %s OR d.description LIKE %s)"
        like = f"%{search}%"
        params.extend([like, like])

    if sort == 'stage':
        stage_placeholders = ','.join(['%s'] * len(STAGE_ORDER))
        sql += f" ORDER BY FIELD(d.stage, {stage_placeholders}) {direction}, d.id DESC"
        params.extend(STAGE_ORDER)
    else:
        sql += f" ORDER BY d.{sort} {direction}, d.id DESC"

    with db.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def get_mna_deal_by_id(deal_id: int) -> dict | None:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT d.*, o.name AS offer_name,
                      COALESCE(oc.short_name, oc.name) AS offer_company_name
               FROM mna_deals d
               LEFT JOIN crm_mna_offers o ON o.id = d.offer_id
               LEFT JOIN crm_companies oc ON oc.id = o.target_company_id
               WHERE d.id=%s""",
            (deal_id,)
        )
        return cur.fetchone()


def create_mna_deal(data: dict, user_id: int | None) -> int:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                """INSERT INTO mna_deals
                   (name, description, offer_id, stage, amount, start_date, end_date, owner_user_id)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    data['name'], data.get('description') or None, data.get('offer_id') or None,
                    data.get('stage', 'long_list'), data.get('amount') or None,
                    data.get('start_date') or None, data.get('end_date') or None,
                    data.get('owner_user_id') or None,
                )
            )
        db.commit()
        deal_id = cur.lastrowid
    except Exception:
        db.rollback()
        raise
    log_history('mna_deal', deal_id, user_id, 'create', f"Utworzono deal „{data['name']}”.")
    return deal_id


def update_mna_deal(deal_id: int, data: dict, user_id: int | None) -> None:
    old = get_mna_deal_by_id(deal_id)
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                """UPDATE mna_deals SET
                   name=%s, description=%s, offer_id=%s, stage=%s, amount=%s,
                   start_date=%s, end_date=%s, owner_user_id=%s
                   WHERE id=%s""",
                (
                    data['name'], data.get('description') or None, data.get('offer_id') or None,
                    data.get('stage', 'long_list'), data.get('amount') or None,
                    data.get('start_date') or None, data.get('end_date') or None,
                    data.get('owner_user_id') or None,
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
        summary = build_diff_summary(old_disp, new_disp, FIELD_LABELS)
        if summary:
            log_history('mna_deal', deal_id, user_id, 'update', summary)


def update_mna_deal_stage(deal_id: int, stage: str, user_id: int | None) -> None:
    old = get_mna_deal_by_id(deal_id)
    if not old:
        return
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("UPDATE mna_deals SET stage=%s WHERE id=%s", (stage, deal_id))
        db.commit()
    except Exception:
        db.rollback()
        raise
    if old.get('stage') != stage:
        log_history('mna_deal', deal_id, user_id, 'update',
                    f"Etap: „{STAGE_LABELS.get(old.get('stage'), old.get('stage'))}” → „{STAGE_LABELS.get(stage, stage)}”.")


def delete_mna_deal(deal_id: int, user_id: int | None) -> None:
    """Miękkie usunięcie — deal trafia do archiwum, skąd można go przywrócić."""
    deal = get_mna_deal_by_id(deal_id)
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("UPDATE mna_deals SET archived_at=NOW() WHERE id=%s", (deal_id,))
        db.commit()
    except Exception:
        db.rollback()
        raise
    if deal:
        log_history('mna_deal', deal_id, user_id, 'archive', f"Zarchiwizowano deal „{deal['name']}”.")


def restore_mna_deal(deal_id: int, user_id: int | None) -> None:
    deal = get_mna_deal_by_id(deal_id)
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("UPDATE mna_deals SET archived_at=NULL WHERE id=%s", (deal_id,))
        db.commit()
    except Exception:
        db.rollback()
        raise
    if deal:
        log_history('mna_deal', deal_id, user_id, 'restore', f"Przywrócono deal „{deal['name']}” z archiwum.")


# ── Long lista / short lista (mna_deal_targets) ─────────────────────────────

def get_targets_for_deal(deal_id: int, list_type: str = None) -> list[dict]:
    db = get_db()
    sql = ("SELECT dt.*, "
           "co.name AS company_name, co.short_name AS company_short_name, co.city AS company_city, "
           "ct.first_name AS contact_first_name, ct.last_name AS contact_last_name, "
           "ct.email AS contact_email, ct.phone AS contact_phone, ct.position AS contact_position "
           "FROM mna_deal_targets dt "
           "LEFT JOIN mna_companies co ON co.id = dt.company_id "
           "LEFT JOIN mna_contacts ct ON ct.id = dt.contact_id "
           "WHERE dt.deal_id = %s")
    params = [deal_id]
    if list_type:
        sql += " AND dt.list_type = %s"
        params.append(list_type)
    sql += " ORDER BY dt.is_valuable DESC, dt.sort_order ASC, dt.id ASC"
    with db.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def get_target_by_id(target_id: int) -> dict | None:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT dt.*, co.name AS company_name, ct.first_name AS contact_first_name,
                      ct.last_name AS contact_last_name
               FROM mna_deal_targets dt
               LEFT JOIN mna_companies co ON co.id = dt.company_id
               LEFT JOIN mna_contacts ct ON ct.id = dt.contact_id
               WHERE dt.id=%s""",
            (target_id,)
        )
        return cur.fetchone()


def _target_label(target: dict) -> str:
    if target.get('contact_first_name'):
        return f"{target['contact_first_name']} {target['contact_last_name']}"
    return target.get('company_name') or f"#{target['id']}"


def add_target(deal_id: int, company_id: int | None, contact_id: int | None,
                list_type: str, user_id: int | None) -> int:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                """INSERT INTO mna_deal_targets (deal_id, company_id, contact_id, list_type, added_by)
                   VALUES (%s,%s,%s,%s,%s)""",
                (deal_id, company_id or None, contact_id or None, list_type, user_id)
            )
        db.commit()
        target_id = cur.lastrowid
    except Exception:
        db.rollback()
        raise
    target = get_target_by_id(target_id)
    log_history('mna_deal', deal_id, user_id, 'update',
                f"Dodano „{_target_label(target)}” do listy: {LIST_TYPE_LABELS.get(list_type, list_type)}.")
    return target_id


def remove_target(target_id: int, user_id: int | None) -> None:
    target = get_target_by_id(target_id)
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("DELETE FROM mna_deal_targets WHERE id=%s", (target_id,))
        db.commit()
    except Exception:
        db.rollback()
        raise
    if target:
        log_history('mna_deal', target['deal_id'], user_id, 'update',
                    f"Usunięto „{_target_label(target)}” z listy.")


def move_target_list(target_id: int, list_type: str, user_id: int | None) -> None:
    target = get_target_by_id(target_id)
    if not target:
        return
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("UPDATE mna_deal_targets SET list_type=%s WHERE id=%s", (list_type, target_id))
        db.commit()
    except Exception:
        db.rollback()
        raise
    if target.get('list_type') != list_type:
        log_history('mna_deal', target['deal_id'], user_id, 'update',
                    f"„{_target_label(target)}”: {LIST_TYPE_LABELS.get(target.get('list_type'), target.get('list_type'))} "
                    f"→ {LIST_TYPE_LABELS.get(list_type, list_type)}.")


def set_target_interest(target_id: int, interest_status: str, user_id: int | None) -> None:
    target = get_target_by_id(target_id)
    if not target:
        return
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("UPDATE mna_deal_targets SET interest_status=%s WHERE id=%s", (interest_status, target_id))
        db.commit()
    except Exception:
        db.rollback()
        raise
    if target.get('interest_status') != interest_status:
        log_history('mna_deal', target['deal_id'], user_id, 'update',
                    f"„{_target_label(target)}”: zainteresowanie → "
                    f"{INTEREST_STATUS_LABELS.get(interest_status, interest_status)}.")


def set_target_valuable(target_id: int, is_valuable: bool, user_id: int | None) -> None:
    target = get_target_by_id(target_id)
    if not target:
        return
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("UPDATE mna_deal_targets SET is_valuable=%s WHERE id=%s",
                        (1 if is_valuable else 0, target_id))
        db.commit()
    except Exception:
        db.rollback()
        raise
    if bool(target.get('is_valuable')) != bool(is_valuable):
        log_history('mna_deal', target['deal_id'], user_id, 'update',
                    f"„{_target_label(target)}”: oznaczono jako "
                    f"{'wartościowy' if is_valuable else 'niewartościowy'}.")


def set_target_score(target_id: int, score: int | None, user_id: int | None) -> None:
    target = get_target_by_id(target_id)
    if not target:
        return
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("UPDATE mna_deal_targets SET score=%s WHERE id=%s", (score, target_id))
        db.commit()
    except Exception:
        db.rollback()
        raise
    if target.get('score') != score:
        log_history('mna_deal', target['deal_id'], user_id, 'update',
                    f"„{_target_label(target)}”: scoring → {score if score is not None else '—'}.")


def reorder_targets(deal_id: int, ordered_target_ids: list[int]) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            for position, target_id in enumerate(ordered_target_ids):
                cur.execute("UPDATE mna_deal_targets SET sort_order=%s WHERE id=%s AND deal_id=%s",
                            (position, target_id, deal_id))
        db.commit()
    except Exception:
        db.rollback()
        raise


def get_deals_for_company(company_id: int) -> list[dict]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT dt.*, d.name AS deal_name, d.stage AS deal_stage
               FROM mna_deal_targets dt JOIN mna_deals d ON d.id = dt.deal_id
               WHERE dt.company_id=%s AND d.archived_at IS NULL
               ORDER BY dt.created_at DESC""",
            (company_id,)
        )
        return cur.fetchall()


def get_deals_for_contact(contact_id: int) -> list[dict]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT dt.*, d.name AS deal_name, d.stage AS deal_stage
               FROM mna_deal_targets dt JOIN mna_deals d ON d.id = dt.deal_id
               WHERE dt.contact_id=%s AND d.archived_at IS NULL
               ORDER BY dt.created_at DESC""",
            (contact_id,)
        )
        return cur.fetchall()


# ---------------------------------------------------------------------------
# Widok roboczy long/short listy — filtrowanie, sortowanie i pola robocze
# ---------------------------------------------------------------------------

TARGET_SORTS = {
    'score': 'dt.score',
    'name': 'COALESCE(co.short_name, co.name, ct.last_name)',
    'city': 'co.city',
    'interest': 'dt.interest_status',
    'contacted': 'dt.contacted_at',
    'added': 'dt.created_at',
}

#: Sortowania, przy których puste wartości mają lądować na końcu niezależnie od kierunku.
_NULLS_LAST = ('score', 'city', 'contacted')


def _targets_order_by(sort: str, direction: str) -> str:
    column = TARGET_SORTS.get(sort, TARGET_SORTS['score'])
    direction = 'ASC' if str(direction).lower() == 'asc' else 'DESC'
    nulls_last = f"({column} IS NULL), " if sort in _NULLS_LAST else ''
    return f" ORDER BY dt.is_valuable DESC, {nulls_last}{column} {direction}, dt.id ASC"


def get_deal_targets(deal_id: int, list_type: str = 'long_list', search: str = None,
                     tag: str = None, interest: str = None, only_valuable: bool = False,
                     min_score: int = None, sort: str = 'score', direction: str = 'desc') -> list[dict]:
    """Pozycje jednej listy deala wraz z danymi firmy/kontaktu i tagami.

    Tagi dociągamy osobnym zapytaniem, a nie przez GROUP_CONCAT — inaczej złączenie
    tagów firmy i kontaktu wymusza GROUP BY na wszystkich kolumnach.
    """
    sql = (
        "SELECT dt.*, "
        "co.name AS company_name, co.short_name AS company_short_name, co.city AS company_city, "
        "co.voivodeship AS company_voivodeship, co.website AS company_website, "
        "co.linkedin_url AS company_linkedin, co.email AS company_email, co.phone AS company_phone, "
        "co.short_description AS company_short_description, co.nip AS company_nip, "
        "ct.first_name AS contact_first_name, ct.last_name AS contact_last_name, "
        "ct.email AS contact_email, ct.phone AS contact_phone, ct.position AS contact_position, "
        "ct.linkedin_url AS contact_linkedin "
        "FROM mna_deal_targets dt "
        "LEFT JOIN mna_companies co ON co.id = dt.company_id "
        "LEFT JOIN mna_contacts ct ON ct.id = dt.contact_id "
        "WHERE dt.deal_id = %s AND dt.list_type = %s"
    )
    params = [deal_id, list_type]

    if search:
        like = f"%{search}%"
        sql += (" AND (co.name LIKE %s OR co.short_name LIKE %s OR co.city LIKE %s OR co.nip LIKE %s"
                " OR ct.first_name LIKE %s OR ct.last_name LIKE %s OR dt.note LIKE %s)")
        params.extend([like] * 7)
    if tag:
        sql += (" AND (dt.company_id IN (SELECT mct.company_id FROM mna_company_tags mct"
                " JOIN mna_tags t ON t.id = mct.tag_id WHERE t.name = %s)"
                " OR dt.contact_id IN (SELECT mtt.contact_id FROM mna_contact_tags mtt"
                " JOIN mna_tags t ON t.id = mtt.tag_id WHERE t.name = %s))")
        params.extend([tag, tag])
    if interest:
        sql += " AND dt.interest_status = %s"
        params.append(interest)
    if only_valuable:
        sql += " AND dt.is_valuable = 1"
    if min_score is not None:
        sql += " AND dt.score >= %s"
        params.append(min_score)

    sql += _targets_order_by(sort, direction)

    db = get_db()
    with db.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

    rows = [dict(r) for r in rows]
    tags = _tags_for_targets(rows)
    for row in rows:
        row['tags'] = tags.get(('company', row['company_id']), []) + tags.get(('contact', row['contact_id']), [])
    return rows


def _tags_for_targets(rows: list[dict]) -> dict[tuple, list[str]]:
    company_ids = [r['company_id'] for r in rows if r.get('company_id')]
    contact_ids = [r['contact_id'] for r in rows if r.get('contact_id')]
    result: dict[tuple, list[str]] = {}
    db = get_db()
    with db.cursor() as cur:
        if company_ids:
            marks = ','.join(['%s'] * len(company_ids))
            cur.execute(
                f"""SELECT mct.company_id AS owner_id, t.name FROM mna_company_tags mct
                    JOIN mna_tags t ON t.id = mct.tag_id
                    WHERE mct.company_id IN ({marks}) ORDER BY t.name""",
                tuple(company_ids))
            for row in cur.fetchall():
                result.setdefault(('company', row['owner_id']), []).append(row['name'])
        if contact_ids:
            marks = ','.join(['%s'] * len(contact_ids))
            cur.execute(
                f"""SELECT mtt.contact_id AS owner_id, t.name FROM mna_contact_tags mtt
                    JOIN mna_tags t ON t.id = mtt.tag_id
                    WHERE mtt.contact_id IN ({marks}) ORDER BY t.name""",
                tuple(contact_ids))
            for row in cur.fetchall():
                result.setdefault(('contact', row['owner_id']), []).append(row['name'])
    return result


def get_deal_target_tags(deal_id: int, list_type: str = 'long_list') -> list[str]:
    """Tagi występujące na danej liście — do filtra, żeby nie pokazywać wszystkich tagów w bazie."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT DISTINCT t.name FROM mna_deal_targets dt
               LEFT JOIN mna_company_tags mct ON mct.company_id = dt.company_id
               LEFT JOIN mna_contact_tags mtt ON mtt.contact_id = dt.contact_id
               JOIN mna_tags t ON t.id = mct.tag_id OR t.id = mtt.tag_id
               WHERE dt.deal_id = %s AND dt.list_type = %s
               ORDER BY t.name""",
            (deal_id, list_type))
        return [r['name'] for r in cur.fetchall()]


def get_deal_targets_stats(deal_id: int) -> dict:
    """Liczniki obu list deala — nagłówek widoku i przełącznik long/short."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT list_type,
                      COUNT(*) AS total,
                      SUM(is_valuable) AS valuable,
                      SUM(interest_status = 'interested') AS interested,
                      SUM(interest_status = 'not_interested') AS not_interested,
                      SUM(interest_status = 'unknown') AS unknown,
                      SUM(contacted_at IS NOT NULL) AS contacted,
                      ROUND(AVG(score)) AS avg_score
               FROM mna_deal_targets WHERE deal_id = %s GROUP BY list_type""",
            (deal_id,))
        by_list = {r['list_type']: dict(r) for r in cur.fetchall()}
    empty = {'total': 0, 'valuable': 0, 'interested': 0, 'not_interested': 0,
             'unknown': 0, 'contacted': 0, 'avg_score': None}
    return {key: by_list.get(key, dict(empty)) for key in LIST_TYPE_LABELS}


def set_target_note(target_id: int, note: str | None, user_id: int | None) -> None:
    target = get_target_by_id(target_id)
    if not target:
        return
    note = (note or '').strip()[:500] or None
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("UPDATE mna_deal_targets SET note=%s WHERE id=%s", (note, target_id))
        db.commit()
    except Exception:
        db.rollback()
        raise
    if target.get('note') != note:
        log_history('mna_deal', target['deal_id'], user_id, 'update',
                    f"„{_target_label(target)}”: notatka → {note or '—'}.")


def set_target_contacted(target_id: int, contacted_at, user_id: int | None) -> None:
    """contacted_at: data (str 'RRRR-MM-DD' lub date) albo None, żeby wyczyścić."""
    target = get_target_by_id(target_id)
    if not target:
        return
    contacted_at = contacted_at or None
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("UPDATE mna_deal_targets SET contacted_at=%s WHERE id=%s", (contacted_at, target_id))
        db.commit()
    except Exception:
        db.rollback()
        raise
    log_history('mna_deal', target['deal_id'], user_id, 'update',
                f"„{_target_label(target)}”: ostatni kontakt → {contacted_at or '—'}.")
