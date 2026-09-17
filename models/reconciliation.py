"""Uzgadnianie (reconciliation): dwukierunkowe dopasowywanie transakcji
bankowych do już zaksięgowanych wydatków/przychodów.

W przeciwieństwie do importu (routes/imports.py), który wpuszcza surowe dane
(transakcje/faktury) do systemu, ten moduł operuje na etapie PO imporcie:
łączy transakcję bankową (bank_transactions, status='pending') z istniejącym
rekordem księgowym (expenses/incomes), którego kwota nie jest jeszcze w pełni
pokryta wpłatami/wypłatami. Cel: łatwo zweryfikować w obie strony, że (1)
każda opłacona faktura ma odpowiadający jej rekord w księgowości oraz (2)
każdy rekord księgowy ma odpowiadającą mu transakcję bankową.
"""
from database import get_db


def _score(txn_amount_abs: float, txn_desc: str, record_amount: float,
           record_ref: str, record_name: str) -> int:
    """Wspólna heurystyka dopasowania transakcja↔rekord (kwota + numer faktury
    + kontrahent/klient w opisie), spójna z istniejącym /api/bank/search."""
    score = 0
    if record_amount and record_amount > 0 and abs(txn_amount_abs - record_amount) < 0.02:
        score += 2
    desc_lower = (txn_desc or '').lower()
    if record_ref and record_ref.strip().lower() in desc_lower:
        score += 1
    if record_name and len(record_name.strip()) >= 3 and record_name.strip().lower() in desc_lower:
        score += 1
    return score


def get_unmatched_bank_transactions(kind: str = None, limit: int = 300) -> list[dict]:
    """Transakcje bankowe status='pending', opcjonalnie tylko wpływy (kind='income')
    lub tylko wypływy (kind='expense')."""
    db = get_db()
    sql = "SELECT * FROM bank_transactions WHERE status = 'pending'"
    params = []
    if kind == 'income':
        sql += " AND amount > 0"
    elif kind == 'expense':
        sql += " AND amount < 0"
    sql += " ORDER BY date DESC, id DESC LIMIT %s"
    params.append(limit)
    with db.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def get_unmatched_expense_records(limit: int = 300) -> list[dict]:
    """Wydatki, które nie mają jeszcze w 100% pokrycia w transakcjach bankowych."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT e.*,
                      COALESCE((SELECT SUM(ABS(bt.amount)) FROM expense_transactions et
                                JOIN bank_transactions bt ON bt.id = et.bank_txn_id
                                WHERE et.expense_id = e.id), 0) AS matched_amount
               FROM expenses e
               WHERE e.payment_percent < 100
               ORDER BY e.date DESC, e.id DESC
               LIMIT %s""",
            (limit,)
        )
        return cur.fetchall()


def get_unmatched_income_records(limit: int = 300) -> list[dict]:
    """Przychody, które nie są oznaczone jako w pełni opłacone."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT i.*,
                      COALESCE((SELECT SUM(bt.amount) FROM income_transactions it
                                JOIN bank_transactions bt ON bt.id = it.bank_txn_id
                                WHERE it.income_id = i.id), 0) AS matched_amount
               FROM incomes i
               WHERE i.payment_status != 'paid'
               ORDER BY i.date DESC, i.id DESC
               LIMIT %s""",
            (limit,)
        )
        return cur.fetchall()


def get_candidates_for_transaction(txn_id: int, limit: int = 8) -> list[dict]:
    """Dla danej transakcji bankowej: ranking pasujących nieopłaconych rekordów
    (wydatków, jeśli kwota ujemna; przychodów, jeśli kwota dodatnia)."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM bank_transactions WHERE id = %s", (txn_id,))
        txn = cur.fetchone()
    if not txn:
        return []
    txn_abs = abs(float(txn['amount']))
    desc = (txn.get('description') or '') + ' ' + (txn.get('counterparty') or '')

    results = []
    if float(txn['amount']) < 0:
        for rec in get_unmatched_expense_records(limit=1000):
            remaining = max(0.0, float(rec['amount_gross']) - float(rec['matched_amount']))
            score = _score(txn_abs, desc, remaining, rec.get('invoice_number'), rec.get('contractor_name'))
            results.append({'record_type': 'expense', 'record': rec, 'score': score, 'remaining': remaining})
    else:
        for rec in get_unmatched_income_records(limit=1000):
            remaining = max(0.0, float(rec['amount_gross']) - float(rec['matched_amount']))
            score = _score(txn_abs, desc, remaining, rec.get('invoice_number'), rec.get('client_name'))
            results.append({'record_type': 'income', 'record': rec, 'score': score, 'remaining': remaining})

    # Jeśli nic nie pasuje wg heurystyki (score=0 dla wszystkich), i tak pokaż
    # najbliższe kwotowo pozycje — lepsze to niż pusta lista bez żadnej podpowiedzi.
    if results and not any(r['score'] > 0 for r in results):
        results.sort(key=lambda r: abs(r['remaining'] - txn_abs))
        return results[:limit]

    results = [r for r in results if r['score'] > 0]
    results.sort(key=lambda r: (-r['score'], abs(r['remaining'] - txn_abs)))
    return results[:limit]


def get_candidates_for_record(record_type: str, record_id: int, limit: int = 8) -> list[dict]:
    """Dla danego rekordu (wydatku/przychodu): ranking pasujących wolnych transakcji."""
    db = get_db()
    if record_type == 'expense':
        with db.cursor() as cur:
            cur.execute("SELECT * FROM expenses WHERE id = %s", (record_id,))
            rec = cur.fetchone()
        if not rec:
            return []
        ref, name, kind = rec.get('invoice_number'), rec.get('contractor_name'), 'expense'
    else:
        with db.cursor() as cur:
            cur.execute("SELECT * FROM incomes WHERE id = %s", (record_id,))
            rec = cur.fetchone()
        if not rec:
            return []
        ref, name, kind = rec.get('invoice_number'), rec.get('client_name'), 'income'

    matched_amount = 0.0
    with db.cursor() as cur:
        table = 'expense_transactions' if record_type == 'expense' else 'income_transactions'
        col = 'expense_id' if record_type == 'expense' else 'income_id'
        cur.execute(
            f"SELECT COALESCE(SUM(ABS(bt.amount)), 0) AS total FROM {table} t "
            f"JOIN bank_transactions bt ON bt.id = t.bank_txn_id WHERE t.{col} = %s",
            (record_id,)
        )
        matched_amount = float(cur.fetchone()['total'])
    remaining = max(0.0, float(rec['amount_gross']) - matched_amount)

    txns = get_unmatched_bank_transactions(kind=kind, limit=1000)
    results = []
    for txn in txns:
        txn_abs = abs(float(txn['amount']))
        desc = (txn.get('description') or '') + ' ' + (txn.get('counterparty') or '')
        score = _score(txn_abs, desc, remaining, ref, name)
        results.append({'transaction': txn, 'score': score})

    if results and not any(r['score'] > 0 for r in results):
        results.sort(key=lambda r: abs(abs(float(r['transaction']['amount'])) - remaining))
        return results[:limit]

    results = [r for r in results if r['score'] > 0]
    results.sort(key=lambda r: (-r['score'], abs(abs(float(r['transaction']['amount'])) - remaining)))
    return results[:limit]


def link(record_type: str, record_id: int, bank_txn_id: int) -> dict:
    """Łączy transakcję bankową z wydatkiem/przychodem. Dla przychodu: jeśli suma
    powiązanych transakcji pokrywa pełną kwotę brutto, oznacza go dodatkowo jako
    opłacony (payment_status='paid'), analogicznie do automatycznego przeliczania
    payment_percent dla wydatków."""
    if record_type == 'expense':
        from models.expense import link_transaction
        return link_transaction(record_id, bank_txn_id)
    from models.income import link_income_transaction, get_income_by_id, bulk_set_payment_status
    result = link_income_transaction(record_id, bank_txn_id)
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT COALESCE(SUM(bt.amount), 0) AS total FROM income_transactions it "
            "JOIN bank_transactions bt ON bt.id = it.bank_txn_id WHERE it.income_id = %s",
            (record_id,)
        )
        total = float(cur.fetchone()['total'])
    income = get_income_by_id(record_id)
    if income and total >= float(income['amount_gross']) - 0.02:
        bulk_set_payment_status([record_id], 'paid')
    return result


def unlink(record_type: str, record_id: int, bank_txn_id: int) -> dict:
    if record_type == 'expense':
        from models.expense import unlink_transaction
        return unlink_transaction(record_id, bank_txn_id)
    from models.income import unlink_income_transaction
    return unlink_income_transaction(record_id, bank_txn_id)


def summary() -> dict:
    """Podsumowanie kompletności uzgodnień w obie strony."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS cnt FROM bank_transactions WHERE status='pending' AND amount < 0")
        unmatched_expense_txns = cur.fetchone()['cnt']
        cur.execute("SELECT COUNT(*) AS cnt FROM bank_transactions WHERE status='pending' AND amount > 0")
        unmatched_income_txns = cur.fetchone()['cnt']
        cur.execute("SELECT COUNT(*) AS cnt FROM expenses WHERE payment_percent < 100")
        unmatched_expense_records = cur.fetchone()['cnt']
        cur.execute("SELECT COUNT(*) AS cnt FROM incomes WHERE payment_status != 'paid'")
        unmatched_income_records = cur.fetchone()['cnt']
        cur.execute("SELECT COUNT(*) AS cnt FROM fakturownia_invoices WHERE status='pending'")
        pending_fakturownia = cur.fetchone()['cnt']
        cur.execute("SELECT COUNT(*) AS cnt FROM gdrive_invoices WHERE status='pending'")
        pending_gdrive = cur.fetchone()['cnt']

    return {
        'unmatched_expense_transactions': unmatched_expense_txns,
        'unmatched_income_transactions': unmatched_income_txns,
        'unmatched_expense_records': unmatched_expense_records,
        'unmatched_income_records': unmatched_income_records,
        'pending_documents': pending_fakturownia + pending_gdrive,
        'total_open_items': (unmatched_expense_txns + unmatched_income_txns
                              + unmatched_expense_records + unmatched_income_records),
    }
