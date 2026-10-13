"""Dokumenty z Dysku w Finansach v2: odczyt OCR → kolejka → dokument → zapłata lokalna."""
import unittest
from datetime import date
from decimal import Decimal
from unittest import mock

import models.fin_drive as store
from services import fin_bank, fin_drive, fin_invoice
from services.fin_drive import FinDriveError
from services.fin_invoice import FinWriteError

OCR = {
    'invoice_number': 'INV-2026-77', 'vendor_name': 'Acme GmbH', 'vendor_nip': 'DE123456789',
    'buyer_name': 'Trustart', 'buyer_nip': '5250000000',
    'issue_date': '2026-09-03', 'payment_to': '2026-09-17', 'currency': 'eur',
    'amount_gross': 123.0, 'amount_net': 100.0, 'vat_amount': 23.0,
    'invoice_type': 'expense', 'confidence_note': 'ok',
}

FORM = {
    'is_income': '0', 'kind': 'vat', 'number': 'INV-2026-77', 'counterparty_name': 'Acme GmbH',
    'counterparty_tax_no': 'DE123456789', 'issue_date': '2026-09-03', 'payment_to': '',
    'currency': 'PLN', 'price_net': '100,00', 'price_tax': '23,00', 'price_gross': '123,00',
}


def queue_row(**over):
    row = {'id': 7, 'gdrive_file_id': 'file-1', 'file_name': 'INV-2026-77.pdf', 'status': 'pending',
           **fin_drive.clean_fields(FORM)}
    row.update(over)
    return row


class MapOcrTest(unittest.TestCase):
    def test_expense_takes_the_vendor_as_counterparty(self):
        row = fin_drive.map_ocr(OCR, file_name='a.pdf', modified='2026-09-04T10:11:12.000Z')
        self.assertEqual(row['is_income'], 0)
        self.assertEqual(row['counterparty_name'], 'Acme GmbH')
        self.assertEqual(row['counterparty_tax_no'], 'DE123456789')
        self.assertEqual(row['currency'], 'EUR')
        self.assertEqual(row['issue_date'], date(2026, 9, 3))
        self.assertEqual(row['price_gross'], Decimal('123.00'))
        self.assertEqual(row['file_modified_at'].year, 2026)

    def test_income_takes_the_buyer_as_counterparty(self):
        row = fin_drive.map_ocr({**OCR, 'invoice_type': 'income'})
        self.assertEqual(row['is_income'], 1)
        self.assertEqual(row['counterparty_name'], 'Trustart')
        self.assertEqual(row['counterparty_tax_no'], '5250000000')

    def test_missing_amount_follows_from_the_other_two(self):
        row = fin_drive.map_ocr({**OCR, 'amount_net': None})
        self.assertEqual(row['price_net'], Decimal('100.00'))
        row = fin_drive.map_ocr({**OCR, 'amount_gross': None})
        self.assertEqual(row['price_gross'], Decimal('123.00'))

    def test_garbage_does_not_break_the_queue(self):
        row = fin_drive.map_ocr({'issue_date': 'wczoraj', 'amount_gross': 'dużo', 'currency': None})
        self.assertIsNone(row['issue_date'])
        self.assertEqual(row['price_gross'], Decimal('0'))
        self.assertEqual(row['currency'], 'PLN')


class CleanFieldsTest(unittest.TestCase):
    def test_polish_number_format_is_accepted(self):
        out = fin_drive.clean_fields({**FORM, 'price_gross': '1 234,56', 'price_net': '', 'price_tax': '0'})
        self.assertEqual(out['price_gross'], Decimal('1234.56'))
        self.assertEqual(out['price_net'], Decimal('1234.56'))

    def test_amounts_must_add_up(self):
        with self.assertRaises(FinDriveError):
            fin_drive.clean_fields({**FORM, 'price_net': '90'})

    def test_issue_date_and_gross_are_required(self):
        with self.assertRaises(FinDriveError):
            fin_drive.clean_fields({**FORM, 'issue_date': ''})
        with self.assertRaises(FinDriveError):
            fin_drive.clean_fields({**FORM, 'price_gross': '', 'price_net': '', 'price_tax': ''})

    def test_unknown_kind_and_currency_are_refused(self):
        with self.assertRaises(FinDriveError):
            fin_drive.clean_fields({**FORM, 'kind': 'proforma'})
        with self.assertRaises(FinDriveError):
            fin_drive.clean_fields({**FORM, 'currency': 'euro'})


class BuildDocumentTest(unittest.TestCase):
    def test_document_gets_an_id_outside_fakturownia_range(self):
        doc = fin_drive.build_document(queue_row(), Decimal('1'))
        self.assertEqual(doc['fakturownia_id'], store.DRIVE_ID_BASE + 7)
        self.assertTrue(store.is_drive_document(doc['fakturownia_id']))
        self.assertFalse(store.is_drive_document(569256970))
        self.assertEqual(doc['status'], 'issued')
        self.assertEqual(doc['vat_date'], date(2026, 9, 3))

    def test_foreign_currency_is_converted_at_the_given_rate(self):
        doc = fin_drive.build_document(queue_row(currency='EUR'), Decimal('4.2500'))
        self.assertEqual(doc['price_gross'], Decimal('123.00'))
        self.assertEqual(doc['gross_pln'], Decimal('522.75'))
        self.assertEqual(doc['net_pln'] + doc['tax_pln'], doc['gross_pln'])

    def test_manual_rate_wins_over_nbp(self):
        with mock.patch('services.nbp.get_nbp_rate') as nbp:
            rate = fin_drive._exchange_rate('EUR', date(2026, 9, 3), '4,30')
        self.assertEqual(rate, Decimal('4.30'))
        nbp.assert_not_called()

    def test_missing_nbp_rate_asks_for_a_manual_one(self):
        with mock.patch('services.nbp.get_nbp_rate', return_value=None):
            with self.assertRaises(FinDriveError):
                fin_drive._exchange_rate('EUR', date(2026, 9, 3))


class AcceptTest(unittest.TestCase):
    def setUp(self):
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(fin_drive, 'get_db').start()
        self.get = mock.patch.object(fin_drive.fin_drive, 'get', return_value=queue_row()).start()
        self.update = mock.patch.object(fin_drive.fin_drive, 'update_fields').start()
        self.status = mock.patch.object(fin_drive.fin_drive, 'set_status').start()
        self.upsert = mock.patch.object(fin_drive.fin_document, 'upsert_document').start()
        self.source = mock.patch.object(fin_drive.fin_document, 'mark_source').start()
        self.delete = mock.patch.object(fin_drive.fin_document, 'delete_document').start()
        mock.patch.object(fin_drive.fin_audit, 'log').start()
        self.rules = mock.patch.object(fin_drive, 'apply_rules', return_value={'assigned': 1}).start()

    def test_accept_creates_a_document_marked_as_drive(self):
        out = fin_drive.accept(7, FORM, actor='user:1')
        doc_id = store.DRIVE_ID_BASE + 7
        self.assertEqual(out['fakturownia_id'], doc_id)
        self.assertEqual(self.upsert.call_args[0][0]['gross_pln'], Decimal('123.00'))
        self.source.assert_called_once_with(doc_id, 'gdrive', 'file-1')
        self.status.assert_called_once_with(7, 'accepted', fakturownia_id=doc_id, actor='user:1')
        self.rules.assert_called_once_with(only_ids=[doc_id])

    def test_bad_form_leaves_everything_untouched(self):
        with self.assertRaises(FinDriveError):
            fin_drive.accept(7, {**FORM, 'price_gross': 'abc'})
        self.upsert.assert_not_called()
        self.status.assert_not_called()

    def test_bulk_accept_takes_queue_values_and_skips_broken_reads(self):
        # 7 jest poprawny, 8 nie ma kwoty — zostaje w kolejce, reszta przechodzi.
        self.get.side_effect = lambda i: queue_row() if i == 7 else queue_row(price_gross=Decimal('0'))
        out = fin_drive.accept_many([7, 8], actor='user:1')
        self.assertEqual(out['accepted'], 1)
        self.assertEqual(len(out['errors']), 1)
        self.assertEqual(self.upsert.call_count, 1)

    def test_accepted_file_is_not_accepted_twice(self):
        self.get.return_value = queue_row(status='accepted')
        with self.assertRaises(FinDriveError):
            fin_drive.accept(7, FORM)
        self.upsert.assert_not_called()

    def test_return_to_queue_is_blocked_by_a_payment_link(self):
        mock.patch.object(fin_drive.fin_drive, 'get_by_document', return_value=queue_row()).start()
        mock.patch.object(fin_drive.fin_bank, 'links_for_document', return_value=[{'id': 1}]).start()
        with self.assertRaises(FinDriveError):
            fin_drive.return_to_queue(store.DRIVE_ID_BASE + 7)
        self.delete.assert_not_called()

    def test_return_to_queue_removes_the_document(self):
        mock.patch.object(fin_drive.fin_drive, 'get_by_document', return_value=queue_row()).start()
        mock.patch.object(fin_drive.fin_bank, 'links_for_document', return_value=[]).start()
        fin_drive.return_to_queue(store.DRIVE_ID_BASE + 7, actor='user:1')
        self.delete.assert_called_once_with(store.DRIVE_ID_BASE + 7)
        self.status.assert_called_once_with(7, 'pending', actor='user:1')


class OcrFileTest(unittest.TestCase):
    def setUp(self):
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(fin_drive, 'get_db').start()
        mock.patch.object(fin_drive, 'get_setting', return_value='x').start()
        self.states = mock.patch.object(fin_drive.fin_drive, 'file_states', return_value={}).start()
        self.save = mock.patch.object(fin_drive.fin_drive, 'save_ocr',
                                      return_value={'outcome': 'new', 'id': 7}).start()
        self.client = mock.Mock()
        self.client.download_file.return_value = b'%PDF'

    def test_result_goes_to_the_queue(self):
        with mock.patch('services.gemini_ocr.ocr_invoice_pdf', return_value=dict(OCR)):
            out = fin_drive.ocr_file('file-1', file_name='a.pdf', client=self.client)
        self.assertEqual(out['outcome'], 'new')
        self.assertEqual(self.save.call_args[0][0], 'file-1')
        self.assertEqual(self.save.call_args[0][1]['number'], 'INV-2026-77')

    def test_accepted_file_is_not_read_again(self):
        self.states.return_value = {'file-1': 'accepted'}
        with mock.patch('services.gemini_ocr.ocr_invoice_pdf') as ocr:
            out = fin_drive.ocr_file('file-1', client=self.client)
        self.assertEqual(out['outcome'], 'accepted')
        ocr.assert_not_called()
        self.client.download_file.assert_not_called()

    def test_ocr_error_reaches_the_user(self):
        with mock.patch('services.gemini_ocr.ocr_invoice_pdf', return_value={'error': 'limit'}):
            with self.assertRaises(FinDriveError) as ctx:
                fin_drive.ocr_file('file-1', client=self.client)
        self.assertIn('limit', str(ctx.exception))
        self.save.assert_not_called()


DRIVE_DOC = {'fakturownia_id': store.DRIVE_ID_BASE + 7, 'number': 'INV-2026-77', 'source': 'gdrive',
             'is_income': 0, 'price_gross': Decimal('123.00'), 'gross_pln': Decimal('522.75'),
             'paid_amount': Decimal('0'), 'gov_status': '', 'status': 'issued'}


class LocalPaymentTest(unittest.TestCase):
    """Dokumentu z Dysku nie ma w Fakturowni — zapłata nie może tam trafić."""

    def setUp(self):
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(fin_invoice, 'get_db').start()
        mock.patch.object(fin_invoice.fin_audit, 'log').start()
        mock.patch.object(fin_invoice.fin_document, 'get_document', return_value=dict(DRIVE_DOC)).start()
        self.set = mock.patch.object(fin_invoice.fin_document, 'set_local_payment').start()
        self.api = mock.patch.object(fin_invoice.FakturowniaApi, 'from_settings').start()

    def test_full_payment_is_stored_locally_in_pln(self):
        out = fin_invoice.mark_paid(DRIVE_DOC['fakturownia_id'], paid_date='2026-09-10')
        self.set.assert_called_once_with(DRIVE_DOC['fakturownia_id'], Decimal('522.75'), '2026-09-10', 'paid')
        self.assertEqual(out['amount_left'], Decimal('0'))
        self.assertTrue(out['local'])
        self.api.assert_not_called()

    def test_partial_payment(self):
        out = fin_invoice.mark_paid(DRIVE_DOC['fakturownia_id'], amount='200', paid_date='2026-09-10')
        self.assertEqual(out['status'], 'partial')
        self.assertEqual(out['amount_left'], Decimal('322.75'))

    def test_zero_clears_the_payment(self):
        out = fin_invoice.mark_paid(DRIVE_DOC['fakturownia_id'], amount=Decimal('0'))
        self.set.assert_called_once_with(DRIVE_DOC['fakturownia_id'], Decimal('0'), None, 'issued')
        self.assertEqual(out['status'], 'issued')

    def test_edit_and_ksef_are_refused(self):
        with self.assertRaises(FinWriteError):
            fin_invoice.update_document(DRIVE_DOC['fakturownia_id'], {'description': 'x'})
        with self.assertRaises(FinWriteError):
            fin_invoice.send_to_ksef(DRIVE_DOC['fakturownia_id'])
        self.api.return_value.assert_not_called()


class UnlinkTest(unittest.TestCase):
    def setUp(self):
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(fin_bank, 'get_db').start()
        mock.patch.object(fin_bank.fin_bank, 'remove_link', return_value=1).start()
        mock.patch.object(fin_bank.fin_bank, 'refresh_status', return_value='new').start()
        mock.patch.object(fin_bank.fin_bank, 'applied_to_document', return_value=Decimal('100.00')).start()
        self.paid = mock.patch.object(fin_invoice, 'mark_paid').start()
        self.settlement = mock.patch('models.fin_settlement.get', return_value=None).start()

    def test_settled_drive_document_keeps_its_payment(self):
        """Rozliczony bez przelewu: o zapłacie mówi tamta decyzja, nie suma powiązań."""
        self.settlement.return_value = {'reason': 'cash'}
        out = fin_bank.unlink_payment(5, DRIVE_DOC['fakturownia_id'])
        self.paid.assert_not_called()
        self.assertFalse(out['payment_reverted'])

    def test_drive_document_payment_follows_the_remaining_links(self):
        out = fin_bank.unlink_payment(5, DRIVE_DOC['fakturownia_id'])
        self.paid.assert_called_once_with(DRIVE_DOC['fakturownia_id'], amount=Decimal('100.00'), actor='bank')
        self.assertTrue(out['payment_reverted'])

    def test_fakturownia_payment_is_left_alone(self):
        out = fin_bank.unlink_payment(5, 569256970)
        self.paid.assert_not_called()
        self.assertFalse(out['payment_reverted'])


class ForeignCurrencyMatchTest(unittest.TestCase):
    """Faktura w EUR zapłacona kartą: bank liczy po swoim kursie, dokument po NBP."""

    TXN = {'id': 327, 'booked_date': date(2026, 9, 17), 'amount': Decimal('-342.98'),
           'title': 'ANTHROPIC* CLAUDE SUB SAN FRANCISCO US',
           'counterparty_name': 'ANTHROPIC* CLAUDE SUB SAN FRANCISCO US'}
    DOC = {'fakturownia_id': store.DRIVE_ID_BASE + 4, 'number': 'CXHRDSAO-0010', 'is_income': 0,
           'issue_date': date(2026, 9, 17), 'payment_to': None, 'status': 'issued',
           'gross_pln': Decimal('327.24'), 'paid_amount': Decimal('0'), 'currency': 'EUR',
           'source': 'gdrive', 'counterparty_name': 'Anthropic, PBC', 'counterparty_tax_no_norm': ''}

    def test_bank_rate_difference_still_counts_as_the_same_amount(self):
        out = fin_bank.score_match(self.TXN, self.DOC)
        self.assertIn('kwota zgodna z EUR po kursie banku', out['reasons'])
        self.assertNotIn('przelew większy niż dokument', out['reasons'])
        self.assertGreaterEqual(out['score'], 25)
        self.assertEqual(out['source'], 'gdrive')

    def test_pln_document_gets_no_such_allowance(self):
        out = fin_bank.score_match(self.TXN, {**self.DOC, 'currency': 'PLN'})
        self.assertIn('przelew większy niż dokument', out['reasons'])

    def test_far_off_amount_is_not_explained_by_the_rate(self):
        out = fin_bank.score_match({**self.TXN, 'amount': Decimal('-82.00')}, self.DOC)
        self.assertNotIn('kwota zgodna z EUR po kursie banku', out['reasons'])

    def test_payment_within_the_rate_margin_settles_the_document(self):
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(fin_invoice, 'get_db').start()
        mock.patch.object(fin_invoice.fin_audit, 'log').start()
        mock.patch.object(fin_invoice.fin_document, 'set_local_payment').start()
        mock.patch.object(fin_invoice.fin_document, 'get_document',
                          return_value={**DRIVE_DOC, 'currency': 'EUR', 'gross_pln': Decimal('327.24')}).start()
        for amount in ('342.98', '320.00'):
            out = fin_invoice.mark_paid(DRIVE_DOC['fakturownia_id'], amount=amount, paid_date='2026-09-17')
            self.assertEqual(out['status'], 'paid')
            self.assertIsNone(out['warning'])
            self.assertEqual(out['amount_left'], Decimal('0'))


class SuggestForRowsTest(unittest.TestCase):
    def test_one_query_serves_the_whole_statement(self):
        docs = [dict(ForeignCurrencyMatchTest.DOC)]
        old = {**ForeignCurrencyMatchTest.TXN, 'id': 1, 'booked_date': date(2025, 1, 5), 'link_count': 0}
        hit = {**ForeignCurrencyMatchTest.TXN, 'link_count': 0}
        with mock.patch.object(fin_bank, '_documents_between', return_value=docs) as fetch, \
                mock.patch.object(fin_bank.fin_bank, 'links_for_transaction') as links:
            out = fin_bank.suggest_for_rows([hit, old])
        fetch.assert_called_once()
        links.assert_not_called()
        self.assertEqual(list(out), [327])
        self.assertEqual(out[327][0]['number'], 'CXHRDSAO-0010')


if __name__ == '__main__':
    unittest.main()
