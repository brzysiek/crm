"""Kategorie kosztów i przychodów oraz przypisania dokumentów.

Kategorie żyją w CRM, nie w Fakturowni: jeden dokument potrzebuje więcej niż
płaskiej etykiety — procentu odliczenia VAT i procentu kosztu podatkowego.
Przypisania siedzą w `fin_document_meta` kluczowanej `fakturownia_id`, więc
pełny re-sync lustra nigdy ich nie rusza.
"""
from database import get_db

SOURCES = ('manual', 'rule', 'agent')
SOURCE_LABELS = {'manual': 'ręcznie', 'rule': 'reguła', 'agent': 'agent'}


def list_categories(kind: str = None, include_archived: bool = False) -> list[dict]:
    where, params = ['1=1'], []
    if kind in ('cost', 'income'):
        where.append('kind = %s')
        params.append(kind)
    if not include_archived:
        where.append('archived_at IS NULL')
    db = get_db()
    with db.cursor() as cur:
        cur.execute(f"""SELECT * FROM fin_categories WHERE {' AND '.join(where)}
                        ORDER BY kind, sort_order, name""", tuple(params))
        return [dict(r) for r in cur.fetchall()]


def get_category(category_id: int) -> dict | None:
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM fin_categories WHERE id = %s", (category_id,))
        row = cur.fetchone()
    return dict(row) if row else None


def get_category_by_slug(slug: str) -> dict | None:
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM fin_categories WHERE slug = %s", (slug,))
        row = cur.fetchone()
    return dict(row) if row else None


def create_category(kind: str, name: str, slug: str, vat: int = 100, kup: int = 100,
                    is_fixed_cost: bool = False, sort_order: int = 500) -> int:
    db = get_db()
    with db.cursor() as cur:
        cur.execute("""INSERT INTO fin_categories
                           (kind, name, slug, default_vat_deduction, default_tax_deductible,
                            is_fixed_cost, sort_order)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (kind if kind in ('cost', 'income') else 'cost', name, slug,
                     int(vat), int(kup), 1 if is_fixed_cost else 0, int(sort_order)))
        new_id = cur.lastrowid
    db.commit()
    return new_id


def update_category(category_id: int, **fields) -> None:
    allowed = ('name', 'default_vat_deduction', 'default_tax_deductible',
               'is_fixed_cost', 'sort_order', 'archived_at')
    sets = {k: v for k, v in fields.items() if k in allowed}
    if not sets:
        return
    db = get_db()
    with db.cursor() as cur:
        cur.execute(f"UPDATE fin_categories SET {', '.join(f'`{k}` = %s' for k in sets)} WHERE id = %s",
                    tuple(sets.values()) + (int(category_id),))
    db.commit()


def set_document_category(fakturownia_id: int, category_id: int | None, source: str = 'manual',
                          vat_percent: int = None, kup_percent: int = None,
                          rule_id: int = None, note: str = None, commit: bool = True) -> None:
    """Przypisuje kategorię. Bez podanych procentów bierze domyślne z kategorii."""
    category = get_category(category_id) if category_id else None
    vat = vat_percent if vat_percent is not None else (category or {}).get('default_vat_deduction', 100)
    kup = kup_percent if kup_percent is not None else (category or {}).get('default_tax_deductible', 100)
    db = get_db()
    with db.cursor() as cur:
        cur.execute("""INSERT INTO fin_document_meta
                           (fakturownia_id, category_id, vat_deduction_percent,
                            tax_deductible_percent, source, rule_id, note, categorized_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                       ON DUPLICATE KEY UPDATE
                           category_id = VALUES(category_id),
                           vat_deduction_percent = VALUES(vat_deduction_percent),
                           tax_deductible_percent = VALUES(tax_deductible_percent),
                           source = VALUES(source), rule_id = VALUES(rule_id),
                           note = COALESCE(VALUES(note), note),
                           categorized_at = NOW()""",
                    (int(fakturownia_id), category_id, int(vat), int(kup),
                     source if source in SOURCES else 'manual', rule_id, note))
    if commit:
        db.commit()


def clear_document_category(fakturownia_id: int) -> None:
    db = get_db()
    with db.cursor() as cur:
        cur.execute("DELETE FROM fin_document_meta WHERE fakturownia_id = %s", (int(fakturownia_id),))
    db.commit()


def bulk_set_category(ids: list[int], category_id: int, source: str = 'manual') -> int:
    """Masowe przypisanie — bez tego 230 nieskategoryzowanych dokumentów to ręczna orka."""
    count = 0
    for fakturownia_id in ids:
        set_document_category(fakturownia_id, category_id, source=source, commit=False)
        count += 1
    get_db().commit()
    return count


def category_totals(date_from: str, date_to: str, is_income: bool = False) -> list[dict]:
    """Sumy w oknie dat wg kategorii; kategoria pusta = NULL na końcu listy."""
    from models.fin_document import FINANCIAL_CLAUSE, NON_FINANCIAL_KINDS
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            f"""SELECT c.id AS category_id, c.name AS category_name, c.slug, c.is_fixed_cost,
                       COUNT(*) AS documents,
                       COALESCE(SUM(d.net_pln), 0) AS net,
                       COALESCE(SUM(d.tax_pln), 0) AS tax,
                       COALESCE(SUM(d.net_pln * COALESCE(m.tax_deductible_percent, 100) / 100), 0) AS net_kup,
                       COALESCE(SUM(d.tax_pln * COALESCE(m.vat_deduction_percent, 100) / 100), 0) AS tax_deductible
                FROM fin_documents d
                LEFT JOIN fin_document_meta m ON m.fakturownia_id = d.fakturownia_id
                LEFT JOIN fin_categories c ON c.id = m.category_id
                WHERE d.is_income = %s AND d.issue_date BETWEEN %s AND %s AND {FINANCIAL_CLAUSE}
                GROUP BY c.id, c.name, c.slug, c.is_fixed_cost
                ORDER BY net DESC""",
            (1 if is_income else 0, date_from, date_to, NON_FINANCIAL_KINDS))
        return [dict(r) for r in cur.fetchall()]


def category_monthly(months: int = 12, is_income: bool = False) -> list[dict]:
    """Kategoria × miesiąc — materiał na tabelę przestawną „koszty w czasie”."""
    from models.fin_document import FINANCIAL_CLAUSE, NON_FINANCIAL_KINDS
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            f"""SELECT DATE_FORMAT(d.issue_date, '%%Y-%%m') AS month,
                       c.id AS category_id, c.name AS category_name,
                       COALESCE(SUM(d.net_pln), 0) AS net, COUNT(*) AS documents
                FROM fin_documents d
                LEFT JOIN fin_document_meta m ON m.fakturownia_id = d.fakturownia_id
                LEFT JOIN fin_categories c ON c.id = m.category_id
                WHERE d.is_income = %s AND {FINANCIAL_CLAUSE}
                  AND d.issue_date >= DATE_SUB(DATE_FORMAT(CURDATE(), '%%Y-%%m-01'), INTERVAL %s MONTH)
                GROUP BY month, c.id, c.name
                ORDER BY month""",
            (1 if is_income else 0, NON_FINANCIAL_KINDS, int(months)))
        return [dict(r) for r in cur.fetchall()]


def counterparty_totals(is_income: bool = False, limit: int = 50) -> list[dict]:
    """Kontrahenci scaleni po znormalizowanym NIP — inaczej PKP byłoby dwa razy."""
    from models.fin_document import FINANCIAL_CLAUSE, NON_FINANCIAL_KINDS
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            f"""SELECT d.counterparty_tax_no_norm AS tax_no,
                       MAX(d.counterparty_name) AS name,
                       COUNT(*) AS documents,
                       COALESCE(SUM(d.net_pln), 0) AS net,
                       SUM(m.category_id IS NULL) AS uncategorized,
                       MAX(c.name) AS category_name,
                       COUNT(DISTINCT m.category_id) AS category_count,
                       MAX(d.issue_date) AS last_date
                FROM fin_documents d
                LEFT JOIN fin_document_meta m ON m.fakturownia_id = d.fakturownia_id
                LEFT JOIN fin_categories c ON c.id = m.category_id
                WHERE d.is_income = %s AND {FINANCIAL_CLAUSE}
                GROUP BY d.counterparty_tax_no_norm
                ORDER BY net DESC
                LIMIT %s""",
            (1 if is_income else 0, NON_FINANCIAL_KINDS, int(limit)))
        return [dict(r) for r in cur.fetchall()]
