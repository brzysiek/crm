"""Testy zapisów do Fakturowni: walidacja, idempotencja, zakazy KSeF, płatności.

Fakturownia jest zamockowana — te testy pilnują *naszych* reguł, żeby ani jeden
zapis do prawdziwej księgowości nie wyszedł z tego pliku.
Uruchomienie: venv/bin/python -m unittest discover tests
"""
import unittest
from datetime import date
from decimal import Decimal
from unittest import mock

from services import fin_invoice
from services.fakturownia_api import FakturowniaError
from services.fin_invoice import FinWriteError


class FakeApi:
    """Podstawka pod klienta API: zapisuje, co dostała, oddaje, co jej kazano."""

    def __init__(self, created=None, existing=None, updated=None, error=None):
        self.created, self.existing, self.updated, self.error = created, existing, updated, error
        self.calls = []

    def find_invoice_by_oid(self, oid):
        self.calls.append(('find', oid))
        return self.existing

    def create_invoice(self, invoice, send_to_ksef=False):
        self.calls.append(('create', invoice, send_to_ksef))
        if self.error:
            raise self.error
        return self.created

    def update_invoice(self, invoice_id, fields):
        self.calls.append(('update', invoice_id, fields))
        if self.error:
            raise self.error
        return self.updated or {'id': invoice_id, **fields}

    def send_invoice_to_ksef(self, invoice_id):
        self.calls.append(('ksef', invoice_id))
        if self.error:
            raise self.error
        return self.updated

    def get_invoice(self, invoice_id):
        self.calls.append(('get', invoice_id))
        return self.updated or {'id': invoice_id}


def invoice(**over) -> dict:
    row = {'id': 900, 'number': 'FV/9/2026', 'oid': 'CRM-20260925-abc', 'kind': 'vat',
           'price_net': '100.00', 'price_tax': '23.00', 'price_gross': '123.00',
           'currency': 'PLN', 'status': 'issued', 'gov_status': None}
    row.update(over)
    return row


def mirrored(**over) -> dict:
    """Wiersz lustra `fin_documents`, taki jak zwraca models.fin_document."""
    row = {'fakturownia_id': 900, 'number': 'FV/9/2026', 'is_income': 1, 'kind': 'vat',
           'price_gross': Decimal('123.00'), 'paid_amount': Decimal('0.00'),
           'paid_date': None, 'status': 'issued', 'gov_status': None}
    row.update(over)
    return row


class NoDbMixin:
    """Zapisy zawsze logują i commitują — w testach jedno i drugie jest atrapą."""

    def setUp(self):
        for target in ('get_db', 'sync_one'):
            patcher = mock.patch.object(fin_invoice, target)
            self.addCleanup(patcher.stop)
            patcher.start()
        self.audit = mock.patch.object(fin_invoice.fin_audit, 'log').start()
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(fin_invoice, 'get_setting', return_value='').start()
        fin_invoice.sync_one.return_value = {'result': 'new'}


class BuildPositionsTest(unittest.TestCase):
    def test_shorthand_makes_one_line(self):
        out = fin_invoice.build_positions(None, title='Hosting', total_gross='123,45', vat_rate=23)
        self.assertEqual(out, [{'name': 'Hosting', 'quantity': 1,
                                'total_price_gross': 123.45, 'tax': 23}])

    def test_no_amount_at_all_is_refused(self):
        with self.assertRaises(FinWriteError):
            fin_invoice.build_positions(None, title='Hosting')

    def test_position_without_name_is_refused(self):
        with self.assertRaises(FinWriteError) as ctx:
            fin_invoice.build_positions([{'total_price_gross': '10'}])
        self.assertIn('brak nazwy', str(ctx.exception))

    def test_position_without_amount_is_refused(self):
        with self.assertRaises(FinWriteError) as ctx:
            fin_invoice.build_positions([{'name': 'Usługa'}])
        self.assertIn('total_price_gross', str(ctx.exception))

    def test_positions_inherit_default_vat_rate(self):
        out = fin_invoice.build_positions([{'name': 'A', 'total_price_gross': '10'}], vat_rate='zw')
        self.assertEqual(out[0]['tax'], 'zw')


class TaxRateTest(unittest.TestCase):
    def test_numbers_and_symbols(self):
        self.assertEqual(fin_invoice._tax('23%'), 23)
        self.assertEqual(fin_invoice._tax(8), 8)
        self.assertEqual(fin_invoice._tax(' ZW '), 'zw')
        self.assertEqual(fin_invoice._tax('np'), 'np')

    def test_out_of_range_and_garbage(self):
        for value in ('120', '-1', 'dwadzieścia trzy'):
            with self.assertRaises(FinWriteError, msg=value):
                fin_invoice._tax(value)


class DayTest(unittest.TestCase):
    def test_accepts_date_and_iso_string(self):
        self.assertEqual(fin_invoice._day(date(2026, 9, 25), 'issue_date'), '2026-09-25')
        self.assertEqual(fin_invoice._day('2026-09-25T10:00:00', 'issue_date'), '2026-09-25')

    def test_empty_optional_is_none_but_required_raises(self):
        self.assertIsNone(fin_invoice._day('', 'sell_date'))
        with self.assertRaises(FinWriteError):
            fin_invoice._day('', 'issue_date', required=True)

    def test_polish_format_is_refused_rather_than_guessed(self):
        with self.assertRaises(FinWriteError):
            fin_invoice._day('25.09.2026', 'issue_date')


class CreateDocumentTest(NoDbMixin, unittest.TestCase):
    def positions(self):
        return fin_invoice.build_positions(None, title='Usługa', total_gross='123.00')

    def create(self, api, **over):
        kwargs = dict(counterparty={'buyer_name': 'Dostawca sp. z o.o.'},
                      positions=self.positions(), actor='test', api=api)
        kwargs.update(over)
        return fin_invoice.create_document(kwargs.pop('is_income', False), **kwargs)

    def test_cost_invoice_goes_out_as_income_zero_with_unique_oid(self):
        api = FakeApi(created=invoice())
        result = self.create(api)
        sent = api.calls[-1][1]
        self.assertEqual(sent['income'], '0')
        self.assertEqual(sent['oid_unique'], 'yes')
        self.assertTrue(sent['oid'].startswith('CRM-'))
        self.assertFalse(api.calls[-1][2], 'kosztu nigdy nie wysyłamy do KSeF')
        self.assertFalse(result['duplicate'])

    def test_repeated_oid_returns_existing_document_instead_of_a_twin(self):
        api = FakeApi(existing=invoice(id=901, number='FV/1/2026'))
        result = self.create(api, oid='CRM-20260925-abc')
        self.assertTrue(result['duplicate'])
        self.assertEqual(result['fakturownia_id'], 901)
        self.assertNotIn('create', [c[0] for c in api.calls])

    def test_ksef_refused_on_cost_invoice(self):
        api = FakeApi(created=invoice())
        with self.assertRaises(FinWriteError) as ctx:
            self.create(api, send_to_ksef=True)
        self.assertIn('kosztowej', str(ctx.exception))
        self.assertEqual(api.calls, [], 'odmowa musi nastąpić przed jakimkolwiek zapisem')

    def test_ksef_refused_for_kind_ksef_does_not_accept(self):
        api = FakeApi(created=invoice())
        with self.assertRaises(FinWriteError) as ctx:
            self.create(api, is_income=True, kind='proforma', send_to_ksef=True)
        self.assertIn('proforma', str(ctx.exception))
        self.assertEqual(api.calls, [])

    def test_due_date_sets_payment_to_kind(self):
        api = FakeApi(created=invoice())
        self.create(api, payment_to='2026-10-10')
        self.assertEqual(api.calls[-1][1]['payment_to_kind'], 'other_date')

    def test_api_rejection_is_logged_before_raising(self):
        api = FakeApi(error=FakturowniaError('422: buyer_tax_no jest wymagany'))
        with self.assertRaises(FinWriteError) as ctx:
            self.create(api)
        self.assertIn('422', str(ctx.exception))
        self.assertFalse(self.audit.call_args.kwargs['ok'])

    def test_response_without_id_is_treated_as_failure(self):
        api = FakeApi(created={'ok': True})
        with self.assertRaises(FinWriteError):
            self.create(api)
        self.assertFalse(self.audit.call_args.kwargs['ok'])

    def test_income_invoice_reports_ksef_send_we_did_not_ask_for(self):
        """Konto może mieć automatyczną wysyłkę, której API nie widzi — odpowiedź
        musi mówić prawdę o stanie, nie powtarzać naszej prośby."""
        api = FakeApi(created=invoice(gov_status='ok', gov_id='KSEF-1'))
        result = self.create(api, is_income=True,
                             counterparty={'buyer_name': 'Klient S.A.', 'buyer_company': True})
        self.assertTrue(result['ksef']['sent'])
        self.assertFalse(result['ksef']['requested'])
        self.assertIn('automatyczną wysyłkę', result['ksef']['note'])

    def test_cost_gov_status_is_explained_not_reported_as_our_send(self):
        api = FakeApi(created=invoice(gov_status='ok'))
        result = self.create(api)
        self.assertIn('przyszła z KSeF', result['ksef']['note'])


class MarkPaidTest(NoDbMixin, unittest.TestCase):
    def test_full_amount_sets_paid_status(self):
        api = FakeApi(updated=invoice())
        with mock.patch.object(fin_invoice.fin_document, 'get_document',
                               side_effect=[mirrored(), mirrored(paid_amount=Decimal('123.00'),
                                                                 status='paid')]):
            result = fin_invoice.mark_paid(900, api=api)
        self.assertEqual(api.calls[-1][2]['status'], 'paid')
        self.assertEqual(api.calls[-1][2]['paid'], 123.0)
        self.assertEqual(result['status'], 'paid')

    def test_part_of_the_amount_sets_partial(self):
        api = FakeApi(updated=invoice())
        with mock.patch.object(fin_invoice.fin_document, 'get_document',
                               side_effect=[mirrored(), mirrored(paid_amount=Decimal('50.00'),
                                                                 status='partial')]):
            fin_invoice.mark_paid(900, amount='50,00', api=api)
        self.assertEqual(api.calls[-1][2]['status'], 'partial')
        self.assertEqual(api.calls[-1][2]['paid'], 50.0)

    def test_amount_is_total_not_increment_so_a_repeat_changes_nothing(self):
        """Powtórzone wywołanie agenta nie może podwoić zapłaty."""
        api = FakeApi(updated=invoice())
        docs = [mirrored(paid_amount=Decimal('50.00')), mirrored(paid_amount=Decimal('50.00')),
                mirrored(paid_amount=Decimal('50.00')), mirrored(paid_amount=Decimal('50.00'))]
        with mock.patch.object(fin_invoice.fin_document, 'get_document', side_effect=docs):
            fin_invoice.mark_paid(900, amount='50.00', api=api)
            fin_invoice.mark_paid(900, amount='50.00', api=api)
        self.assertEqual([c[2]['paid'] for c in api.calls if c[0] == 'update'], [50.0, 50.0])

    def test_overpayment_is_saved_but_flagged(self):
        api = FakeApi(updated=invoice())
        with mock.patch.object(fin_invoice.fin_document, 'get_document',
                               side_effect=[mirrored(), mirrored(paid_amount=Decimal('200.00'))]):
            result = fin_invoice.mark_paid(900, amount='200', api=api)
        self.assertIn('przekracza brutto', result['warning'])

    def test_negative_amount_is_refused(self):
        api = FakeApi(updated=invoice())
        with mock.patch.object(fin_invoice.fin_document, 'get_document', return_value=mirrored()):
            with self.assertRaises(FinWriteError):
                fin_invoice.mark_paid(900, amount='-10', api=api)
        self.assertEqual(api.calls, [])

    def test_unknown_document_is_refused_before_any_call(self):
        api = FakeApi()
        with mock.patch.object(fin_invoice.fin_document, 'get_document', return_value=None):
            with self.assertRaises(FinWriteError) as ctx:
                fin_invoice.mark_paid(900, api=api)
        self.assertIn('zsynchronizuj', str(ctx.exception))
        self.assertEqual(api.calls, [])


class UpdateDocumentTest(NoDbMixin, unittest.TestCase):
    def test_unknown_field_is_refused_wholesale(self):
        api = FakeApi()
        with mock.patch.object(fin_invoice.fin_document, 'get_document', return_value=mirrored()):
            with self.assertRaises(FinWriteError) as ctx:
                fin_invoice.update_document(900, {'price_gross': '999'}, api=api)
        self.assertIn('price_gross', str(ctx.exception))
        self.assertEqual(api.calls, [])

    def test_invoice_already_in_ksef_accepts_only_bookkeeping_fields(self):
        api = FakeApi(updated=invoice())
        doc = mirrored(is_income=1, gov_status='ok')
        with mock.patch.object(fin_invoice.fin_document, 'get_document', return_value=doc):
            with self.assertRaises(FinWriteError) as ctx:
                fin_invoice.update_document(900, {'buyer_name': 'Inny Klient'}, api=api)
            self.assertIn('korygującą', str(ctx.exception))
            self.assertEqual(api.calls, [])
            fin_invoice.update_document(900, {'description': 'nasza notatka'}, api=api)
        self.assertEqual(api.calls[-1][2], {'description': 'nasza notatka'})

    def test_cost_invoice_in_ksef_is_not_locked(self):
        """`gov_status` na koszcie znaczy „przyszła z KSeF” — nie blokuje edycji."""
        api = FakeApi(updated=invoice())
        doc = mirrored(is_income=0, gov_status='ok')
        with mock.patch.object(fin_invoice.fin_document, 'get_document', return_value=doc):
            fin_invoice.update_document(900, {'payment_to': '2026-10-01'}, api=api)
        self.assertEqual(api.calls[-1][2], {'payment_to': '2026-10-01'})

    def test_bad_date_is_refused(self):
        api = FakeApi()
        with mock.patch.object(fin_invoice.fin_document, 'get_document', return_value=mirrored()):
            with self.assertRaises(FinWriteError):
                fin_invoice.update_document(900, {'payment_to': '01.10.2026'}, api=api)
        self.assertEqual(api.calls, [])


class SendToKsefTest(NoDbMixin, unittest.TestCase):
    def test_cost_invoice_is_never_sent(self):
        api = FakeApi()
        with mock.patch.object(fin_invoice.fin_document, 'get_document',
                               return_value=mirrored(is_income=0)):
            with self.assertRaises(FinWriteError) as ctx:
                fin_invoice.send_to_ksef(900, api=api)
        self.assertIn('kosztowy', str(ctx.exception))
        self.assertEqual(api.calls, [])

    def test_kind_outside_ksef_is_refused(self):
        api = FakeApi()
        with mock.patch.object(fin_invoice.fin_document, 'get_document',
                               return_value=mirrored(kind='proforma')):
            with self.assertRaises(FinWriteError):
                fin_invoice.send_to_ksef(900, api=api)
        self.assertEqual(api.calls, [])

    def test_already_sent_invoice_is_not_sent_twice(self):
        api = FakeApi()
        with mock.patch.object(fin_invoice.fin_document, 'get_document',
                               return_value=mirrored(gov_status='ok', gov_id='KSEF-1')):
            result = fin_invoice.send_to_ksef(900, api=api)
        self.assertTrue(result['already_sent'])
        self.assertEqual(api.calls, [])

    def test_send_reports_status_from_the_response(self):
        api = FakeApi(updated=invoice(gov_status='processing'))
        with mock.patch.object(fin_invoice.fin_document, 'get_document', return_value=mirrored()):
            result = fin_invoice.send_to_ksef(900, api=api)
        self.assertEqual(api.calls[0], ('ksef', 900))
        self.assertTrue(result['ksef']['sent'])
        self.assertEqual(result['ksef']['gov_status'], 'processing')


class KsefReportTest(unittest.TestCase):
    def test_error_statuses_are_not_counted_as_sent(self):
        for status in ('send_error', 'server_error', 'not_applicable', 'not_connected',
                       'blocked_403_error', None):
            report = fin_invoice._ksef_report({'gov_status': status}, requested=True, is_income=True)
            self.assertFalse(report['sent'], status)
            self.assertIn('nie potwierdził', report['note'])

    def test_demo_statuses_count_the_same_as_real_ones(self):
        report = fin_invoice._ksef_report({'gov_status': 'demo_ok'}, requested=True, is_income=True)
        self.assertTrue(report['sent'])


if __name__ == '__main__':
    unittest.main()
