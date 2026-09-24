"""Uruchamia plik .sql instrukcja po instrukcji.

Dzielenie po samym `;` już raz urwało migrację w połowie (część instrukcji
zaczynających się komentarzem zniknęła, a kolejny UPDATE wpisał wartość spoza
ENUM-a). Dlatego tu jest prawdziwy podział: średnik kończy instrukcję tylko
poza łańcuchami, identyfikatorami i komentarzami.

Użycie: venv/bin/python scripts/run_migration.py migration_x.sql [--dry-run]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pymysql
import pymysql.cursors

from config import Config


def split_statements(sql: str) -> list[str]:
    statements, buf = [], []
    quote = None          # ', " albo `
    comment = None        # 'line' albo 'block'
    i, n = 0, len(sql)
    while i < n:
        ch, nxt = sql[i], sql[i + 1] if i + 1 < n else ''
        if comment == 'line':
            if ch == '\n':
                comment = None
                buf.append(ch)
            i += 1
            continue
        if comment == 'block':
            if ch == '*' and nxt == '/':
                comment, i = None, i + 2
                continue
            i += 1
            continue
        if quote:
            buf.append(ch)
            if ch == '\\' and quote in ("'", '"'):
                if nxt:
                    buf.append(nxt)
                    i += 2
                    continue
            elif ch == quote:
                if nxt == quote:          # zdwojony znak = znak w treści
                    buf.append(nxt)
                    i += 2
                    continue
                quote = None
            i += 1
            continue
        if ch in ('\'', '"', '`'):
            quote = ch
            buf.append(ch)
        elif ch == '-' and nxt == '-' and (i + 2 >= n or sql[i + 2] in ' \t\r\n'):
            comment = 'line'
            i += 2
            continue
        elif ch == '#':
            comment = 'line'
            i += 1
            continue
        elif ch == '/' and nxt == '*':
            comment = 'block'
            i += 2
            continue
        elif ch == ';':
            statements.append(''.join(buf).strip())
            buf = []
        else:
            buf.append(ch)
        i += 1
    tail = ''.join(buf).strip()
    if tail:
        statements.append(tail)
    return [s for s in statements if s]


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    dry_run = '--dry-run' in sys.argv
    if not args:
        print(__doc__)
        return 2

    path = Path(args[0])
    statements = split_statements(path.read_text(encoding='utf-8'))
    print(f'{path}: {len(statements)} instrukcji')
    if dry_run:
        for idx, stmt in enumerate(statements, 1):
            print(f'--- {idx}: {stmt.splitlines()[0][:100]}')
        return 0

    conn = pymysql.connect(
        host=Config.MYSQL_HOST, port=Config.MYSQL_PORT, user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD, database=Config.MYSQL_DB,
        charset=Config.MYSQL_CHARSET, cursorclass=pymysql.cursors.DictCursor,
        autocommit=False)
    try:
        with conn.cursor() as cur:
            for idx, stmt in enumerate(statements, 1):
                head = stmt.splitlines()[0][:90]
                cur.execute(stmt)
                print(f'  [{idx}/{len(statements)}] {head} → {cur.rowcount}')
        conn.commit()
        print('OK, zatwierdzone.')
    except Exception as e:
        conn.rollback()
        print(f'BŁĄD, wycofane: {e}')
        return 1
    finally:
        conn.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
