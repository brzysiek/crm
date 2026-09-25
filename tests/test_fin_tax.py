"""Testy silnika podatkowego: VAT, zaliczka PIT, zdrowotna, terminy.

Wszystkie przypadki policzone ręcznie — po to jest czysta warstwa w
`services/fin_tax.py`, żeby dało się sprawdzić kwotę bez bazy i bez Fakturowni.
Uruchomienie: venv/bin/python -m unittest discover tests
"""
import unittest
from datetime import date
from decimal import Decimal
from unittest import mock

from services import fin_tax


def D(value) -> Decimal:
    return Decimal(str(value))


RATES = {
    'pit_rate': {'value': D('0.19'), 'note': '', 'year': 2026, 'is_confirmed': True},
    'health_rate': {'value': D('0.049'), 'note': '', 'year': 2026, 'is_confirmed': True},
    'health_min_monthly': {'value': D('314.96'), 'note': '', 'year': 2026, 'is_confirmed': True},
    'health_deduction_limit': {'value': D('12900'), 'note': '', 'year': 2026, 'is_confirmed': True},
    'zus_social_monthly': {'value': D('1646.47'), 'note': '', 'year': 2026, 'is_confirmed': True},
    'zus_fp_monthly': {'value': D('127.49'), 'note': '', 'year': 2026, 'is_confirmed': True},
}


def doc(fid, net, tax, is_income=False, **extra):
    row = {'fakturownia_id': fid, 'number': f'FV/{fid}', 'counterparty_name': f'Kontrahent {fid}',
           'kind': 'vat', 'is_income': is_income, 'net_pln': D(net), 'tax_pln': D(tax)}
    row.update(extra)
    return row


class VatEstimateTest(unittest.TestCase):
    def test_nalezny_minus_naliczony(self):
        """10 000 netto sprzedaży (2 300 VAT) minus 1 000 VAT zakupów = 1 300 do zapłaty."""
        result = fin_tax.vat_estimate(
            '2026-08',
            [doc(1, 10000, 2300, is_income=True)],
            [doc(2, 4000, 1000, vat_deduction_percent=100)])
        self.assertEqual(result['due'], D('2300.00'))
        self.assertEqual(result['deductible'], D('1000.00'))
        self.assertEqual(result['to_pay'], D('1300'))
        self.assertEqual(result['carry_forward'], Decimal('0'))
        self.assertEqual(result['income_count'], 1)
        self.assertEqual(result['cost_count'], 1)
        self.assertEqual(result['exceptions'], [])

    def test_odliczenie_50_procent_i_nkup(self):
        """Paliwo: VAT 1 000 przy 50% odliczenia daje 500, reszta jest wypisana."""
        result = fin_tax.vat_estimate(
            '2026-08', [doc(1, 10000, 2300, is_income=True)],
            [doc(2, 4000, 1000, vat_deduction_percent=50),
             doc(3, 1000, 230, vat_deduction_percent=0)])
        self.assertEqual(result['deductible'], D('500.00'))
        self.assertEqual(result['to_pay'], D('1800'))
        self.assertEqual({e['fakturownia_id'] for e in result['limited']}, {2, 3})
        limited = {e['fakturownia_id']: e for e in result['limited']}
        self.assertEqual(limited[2]['deducted'], D('500.00'))
        self.assertEqual(limited[2]['dropped'], D('500.00'))
        self.assertEqual(limited[3]['deducted'], Decimal('0.00'))

    def test_brak_kategorii_liczy_sie_jak_100_procent_ale_jest_wypisany(self):
        result = fin_tax.vat_estimate('2026-08', [], [doc(2, 1000, 230)])
        self.assertEqual(result['deductible'], D('230.00'))
        self.assertEqual(result['uncategorized_tax'], D('230.00'))
        self.assertEqual([d['fakturownia_id'] for d in result['uncategorized']], [2])
        self.assertEqual(result['limited'], [])

    def test_nadwyzka_zamiast_zaplaty(self):
        result = fin_tax.vat_estimate('2026-08', [doc(1, 1000, 230, is_income=True)],
                                      [doc(2, 4000, 920, vat_deduction_percent=100)])
        self.assertEqual(result['to_pay'], Decimal('0'))
        self.assertEqual(result['carry_forward'], D('690.00'))

    def test_nadwyzka_z_poprzedniego_okresu_obniza_zaplate(self):
        result = fin_tax.vat_estimate('2026-08', [doc(1, 10000, 2300, is_income=True)], [],
                                      carry_from_previous=D('300'))
        self.assertEqual(result['to_pay'], D('2000'))

    def test_zaokraglenie_do_pelnych_zlotych(self):
        """Podatek zaokrągla się do pełnych złotych, w górę od 50 groszy."""
        result = fin_tax.vat_estimate('2026-08', [doc(1, 1000, '230.50', is_income=True)], [])
        self.assertEqual(result['to_pay'], D('231'))
        result = fin_tax.vat_estimate('2026-08', [doc(1, 1000, '230.49', is_income=True)], [])
        self.assertEqual(result['to_pay'], D('230'))


class VatExceptionTest(unittest.TestCase):
    def test_powody_wylaczenia(self):
        cases = [
            (doc(1, 100, 23, cancelled=True), 'cancelled'),
            (doc(2, 100, 23, exclude_from_accounting=True), 'excluded'),
            (doc(3, 100, 23, kind='vat_margin'), 'margin'),
            (doc(4, 100, 23, use_moss=True), 'oss'),
            (doc(5, 100, 23, reverse_charge=True), 'reverse_charge'),
            (doc(6, 100, 0, kind='import_service'), 'self_charge'),
            (doc(7, 100, 0), 'zero_vat'),
            (doc(8, 100, 23), None),
        ]
        for row, expected in cases:
            self.assertEqual(fin_tax.vat_exception(row), expected, row['fakturownia_id'])

    def test_korekta_z_zerowym_vat_na_ujemnym_netto_nie_jest_wyjatkiem(self):
        """Korekta samego netto ma zerowy VAT z definicji — nie ma co zgłaszać."""
        self.assertIsNone(fin_tax.vat_exception(doc(9, -500, 0, kind='correction')))

    def test_wyjatki_nie_wchodza_do_sum(self):
        result = fin_tax.vat_estimate(
            '2026-08',
            [doc(1, 10000, 2300, is_income=True), doc(2, 5000, 0, is_income=True)],
            [doc(3, 1000, 230, vat_deduction_percent=100),
             doc(4, 2000, 460, reverse_charge=True, vat_deduction_percent=100)])
        self.assertEqual(result['due'], D('2300.00'))       # bez zerowego VAT-u
        self.assertEqual(result['deductible'], D('230.00'))  # bez odwrotnego obciążenia
        self.assertEqual(result['income_count'], 1)
        self.assertEqual(result['cost_count'], 1)
        reasons = {e['fakturownia_id']: e['reason'] for e in result['exceptions']}
        self.assertEqual(reasons, {2: 'zero_vat', 4: 'reverse_charge'})
        self.assertTrue(all(e['reason_label'] for e in result['exceptions']))


class PitAdvanceTest(unittest.TestCase):
    def test_zaliczka_narastajaco(self):
        """100 000 − 40 000 − 5 000 − 2 000 = 53 000; 19% = 10 070; minus 4 000 zaliczek."""
        result = fin_tax.pit_advance('2026-08', D(100000), D(40000), D(5000), D(2000),
                                     D(4000), RATES)
        self.assertEqual(result['taxable'], D('53000.00'))
        self.assertEqual(result['tax_ytd'], D('10070'))
        self.assertEqual(result['to_pay'], D('6070'))
        self.assertEqual(result['overpaid'], Decimal('0'))
        self.assertEqual(result['due_date'], date(2026, 9, 21))  # 20 września to niedziela

    def test_strata_daje_zero_a_nie_ujemny_podatek(self):
        result = fin_tax.pit_advance('2026-08', D(10000), D(30000), D(5000), Decimal('0'),
                                     Decimal('0'), RATES)
        self.assertEqual(result['taxable'], Decimal('0.00'))
        self.assertEqual(result['tax_ytd'], Decimal('0'))
        self.assertEqual(result['to_pay'], Decimal('0'))
        self.assertEqual(result['loss'], D('25000.00'))

    def test_nadplata_gdy_zaliczki_wyzsze_od_podatku(self):
        result = fin_tax.pit_advance('2026-08', D(10000), Decimal('0'), Decimal('0'),
                                     Decimal('0'), D(5000), RATES)
        self.assertEqual(result['tax_ytd'], D('1900'))
        self.assertEqual(result['to_pay'], Decimal('0'))
        self.assertEqual(result['overpaid'], D('3100'))

    def test_brak_stawki_to_blad_a_nie_zero(self):
        with self.assertRaises(ValueError):
            fin_tax.pit_advance('2026-08', D(1000), Decimal('0'), Decimal('0'),
                                Decimal('0'), Decimal('0'), {})


class HealthContributionTest(unittest.TestCase):
    def test_procent_od_dochodu(self):
        result = fin_tax.health_contribution('2026-08', D(20000), RATES)
        self.assertEqual(result['amount'], D('980.00'))  # 4,9% z 20 000
        self.assertFalse(result['is_minimum'])

    def test_minimum_gdy_dochod_niski(self):
        result = fin_tax.health_contribution('2026-08', D(1000), RATES)
        self.assertEqual(result['from_income'], D('49.00'))
        self.assertEqual(result['amount'], D('314.96'))
        self.assertTrue(result['is_minimum'])

    def test_minimum_gdy_strata(self):
        result = fin_tax.health_contribution('2026-08', D(-5000), RATES)
        self.assertEqual(result['amount'], D('314.96'))
        self.assertTrue(result['is_minimum'])

    def test_skladki_spoleczne_z_tabeli_stawek(self):
        result = fin_tax.social_contribution('2026-08', RATES)
        self.assertEqual(result['amount'], D('1773.96'))
        self.assertEqual(result['due_date'], date(2026, 9, 21))


class DeadlineTest(unittest.TestCase):
    def test_wielkanoc(self):
        self.assertEqual(fin_tax.easter(2025), date(2025, 4, 20))
        self.assertEqual(fin_tax.easter(2026), date(2026, 4, 5))
        self.assertEqual(fin_tax.easter(2027), date(2027, 3, 28))

    def test_swieta_ruchome_sa_wolne(self):
        free = fin_tax.holidays(2026)
        self.assertIn(date(2026, 4, 6), free)   # poniedziałek wielkanocny
        self.assertIn(date(2026, 6, 4), free)   # Boże Ciało
        self.assertIn(date(2026, 5, 24), free)  # Zielone Świątki

    def test_vat_do_25_z_przesunieciem_za_weekend(self):
        self.assertEqual(fin_tax.due_date('vat', '2026-08'), date(2026, 9, 25))  # piątek
        self.assertEqual(fin_tax.due_date('vat', '2025-12'), date(2026, 1, 26))  # 25 to niedziela

    def test_termin_przeskakuje_swieta_bozonarodzeniowe(self):
        """25 XI +1 miesiąc = 25 XII: święto, potem drugi dzień świąt i weekend."""
        self.assertEqual(fin_tax.due_date('vat', '2025-11'), date(2025, 12, 29))

    def test_pit_i_zus_do_20(self):
        self.assertEqual(fin_tax.due_date('pit', '2026-04'), date(2026, 5, 20))
        self.assertEqual(fin_tax.due_date('zus_social', '2026-08'), date(2026, 9, 21))
        self.assertEqual(fin_tax.due_date('zus_health', '2026-08'), date(2026, 9, 21))

    def test_grudzien_przechodzi_na_kolejny_rok(self):
        self.assertEqual(fin_tax.due_date('pit', '2026-12'), date(2027, 1, 20))

    def test_nieznany_rodzaj_i_zly_okres(self):
        self.assertIsNone(fin_tax.due_date('cit', '2026-08'))
        self.assertIsNone(fin_tax.due_date('vat', 'sierpień'))


class ObligationRowsTest(unittest.TestCase):
    def _overview(self, saved=None):
        return {
            'period': '2026-08',
            'vat': {'to_pay': D('1300'), 'due_date': date(2026, 9, 25)},
            'pit': {'to_pay': D('6070'), 'due_date': date(2026, 9, 21)},
            'social': {'amount': D('1773.96'), 'due_date': date(2026, 9, 21)},
            'health': {'amount': D('314.96'), 'due_date': date(2026, 9, 21)},
            'obligations': saved or {},
        }

    def test_cztery_zobowiazania_z_symulacji(self):
        rows = fin_tax.obligation_rows(self._overview())
        self.assertEqual([r['kind'] for r in rows], ['vat', 'pit', 'zus_social', 'zus_health'])
        self.assertEqual(rows[0]['amount'], D('1300.00'))
        self.assertIsNone(rows[0]['declared'])
        self.assertIsNone(rows[0]['paid_at'])

    def test_wpis_czlowieka_wygrywa_z_symulacja(self):
        saved = {'vat': {'amount_declared': D('1250'), 'paid_at': date(2026, 9, 24),
                         'due_date': date(2026, 9, 25)}}
        rows = {r['kind']: r for r in fin_tax.obligation_rows(self._overview(saved))}
        self.assertEqual(rows['vat']['calculated'], D('1300.00'))
        self.assertEqual(rows['vat']['declared'], D('1250.00'))
        self.assertEqual(rows['vat']['amount'], D('1250.00'))
        self.assertEqual(rows['vat']['paid_at'], date(2026, 9, 24))
        self.assertIsNone(rows['pit']['paid_at'])


class PeriodOverviewTest(unittest.TestCase):
    """Spięcie warstw: sprawdzamy, czym silnik jest karmiony, nie samą arytmetykę."""

    def setUp(self):
        self.store = mock.MagicMock()
        self.store.get_rates.return_value = dict(RATES)
        self.store.vat_register.return_value = ([doc(1, 10000, 2300, is_income=True)],
                                                [doc(2, 4000, 1000, vat_deduction_percent=100)])
        self.store.income_tax_totals.return_value = {
            'income_net': D(100000), 'cost_net': D(40000), 'cost_gross_net': D(41000),
            'cost_uncategorized': 3, 'documents': 20, 'result': D(60000),
            'months': 8, 'year': 2026}
        self.store.month_income.return_value = D(20000)
        self.store.paid_amount.side_effect = lambda kind, year, period, inclusive=True: {
            'zus_social': D(5000), 'zus_health': D(2000), 'pit': D(4000)}[kind]
        self.store.list_obligations.return_value = []
        # `from models import fin_tax` czyta atrybut pakietu, więc podmiana samego
        # sys.modules nie wystarcza — patchujemy oba wejścia.
        for patcher in (mock.patch.dict('sys.modules', {'models.fin_tax': self.store}),
                        mock.patch('models.fin_tax', self.store)):
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_podstawa_zdrowotnej_to_poprzedni_miesiac(self):
        overview = fin_tax.period_overview('2026-08')
        self.store.month_income.assert_called_once_with('2026-07')
        self.assertEqual(overview['health']['basis_month'], '2026-07')
        self.assertEqual(overview['health']['amount'], D('980.00'))

    def test_styczen_bierze_podstawe_z_grudnia_poprzedniego_roku(self):
        fin_tax.period_overview('2026-01')
        self.store.month_income.assert_called_once_with('2025-12')

    def test_zaliczki_pit_licza_sie_tylko_za_wczesniejsze_miesiace(self):
        fin_tax.period_overview('2026-08')
        pit_call = [c for c in self.store.paid_amount.call_args_list if c.args[0] == 'pit'][0]
        self.assertFalse(pit_call.kwargs['inclusive'])

    def test_zdrowotna_odliczana_do_limitu(self):
        self.store.paid_amount.side_effect = lambda kind, year, period, inclusive=True: {
            'zus_social': D(0), 'zus_health': D(20000), 'pit': D(0)}[kind]
        overview = fin_tax.period_overview('2026-08')
        self.assertEqual(overview['pit']['health_deducted'], D('12900.00'))

    def test_ostrzezenie_o_niepotwierdzonych_stawkach(self):
        rates = dict(RATES)
        rates['zus_social_monthly'] = {'value': D('1646.47'), 'note': 'PRZENIESIONE Z 2025',
                                       'year': 2025, 'is_confirmed': False}
        self.store.get_rates.return_value = rates
        overview = fin_tax.period_overview('2026-08')
        self.assertEqual(overview['rates_warning'], ['PRZENIESIONE Z 2025'])

    def test_brak_ostrzezen_gdy_stawki_potwierdzone(self):
        self.assertEqual(fin_tax.period_overview('2026-08')['rates_warning'], [])
