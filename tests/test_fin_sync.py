"""Testy modułu Finanse v2: mapowanie faktur, kursor synchronizacji, filtry.

Baza jest zamockowana — te testy mają chodzić bez połączenia z produkcją.
Uruchomienie: venv/bin/python -m unittest discover tests
"""
import unittest
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest import mock

import models.fin_document as fin_doc
import routes.fin as fin_routes
import services.fin_sync as fin_sync
from services.fakturownia_api import is_income_doc


class IsIncomeDocTest(unittest.TestCase):
    """API zwraca `income` raz jako bool, raz jako "1"/"0" — obie formy znaczą to samo."""

    def test_truthy_forms(self):
        for value in (True, 1, '1', 'true', 'yes', 't', 'TRUE'):
            self.assertTrue(is_income_doc({'income': value}), value)

    def test_falsy_forms(self):
        for value in (False, 0, '0', 'false', 'no', '', None):
            self.assertFalse(is_income_doc({'income': value}), value)

    def test_missing_key_is_cost(self):
        self.assertFalse(is_income_doc({}))


class MapInvoiceTest(unittest.TestCase):
    def cost(self, **over):
        raw = {
            'id': 111, 'number': 'FV/1/2026', 'income': False, 'kind': 'vat',
            'issue_date': '2026-09-01', 'payment_to': '2026-09-15', 'status': 'received',
            'price_net': '100.00', 'price_tax': '23.00', 'price_gross': '123.00', 'paid': '0.0',
            'seller_name': 'Moja Firma', 'seller_tax_no': '6782864550',
            'buyer_name': 'Dostawca sp. z o.o.', 'buyer_tax_no': '1234567890',
            'currency': 'PLN', 'updated_at': '2026-09-02T10:11:12+02:00',
        }
        raw.update(over)
        return fin_sync.map_invoice(raw)

    def test_vendor_comes_from_buyer_on_cost(self):
        """Przy kosztach Fakturownia odwraca role: dostawca siedzi w buyer_*."""
        row = self.cost()
        self.assertEqual(row['counterparty_name'], 'Dostawca sp. z o.o.')
        self.assertEqual(row['counterparty_tax_no'], '1234567890')
        self.assertEqual(row['is_income'], 0)

    def test_client_also_comes_from_buyer_on_income(self):
        row = self.cost(income=True, buyer_name='Klient S.A.')
        self.assertEqual(row['counterparty_name'], 'Klient S.A.')
        self.assertEqual(row['is_income'], 1)

    def test_foreign_currency_is_converted_to_pln(self):
        row = self.cost(currency='EUR', exchange_currency_rate='4.3268',
                        price_net='1950.00', price_tax='0.00', price_gross='1950.00')
        self.assertEqual(row['currency'], 'EUR')
        self.assertEqual(row['exchange_rate'], Decimal('4.3268'))
        self.assertEqual(row['net_pln'], Decimal('8437.26'))
        self.assertEqual(row['price_net'], Decimal('1950.00'))

    def test_pln_keeps_rate_one(self):
        row = self.cost(exchange_currency_rate='4.30')
        self.assertEqual(row['exchange_rate'], Decimal('1'))
        self.assertEqual(row['net_pln'], Decimal('100.00'))

    def test_month_only_date_is_accepted(self):
        """Fakturownia dopuszcza sam miesiąc jako datę sprzedaży."""
        self.assertEqual(self.cost(sell_date='2026-09')['sell_date'], date(2026, 9, 1))

    def test_broken_date_does_not_explode(self):
        self.assertIsNone(self.cost(payment_to='')['payment_to'])
        self.assertIsNone(self.cost(payment_to='0000-00-00')['payment_to'])

    def test_updated_at_is_parsed(self):
        self.assertEqual(self.cost()['fakturownia_updated_at'], datetime(2026, 9, 2, 10, 11, 12))

    def test_amounts_with_comma_and_spaces(self):
        self.assertEqual(self.cost(price_net='1 234,56')['price_net'], Decimal('1234.56'))

    def test_raw_json_is_kept(self):
        self.assertIn('"buyer_name"', self.cost()['raw_json'])


class FakeApi:
    """Zwraca zadane strony, licząc, ile razy o nie poproszono."""

    def __init__(self, pages_by_income):
        self.pages_by_income = pages_by_income
        self.pages_served = 0

    def iter_invoices(self, income, max_pages=100):
        for page in self.pages_by_income.get(bool(income), []):
            self.pages_served += 1
            yield page


def invoice(doc_id, updated_at, income=False):
    return {'id': doc_id, 'income': income, 'number': f'F/{doc_id}', 'kind': 'vat',
            'issue_date': '2026-09-01', 'status': 'received', 'currency': 'PLN',
            'price_net': '100.00', 'price_tax': '23.00', 'price_gross': '123.00',
            'buyer_name': 'Kontrahent', 'updated_at': updated_at}


class SyncCursorTest(unittest.TestCase):
    """Delta opiera się na kursorze `updated_at` — API nie ma filtra „zmienione od”."""

    def setUp(self):
        self.upserts = []
        upsert = mock.patch.object(fin_sync, 'upsert_document',
                                   side_effect=lambda d: self.upserts.append(d) or 'new')
        upsert.start()
        self.addCleanup(upsert.stop)
        self.saved = []
        save = mock.patch.object(fin_sync, '_save_state',
                                 side_effect=lambda *a: self.saved.append(a))
        save.start()
        self.addCleanup(save.stop)
        db = mock.patch.object(fin_sync, 'get_db', return_value=mock.MagicMock())
        db.start()
        self.addCleanup(db.stop)
        # Reguły mają własne testy; tu sprawdzamy tylko, co sync im podaje.
        self.rules = mock.patch.object(fin_sync, 'apply_rules',
                                       return_value={'checked': 0, 'assigned': 0, 'rules': 0})
        self.apply_rules = self.rules.start()
        self.addCleanup(self.rules.stop)

    def state(self, cursor):
        return mock.patch.object(fin_sync, 'get_sync_state',
                                 return_value={'cursor_updated_at': cursor})

    def test_full_run_reads_every_page(self):
        api = FakeApi({False: [[invoice(1, '2026-09-01 10:00:00')],
                               [invoice(2, '2026-01-01 10:00:00')]],
                       True: [[invoice(3, '2026-09-02 10:00:00', income=True)]]})
        with self.state(None):
            result = fin_sync.sync_documents(full=True, api=api)
        self.assertEqual(result['seen'], 3)
        self.assertEqual(api.pages_served, 3)
        self.assertEqual(result['cursor'], datetime(2026, 9, 2, 10, 0, 0))

    def test_delta_stops_below_cursor(self):
        """Strona w całości starsza niż kursor minus zakładka kończy paginację."""
        cursor = datetime(2026, 9, 10, 12, 0, 0)
        api = FakeApi({False: [[invoice(1, '2026-09-11 08:00:00')],
                               [invoice(2, '2026-01-01 08:00:00')],
                               [invoice(3, '2025-01-01 08:00:00')]],
                       True: []})
        with self.state(cursor):
            result = fin_sync.sync_documents(api=api)
        self.assertEqual(api.pages_served, 2)      # trzeciej strony już nie tyka
        self.assertEqual(result['seen'], 2)

    def test_overlap_window_keeps_edge_documents(self):
        """Dokument z granicy okna (kursor minus mniej niż doba) wciąż się dociąga."""
        cursor = datetime(2026, 9, 10, 12, 0, 0)
        edge = (cursor - timedelta(hours=6)).strftime('%Y-%m-%d %H:%M:%S')
        api = FakeApi({False: [[invoice(1, edge)], [invoice(2, '2026-01-01 08:00:00')]], True: []})
        with self.state(cursor):
            result = fin_sync.sync_documents(api=api)
        self.assertEqual(result['seen'], 2)
        self.assertEqual(api.pages_served, 2)

    def test_cursor_never_moves_backwards(self):
        """Delta widząca same starsze dokumenty nie cofa kursora."""
        cursor = datetime(2026, 9, 10, 12, 0, 0)
        api = FakeApi({False: [[invoice(1, '2026-09-10 06:00:00')]], True: []})
        with self.state(cursor):
            result = fin_sync.sync_documents(api=api)
        self.assertEqual(result['cursor'], cursor)

    def test_only_new_documents_go_through_rules(self):
        """Reguły dostają wyłącznie nowe dokumenty — stare mają już swoje kategorie."""
        api = FakeApi({False: [[invoice(1, '2026-09-01 10:00:00')]], True: []})
        with self.state(None), \
             mock.patch.object(fin_sync, 'upsert_document', side_effect=['new']):
            fin_sync.sync_documents(full=True, api=api)
        self.apply_rules.assert_called_once_with(only_ids=[1])

    def test_rules_are_skipped_when_nothing_is_new(self):
        api = FakeApi({False: [[invoice(1, '2026-09-01 10:00:00')]], True: []})
        with self.state(None), \
             mock.patch.object(fin_sync, 'upsert_document', side_effect=['unchanged']):
            result = fin_sync.sync_documents(full=True, api=api)
        self.apply_rules.assert_not_called()
        self.assertEqual(result['categorized'], 0)

    def test_missing_exchange_rate_is_reported(self):
        api = FakeApi({False: [[dict(invoice(1, '2026-09-01 10:00:00'), currency='EUR')]], True: []})
        with self.state(None):
            result = fin_sync.sync_documents(full=True, api=api)
        self.assertEqual(len(result['warnings']), 1)
        self.assertIn('EUR', result['warnings'][0])

    def test_error_marks_state_and_keeps_old_cursor(self):
        cursor = datetime(2026, 9, 10, 12, 0, 0)
        api = FakeApi({False: [[invoice(1, '2026-09-11 08:00:00')]], True: []})
        with self.state(cursor), \
             mock.patch.object(fin_sync, 'upsert_document', side_effect=RuntimeError('boom')):
            with self.assertRaises(RuntimeError):
                fin_sync.sync_documents(api=api)
        self.assertEqual(self.saved[-1][1], cursor)
        self.assertEqual(self.saved[-1][2], 'error')


class FiltersSqlTest(unittest.TestCase):
    """Do SQL-a nie trafia nic, czego nie ma na białej liście."""

    def test_unknown_values_are_ignored(self):
        where, params = fin_doc._filters_sql({'kind': 'DROP TABLE', 'payment': 'x', 'ksef': 'y'})
        self.assertEqual(where, '1=1')
        self.assertEqual(params, [])

    def test_search_is_parameterised(self):
        where, params = fin_doc._filters_sql({'search': "'; DROP TABLE fin_documents--"})
        self.assertNotIn('DROP', where)
        self.assertEqual(len(params), 5)

    def test_financial_only_passes_kinds_as_one_param(self):
        where, params = fin_doc._filters_sql({'financial_only': True})
        self.assertIn(fin_doc.FINANCIAL_CLAUSE, where)
        self.assertEqual(params, [fin_doc.NON_FINANCIAL_KINDS])

    def test_month_placeholder_survives_escaping(self):
        where, params = fin_doc._filters_sql({'month': '2026-09'})
        self.assertIn("DATE_FORMAT(d.issue_date, '%%Y-%%m') = %s", where)
        self.assertEqual(params, ['2026-09'])

    def test_category_filter_wins_over_uncategorized(self):
        where, params = fin_doc._filters_sql({'category_id': 7, 'uncategorized': True})
        self.assertIn('m.category_id = %s', where)
        self.assertNotIn('IS NULL', where)

    def test_order_by_falls_back_to_issue_date(self):
        self.assertIn('d.issue_date', fin_doc._order_by('; DROP', 'desc'))
        self.assertIn('ASC', fin_doc._order_by('gross', 'asc'))
        self.assertIn('DESC', fin_doc._order_by('gross', 'cokolwiek'))


class BucketGroupingTest(unittest.TestCase):
    def test_buckets_keep_urgency_order_and_sum_amounts(self):
        rows = [{'bucket': 'later', 'amount_left': Decimal('10')},
                {'bucket': 'overdue', 'amount_left': Decimal('100')},
                {'bucket': 'overdue', 'amount_left': Decimal('5')},
                {'bucket': 'week', 'amount_left': Decimal('50')}]
        groups = fin_routes._group_by_bucket(rows)
        self.assertEqual([g['key'] for g in groups], ['overdue', 'week', 'later'])
        self.assertEqual(groups[0]['total'], Decimal('105'))

    def test_empty_buckets_are_dropped(self):
        self.assertEqual(fin_routes._group_by_bucket([]), [])

    def test_unknown_bucket_lands_in_later(self):
        groups = fin_routes._group_by_bucket([{'bucket': 'nonsense', 'amount_left': Decimal('1')}])
        self.assertEqual(groups[0]['key'], 'later')


class LabelCoverageTest(unittest.TestCase):
    """Etykiety muszą pokrywać to, co naprawdę przychodzi z konta."""

    def test_statuses_seen_on_the_account(self):
        for status in ('issued', 'paid', 'received', 'not_approved'):
            self.assertIn(status, fin_doc.STATUS_LABELS)

    def test_kinds_seen_on_the_account(self):
        for kind in ('vat', 'proforma', 'correction', 'advance', 'estimate', 'inbox', 'final'):
            self.assertIn(kind, fin_doc.KIND_LABELS)

    def test_non_financial_kinds_are_excluded_from_totals(self):
        self.assertIn('proforma', fin_doc.NON_FINANCIAL_KINDS)
        self.assertIn('inbox', fin_doc.NON_FINANCIAL_KINDS)
        self.assertNotIn('vat', fin_doc.NON_FINANCIAL_KINDS)
        self.assertNotIn('correction', fin_doc.NON_FINANCIAL_KINDS)


if __name__ == '__main__':
    unittest.main()
