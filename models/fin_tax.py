"""Dane dla silnika podatkowego: stawki roczne, rejestry i rejestr zobowiązań.

Podział pracy: tu są zapytania, w `services/fin_tax.py` arytmetyka. Dwie rzeczy
warte uwagi:

* **rejestr VAT idzie po `vat_date`**, nie po dacie wystawienia. Fakturownia
  trzyma w `accounting_vat_tax_date` datę, od której liczy się prawo do
  odliczenia (przy kosztach zwykle data otrzymania) — na 230 dokumentach konta
  różni się od `issue_date` w 17 przypadkach, więc to nie jest detal.
* **PIT idzie po `income_tax_date`** i narastająco od stycznia.
"""
import json

from database import get_db
from models.fin_document import FINANCIAL_CLAUSE, NON_FINANCIAL_KINDS

# Flagi z odpowiedzi API, które decydują o tym, czy dokument da się policzyć
# automatem. Nie mają własnych kolumn — czytamy je z zapisanego `raw_json`.
RAW_FLAGS = ('reverse_charge', 'use_moss', 'cancelled', 'exclude_from_accounting', 'not_cost')

RATE_LABELS = {
    'pit_rate': 'Stawka PIT liniowego',
    'health_rate': 'Stawka składki zdrowotnej',
    'health_min_monthly': 'Minimalna składka zdrowotna (miesięcznie)',
    'health_deduction_limit': 'Roczny limit odliczenia składki zdrowotnej',
    'zus_social_monthly': 'ZUS społeczny (miesięcznie)',
    'zus_fp_monthly': 'Fundusz Pracy (miesięcznie)',
    'zus_base': 'Podstawa składek społecznych',
    'min_wage': 'Minimalne wynagrodzenie',
}

# Klucze, bez których silnik nie policzy nic — brak = ostrzeżenie na ekranie.
REQUIRED_RATES = ('pit_rate', 'health_rate', 'health_min_monthly',
                  'health_deduction_limit', 'zus_social_monthly', 'zus_fp_monthly')


# ── Stawki ───────────────────────────────────────────────────────────────────

def get_rates(year: int) -> dict:
    """Stawki na rok, z zjazdem do najnowszego wcześniejszego rocznika.

    Zwraca `{key: {'value', 'note', 'year', 'is_confirmed'}}`. Gdy stawka
    pochodzi z wcześniejszego roku, `is_confirmed` jest wyzerowane, a `note`
    mówi wprost skąd ją wzięto — silnik nie ma prawa udawać, że zna przyszłość.
    """
    db = get_db()
    with db.cursor() as cur:
        cur.execute("""SELECT year, `key`, value, note, is_confirmed FROM fin_tax_rates
                       WHERE year <= %s ORDER BY year ASC""", (int(year),))
        rows = cur.fetchall()
    rates: dict = {}
    for row in rows:  # rosnąco po roku — późniejszy rocznik nadpisuje wcześniejszy
        rates[row['key']] = {
            'value': row['value'],
            'note': row['note'] or '',
            'year': int(row['year']),
            'is_confirmed': bool(row['is_confirmed']),
            'label': RATE_LABELS.get(row['key'], row['key']),
        }
    for key, entry in rates.items():
        if entry['year'] != int(year):
            entry['is_confirmed'] = False
            entry['note'] = (f"Stawka przeniesiona z {entry['year']} — potwierdź wartość "
                             f"na {year}." + (f" ({entry['note']})" if entry['note'] else ''))
    return rates


def missing_rates(year: int) -> list[str]:
    rates = get_rates(year)
    return [k for k in REQUIRED_RATES if k not in rates]


def list_rates(year: int = None) -> list[dict]:
    db = get_db()
    sql = "SELECT * FROM fin_tax_rates"
    params: tuple = ()
    if year:
        sql += " WHERE year = %s"
        params = (int(year),)
    sql += " ORDER BY year DESC, `key`"
    with db.cursor() as cur:
        cur.execute(sql, params)
        rows = [dict(r) for r in cur.fetchall()]
    for row in rows:
        row['label'] = RATE_LABELS.get(row['key'], row['key'])
    return rows


def rate_years() -> list[int]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT DISTINCT year FROM fin_tax_rates ORDER BY year DESC")
        return [int(r['year']) for r in cur.fetchall()]


def set_rate(year: int, key: str, value, note: str = '', is_confirmed: bool = True) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("""INSERT INTO fin_tax_rates (year, `key`, value, note, is_confirmed)
                           VALUES (%s, %s, %s, %s, %s)
                           ON DUPLICATE KEY UPDATE value = VALUES(value), note = VALUES(note),
                                                   is_confirmed = VALUES(is_confirmed)""",
                        (int(year), key[:64], value, (note or '')[:256], 1 if is_confirmed else 0))
        db.commit()
    except Exception:
        db.rollback()
        raise


# ── Rejestr VAT ──────────────────────────────────────────────────────────────

def _flags(row: dict) -> dict:
    """Wyciąga flagi z `raw_json` i wyrzuca sam blob — nie ma po co jechać dalej."""
    raw = row.pop('raw_json', None)
    data = {}
    if raw:
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            data = {}
    for flag in RAW_FLAGS:
        value = data.get(flag)
        row[flag] = value in (True, 1, '1', 'true', 'yes')
    return row


def vat_register(period: str) -> tuple[list[dict], list[dict]]:
    """Dokumenty wchodzące do VAT za miesiąc `YYYY-MM`, po `vat_date`."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            f"""SELECT d.fakturownia_id, d.number, d.kind, d.is_income, d.counterparty_name,
                       d.issue_date, d.vat_date, d.net_pln, d.tax_pln, d.gross_pln,
                       d.accounting_kind, d.raw_json,
                       m.vat_deduction_percent, c.name AS category_name
                FROM fin_documents d
                LEFT JOIN fin_document_meta m ON m.fakturownia_id = d.fakturownia_id
                LEFT JOIN fin_categories c ON c.id = m.category_id
                WHERE DATE_FORMAT(d.vat_date, '%%Y-%%m') = %s AND {FINANCIAL_CLAUSE}
                ORDER BY d.vat_date, d.number""",
            (period, NON_FINANCIAL_KINDS))
        rows = [_flags(dict(r)) for r in cur.fetchall()]
    return ([r for r in rows if r['is_income']], [r for r in rows if not r['is_income']])


def vat_months() -> list[str]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute("""SELECT DISTINCT DATE_FORMAT(vat_date, '%Y-%m') AS month
                       FROM fin_documents WHERE vat_date IS NOT NULL
                       ORDER BY month DESC LIMIT 36""")
        return [r['month'] for r in cur.fetchall()]


# ── Podstawa PIT ─────────────────────────────────────────────────────────────

_PIT_SELECT = """
    SELECT COALESCE(SUM(CASE WHEN d.is_income = 1 THEN d.net_pln END), 0) AS income_net,
           COALESCE(SUM(CASE WHEN d.is_income = 0
                             THEN d.net_pln * COALESCE(m.tax_deductible_percent, 100) / 100
                        END), 0) AS cost_net,
           COALESCE(SUM(CASE WHEN d.is_income = 0 THEN d.net_pln END), 0) AS cost_gross_net,
           SUM(CASE WHEN d.is_income = 0 AND m.category_id IS NULL THEN 1 ELSE 0 END) AS cost_uncategorized,
           COUNT(*) AS documents
    FROM fin_documents d
    LEFT JOIN fin_document_meta m ON m.fakturownia_id = d.fakturownia_id
"""


def income_tax_totals(year: int, up_to_month: int) -> dict:
    """Przychód i koszty KUP narastająco od stycznia do końca `up_to_month`.

    Koszt wchodzi w części wynikającej z `tax_deductible_percent` (NKUP = 0,
    reprezentacja, 75% przy samochodzie). Dokument bez kategorii liczy się jak
    100% KUP — i jest policzony w `cost_uncategorized`, żeby ekran mógł
    powiedzieć, ile wyniku stoi na domyśle.
    """
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            f"""{_PIT_SELECT}
                WHERE YEAR(d.income_tax_date) = %s AND MONTH(d.income_tax_date) <= %s
                  AND {FINANCIAL_CLAUSE}""",
            (int(year), int(up_to_month), NON_FINANCIAL_KINDS))
        row = dict(cur.fetchone())
    row['result'] = row['income_net'] - row['cost_net']
    row['months'] = int(up_to_month)
    row['year'] = int(year)
    return row


def month_income(period: str) -> object:
    """Dochód (przychód − KUP) za jeden miesiąc — podstawa składki zdrowotnej."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            f"""{_PIT_SELECT}
                WHERE DATE_FORMAT(d.income_tax_date, '%%Y-%%m') = %s AND {FINANCIAL_CLAUSE}""",
            (period, NON_FINANCIAL_KINDS))
        row = cur.fetchone()
    return row['income_net'] - row['cost_net']


# ── Rejestr zobowiązań ───────────────────────────────────────────────────────

def list_obligations(period: str = None, year: int = None, unpaid_only: bool = False) -> list[dict]:
    where, params = ["1=1"], []
    if period:
        where.append("period = %s")
        params.append(period)
    if year:
        where.append("period LIKE %s")
        params.append(f'{int(year)}-%')
    if unpaid_only:
        where.append("paid_at IS NULL")
    db = get_db()
    with db.cursor() as cur:
        cur.execute(f"""SELECT * FROM fin_tax_obligations WHERE {' AND '.join(where)}
                        ORDER BY period DESC, due_date""", tuple(params))
        rows = [dict(r) for r in cur.fetchall()]
    for row in rows:
        row['amount'] = row['amount_declared'] if row['amount_declared'] is not None \
            else row['amount_calculated']
    return rows


def upsert_obligation(kind: str, period: str, amount_calculated, due_date=None,
                      note: str = '') -> None:
    """Zapisuje wyliczoną kwotę. Nie rusza `amount_declared` ani `paid_at` —
    to, co wpisał człowiek, jest ważniejsze od kolejnej symulacji."""
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("""INSERT INTO fin_tax_obligations
                               (kind, period, amount_calculated, due_date, note)
                           VALUES (%s, %s, %s, %s, %s)
                           ON DUPLICATE KEY UPDATE amount_calculated = VALUES(amount_calculated),
                                                   due_date = VALUES(due_date)""",
                        (kind[:24], period[:7], amount_calculated, due_date, note or None))
        db.commit()
    except Exception:
        db.rollback()
        raise


def mark_obligation_paid(kind: str, period: str, paid_at, amount_declared=None,
                         amount_calculated=0, due_date=None) -> None:
    """Oznacza zobowiązanie jako zapłacone; tworzy wiersz, jeśli go nie było."""
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("""INSERT INTO fin_tax_obligations
                               (kind, period, amount_calculated, amount_declared, due_date, paid_at)
                           VALUES (%s, %s, %s, %s, %s, %s)
                           ON DUPLICATE KEY UPDATE paid_at = VALUES(paid_at),
                               amount_declared = COALESCE(VALUES(amount_declared), amount_declared)""",
                        (kind[:24], period[:7], amount_calculated, amount_declared,
                         due_date, paid_at))
        db.commit()
    except Exception:
        db.rollback()
        raise


def unmark_obligation_paid(kind: str, period: str) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("""UPDATE fin_tax_obligations SET paid_at = NULL
                           WHERE kind = %s AND period = %s""", (kind[:24], period[:7]))
        db.commit()
    except Exception:
        db.rollback()
        raise


def paid_amount(kind: str, year: int, up_to_period: str, inclusive: bool = True) -> object:
    """Suma faktycznie zapłaconych zobowiązań danego rodzaju w roku.

    Przy zaliczce PIT wołane z `inclusive=False`: zaliczki „już zapłacone” to te
    za miesiące **poprzedzające** liczony okres, nie za sam liczony okres.
    """
    comparison = '<=' if inclusive else '<'
    db = get_db()
    with db.cursor() as cur:
        cur.execute(f"""SELECT COALESCE(SUM(COALESCE(amount_declared, amount_calculated)), 0) AS total
                        FROM fin_tax_obligations
                        WHERE kind = %s AND paid_at IS NOT NULL
                          AND period LIKE %s AND period {comparison} %s""",
                    (kind[:24], f'{int(year)}-%', up_to_period))
        return cur.fetchone()['total']


def upcoming_obligations(limit: int = 12) -> list[dict]:
    """Niezapłacone zobowiązania z terminem — do ekranu „Do zapłaty”."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute("""SELECT *, DATEDIFF(due_date, CURDATE()) AS days_left
                       FROM fin_tax_obligations
                       WHERE paid_at IS NULL AND due_date IS NOT NULL
                         AND COALESCE(amount_declared, amount_calculated) > 0
                       ORDER BY due_date LIMIT %s""", (int(limit),))
        rows = [dict(r) for r in cur.fetchall()]
    for row in rows:
        row['amount'] = row['amount_declared'] if row['amount_declared'] is not None \
            else row['amount_calculated']
    return rows
