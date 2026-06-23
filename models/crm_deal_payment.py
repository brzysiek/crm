from database import get_db


def get_payments_for_deal(deal_id: int) -> list[dict]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT * FROM crm_deal_payments WHERE deal_id=%s ORDER BY pay_month",
            (deal_id,)
        )
        return cur.fetchall()


def add_payment(deal_id: int, pay_month: str, amount_net: float) -> int:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "INSERT INTO crm_deal_payments (deal_id, pay_month, amount_net) VALUES (%s, %s, %s)",
                (deal_id, pay_month, amount_net)
            )
        db.commit()
        return cur.lastrowid
    except Exception:
        db.rollback()
        raise


def delete_payment(payment_id: int) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("DELETE FROM crm_deal_payments WHERE id=%s", (payment_id,))
        db.commit()
    except Exception:
        db.rollback()
        raise


def maybe_auto_schedule_payment(deal_id: int, end_date, amount) -> None:
    """Jeśli ustawiono datę zakończenia i interes nie ma jeszcze żadnych płatności,
    automatycznie tworzy jedną płatność na 100% wartości interesu w miesiącu zakończenia.
    Jeśli jakiekolwiek płatności już istnieją, nie modyfikuje ich."""
    if not end_date or not amount:
        return
    if get_payments_for_deal(deal_id):
        return
    pay_month = f"{str(end_date)[:7]}-01"
    add_payment(deal_id, pay_month, float(amount))


def get_payments_in_range(start_month: str, end_month: str,
                           exclude_stages: tuple = ('lost',)) -> list[dict]:
    """start_month/end_month w formacie 'YYYY-MM-01'. Domyślnie wyklucza interesy przegrane
    (ich przychód się nie zrealizuje), pozostałe etapy liczą się do planu."""
    db = get_db()
    sql = ("SELECT p.*, d.name AS deal_name, d.stage AS deal_stage, "
           "co.name AS company_name, co.short_name AS company_short_name "
           "FROM crm_deal_payments p "
           "JOIN crm_deals d ON d.id = p.deal_id "
           "LEFT JOIN crm_companies co ON co.id = d.company_id "
           "WHERE p.pay_month BETWEEN %s AND %s")
    params = [start_month, end_month]
    if exclude_stages:
        placeholders = ','.join(['%s'] * len(exclude_stages))
        sql += f" AND d.stage NOT IN ({placeholders})"
        params.extend(exclude_stages)
    sql += " ORDER BY p.pay_month, d.name"
    with db.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()
