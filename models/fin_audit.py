"""Dziennik zapisów idących z CRM do Fakturowni.

Każde wywołanie, które zmienia coś po stronie Fakturowni (utworzenie faktury,
oznaczenie zapłaty, edycja, wysyłka do KSeF), zostawia tu wiersz — razem
z payloadem i odpowiedzią. Agent mutujący prawdziwą księgowość bez takiego
dziennika jest nieaudytowalny, a księgowość to nie miejsce na domysły.

Wpis powstaje także wtedy, gdy zapis się nie udał (`ok=0`) — nieudana próba
wystawienia faktury jest równie ważną informacją jak udana.
"""
import json

from database import get_db

MAX_TEXT = 60000        # kolumny są TEXT (64 KB); zostawiamy zapas na utf8mb4


def _clip(value) -> str | None:
    if value is None:
        return None
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    return text if len(text) <= MAX_TEXT else text[:MAX_TEXT] + '…[obcięte]'


def log(action: str, actor: str = '', fakturownia_id: int = None,
        payload=None, response=None, ok: bool = True) -> int:
    """Dopisuje wiersz do dziennika. Bez commita — o transakcji decyduje
    wołający, żeby wpis i skutki zapisu lądowały razem."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute("""INSERT INTO fin_audit_log (actor, action, fakturownia_id, payload, response, ok)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    ((actor or '')[:64], action[:64], fakturownia_id,
                     _clip(payload), _clip(response), 1 if ok else 0))
        return cur.lastrowid


def list_entries(limit: int = 50, action: str = '', fakturownia_id: int = None) -> list[dict]:
    where, params = ['1=1'], []
    if action:
        where.append('action = %s')
        params.append(action)
    if fakturownia_id:
        where.append('fakturownia_id = %s')
        params.append(int(fakturownia_id))
    with get_db().cursor() as cur:
        cur.execute(f"""SELECT id, actor, action, fakturownia_id, ok, created_at,
                               LEFT(payload, 2000) AS payload, LEFT(response, 2000) AS response
                        FROM fin_audit_log WHERE {' AND '.join(where)}
                        ORDER BY id DESC LIMIT %s""", tuple(params) + (max(1, min(int(limit), 300)),))
        return [dict(r) for r in cur.fetchall()]
