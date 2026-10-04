from datetime import datetime

from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db


def get_all_users() -> list[dict]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT id, username, full_name, email, role, is_active, created_at "
            "FROM users ORDER BY full_name"
        )
        return cur.fetchall()


def get_user_by_id(user_id: int) -> dict | None:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT id, username, full_name, email, role, is_active, created_at "
            "FROM users WHERE id = %s",
            (user_id,)
        )
        return cur.fetchone()


def get_user_by_username(username: str) -> dict | None:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT id, username, full_name, email, role, is_active "
            "FROM users WHERE username = %s",
            (username,)
        )
        return cur.fetchone()


def get_user_by_login_or_email(identifier: str) -> dict | None:
    """Odzyskiwanie hasła nie może wymagać pamiętania, czy logowało się loginem, czy mailem —
    szukamy po obu. Mail porównujemy bez względu na wielkość liter, bo tak działa poczta."""
    identifier = (identifier or '').strip()
    if not identifier:
        return None
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT id, username, full_name, email, role, is_active "
            "FROM users WHERE username = %s OR LOWER(email) = LOWER(%s) "
            "ORDER BY (username = %s) DESC LIMIT 1",
            (identifier, identifier, identifier)
        )
        return cur.fetchone()


def get_active_users() -> list[dict]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT id, full_name FROM users WHERE is_active = 1 ORDER BY full_name"
        )
        return cur.fetchall()


def create_user(username: str, full_name: str, email: str,
                password: str, role: str = 'cashier') -> int:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "INSERT INTO users (username, full_name, email, password_hash, role) "
                "VALUES (%s, %s, %s, %s, %s)",
                (username, full_name, email or None,
                 generate_password_hash(password), role)
            )
        db.commit()
        return cur.lastrowid
    except Exception:
        db.rollback()
        raise


def update_user(user_id: int, full_name: str, email: str,
                role: str, is_active: int) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "UPDATE users SET full_name=%s, email=%s, role=%s, is_active=%s "
                "WHERE id = %s",
                (full_name, email or None, role, is_active, user_id)
            )
        db.commit()
    except Exception:
        db.rollback()
        raise


def update_user_profile(user_id: int, username: str, full_name: str, email: str = None) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "UPDATE users SET username=%s, full_name=%s, email=%s WHERE id = %s",
                (username, full_name, email or None, user_id)
            )
        db.commit()
    except Exception:
        db.rollback()
        raise


def get_user_avatar(user_id: int) -> str | None:
    """Zdjęcie jako data URI. Czytane osobnym zapytaniem, nie w get_user_by_id —
    to kilkanaście kB, których nie chcemy wozić przy każdym odczycie użytkownika."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT avatar FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
        return (row or {}).get('avatar') or None


def get_user_avatar_version(user_id: int) -> str | None:
    """Znacznik zmiany zdjęcia — doklejany do adresu ikonki, żeby po podmianie
    przeglądarka nie pokazywała starego obrazka z cache. None = brak zdjęcia."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT avatar_updated_at FROM users WHERE id = %s AND avatar IS NOT NULL",
            (user_id,)
        )
        row = cur.fetchone()
    if not row:
        return None
    stamp = row.get('avatar_updated_at')
    return stamp.strftime('%Y%m%d%H%M%S') if stamp else '1'


def set_user_avatar(user_id: int, data_uri: str | None) -> None:
    """None kasuje zdjęcie — wtedy ikonka wraca do inicjałów."""
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "UPDATE users SET avatar=%s, avatar_updated_at=%s WHERE id = %s",
                (data_uri, datetime.now() if data_uri else None, user_id)
            )
        db.commit()
    except Exception:
        db.rollback()
        raise


def change_password(user_id: int, new_password: str) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "UPDATE users SET password_hash = %s WHERE id = %s",
                (generate_password_hash(new_password), user_id)
            )
        db.commit()
    except Exception:
        db.rollback()
        raise


def delete_user(user_id: int) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
        db.commit()
    except Exception:
        db.rollback()
        raise


def verify_password(username: str, password: str) -> dict | None:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT id, username, full_name, email, role, is_active, password_hash "
            "FROM users WHERE username = %s",
            (username,)
        )
        user = cur.fetchone()
    if user and user['is_active'] and check_password_hash(user['password_hash'], password):
        user.pop('password_hash')
        return user
    return None
