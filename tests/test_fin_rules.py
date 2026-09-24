"""Testy auto-kategoryzacji: normalizacja NIP, dopasowanie reguł, tabela przestawna.

Baza jest zamockowana. Uruchomienie: venv/bin/python -m unittest discover tests
"""
import unittest
from decimal import Decimal
from unittest import mock

import routes.fin as fin_routes
import services.fin_rules as fin_rules
from services.fin_sync import normalize_tax_no


class NormalizeTaxNoTest(unittest.TestCase):
    """Ten sam kontrahent przychodzi raz z prefiksem kraju, raz bez."""

    def test_pl_prefix_is_stripped(self):
        self.assertEqual(normalize_tax_no('PL5262544258'), '5262544258')
        self.assertEqual(normalize_tax_no('5262544258'), '5262544258')

    def test_separators_are_removed(self):
        self.assertEqual(normalize_tax_no('526-254-42-58'), '5262544258')
        self.assertEqual(normalize_tax_no(' 526 254 42 58 '), '5262544258')

    def test_foreign_number_keeps_its_prefix(self):
        """IE8256796U to numer irlandzki — obcięcie „IE” zrobiłoby z niego śmieć."""
        self.assertEqual(normalize_tax_no('IE8256796U'), 'IE8256796U')

    def test_country_prefix_stays_when_rest_is_not_ten_digits(self):
        self.assertEqual(normalize_tax_no('DE123456789'), 'DE123456789')

    def test_empty_values(self):
        self.assertEqual(normalize_tax_no(None), '')
        self.assertEqual(normalize_tax_no(''), '')


class RuleMatchTest(unittest.TestCase):
    def rule(self, **over):
        base = {'id': 1, 'match_field': 'counterparty_name', 'match_type': 'contains',
                'match_value': 'orlen', 'category_id': 5, 'category_kind': 'cost'}
        base.update(over)
        return base

    def doc(self, **over):
        base = {'fakturownia_id': 1, 'is_income': 0, 'counterparty_name': 'ORLEN S.A.',
                'counterparty_tax_no_norm': '7740001454', 'number': 'FV/1/2026',
                'description': '', 'accounting_kind': ''}
        base.update(over)
        return base

    def test_contains_ignores_case(self):
        self.assertTrue(fin_rules.rule_matches(self.rule(), self.doc()))

    def test_equals_needs_whole_value(self):
        self.assertFalse(fin_rules.rule_matches(self.rule(match_type='equals'), self.doc()))
        self.assertTrue(fin_rules.rule_matches(
            self.rule(match_type='equals', match_field='counterparty_tax_no_norm',
                      match_value='7740001454'), self.doc()))

    def test_starts_with(self):
        self.assertTrue(fin_rules.rule_matches(self.rule(match_type='starts_with'), self.doc()))
        self.assertFalse(fin_rules.rule_matches(
            self.rule(match_type='starts_with', match_value='s.a.'), self.doc()))

    def test_regex(self):
        self.assertTrue(fin_rules.rule_matches(
            self.rule(match_type='regex', match_value=r'orlen|shell'), self.doc()))

    def test_broken_regex_does_not_raise(self):
        """Zepsuta reguła nie może wywalić całej synchronizacji."""
        self.assertFalse(fin_rules.rule_matches(
            self.rule(match_type='regex', match_value='[niedomknięte'), self.doc()))

    def test_unknown_field_never_matches(self):
        self.assertFalse(fin_rules.rule_matches(self.rule(match_field='password'), self.doc()))

    def test_empty_document_field_never_matches(self):
        self.assertFalse(fin_rules.rule_matches(self.rule(), self.doc(counterparty_name='')))

    def test_empty_rule_value_never_matches(self):
        self.assertFalse(fin_rules.rule_matches(self.rule(match_value='  '), self.doc()))


class FirstMatchTest(unittest.TestCase):
    def test_first_rule_in_order_wins(self):
        rules = [{'id': 1, 'match_field': 'counterparty_name', 'match_type': 'contains',
                  'match_value': 'orlen', 'category_id': 5, 'category_kind': 'cost'},
                 {'id': 2, 'match_field': 'counterparty_name', 'match_type': 'contains',
                  'match_value': 'orlen', 'category_id': 9, 'category_kind': 'cost'}]
        doc = {'is_income': 0, 'counterparty_name': 'ORLEN'}
        self.assertEqual(fin_rules.first_match(doc, rules)['category_id'], 5)

    def test_cost_category_never_lands_on_income(self):
        rules = [{'id': 1, 'match_field': 'counterparty_name', 'match_type': 'contains',
                  'match_value': 'klient', 'category_id': 5, 'category_kind': 'cost'}]
        doc = {'is_income': 1, 'counterparty_name': 'Klient S.A.'}
        self.assertIsNone(fin_rules.first_match(doc, rules))

    def test_income_rule_matches_income_document(self):
        rules = [{'id': 1, 'match_field': 'counterparty_name', 'match_type': 'contains',
                  'match_value': 'klient', 'category_id': 5, 'category_kind': 'income'}]
        doc = {'is_income': 1, 'counterparty_name': 'Klient S.A.'}
        self.assertEqual(fin_rules.first_match(doc, rules)['id'], 1)

    def test_no_rules_means_no_match(self):
        self.assertIsNone(fin_rules.first_match({'is_income': 0}, []))


class CreateRuleValidationTest(unittest.TestCase):
    def test_unknown_field_is_rejected(self):
        with self.assertRaises(ValueError):
            fin_rules.create_rule('haslo', 'equals', 'x', 1)

    def test_unknown_type_is_rejected(self):
        with self.assertRaises(ValueError):
            fin_rules.create_rule('counterparty_name', 'sounds_like', 'x', 1)

    def test_broken_regex_is_rejected_at_creation(self):
        """Lepiej, żeby zła regexp wybuchła przy zapisie niż w trakcie syncu."""
        import re
        with self.assertRaises(re.error):
            fin_rules.create_rule('counterparty_name', 'regex', '[niedomknięte', 1)


class ApplyRulesTest(unittest.TestCase):
    def test_manual_assignments_are_never_overwritten(self):
        """Reguły dotykają tylko dokumentów bez kategorii albo przypisanych regułą."""
        captured = {}

        class Cursor:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def execute(self, sql, params=()):
                captured['sql'] = sql
            def fetchall(self): return []

        db = mock.MagicMock()
        db.cursor.return_value = Cursor()
        rules = [{'id': 1, 'match_field': 'counterparty_name', 'match_type': 'contains',
                  'match_value': 'x', 'category_id': 1, 'category_kind': 'cost'}]
        with mock.patch.object(fin_rules, 'list_rules', return_value=rules), \
             mock.patch.object(fin_rules, 'get_db', return_value=db):
            fin_rules.apply_rules()
        self.assertIn('m.category_id IS NULL', captured['sql'])
        self.assertNotIn("m.source = 'rule'", captured['sql'])

    def test_recategorize_mode_includes_rule_assigned(self):
        captured = {}

        class Cursor:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def execute(self, sql, params=()):
                captured['sql'] = sql
            def fetchall(self): return []

        db = mock.MagicMock()
        db.cursor.return_value = Cursor()
        rules = [{'id': 1, 'match_field': 'counterparty_name', 'match_type': 'contains',
                  'match_value': 'x', 'category_id': 1, 'category_kind': 'cost'}]
        with mock.patch.object(fin_rules, 'list_rules', return_value=rules), \
             mock.patch.object(fin_rules, 'get_db', return_value=db):
            fin_rules.apply_rules(recategorize_rule_assigned=True)
        self.assertIn("m.source = 'rule'", captured['sql'])

    def test_no_rules_means_no_query(self):
        with mock.patch.object(fin_rules, 'list_rules', return_value=[]):
            self.assertEqual(fin_rules.apply_rules(), {'checked': 0, 'assigned': 0, 'rules': 0})


class PivotTest(unittest.TestCase):
    def test_categories_are_ordered_by_total(self):
        months = ['2026-08', '2026-09']
        rows = [
            {'month': '2026-08', 'category_id': 1, 'category_name': 'Paliwo',
             'net': Decimal('100'), 'documents': 1},
            {'month': '2026-09', 'category_id': 1, 'category_name': 'Paliwo',
             'net': Decimal('50'), 'documents': 1},
            {'month': '2026-09', 'category_id': 2, 'category_name': 'IT',
             'net': Decimal('500'), 'documents': 2},
        ]
        pivot = fin_routes._pivot(rows, months)
        self.assertEqual([p['category_name'] for p in pivot], ['IT', 'Paliwo'])
        self.assertEqual(pivot[1]['series'], [Decimal('100'), Decimal('50')])
        self.assertEqual(pivot[1]['documents'], 2)

    def test_missing_month_becomes_zero(self):
        pivot = fin_routes._pivot(
            [{'month': '2026-09', 'category_id': 1, 'category_name': 'IT',
              'net': Decimal('10'), 'documents': 1}],
            ['2026-07', '2026-08', '2026-09'])
        self.assertEqual(pivot[0]['series'], [Decimal('0'), Decimal('0'), Decimal('10')])

    def test_null_category_gets_a_name(self):
        pivot = fin_routes._pivot(
            [{'month': '2026-09', 'category_id': None, 'category_name': None,
              'net': Decimal('10'), 'documents': 1}], ['2026-09'])
        self.assertEqual(pivot[0]['category_name'], 'Bez kategorii')


class SlugifyTest(unittest.TestCase):
    def test_polish_letters_are_transliterated(self):
        self.assertEqual(fin_routes._slugify('Podróże służbowe'), 'podroze-sluzbowe')
        self.assertEqual(fin_routes._slugify('Księgowość i prawo'), 'ksiegowosc-i-prawo')

    def test_separators_are_collapsed(self):
        self.assertEqual(fin_routes._slugify('Samochód — paliwo'), 'samochod-paliwo')

    def test_empty_input(self):
        self.assertEqual(fin_routes._slugify('   '), '')


if __name__ == '__main__':
    unittest.main()
