"""Jednorazowe sekrety logowania: kod 2FA z maila i link do resetu hasła.

Dwie zasady, na których stoi ten moduł:
 1. W bazie leży wyłącznie SHA-256 sekretu. Kod i token istnieją w jawnej postaci tylko tyle,
    ile trwa wysyłka maila — wyciek tabeli nie daje nikomu wejścia do aplikacji.
 2. Każdy sekret ma termin i licznik prób. Sześć znaków to 32^6 kombinacji; bez limitu prób
    zgadłby je skrypt w kilka minut, z limitem pięciu — nie zgadnie ich nikt.
"""
import hashlib
import secrets
from datetime import datetime, timedelta

from database import get_db

# Alfabet bez 0/O/1/I/L — kod przepisuje się ręcznie z maila, więc znaki mylące w druku
# kosztowałyby więcej nieudanych prób, niż dałyby entropii.
CODE_ALPHABET = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'
CODE_LENGTH = 6
CODE_TTL_MINUTES = 10
RESET_TTL_MINUTES = 60
MAX_ATTEMPTS = 5
RESEND_INTERVAL_SECONDS = 60


def normalize_code(code: str) -> str:
    """Kod z maila bywa wklejany ze spacją albo małymi literami — liczy się treść, nie zapis."""
    return ''.join(ch for ch in (code or '').upper() if ch.isalnum())


def _hash(kind: str, secret: str) -> str:
    value = normalize_code(secret) if kind == 'login_code' else (secret or '').strip()
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def _issue(user_id: int, kind: str, secret: str, ttl_minutes: int, ip: str | None) -> str:
    """Nowy sekret unieważnia poprzednie tego samego rodzaju — w danej chwili działa dokładnie
    jeden kod i jeden link, więc „wyślij ponownie” nie zostawia za sobą ważnych duplikatów."""
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "UPDATE auth_tokens SET used_at = NOW()"
                " WHERE user_id = %s AND kind = %s AND used_at IS NULL",
                (user_id, kind))
            cur.execute(
                "INSERT INTO auth_tokens (user_id, kind, token_hash, expires_at, ip)"
                " VALUES (%s, %s, %s, %s, %s)",
                (user_id, kind, _hash(kind, secret),
                 datetime.now() + timedelta(minutes=ttl_minutes), ip))
            # Sprzątanie przy okazji — tabela ma być krótka, a zużyte sekrety nie są dowodem
            # na nic poza tym, że ktoś się logował.
            cur.execute("DELETE FROM auth_tokens WHERE created_at < NOW() - INTERVAL 30 DAY")
        db.commit()
    except Exception:
        db.rollback()
        raise
    return secret


def issue_login_code(user_id: int, ip: str | None = None) -> str:
    code = ''.join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
    return _issue(user_id, 'login_code', code, CODE_TTL_MINUTES, ip)


def issue_password_reset(user_id: int, ip: str | None = None) -> str:
    return _issue(user_id, 'password_reset', secrets.token_urlsafe(32), RESET_TTL_MINUTES, ip)


def _active_row(cur, kind: str, where: str, params: tuple) -> dict | None:
    cur.execute(
        "SELECT id, user_id, attempts, token_hash, expires_at FROM auth_tokens"
        f" WHERE kind = %s AND used_at IS NULL AND {where}"
        " ORDER BY id DESC LIMIT 1",
        (kind, *params))
    return cur.fetchone()


def consume_login_code(user_id: int, code: str) -> str:
    """Zwraca 'ok' | 'invalid' | 'expired' | 'blocked' | 'missing'.

    Nieudana próba podbija licznik, a po piątej kod przepada — ponowna wysyłka jest jedyną
    drogą dalej. Dzięki temu zgadywanie kosztuje dostęp do skrzynki, a nie tylko czas.
    """
    db = get_db()
    try:
        with db.cursor() as cur:
            row = _active_row(cur, 'login_code', 'user_id = %s', (user_id,))
            if not row:
                return 'missing'
            if row['expires_at'] < datetime.now():
                cur.execute("UPDATE auth_tokens SET used_at = NOW() WHERE id = %s", (row['id'],))
                db.commit()
                return 'expired'
            if row['token_hash'] == _hash('login_code', code):
                cur.execute("UPDATE auth_tokens SET used_at = NOW() WHERE id = %s", (row['id'],))
                db.commit()
                return 'ok'
            attempts = row['attempts'] + 1
            if attempts >= MAX_ATTEMPTS:
                cur.execute("UPDATE auth_tokens SET attempts = %s, used_at = NOW() WHERE id = %s",
                            (attempts, row['id']))
                db.commit()
                return 'blocked'
            cur.execute("UPDATE auth_tokens SET attempts = %s WHERE id = %s", (attempts, row['id']))
            db.commit()
            return 'invalid'
    except Exception:
        db.rollback()
        raise


def peek_reset_token(token: str) -> int | None:
    """Czy link do resetu jeszcze żyje — bez zużywania go, bo formularz nowego hasła
    najpierw trzeba pokazać, a dopiero potem przyjąć."""
    if not token:
        return None
    db = get_db()
    with db.cursor() as cur:
        row = _active_row(cur, 'password_reset', 'token_hash = %s', (_hash('password_reset', token),))
    if not row or row['expires_at'] < datetime.now():
        return None
    return row['user_id']


def consume_reset_token(token: str) -> int | None:
    """Zużywa link i zwraca id użytkownika albo None, jeśli link jest nieważny."""
    user_id = peek_reset_token(token)
    if user_id is None:
        return None
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "UPDATE auth_tokens SET used_at = NOW()"
                " WHERE kind = 'password_reset' AND token_hash = %s AND used_at IS NULL",
                (_hash('password_reset', token),))
            changed = cur.rowcount
        db.commit()
    except Exception:
        db.rollback()
        raise
    return user_id if changed else None


def invalidate_user_tokens(user_id: int) -> None:
    """Po zmianie hasła nie ma już ważnych kodów ani linków tego użytkownika — stary link
    w cudzej skrzynce nie może odwrócić tej zmiany."""
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("UPDATE auth_tokens SET used_at = NOW()"
                        " WHERE user_id = %s AND used_at IS NULL", (user_id,))
        db.commit()
    except Exception:
        db.rollback()
        raise
