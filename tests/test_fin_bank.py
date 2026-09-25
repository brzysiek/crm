"""Testy importu wyciągów i scoringu dopasowań.

Wiersze w fikstrach mają dokładnie ten kształt, co prawdziwe eksporty (nagłówki
i kolejność kolumn przepisane z plików Aliora, mBanku i UniCredit), tylko dane
są wymyślone. Scoring i parsery są czyste — baza nie jest tu potrzebna.
Uruchomienie: venv/bin/python -m unittest discover tests
"""
import unittest
from datetime import date
from decimal import Decimal
from unittest import mock

from services import fin_bank
from services.fin_bank import BankImportError

ALIOR = (
    'Historia operacji\n'
    'Data transakcji;Data księgowania;Nazwa nadawcy;Nazwa odbiorcy;Szczegóły transakcji;'
    'Kwota operacji;Waluta operacji;Kwota w walucie rachunku;Waluta rachunku;'
    'Numer rachunku nadawcy;Numer rachunku odbiorcy\n'
    '11-06-2026;11-06-2026;Łukasz Brzyski;T-MOBILE POLSKA S.A.;FV 529091120526 za telefon;'
    '-479,70;PLN;-479,70;PLN;25 2490 0005 0000 4530 2954 7384;11 1140 1010 0000 1111 2222 3333\n'
    '10-06-2026;10-06-2026;OPEN EDUCATION GROUP;Łukasz Brzyski;3/05/2026 doradztwo;'
    '3 355,75;PLN;3 355,75;PLN;99 1020 0000 0000 0000 0000 0001;25 2490 0005 0000 4530 2954 7384\n'
    ';;;;wiersz bez daty, do pominięcia;;;;;;\n'
)

MBANK = (
    'mBank S.A. Bankowość Detaliczna;\n'
    '\n'
    '#Data operacji;#Opis operacji;#Rachunek;#Kategoria;#Kwota;\n'
    '2026-05-28;"SZKOLKA KRZEWOW, FAKTURA NR 34/26     PRZELEW ZEWNĘTRZNY WYCHODZĄCY  ";'
    '"mBiznes konto 8411 ... 3849";"Materiały";-3 168,00 PLN;;\n'
    '#Saldo końcowe;;;;1 000,00 PLN;\n'
)

UNICREDIT = (
    '2026-05-31T13:28:00Z,ARBORUM GROUP SP. Z O.O.,0001223566,'
    'PL24291000060000000001331660,fb.me/ads,,fb.me/ads,,"FACEBK *7PPHNT99Q2",'
    'd75b459c-19ef-4895-9cc4-f94097aa456a,-50,PLN,0,PLN,0,8820.34\n'
    'zbyt krótki wiersz,do,pominięcia\n'
)


class DetectBankTest(unittest.TestCase):
    def test_each_format_is_recognised_by_content(self):
        self.assertEqual(fin_bank.detect_bank(ALIOR), 'alior')
        self.assertEqual(fin_bank.detect_bank(MBANK), 'mbank')
        self.assertEqual(fin_bank.detect_bank(UNICREDIT), 'unicredit')

    def test_foreign_file_is_not_guessed(self):
        self.assertEqual(fin_bank.detect_bank('imie;nazwisko\nJan;Kowalski\n'), '')

    def test_unknown_format_is_refused_with_a_list_of_supported_banks(self):
        with self.assertRaises(BankImportError) as ctx:
            fin_bank.parse(b'a;b\n1;2\n')
        self.assertIn('Alior Bank', str(ctx.exception))

    def test_recognised_format_without_operations_is_refused(self):
        header = ALIOR.splitlines()[1] + '\n'
        with self.assertRaises(BankImportError) as ctx:
            fin_bank.parse(header.encode('utf-8'))
        self.assertIn('ani jednej operacji', str(ctx.exception))


class DecodeTest(unittest.TestCase):
    def test_cp1250_export_keeps_polish_letters(self):
        self.assertEqual(fin_bank.decode('Szczegóły;Łukasz'.encode('cp1250')), 'Szczegóły;Łukasz')

    def test_utf8_with_bom_loses_the_bom(self):
        self.assertEqual(fin_bank.decode('#Data operacji'.encode('utf-8-sig')), '#Data operacji')


class ParseAliorTest(unittest.TestCase):
    def setUp(self):
        self.rows = fin_bank.parse_alior(ALIOR)

    def test_only_rows_with_a_date_are_taken(self):
        self.assertEqual(len(self.rows), 2)

    def test_outflow_keeps_the_recipient_as_counterparty(self):
        row = self.rows[0]
        self.assertEqual(row['amount'], Decimal('-479.70'))
        self.assertEqual(row['counterparty_name'], 'T-MOBILE POLSKA S.A.')
        self.assertEqual(row['booked_date'], '2026-06-11')
        self.assertIn('529091120526', row['title'])

    def test_inflow_keeps_the_sender_as_counterparty(self):
        row = self.rows[1]
        self.assertEqual(row['amount'], Decimal('3355.75'))
        self.assertEqual(row['counterparty_name'], 'OPEN EDUCATION GROUP')

    def test_external_id_is_stable_across_reimports(self):
        again = fin_bank.parse_alior(ALIOR)
        self.assertEqual([r['external_id'] for r in self.rows],
                         [r['external_id'] for r in again])

    def test_the_two_operations_do_not_share_an_id(self):
        self.assertNotEqual(self.rows[0]['external_id'], self.rows[1]['external_id'])


class ParseMbankTest(unittest.TestCase):
    def test_amount_currency_and_summary_lines(self):
        rows = fin_bank.parse_mbank(MBANK)
        self.assertEqual(len(rows), 1, 'wiersz „#Saldo końcowe” to nie operacja')
        self.assertEqual(rows[0]['amount'], Decimal('-3168.00'))
        self.assertEqual(rows[0]['booked_date'], '2026-05-28')
        self.assertIn('FAKTURA NR 34/26', rows[0]['title'])


class ParseUnicreditTest(unittest.TestCase):
    def test_uuid_column_becomes_the_external_id(self):
        rows = fin_bank.parse_unicredit(UNICREDIT)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['external_id'],
                         'unicredit_d75b459c-19ef-4895-9cc4-f94097aa456a')
        self.assertEqual(rows[0]['amount'], Decimal('-50.00'))
        self.assertEqual(rows[0]['title'], 'FACEBK *7PPHNT99Q2')


class AmountTest(unittest.TestCase):
    def test_polish_notation_with_spaces_and_currency(self):
        self.assertEqual(fin_bank._amount('-3 168,00 PLN'), Decimal('-3168.00'))
        self.assertEqual(fin_bank._amount('1\xa0234,56'), Decimal('1234.56'))

    def test_garbage_is_rejected(self):
        with self.assertRaises(ValueError):
            fin_bank._amount('brak')


def txn(**over) -> dict:
    row = {'id': 1, 'booked_date': date(2026, 6, 10), 'amount': Decimal('-1704.10'),
           'title': 'FV 14846/0626/RM leasing', 'counterparty_name': 'VOLKSWAGEN FINANCIAL SERVICES'}
    row.update(over)
    return row


def doc(**over) -> dict:
    row = {'fakturownia_id': 500, 'number': '14846/0626/RM', 'is_income': 0,
           'issue_date': date(2026, 5, 21), 'payment_to': date(2026, 6, 9),
           'status': 'received', 'gross_pln': Decimal('1704.10'),
           'paid_amount': Decimal('0'), 'counterparty_name': 'Volkswagen Financial Services Polska Sp. z o.o.',
           'counterparty_tax_no_norm': '5262197937'}
    row.update(over)
    return row


class ScoreMatchTest(unittest.TestCase):
    def test_number_amount_name_and_date_all_add_up(self):
        result = fin_bank.score_match(txn(), doc())
        self.assertGreater(result['score'], 100)
        self.assertIn('numer 14846/0626/RM w tytule przelewu', result['reasons'])
        self.assertIn('kwota równa pozostałej do zapłaty', result['reasons'])

    def test_nip_in_the_transfer_title_counts(self):
        result = fin_bank.score_match(txn(title='zapłata NIP 5262197937'), doc())
        self.assertIn('NIP 5262197937 w tytule przelewu', result['reasons'])

    def test_bare_four_digit_number_is_not_matched_against_the_title(self):
        """„1026” siedzi w środku numeru 14803/1026/RM — sam w sobie nic nie znaczy."""
        result = fin_bank.score_match(txn(title='FV 14803/1026/RM leasing'), doc(number='1026'))
        self.assertNotIn('numer 1026 w tytule przelewu', result['reasons'])

    def test_short_number_with_a_separator_still_counts(self):
        result = fin_bank.score_match(txn(title='FAKTURA NR 34/26'), doc(number='34/26'))
        self.assertIn('numer 34/26 w tytule przelewu', result['reasons'])

    def test_long_bare_number_counts(self):
        result = fin_bank.score_match(txn(title='FV 529091120526 za telefon'),
                                      doc(number='529091120526'))
        self.assertIn('numer 529091120526 w tytule przelewu', result['reasons'])

    def test_amount_left_beats_gross_when_part_is_already_paid(self):
        partial = doc(paid_amount=Decimal('704.10'))
        result = fin_bank.score_match(txn(amount=Decimal('-1000.00')), partial)
        self.assertIn('kwota równa pozostałej do zapłaty', result['reasons'])

    def test_two_grosz_of_rounding_still_counts_as_equal(self):
        result = fin_bank.score_match(txn(amount=Decimal('-1704.12')), doc())
        self.assertIn('kwota równa pozostałej do zapłaty', result['reasons'])

    def test_bigger_transfer_than_document_is_punished(self):
        result = fin_bank.score_match(txn(amount=Decimal('-9999.00'), title='leasing'), doc())
        self.assertIn('przelew większy niż dokument', result['reasons'])

    def test_transfer_before_the_invoice_was_issued_is_punished(self):
        result = fin_bank.score_match(txn(booked_date=date(2026, 1, 5), title='leasing'), doc())
        self.assertIn('przelew wcześniejszy niż wystawienie dokumentu', result['reasons'])

    def test_paid_document_is_pushed_down(self):
        paid = doc(status='paid', paid_amount=Decimal('1704.10'))
        with_number = fin_bank.score_match(txn(), paid)
        self.assertIn('dokument już oznaczony jako opłacony', with_number['reasons'])
        self.assertLess(with_number['score'], fin_bank.score_match(txn(), doc())['score'])

    def test_legal_form_alone_is_not_a_name_match(self):
        """„SP. Z O.O.” mają wszyscy — dopasowanie po formie prawnej to fałszywy trop."""
        result = fin_bank.score_match(
            txn(title='przelew', counterparty_name='INNA FIRMA SP. Z O.O.'),
            doc(counterparty_name='Zupełnie Inny Dostawca sp. z o.o.'))
        self.assertNotIn('kontrahent', ' '.join(result['reasons']))

    def test_string_dates_are_accepted_like_date_objects(self):
        result = fin_bank.score_match(txn(booked_date='2026-06-10'), doc())
        self.assertGreater(result['score'], 100)


class NameOverlapTest(unittest.TestCase):
    def test_bank_shorthand_still_matches_the_full_name(self):
        self.assertGreaterEqual(
            fin_bank._name_overlap('T-MOBILE POLSKA S.A. UL.MARYNARSKA',
                                   'T-Mobile Polska S.A.'), 0.6)

    def test_unrelated_names_do_not_match(self):
        self.assertEqual(fin_bank._name_overlap('ZUS', 'Volkswagen Financial Services'), 0.0)

    def test_empty_names_do_not_blow_up(self):
        self.assertEqual(fin_bank._name_overlap('', 'Cokolwiek'), 0.0)
        self.assertEqual(fin_bank._name_overlap(None, None), 0.0)


class SuggestMatchesTest(unittest.TestCase):
    def test_weak_candidates_are_dropped_and_the_best_comes_first(self):
        good, weak = doc(), doc(fakturownia_id=501, number='99999/0126/XX',
                                counterparty_name='Ktoś Inny', counterparty_tax_no_norm='1111111111',
                                gross_pln=Decimal('88.00'))
        with mock.patch.object(fin_bank, '_candidates', return_value=[weak, good]), \
             mock.patch.object(fin_bank.fin_bank, 'links_for_transaction', return_value=[]):
            found = fin_bank.suggest_matches(txn())
        self.assertEqual([m['fakturownia_id'] for m in found], [500])

    def test_already_linked_document_is_not_suggested_again(self):
        with mock.patch.object(fin_bank, '_candidates', return_value=[doc()]), \
             mock.patch.object(fin_bank.fin_bank, 'links_for_transaction',
                               return_value=[{'fakturownia_id': 500}]):
            self.assertEqual(fin_bank.suggest_matches(txn()), [])


class LinkPaymentGuardsTest(unittest.TestCase):
    """Reguły, które muszą zadziałać *przed* jakimkolwiek zapisem."""

    def link(self, transaction, document, links=(), **kw):
        with mock.patch.object(fin_bank.fin_bank, 'get_transaction', return_value=transaction), \
             mock.patch.object(fin_bank.fin_bank, 'links_for_transaction', return_value=list(links)), \
             mock.patch('models.fin_document.get_document', return_value=document), \
             mock.patch.object(fin_bank.fin_bank, 'add_link') as add_link, \
             mock.patch.object(fin_bank.fin_bank, 'refresh_status', return_value='matched'), \
             mock.patch.object(fin_bank, 'get_db'):
            result = fin_bank.link_payment(1, 500, push=False, **kw)
        return result, add_link

    def test_outflow_is_not_linked_to_an_income_document(self):
        with self.assertRaises(BankImportError) as ctx:
            self.link(txn(), {**doc(), 'is_income': 1, 'price_gross': Decimal('1704.10')})
        self.assertIn('nie wiążę przeciwnych stron', str(ctx.exception))

    def test_inflow_is_not_linked_to_a_cost_document(self):
        with self.assertRaises(BankImportError):
            self.link(txn(amount=Decimal('1704.10')), doc())

    def test_unknown_transaction_and_unknown_document_are_refused(self):
        with self.assertRaises(BankImportError):
            self.link(None, doc())
        with self.assertRaises(BankImportError) as ctx:
            self.link(txn(), None)
        self.assertIn('zsynchronizuj', str(ctx.exception))

    def test_amount_defaults_to_what_is_left_on_the_document(self):
        result, add_link = self.link(txn(amount=Decimal('-5000.00')), doc())
        self.assertEqual(result['amount_applied'], Decimal('1704.10'))
        self.assertEqual(add_link.call_args[0][2], Decimal('1704.10'))

    def test_more_than_the_transfer_holds_is_refused(self):
        existing = [{'fakturownia_id': 777, 'amount_applied': Decimal('1500.00')}]
        with self.assertRaises(BankImportError) as ctx:
            self.link(txn(), doc(), links=existing, amount='1000.00')
        self.assertIn('204.10', str(ctx.exception))

    def test_fixing_an_existing_link_does_not_count_against_itself(self):
        """Poprawianie kwoty istniejącego powiązania to nie dokładanie nowej raty."""
        existing = [{'fakturownia_id': 500, 'amount_applied': Decimal('1704.10')}]
        result, _ = self.link(txn(), doc(), links=existing, amount='1000.00')
        self.assertEqual(result['amount_applied'], Decimal('1000.00'))

    def test_fully_allocated_transfer_has_nothing_left_to_link(self):
        existing = [{'fakturownia_id': 777, 'amount_applied': Decimal('1704.10')}]
        with self.assertRaises(BankImportError) as ctx:
            self.link(txn(), doc(), links=existing)
        self.assertIn('rozdysponowany', str(ctx.exception))

    def test_push_disabled_leaves_fakturownia_alone(self):
        result, _ = self.link(txn(), doc())
        self.assertFalse(result['pushed'])
        self.assertIsNone(result['document'])


class LinkPaymentPushTest(unittest.TestCase):
    def test_the_sum_of_all_links_goes_to_fakturownia_not_just_this_instalment(self):
        """`mark_paid` ustawia łączną kwotę — wysyłamy sumę, więc powtórka nie podwoi."""
        with mock.patch.object(fin_bank.fin_bank, 'get_transaction', return_value=txn()), \
             mock.patch.object(fin_bank.fin_bank, 'links_for_transaction', return_value=[]), \
             mock.patch('models.fin_document.get_document', return_value=doc()), \
             mock.patch.object(fin_bank.fin_bank, 'add_link'), \
             mock.patch.object(fin_bank.fin_bank, 'refresh_status', return_value='matched'), \
             mock.patch.object(fin_bank.fin_bank, 'applied_to_document',
                               return_value=Decimal('1704.10')), \
             mock.patch.object(fin_bank, 'get_db'), \
             mock.patch('services.fin_invoice.mark_paid',
                        return_value={'status': 'paid'}) as mark_paid:
            result = fin_bank.link_payment(1, 500, amount='1704.10', actor='test')
        self.assertTrue(result['pushed'])
        self.assertEqual(mark_paid.call_args.kwargs['amount'], Decimal('1704.10'))
        self.assertEqual(mark_paid.call_args.kwargs['paid_date'], date(2026, 6, 10))


if __name__ == '__main__':
    unittest.main()
