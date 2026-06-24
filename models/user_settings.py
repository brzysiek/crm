from database import get_db


def get_user_setting(user_id: int, key: str, default=None):
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT value FROM user_settings WHERE user_id=%s AND `key`=%s", (user_id, key))
        row = cur.fetchone()
    return row['value'] if row else default


def set_user_setting(user_id: int, key: str, value) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "INSERT INTO user_settings (user_id, `key`, value) VALUES (%s, %s, %s) "
                "ON DUPLICATE KEY UPDATE value = %s",
                (user_id, key, value, value)
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
