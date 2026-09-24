"""Auto-kategoryzacja dokumentów regułami.

Bez reguł kategoryzacja 230 dokumentów (i każdego kolejnego z KSeF) jest ręczną
orką. Reguła to: pole + sposób dopasowania + wartość → kategoria. Wygrywa
reguła o najniższym `priority`, przy remisie starsza (mniejsze id) — kolejność
ma być przewidywalna, a nie zależna od tego, jak baza akurat zwróci wiersze.

Reguły dotykają wyłącznie dokumentów bez kategorii albo takich, które kategorię
dostały od reguły. Ręcznego przypisania (`source='manual'`) silnik nie nadpisuje.
"""
import re

from database import get_db
from models.fin_category import set_document_category

MATCH_FIELDS = ('counterparty_tax_no_norm', 'counterparty_name', 'number',
                'description', 'accounting_kind')
MATCH_TYPES = ('equals', 'contains', 'starts_with', 'regex')

FIELD_LABELS = {
    'counterparty_tax_no_norm': 'NIP kontrahenta',
    'counterparty_name': 'Nazwa kontrahenta',
    'number': 'Numer dokumentu',
    'description': 'Opis',
    'accounting_kind': 'Rodzaj księgowy',
}
TYPE_LABELS = {
    'equals': 'równe', 'contains': 'zawiera',
    'starts_with': 'zaczyna się od', 'regex': 'wyrażenie regularne',
}


def list_rules(active_only: bool = False) -> list[dict]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(f"""SELECT r.*, c.name AS category_name, c.kind AS category_kind
                        FROM fin_category_rules r
                        LEFT JOIN fin_categories c ON c.id = r.category_id
                        {'WHERE r.is_active = 1' if active_only else ''}
                        ORDER BY r.priority, r.id""")
        return [dict(r) for r in cur.fetchall()]


def create_rule(match_field: str, match_type: str, match_value: str, category_id: int,
                priority: int = 100, vat_percent: int = None, kup_percent: int = None) -> int:
    if match_field not in MATCH_FIELDS:
        raise ValueError(f'Nieznane pole dopasowania: {match_field}')
    if match_type not in MATCH_TYPES:
        raise ValueError(f'Nieznany sposób dopasowania: {match_type}')
    if match_type == 'regex':
        re.compile(match_value)          # zła regexp ma wybuchnąć tu, nie przy syncu
    db = get_db()
    with db.cursor() as cur:
        cur.execute("""INSERT INTO fin_category_rules
                           (priority, match_field, match_type, match_value, category_id,
                            vat_deduction_percent, tax_deductible_percent)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (int(priority), match_field, match_type, match_value[:256],
                     int(category_id), vat_percent, kup_percent))
        new_id = cur.lastrowid
    db.commit()
    return new_id


def delete_rule(rule_id: int) -> None:
    db = get_db()
    with db.cursor() as cur:
        cur.execute("DELETE FROM fin_category_rules WHERE id = %s", (int(rule_id),))
    db.commit()


def toggle_rule(rule_id: int, active: bool) -> None:
    db = get_db()
    with db.cursor() as cur:
        cur.execute("UPDATE fin_category_rules SET is_active = %s WHERE id = %s",
                    (1 if active else 0, int(rule_id)))
    db.commit()


def rule_matches(rule: dict, doc: dict) -> bool:
    """Czy reguła pasuje do dokumentu. Porównania bez rozróżniania wielkości liter."""
    field = rule.get('match_field')
    if field not in MATCH_FIELDS:
        return False
    value = str(doc.get(field) or '').strip().lower()
    if not value:
        return False
    needle = str(rule.get('match_value') or '').strip().lower()
    if not needle:
        return False

    match_type = rule.get('match_type')
    if match_type == 'equals':
        return value == needle
    if match_type == 'contains':
        return needle in value
    if match_type == 'starts_with':
        return value.startswith(needle)
    if match_type == 'regex':
        try:
            return re.search(needle, value, re.IGNORECASE) is not None
        except re.error:
            return False      # zepsuta reguła nie może wywalić całego syncu
    return False


def first_match(doc: dict, rules: list[dict]) -> dict | None:
    """Pierwsza pasująca reguła w kolejności priorytetu (reguły przychodzą posortowane)."""
    for rule in rules:
        if rule.get('category_kind') and bool(doc.get('is_income')) != (rule['category_kind'] == 'income'):
            continue          # kategoria kosztowa nie trafi na przychód i odwrotnie
        if rule_matches(rule, doc):
            return rule
    return None


def _mark_hits(hits: dict[int, int]) -> None:
    if not hits:
        return
    db = get_db()
    with db.cursor() as cur:
        for rule_id, count in hits.items():
            cur.execute("""UPDATE fin_category_rules
                           SET hits = hits + %s, last_hit_at = NOW() WHERE id = %s""",
                        (count, rule_id))
    db.commit()


def apply_rules(only_ids: list[int] = None, recategorize_rule_assigned: bool = False) -> dict:
    """Przepuszcza dokumenty przez reguły. Zwraca podsumowanie.

    `only_ids` zawęża do konkretnych dokumentów (używa tego sync dla nowości).
    `recategorize_rule_assigned=True` pozwala regułom poprawić swoje wcześniejsze
    przypisania — przydaje się po edycji reguł. Ręczne przypisania zostają zawsze.
    """
    rules = list_rules(active_only=True)
    if not rules:
        return {'checked': 0, 'assigned': 0, 'rules': 0}

    where = ["m.source IS NULL OR m.source = 'rule'"] if recategorize_rule_assigned \
        else ['m.category_id IS NULL']
    params: list = []
    if only_ids:
        where.append('d.fakturownia_id IN %s')
        params.append(tuple(only_ids))

    db = get_db()
    with db.cursor() as cur:
        cur.execute(f"""SELECT d.fakturownia_id, d.is_income, d.counterparty_name,
                               d.counterparty_tax_no_norm, d.number, d.description, d.accounting_kind
                        FROM fin_documents d
                        LEFT JOIN fin_document_meta m ON m.fakturownia_id = d.fakturownia_id
                        WHERE ({') AND ('.join(where)})""", tuple(params))
        docs = [dict(r) for r in cur.fetchall()]

    hits: dict[int, int] = {}
    assigned = 0
    for doc in docs:
        rule = first_match(doc, rules)
        if not rule:
            continue
        set_document_category(doc['fakturownia_id'], rule['category_id'], source='rule',
                              vat_percent=rule.get('vat_deduction_percent'),
                              kup_percent=rule.get('tax_deductible_percent'),
                              rule_id=rule['id'], commit=False)
        hits[rule['id']] = hits.get(rule['id'], 0) + 1
        assigned += 1
    db.commit()
    _mark_hits(hits)
    return {'checked': len(docs), 'assigned': assigned, 'rules': len(rules)}
