from database import get_db


def get_all_settings() -> dict:
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT `key`, value FROM settings")
        return {r['key']: r['value'] for r in cur.fetchall()}


def get_setting(key: str, default=None):
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT value FROM settings WHERE `key` = %s", (key,))
        row = cur.fetchone()
    return row['value'] if row else default


def set_setting(key: str, value) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "INSERT INTO settings (`key`, value) VALUES (%s, %s) "
                "ON DUPLICATE KEY UPDATE value = %s",
                (key, value, value)
            )
        db.commit()
    except Exception:
        db.rollback()
        raise


def set_many(data: dict) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            for key, value in data.items():
                cur.execute(
                    "INSERT INTO settings (`key`, value) VALUES (%s, %s) "
                    "ON DUPLICATE KEY UPDATE value = %s",
                    (key, value, value)
                )
        db.commit()
    except Exception:
        db.rollback()
        raise
