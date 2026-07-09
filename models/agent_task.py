from database import get_db

VALID_INTENTS = ('note', 'create')
VALID_ENTITY_TYPES = ('company', 'contact', 'deal')

ENTITY_TYPE_LABELS = {'company': 'Klient', 'contact': 'Kontakt', 'deal': 'Interes'}
INTENT_LABELS = {'note': 'Notatka', 'create': 'Dodanie'}


def _valid_user_id(user_id: int | None) -> int | None:
    if not user_id:
        return None
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT id FROM users WHERE id=%s", (user_id,))
        return user_id if cur.fetchone() else None


def log_task(user_id: int | None, input_text: str, intent: str, entity_type: str,
             entity_id: int | None, summary: str, status: str = 'done') -> int:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                """INSERT INTO agent_tasks
                   (user_id, input_text, intent, entity_type, entity_id, summary, status)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (_valid_user_id(user_id), input_text, intent, entity_type,
                 entity_id, summary, status)
            )
        db.commit()
        return cur.lastrowid
    except Exception:
        db.rollback()
        raise


def get_tasks(limit: int = 200) -> list[dict]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT t.*, u.full_name AS user_name
               FROM agent_tasks t
               LEFT JOIN users u ON u.id = t.user_id
               ORDER BY t.created_at DESC, t.id DESC
               LIMIT %s""",
            (limit,)
        )
        return cur.fetchall()
