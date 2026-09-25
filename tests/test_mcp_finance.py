"""Testy narzędzi MCP: listy kontaktów i faktury z modułu Finanse v2.

Baza jest zamockowana — sprawdzamy warstwę narzędzi, nie SQL.
Uruchomienie: venv/bin/python -m unittest discover tests
"""
import unittest
from datetime import date, timedelta
from decimal import Decimal
from unittest import mock

import mcp_server


class ContactListToolsTest(unittest.TestCase):
    def setUp(self):
        self.lists = [
            {'id': 5, 'name': 'Klienci', 'description': 'aktywni', 'member_count': 2},
            {'id': 6, 'name': 'Newsletter', 'description': None, 'member_count': 0},
        ]
        patches = [
            mock.patch.object(mcp_server.crm_contact_list, 'get_all_lists',
                              side_effect=lambda with_counts=False: self.lists),
            mock.patch.object(mcp_server.crm_contact_list, 'get_list',
                              side_effect=lambda lid: next((l for l in self.lists if l['id'] == lid), None)),
            mock.patch.object(mcp_server.crm_contact_list, 'create_list', return_value=7),
            mock.patch.object(mcp_server.crm_contact_list, 'add_contacts_to_list', return_value=1),
            mock.patch.object(mcp_server.crm_contact_list, 'remove_contacts_from_list', return_value=2),
            mock.patch.object(mcp_server.crm_contact_list, 'get_contact_lists',
                              return_value=[{'id': 5, 'name': 'Klienci'}]),
            mock.patch.object(mcp_server.crm_contact, 'get_contact_by_id',
                              side_effect=lambda cid: {'id': cid} if cid == 1 else None),
            mock.patch.object(mcp_server.crm_contact, 'get_all_contacts', return_value=[
                {'id': 1, 'first_name': 'Jan', 'last_name': 'Kowalski', 'position': None,
                 'email': 'j@k.pl', 'phone': None, 'company_id': 3, 'company_name': 'Acme',
                 'description': 'nieistotne dla MCP'}]),
            mock.patch.object(mcp_server.crm_contact, 'count_contacts', return_value=1),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def test_lists_report_member_counts(self):
        out = mcp_server.list_contact_lists()
        self.assertEqual(out[0], {'id': 5, 'name': 'Klienci', 'description': 'aktywni', 'contacts': 2})

    def test_create_reuses_existing_name_case_insensitively(self):
        """Agent pytany dwa razy o tę samą listę nie może zrobić dwóch list."""
        out = mcp_server.create_contact_list(name='klienci')
        self.assertEqual(out, {'id': 5, 'name': 'Klienci', 'created': False})
        mcp_server.crm_contact_list.create_list.assert_not_called()

    def test_create_new_list(self):
        out = mcp_server.create_contact_list(name='  Konferencja  ', description=' ')
        self.assertEqual(out, {'id': 7, 'name': 'Konferencja', 'created': True})
        mcp_server.crm_contact_list.create_list.assert_called_once_with('Konferencja', description=None)

    def test_create_rejects_empty_name(self):
        with self.assertRaises(ValueError):
            mcp_server.create_contact_list(name='   ')

    def test_unknown_list_is_rejected_everywhere(self):
        for fn, kwargs in ((mcp_server.list_contacts_in_list, {}),
                           (mcp_server.add_contacts_to_list, {'contact_ids': [1]}),
                           (mcp_server.remove_contacts_from_list, {'contact_ids': [1]})):
            with self.assertRaises(ValueError) as ctx:
                fn(list_id=99, **kwargs)
            self.assertIn('id=99', str(ctx.exception))

    def test_contacts_in_list_are_trimmed_to_useful_fields(self):
        out = mcp_server.list_contacts_in_list(list_id=5)
        self.assertEqual(out['list'], {'id': 5, 'name': 'Klienci'})
        self.assertEqual(out['total'], 1)
        self.assertNotIn('description', out['contacts'][0])
        self.assertEqual(out['contacts'][0]['company_name'], 'Acme')

    def test_limit_is_clamped(self):
        mcp_server.list_contacts_in_list(list_id=5, limit=100000)
        self.assertEqual(mcp_server.crm_contact.get_all_contacts.call_args.kwargs['limit'], 500)

    def test_add_reports_how_many_were_already_there(self):
        out = mcp_server.add_contacts_to_list(list_id=5, contact_ids=[1, 2, 3])
        self.assertEqual((out['requested'], out['added'], out['already_on_list']), (3, 1, 2))

    def test_remove_reports_contacts_that_were_not_members(self):
        out = mcp_server.remove_contacts_from_list(list_id=5, contact_ids=[1, 2, 3])
        self.assertEqual((out['requested'], out['removed'], out['not_on_list']), (3, 2, 1))

    def test_empty_id_list_is_rejected(self):
        for fn in (mcp_server.add_contacts_to_list, mcp_server.remove_contacts_from_list):
            with self.assertRaises(ValueError):
                fn(list_id=5, contact_ids=[])

    def test_membership_requires_existing_contact(self):
        self.assertEqual(mcp_server.get_contact_list_membership(contact_id=1),
                         [{'id': 5, 'name': 'Klienci'}])
        with self.assertRaises(ValueError):
            mcp_server.get_contact_list_membership(contact_id=42)


class FinanceToolsTest(unittest.TestCase):
    def setUp(self):
        self.doc = {
            'fakturownia_id': 123, 'number': 'FV 1/2026', 'kind': 'vat', 'is_income': 0,
            'issue_date': '2026-08-31', 'status': 'paid', 'currency': 'PLN',
            'net_pln': Decimal('100.00'), 'tax_pln': Decimal('23.00'),
            'gross_pln': Decimal('123.00'), 'counterparty_name': 'Orlen',
            'category_id': 1, 'category_name': 'Paliwo', 'vat_deduction_percent': 50,
            'raw_json': '{"ogromny": "json"}',
        }
        self.categories = [
            {'id': 1, 'kind': 'cost', 'name': 'Paliwo', 'slug': 'samochod-paliwo',
             'default_vat_deduction': 50, 'default_tax_deductible': 75, 'is_fixed_cost': 0},
        ]
        patches = [
            mock.patch.object(mcp_server.fin_document, 'list_documents', return_value=[dict(self.doc)]),
            mock.patch.object(mcp_server.fin_document, 'count_documents', return_value=14),
            mock.patch.object(mcp_server.fin_document, 'get_document',
                              side_effect=lambda fid: dict(self.doc) if fid == 123 else None),
            mock.patch.object(mcp_server.fin_document, 'count_uncategorized', return_value=139),
            mock.patch.object(mcp_server.fin_document, 'period_totals', return_value={
                'cost': {'documents': 2, 'net': Decimal('100'), 'tax': Decimal('23'),
                         'gross': Decimal('123'), 'open_amount': 0},
                'income': {'documents': 1, 'net': Decimal('500'), 'tax': Decimal('115'),
                           'gross': Decimal('615'), 'open_amount': 0}}),
            mock.patch.object(mcp_server.fin_document, 'open_items', return_value=[
                {**self.doc, 'bucket': 'overdue', 'amount_left': Decimal('123.00'), 'days_left': -5},
                {**self.doc, 'fakturownia_id': 124, 'bucket': 'week',
                 'amount_left': Decimal('50.00'), 'days_left': 3}]),
            mock.patch.object(mcp_server.fin_category, 'list_categories', return_value=self.categories),
            mock.patch.object(mcp_server.fin_category, 'get_category',
                              side_effect=lambda cid: self.categories[0] if cid == 1 else None),
            mock.patch.object(mcp_server.fin_category, 'get_category_by_slug',
                              side_effect=lambda slug: self.categories[0] if slug == 'samochod-paliwo' else None),
            mock.patch.object(mcp_server.fin_category, 'set_document_category'),
            mock.patch.object(mcp_server.fin_category, 'clear_document_category'),
            mock.patch.object(mcp_server.fin_category, 'bulk_set_category', return_value=3),
            mock.patch.object(mcp_server.fin_rules, 'create_rule', return_value=9),
            mock.patch.object(mcp_server.fin_rules, 'apply_rules',
                              return_value={'checked': 139, 'assigned': 12}),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def test_documents_never_carry_raw_json(self):
        """raw_json to kilka kilobajtów na dokument — w odpowiedzi MCP nie ma go po co."""
        out = mcp_server.fin_list_documents()
        self.assertNotIn('raw_json', out['documents'][0])
        self.assertNotIn('raw_json', mcp_server.fin_get_document(fakturownia_id=123))

    def test_is_income_comes_back_as_bool(self):
        self.assertIs(mcp_server.fin_list_documents()['documents'][0]['is_income'], False)

    def test_amounts_stay_decimal(self):
        """Kwoty nie przechodzą przez float — grosze muszą się zgadzać."""
        self.assertIsInstance(mcp_server.fin_list_documents()['documents'][0]['net_pln'], Decimal)

    def test_kind_all_clears_the_filter(self):
        mcp_server.fin_list_documents(kind='all')
        self.assertEqual(mcp_server.fin_document.list_documents.call_args.args[0]['kind'], '')

    def test_non_financial_documents_are_always_excluded(self):
        mcp_server.fin_list_documents()
        self.assertTrue(mcp_server.fin_document.list_documents.call_args.args[0]['financial_only'])

    def test_limit_is_clamped(self):
        mcp_server.fin_list_documents(limit=9999)
        self.assertEqual(mcp_server.fin_document.list_documents.call_args.kwargs['limit'], 200)

    def test_category_can_be_given_as_slug_or_id(self):
        mcp_server.fin_list_documents(category='samochod-paliwo')
        self.assertEqual(mcp_server.fin_document.list_documents.call_args.args[0]['category_id'], 1)
        mcp_server.fin_list_documents(category='1')
        self.assertEqual(mcp_server.fin_document.list_documents.call_args.args[0]['category_id'], 1)

    def test_unknown_category_is_rejected_before_writing(self):
        with self.assertRaises(ValueError):
            mcp_server.fin_set_category(fakturownia_id=123, category='nie-ma-takiej')
        mcp_server.fin_category.set_document_category.assert_not_called()

    def test_unknown_document_is_rejected(self):
        with self.assertRaises(ValueError):
            mcp_server.fin_get_document(fakturownia_id=999)
        with self.assertRaises(ValueError):
            mcp_server.fin_set_category(fakturownia_id=999, category='1')

    def test_set_category_marks_the_agent_as_source(self):
        """Źródło 'agent' odróżnia przypisania bota od moich własnych."""
        mcp_server.fin_set_category(fakturownia_id=123, category='1',
                                     vat_deduction_percent=50, tax_deductible_percent=75)
        kwargs = mcp_server.fin_category.set_document_category.call_args.kwargs
        self.assertEqual(kwargs['source'], 'agent')
        self.assertEqual((kwargs['vat_percent'], kwargs['kup_percent']), (50, 75))

    def test_empty_category_clears_the_assignment(self):
        mcp_server.fin_set_category(fakturownia_id=123, category=None)
        mcp_server.fin_category.clear_document_category.assert_called_once_with(123)
        mcp_server.fin_category.set_document_category.assert_not_called()

    def test_bulk_requires_a_category_and_ids(self):
        with self.assertRaises(ValueError):
            mcp_server.fin_bulk_categorize(fakturownia_ids=[1, 2], category='')
        with self.assertRaises(ValueError):
            mcp_server.fin_bulk_categorize(fakturownia_ids=[], category='1')

    def test_bulk_returns_how_many_changed(self):
        out = mcp_server.fin_bulk_categorize(fakturownia_ids=[1, 2, 3], category='1')
        self.assertEqual((out['requested'], out['updated']), (3, 3))

    def test_unpaid_groups_by_bucket_and_sums_overdue(self):
        out = mcp_server.fin_unpaid(kind='cost')
        self.assertEqual(sorted(out['buckets']), ['overdue', 'week'])
        self.assertEqual(out['total_amount_left'], Decimal('173.00'))
        self.assertEqual(out['overdue_amount'], Decimal('123.00'))

    def test_summary_accepts_month_and_year(self):
        month = mcp_server.fin_summary(period='2026-02')
        self.assertEqual((month['from'], month['to']), ('2026-02-01', '2026-02-28'))
        year = mcp_server.fin_summary(period='2026')
        self.assertEqual((year['from'], year['to']), ('2026-01-01', '2026-12-31'))

    def test_summary_result_is_income_minus_cost(self):
        self.assertEqual(mcp_server.fin_summary(period='2026-02')['result_net'], Decimal('400'))

    def test_summary_rejects_nonsense_period(self):
        with self.assertRaises(ValueError):
            mcp_server.fin_summary(period='luty')

    def test_rule_can_be_added_without_applying_it(self):
        out = mcp_server.fin_add_rule(match_field='counterparty_name', match_type='contains',
                                       match_value='orlen', category='1', apply_now=False)
        self.assertEqual(out, {'rule_id': 9, 'category_id': 1})
        mcp_server.fin_rules.apply_rules.assert_not_called()

    def test_rule_applied_now_reports_assignments(self):
        out = mcp_server.fin_add_rule(match_field='counterparty_name', match_type='contains',
                                       match_value='orlen', category='samochod-paliwo')
        self.assertEqual(out['assigned'], 12)


if __name__ == '__main__':
    unittest.main()

class TaxEstimateToolTest(unittest.TestCase):
    """Narzędzie podatkowe: sprawdzamy kontrakt odpowiedzi, nie arytmetykę
    (ta ma własne testy w test_fin_tax.py)."""

    def setUp(self):
        self.overview = {
            'period': '2026-08',
            'vat': {'due': Decimal('2300.00'), 'deductible': Decimal('1000.00'),
                    'to_pay': Decimal('1300'), 'carry_forward': Decimal('0'),
                    'due_date': date(2026, 9, 25), 'income_count': 1, 'cost_count': 1,
                    'uncategorized': [{'fakturownia_id': 9, 'tax': Decimal('230.00')}],
                    'uncategorized_tax': Decimal('230.00'),
                    'limited': [{'fakturownia_id': 8, 'percent': 50}],
                    'exceptions': [{'fakturownia_id': 7, 'number': 'FV/7',
                                    'counterparty_name': 'Microsoft', 'net': Decimal('100'),
                                    'tax': Decimal('0'), 'is_income': False,
                                    'reason': 'self_charge', 'reason_label': 'Import usług'}]},
            'pit': {'income_net': Decimal('100000'), 'cost_net': Decimal('40000'),
                    'social_paid': Decimal('5000'), 'health_deducted': Decimal('2000'),
                    'taxable': Decimal('53000'), 'rate': Decimal('0.19'),
                    'tax_ytd': Decimal('10070'), 'advances_paid': Decimal('4000'),
                    'to_pay': Decimal('6070'), 'overpaid': Decimal('0'),
                    'due_date': date(2026, 9, 21)},
            'health': {'amount': Decimal('980.00'), 'basis_month': '2026-07',
                       'due_date': date(2026, 9, 21),
                       'basis_income': Decimal('20000'), 'is_minimum': False,
                       'deduction_limit': Decimal('12900')},
            'social': {'amount': Decimal('1773.96'), 'due_date': date(2026, 9, 21)},
            'ytd': {'cost_uncategorized': 3, 'months': 8, 'year': 2026},
            'rates_year': 2026,
            'rates_warning': ['PRZENIESIONE Z 2025 — potwierdź składki społeczne na 2026'],
            'obligations': {},
        }
        patches = [
            mock.patch.object(mcp_server.fin_tax, 'period_overview', return_value=self.overview),
            mock.patch.object(mcp_server.fin_tax_store, 'missing_rates', return_value=[]),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def test_zwraca_zobowiazania_terminy_i_wyjatki(self):
        result = mcp_server.fin_tax_estimate(period='2026-08')
        self.assertEqual(result['period'], '2026-08')
        self.assertIn('Symulacja', result['disclaimer'])
        self.assertEqual([o['kind'] for o in result['obligations']],
                         ['vat', 'pit', 'zus_social', 'zus_health'])
        self.assertEqual(result['obligations'][1]['amount'], Decimal('6070.00'))
        self.assertEqual(result['vat']['exceptions'][0]['reason'], 'self_charge')
        self.assertEqual(result['zus']['health_basis_month'], '2026-07')
        self.assertTrue(result['rates_warnings'])

    def test_kwoty_zostaja_dziesietne(self):
        result = mcp_server.fin_tax_estimate(period='2026-08')
        self.assertIsInstance(result['pit']['tax_ytd'], Decimal)
        self.assertIsInstance(result['zus']['social'], Decimal)

    def test_dokumenty_tylko_na_zyczenie(self):
        self.assertNotIn('limited', mcp_server.fin_tax_estimate(period='2026-08')['vat'])
        detailed = mcp_server.fin_tax_estimate(period='2026-08', include_documents=True)
        self.assertEqual(detailed['vat']['limited'][0]['fakturownia_id'], 8)

    def test_pusty_okres_to_poprzedni_miesiac(self):
        mcp_server.fin_tax_estimate()
        expected = (date.today().replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
        mcp_server.fin_tax.period_overview.assert_called_with(expected)

    def test_zly_format_okresu_odrzucony_przed_liczeniem(self):
        with self.assertRaises(ValueError):
            mcp_server.fin_tax_estimate(period='sierpień 2026')
        mcp_server.fin_tax.period_overview.assert_not_called()

    def test_brak_stawek_to_blad_z_podpowiedzia(self):
        mcp_server.fin_tax_store.missing_rates.return_value = ['pit_rate']
        with self.assertRaises(ValueError) as ctx:
            mcp_server.fin_tax_estimate(period='2026-08')
        self.assertIn('pit_rate', str(ctx.exception))
        mcp_server.fin_tax.period_overview.assert_not_called()


class FakturowniaWriteToolsTest(unittest.TestCase):
    """Narzędzia zapisu: interesuje nas, co narzędzie przekazuje do
    `services.fin_invoice` i czego nie przepuszcza dalej (reguły samego serwisu
    mają własne testy w test_fin_invoice.py)."""

    def setUp(self):
        self.create = mock.patch.object(mcp_server.fin_invoice, 'create_document',
                                        return_value={'fakturownia_id': 1, 'ksef': {}}).start()
        self.mark_paid = mock.patch.object(mcp_server.fin_invoice, 'mark_paid',
                                           return_value={'status': 'paid'}).start()
        self.update = mock.patch.object(mcp_server.fin_invoice, 'update_document',
                                        return_value={'changed': ['description']}).start()
        self.addCleanup(mock.patch.stopall)

    def kwargs(self, call):
        return call.call_args.kwargs

    def test_cost_invoice_maps_supplier_onto_buyer_fields(self):
        """Fakturownia trzyma dostawcę w `buyer_*` — agent tego nie musi wiedzieć."""
        mcp_server.fin_create_cost_invoice(supplier_name='Dostawca sp. z o.o.',
                                          supplier_tax_no='123-456-78-90',
                                          total_gross='123,00', title='Hosting')
        kwargs = self.kwargs(self.create)
        self.assertFalse(kwargs['is_income'])
        self.assertEqual(kwargs['counterparty']['buyer_name'], 'Dostawca sp. z o.o.')
        self.assertEqual(kwargs['counterparty']['buyer_tax_no'], '123-456-78-90')
        self.assertEqual(kwargs['positions'][0]['total_price_gross'], 123.0)
        self.assertFalse(kwargs['send_to_ksef'])

    def test_cost_invoice_has_no_way_to_ask_for_ksef(self):
        self.assertNotIn('send_to_ksef',
                         mcp_server.fin_create_cost_invoice.__annotations__)

    def test_cost_invoice_needs_a_supplier_name(self):
        with self.assertRaises(ValueError):
            mcp_server.fin_create_cost_invoice(supplier_name='  ', total_gross='100')
        self.create.assert_not_called()

    def test_cost_invoice_needs_an_amount(self):
        with self.assertRaises(mcp_server.fin_invoice.FinWriteError):
            mcp_server.fin_create_cost_invoice(supplier_name='Dostawca')
        self.create.assert_not_called()

    def test_income_invoice_for_a_company_requires_a_tax_number(self):
        """Bez NIP-u KSeF odrzuci fakturę B2B — lepiej powiedzieć to od razu."""
        with self.assertRaises(ValueError) as ctx:
            mcp_server.fin_create_income_invoice(buyer_name='Klient S.A.', total_gross='1230')
        self.assertIn('NIP', str(ctx.exception))
        self.create.assert_not_called()

    def test_income_invoice_for_a_private_person_does_not(self):
        mcp_server.fin_create_income_invoice(buyer_name='Jan Kowalski', total_gross='1230',
                                            buyer_company=False)
        kwargs = self.kwargs(self.create)
        self.assertTrue(kwargs['is_income'])
        self.assertFalse(kwargs['counterparty']['buyer_company'])

    def test_income_invoice_does_not_send_to_ksef_by_default(self):
        mcp_server.fin_create_income_invoice(buyer_name='Klient S.A.', buyer_tax_no='1234567890',
                                            total_gross='1230')
        self.assertFalse(self.kwargs(self.create)['send_to_ksef'])

    def test_ksef_is_passed_through_when_explicitly_asked_for(self):
        mcp_server.fin_create_income_invoice(buyer_name='Klient S.A.', buyer_tax_no='1234567890',
                                            total_gross='1230', send_to_ksef=True)
        self.assertTrue(self.kwargs(self.create)['send_to_ksef'])

    def test_mark_paid_passes_total_amount_and_date_through(self):
        mcp_server.fin_mark_paid(900, amount='50.00', date='2026-06-10')
        self.assertEqual(self.kwargs(self.mark_paid)['amount'], '50.00')
        self.assertEqual(self.kwargs(self.mark_paid)['paid_date'], '2026-06-10')

    def test_mark_paid_with_no_amount_means_the_whole_invoice(self):
        mcp_server.fin_mark_paid(900)
        self.assertIsNone(self.kwargs(self.mark_paid)['amount'])
        self.assertIsNone(self.kwargs(self.mark_paid)['paid_date'])

    def test_update_needs_a_non_empty_object(self):
        for fields in ({}, None, 'description'):
            with self.assertRaises(ValueError, msg=repr(fields)):
                mcp_server.fin_update_document(900, fields)
        self.update.assert_not_called()

    def test_write_errors_reach_the_agent_as_plain_errors(self):
        """FinWriteError niesie komunikat dla człowieka — nie gubimy go."""
        self.mark_paid.side_effect = mcp_server.fin_invoice.FinWriteError('Fakturownia: 422')
        with self.assertRaises(ValueError) as ctx:
            mcp_server.fin_mark_paid(900)
        self.assertIn('422', str(ctx.exception))

    def test_every_write_is_signed_with_the_mcp_actor(self):
        mcp_server.fin_mark_paid(900)
        self.assertTrue(self.kwargs(self.mark_paid)['actor'].startswith('mcp:'))


class BankToolsTest(unittest.TestCase):
    def setUp(self):
        self.transaction = {'id': 1, 'amount': Decimal('-479.70'), 'title': 'FV 529091120526',
                            'booked_date': date(2026, 6, 11), 'status': 'pending'}
        patches = [
            mock.patch.object(mcp_server.fin_bank_service, 'import_csv',
                              return_value={'bank': 'alior', 'parsed': 2, 'new': 2}),
            mock.patch.object(mcp_server.fin_bank_service, 'suggest_matches',
                              return_value=[{'fakturownia_id': 500, 'score': 98}]),
            mock.patch.object(mcp_server.fin_bank_service, 'suggest_for_pending',
                              return_value=[]),
            mock.patch.object(mcp_server.fin_bank_service, 'link_payment',
                              return_value={'pushed': True}),
            mock.patch.object(mcp_server.fin_bank_service, 'unlink_payment',
                              return_value={'removed': 1}),
            mock.patch.object(mcp_server.fin_bank_store, 'get_transaction',
                              side_effect=lambda tid: self.transaction if tid == 1 else None),
            mock.patch.object(mcp_server.fin_bank_store, 'list_transactions',
                              return_value=[self.transaction]),
            mock.patch.object(mcp_server.fin_bank_store, 'count_by_status',
                              return_value={'pending': 1}),
            mock.patch.object(mcp_server.fin_bank_store, 'set_ignored'),
            mock.patch.object(mcp_server, 'get_db'),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def test_base64_is_decoded_before_parsing(self):
        """Wyciągi Aliora są w cp1250 — base64 jest jedyną pewną drogą."""
        import base64
        payload = 'Szczegóły;Łukasz'.encode('cp1250')
        mcp_server.fin_import_bank_csv(csv_base64=base64.b64encode(payload).decode())
        self.assertEqual(mcp_server.fin_bank_service.import_csv.call_args[0][0], payload)

    def test_plain_text_is_sent_as_utf8(self):
        mcp_server.fin_import_bank_csv(csv_content='Data transakcji;x\n')
        self.assertEqual(mcp_server.fin_bank_service.import_csv.call_args[0][0],
                         b'Data transakcji;x\n')

    def test_no_content_and_broken_base64_are_refused(self):
        for kwargs in ({}, {'csv_content': '   '}, {'csv_base64': 'to nie base64!'}):
            with self.assertRaises(ValueError, msg=repr(kwargs)):
                mcp_server.fin_import_bank_csv(**kwargs)
        mcp_server.fin_bank_service.import_csv.assert_not_called()

    def test_import_error_is_translated_for_the_agent(self):
        mcp_server.fin_bank_service.import_csv.side_effect = \
            mcp_server.fin_bank_service.BankImportError('Nie rozpoznaję formatu pliku.')
        with self.assertRaises(ValueError) as ctx:
            mcp_server.fin_import_bank_csv(csv_content='cokolwiek')
        self.assertIn('Nie rozpoznaję', str(ctx.exception))

    def test_status_all_means_no_filter(self):
        mcp_server.fin_bank_transactions(status='all')
        self.assertEqual(mcp_server.fin_bank_store.list_transactions.call_args.kwargs['status'], '')

    def test_suggestions_for_one_transaction(self):
        out = mcp_server.fin_suggest_payment_matches(transaction_id=1)
        self.assertEqual(out['matches'][0]['fakturownia_id'], 500)
        mcp_server.fin_bank_service.suggest_for_pending.assert_not_called()

    def test_unknown_transaction_is_refused(self):
        with self.assertRaises(ValueError):
            mcp_server.fin_suggest_payment_matches(transaction_id=99)

    def test_queue_scan_is_independent_of_how_many_results_we_want(self):
        mcp_server.fin_suggest_payment_matches(limit=3)
        kwargs = mcp_server.fin_bank_service.suggest_for_pending.call_args.kwargs
        self.assertEqual(kwargs['limit'], 3)
        self.assertEqual(kwargs['scan'], 200)

    def test_link_pushes_to_fakturownia_by_default(self):
        mcp_server.fin_link_payment(1, 500)
        kwargs = mcp_server.fin_bank_service.link_payment.call_args.kwargs
        self.assertTrue(kwargs['push'])
        self.assertIsNone(kwargs['amount'])
        self.assertTrue(kwargs['actor'].startswith('mcp:'))

    def test_link_can_stay_local(self):
        mcp_server.fin_link_payment(1, 500, push_to_fakturownia=False)
        self.assertFalse(mcp_server.fin_bank_service.link_payment.call_args.kwargs['push'])

    def test_link_refusals_reach_the_agent(self):
        mcp_server.fin_bank_service.link_payment.side_effect = \
            mcp_server.fin_bank_service.BankImportError('nie wiążę przeciwnych stron')
        with self.assertRaises(ValueError) as ctx:
            mcp_server.fin_link_payment(1, 500)
        self.assertIn('przeciwnych stron', str(ctx.exception))

    def test_ignore_and_undo_flip_the_same_flag(self):
        mcp_server.fin_ignore_transaction(1)
        mcp_server.fin_bank_store.set_ignored.assert_called_with(1, True)
        mcp_server.fin_ignore_transaction(1, undo=True)
        mcp_server.fin_bank_store.set_ignored.assert_called_with(1, False)
