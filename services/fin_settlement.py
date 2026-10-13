"""Rozliczanie dokumentów, do których nie ma przelewu na wyciągu.

Kolejka rozliczeń ma dwie strony: operacja szuka dokumentu (`services/fin_bank`)
i dokument szuka operacji. Gdy operacji nie ma i nie będzie — gotówka, karta
prywatna, kompensata — dokument zamyka się tutaj decyzją z powodem.

Zapłata zachowuje się jak przy powiązaniu z przelewem: decyzja zapisuje się
zawsze, a dopisanie zapłaty jest osobnym krokiem, którego odmowa wraca jako
`push_error`, nie jako porażka całej operacji.
"""
from datetime import date, datetime

import models.fin_audit as fin_audit
import models.fin_bank as fin_bank
import models.fin_document as fin_document
import models.fin_drive as fin_drive
import models.fin_settlement as store
from database import get_db
from models.fin_settlement import REASONS
from services import fin_invoice
from services.fin_invoice import FinWriteError


def _day(value) -> date | None:
    if value in (None, ''):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value)[:10], '%Y-%m-%d').date()
    except ValueError:
        raise FinWriteError(f'„{value}” to nie data — podaj ją jako RRRR-MM-DD.')


def settle(fakturownia_id: int, reason: str, settled_date=None, note: str = '',
           push: bool = True, actor: str = '') -> dict:
    """Zamyka dokument bez przelewu. Nieopłacony — domyślnie — dostaje pełną
    zapłatę z datą rozliczenia; opłaconego nie ruszamy, zapisujemy sam powód."""
    if reason not in REASONS:
        raise FinWriteError('Wybierz powód rozliczenia bez przelewu.')
    note = (note or '').strip()
    if reason == 'other' and not note:
        raise FinWriteError('Przy powodzie „inne” dopisz notatkę — za rok nikt nie zgadnie, o co chodziło.')
    doc = fin_document.get_document(int(fakturownia_id))
    if not doc:
        raise FinWriteError(f'Nie znam dokumentu {fakturownia_id} — zsynchronizuj najpierw lustro.')

    already_paid = doc['status'] == 'paid'
    when = _day(settled_date) or (doc.get('paid_date') if already_paid else None) or date.today()

    db = get_db()
    try:
        store.save(fakturownia_id, reason, when, note, created_by=actor)
        fin_audit.log('settle_without_transfer', actor=actor, fakturownia_id=int(fakturownia_id),
                      payload={'reason': reason, 'settled_date': when, 'note': note,
                               'push': bool(push and not already_paid)}, ok=True)
        db.commit()
    except Exception:
        db.rollback()
        raise

    result = {'fakturownia_id': int(fakturownia_id), 'number': doc.get('number'),
              'reason': reason, 'settled_date': when, 'already_paid': already_paid,
              'pushed': False, 'document': None}
    if push and not already_paid:
        try:
            paid = fin_invoice.mark_paid(int(fakturownia_id), paid_date=when,
                                         actor=actor or 'settlement')
        except FinWriteError as e:
            result['push_error'] = str(e)
        else:
            store.set_payment_marked(fakturownia_id)
            db.commit()
            result['pushed'] = True
            result['document'] = paid
    return result


def settle_many(ids: list[int], reason: str, settled_date=None, note: str = '',
                push: bool = True, actor: str = '') -> dict:
    """Ta sama decyzja dla wielu dokumentów — np. cała historia sprzed
    pierwszego wyciągu. Błąd jednego dokumentu nie zatrzymuje reszty."""
    out = {'settled': 0, 'pushed': 0, 'push_errors': [], 'errors': []}
    for fakturownia_id in ids:
        try:
            result = settle(fakturownia_id, reason, settled_date=settled_date, note=note,
                            push=push, actor=actor)
        except FinWriteError as e:
            out['errors'].append(str(e))
            continue
        out['settled'] += 1
        if result['pushed']:
            out['pushed'] += 1
        elif result.get('push_error'):
            out['push_errors'].append(f"{result['number'] or fakturownia_id}: {result['push_error']}")
    return out


def unsettle(fakturownia_id: int, actor: str = '') -> dict:
    """Cofa decyzję — dokument wraca do kolejki. Zapłaty w Fakturowni nie
    cofamy (tak samo jak przy odwiązaniu przelewu); dokument z Dysku żyje tylko
    w CRM, więc jego zapłata wraca do sumy powiązanych przelewów."""
    row = store.get(fakturownia_id)
    if not row:
        return {'removed': 0, 'payment_marked': False, 'payment_reverted': False}
    db = get_db()
    try:
        store.delete(fakturownia_id)
        fin_audit.log('unsettle', actor=actor, fakturownia_id=int(fakturownia_id),
                      payload={'reason': row['reason']}, ok=True)
        db.commit()
    except Exception:
        db.rollback()
        raise
    result = {'removed': 1, 'payment_marked': bool(row['payment_marked']), 'payment_reverted': False}
    if row['payment_marked'] and fin_drive.is_drive_document(fakturownia_id):
        fin_invoice.mark_paid(int(fakturownia_id),
                              amount=fin_bank.applied_to_document(fakturownia_id),
                              actor=actor or 'settlement')
        result['payment_reverted'] = True
    return result
