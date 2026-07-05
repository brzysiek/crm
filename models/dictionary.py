from database import get_db


def get_dict_items(dict_type: str) -> list[dict]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT id, value, label, sort_order FROM dictionary_items "
            "WHERE dict_type=%s ORDER BY sort_order, label, value",
            (dict_type,)
        )
        rows = cur.fetchall()
    return [dict(r) for r in rows]


def add_dict_item(dict_type: str, value: str, label: str | None = None) -> int:
    value = value.strip()
    label = (label or '').strip() or None
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "SELECT COALESCE(MAX(sort_order),0)+1 AS next_order "
                "FROM dictionary_items WHERE dict_type=%s",
                (dict_type,)
            )
            next_order = cur.fetchone()['next_order']
            cur.execute(
                "INSERT INTO dictionary_items (dict_type, value, label, sort_order) "
                "VALUES (%s, %s, %s, %s)",
                (dict_type, value, label, next_order)
            )
        db.commit()
        return cur.lastrowid
    except Exception:
        db.rollback()
        raise


def get_dict_item_type(item_id: int) -> str | None:
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT dict_type FROM dictionary_items WHERE id=%s", (item_id,))
        row = cur.fetchone()
        return row['dict_type'] if row else None


def delete_dict_item(item_id: int) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("DELETE FROM dictionary_items WHERE id=%s", (item_id,))
        db.commit()
    except Exception:
        db.rollback()
        raise


def get_expense_categories() -> list[str]:
    """Returns expense categories from dictionary, merged with any existing in DB."""
    from database import get_db as _get_db
    items = [r['label'] or r['value'] for r in get_dict_items('expense_category')]
    db = _get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT DISTINCT category FROM expenses "
            "WHERE category IS NOT NULL AND category != '' ORDER BY category"
        )
        for r in cur.fetchall():
            if r['category'] not in items:
                items.append(r['category'])
    return items


def get_income_categories() -> list[str]:
    """Returns income categories from dictionary, merged with any existing in DB."""
    from database import get_db as _get_db
    items = [r['label'] or r['value'] for r in get_dict_items('income_category')]
    db = _get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT DISTINCT category FROM incomes "
            "WHERE category IS NOT NULL AND category != '' ORDER BY category"
        )
        for r in cur.fetchall():
            if r['category'] not in items:
                items.append(r['category'])
    return items


def get_vat_rates() -> list[dict]:
    """Returns VAT rates as list of {value, label}."""
    items = get_dict_items('vat_rate')
    if items:
        return [{'value': r['value'], 'label': r['label'] or r['value']} for r in items]
    return [
        {'value': '23',  'label': '23%'},
        {'value': '8',   'label': '8%'},
        {'value': '5',   'label': '5%'},
        {'value': '0',   'label': '0%'},
        {'value': '-1',  'label': 'zw.'},
    ]


def get_payment_methods() -> list[dict]:
    """Returns payment methods as list of {value, label}."""
    items = get_dict_items('payment_method')
    if items:
        return [{'value': r['value'], 'label': r['label'] or r['value']} for r in items]
    return [
        {'value': 'transfer', 'label': 'Przelew / karta'},
        {'value': 'cash',     'label': 'Gotówka'},
    ]
