"""Rozliczanie dokumentów bez przelewu i szukanie przelewu od strony dokumentu."""
import unittest
from datetime import date
from decimal import Decimal
from unittest import mock

from services import fin_bank, fin_settlement
from services.fin_invoice import FinWriteError

DRIVE_ID = 9_000_000_000_007


def doc(**over) -> dict:
    row = {'fakturownia_id': 500, 'number': 'FV 7/2026', 'is_income': 0, 'status': 'issued',
           'issue_date': date(2026, 6, 1), 'payment_to': date(2026, 6, 15), 'paid_date': None,
           'gross_pln': Decimal('246.00'), 'paid_amount': Decimal('0'), 'currency': 'PLN',
           'counterparty_name': 'Warsztat Kowalski', 'counterparty_tax_no_norm': '5250001111'}
    row.update(over)
    return row


def transfer(**over) -> dict:
    row = {'id': 11, 'bank': 'alior', 'booked_date': date(2026, 6, 14), 'amount': Decimal('-246.00'),
           'currency': 'PLN', 'counterparty_name': 'WARSZTAT KOWALSKI', 'title': 'FV 7/2026',
           'matched_amount': Decimal('0'), 'status': 'pending'}
    row.update(over)
    return row


class SettleTest(unittest.TestCase):
    def setUp(self):
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(fin_settlement, 'get_db').start()
        mock.patch.object(fin_settlement.fin_audit, 'log').start()
        self.get = mock.patch.object(fin_settlement.fin_document, 'get_document', return_value=doc()).start()
        self.save = mock.patch.object(fin_settlement.store, 'save').start()
        self.marked = mock.patch.object(fin_settlement.store, 'set_payment_marked').start()
        self.paid = mock.patch.object(fin_settlement.fin_invoice, 'mark_paid',
                                      return_value={'status': 'paid'}).start()

    def test_unpaid_document_gets_the_full_payment_on_the_settlement_date(self):
        out = fin_settlement.settle(500, 'cash', settled_date='2026-06-20', actor='user:1')
        self.save.assert_called_once_with(500, 'cash', date(2026, 6, 20), '', created_by='user:1')
        self.paid.assert_called_once_with(500, paid_date=date(2026, 6, 20), actor='user:1')
        self.marked.assert_called_once_with(500)
        self.assertTrue(out['pushed'])

    def test_paid_document_only_gets_the_reason(self):
        """Opłaconej faktury nie ruszamy — a data rozliczenia to jej data zapłaty."""
        self.get.return_value = doc(status='paid', paid_date=date(2026, 6, 3))
        out = fin_settlement.settle(500, 'other_account')
        self.assertEqual(self.save.call_args[0][2], date(2026, 6, 3))
        self.paid.assert_not_called()
        self.assertTrue(out['already_paid'])
        self.assertFalse(out['pushed'])

    def test_push_can_be_switched_off(self):
        out = fin_settlement.settle(500, 'offset', push=False)
        self.save.assert_called_once()
        self.paid.assert_not_called()
        self.assertFalse(out['pushed'])

    def test_refused_payment_keeps_the_decision_and_reports_the_reason(self):
        self.paid.side_effect = FinWriteError('Fakturownia odrzuciła zapis płatności: 422')
        out = fin_settlement.settle(500, 'cash')
        self.save.assert_called_once()
        self.marked.assert_not_called()
        self.assertIn('odrzuciła', out['push_error'])

    def test_unknown_reason_is_refused_before_any_write(self):
        with self.assertRaises(FinWriteError):
            fin_settlement.settle(500, 'bo tak')
        self.save.assert_not_called()

    def test_other_needs_a_note(self):
        with self.assertRaises(FinWriteError) as ctx:
            fin_settlement.settle(500, 'other', note='  ')
        self.assertIn('notatkę', str(ctx.exception))
        fin_settlement.settle(500, 'other', note='barter za szkolenie')
        self.assertEqual(self.save.call_args[0][3], 'barter za szkolenie')

    def test_bad_date_and_unknown_document_are_refused(self):
        with self.assertRaises(FinWriteError):
            fin_settlement.settle(500, 'cash', settled_date='wczoraj')
        self.get.return_value = None
        with self.assertRaises(FinWriteError):
            fin_settlement.settle(500, 'cash')
        self.save.assert_not_called()

    def test_bulk_keeps_going_after_a_failure(self):
        self.get.side_effect = [doc(), None, doc(status='paid')]
        out = fin_settlement.settle_many([500, 501, 502], 'cash')
        self.assertEqual((out['settled'], out['pushed'], len(out['errors'])), (2, 1, 1))


class UnsettleTest(unittest.TestCase):
    def setUp(self):
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(fin_settlement, 'get_db').start()
        mock.patch.object(fin_settlement.fin_audit, 'log').start()
        self.delete = mock.patch.object(fin_settlement.store, 'delete', return_value=1).start()
        mock.patch.object(fin_settlement.fin_bank, 'applied_to_document',
                          return_value=Decimal('0')).start()
        self.paid = mock.patch.object(fin_settlement.fin_invoice, 'mark_paid').start()

    def unsettle(self, fakturownia_id, row):
        with mock.patch.object(fin_settlement.store, 'get', return_value=row):
            return fin_settlement.unsettle(fakturownia_id)

    def test_fakturownia_payment_is_left_alone(self):
        out = self.unsettle(500, {'reason': 'cash', 'payment_marked': 1})
        self.delete.assert_called_once_with(500)
        self.paid.assert_not_called()
        self.assertTrue(out['payment_marked'])
        self.assertFalse(out['payment_reverted'])

    def test_drive_document_goes_back_to_what_its_transfers_paid(self):
        out = self.unsettle(DRIVE_ID, {'reason': 'cash', 'payment_marked': 1})
        self.paid.assert_called_once_with(DRIVE_ID, amount=Decimal('0'), actor='settlement')
        self.assertTrue(out['payment_reverted'])

    def test_drive_document_paid_before_the_decision_stays_paid(self):
        out = self.unsettle(DRIVE_ID, {'reason': 'cash', 'payment_marked': 0})
        self.paid.assert_not_called()
        self.assertFalse(out['payment_reverted'])

    def test_nothing_to_undo(self):
        out = self.unsettle(500, None)
        self.assertEqual(out['removed'], 0)
        self.delete.assert_not_called()


class SearchTransfersTest(unittest.TestCase):
    def search(self, document, rows, query=''):
        with mock.patch.object(fin_bank, '_open_transfers', return_value=rows) as fetch:
            return fin_bank.search_transfers(document, query), fetch

    def test_best_transfer_comes_first_with_what_is_left_on_it(self):
        rows = [transfer(id=12, amount=Decimal('-90.00'), counterparty_name='ORLEN', title='paliwo'),
                transfer(matched_amount=Decimal('46.00'), status='partial')]
        found, fetch = self.search(doc(), rows)
        self.assertEqual(found[0]['transaction_id'], 11)
        self.assertEqual(found[0]['amount_left'], Decimal('200.00'))
        # Okno: 45 dni przed wystawieniem, 180 po — i tylko wypływy dla kosztu.
        self.assertEqual(fetch.call_args[0], (date(2026, 4, 17), date(2026, 11, 28)))
        self.assertFalse(fetch.call_args.kwargs['is_income'])

    def test_a_phrase_searches_the_whole_statement_and_keeps_weak_hits(self):
        rows = [transfer(id=12, amount=Decimal('-90.00'), counterparty_name='ORLEN', title='paliwo',
                         booked_date=date(2026, 1, 2))]
        found, fetch = self.search(doc(), rows, query='orlen')
        self.assertEqual(len(found), 1)
        self.assertEqual(fetch.call_args.kwargs, {'is_income': False, 'query': 'orlen'})

    def test_document_without_a_date_has_no_window_to_look_in(self):
        found, fetch = self.search(doc(issue_date=None), [transfer()])
        self.assertEqual(found, [])
        fetch.assert_not_called()

    def test_list_gets_one_best_transfer_per_document(self):
        income = doc(fakturownia_id=600, is_income=1, number='3/06/2026')
        rows = [transfer(), transfer(id=12, amount=Decimal('246.00'))]
        with mock.patch.object(fin_bank, '_open_transfers', return_value=rows):
            out = fin_bank.suggest_transfers_for_docs([doc(), income, doc(fakturownia_id=700, issue_date=None)])
        self.assertEqual(out[500]['transaction_id'], 11)
        # Wpływ o tej samej kwocie nie jest zapłatą kosztu — i odwrotnie.
        self.assertNotIn(700, out)
        self.assertTrue(600 not in out or out[600]['transaction_id'] == 12)


class LinkOnSettledDocumentTest(unittest.TestCase):
    def test_transfer_linked_to_a_settled_paid_document_does_not_rewrite_its_payment(self):
        txn = {'id': 1, 'booked_date': date(2026, 6, 14), 'amount': Decimal('-100.00')}
        with mock.patch.object(fin_bank.fin_bank, 'get_transaction', return_value=txn), \
             mock.patch.object(fin_bank.fin_bank, 'links_for_transaction', return_value=[]), \
             mock.patch('models.fin_document.get_document', return_value=doc(status='paid')), \
             mock.patch('models.fin_settlement.get', return_value={'reason': 'cash'}), \
             mock.patch.object(fin_bank.fin_bank, 'add_link') as add_link, \
             mock.patch.object(fin_bank.fin_bank, 'refresh_status', return_value='matched'), \
             mock.patch.object(fin_bank, 'get_db'), \
             mock.patch('services.fin_invoice.mark_paid') as mark_paid:
            out = fin_bank.link_payment(1, 500)
        add_link.assert_called_once()
        mark_paid.assert_not_called()
        self.assertFalse(out['pushed'])


if __name__ == '__main__':
    unittest.main()
