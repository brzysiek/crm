"""Liczniki użyć przy tagach/branżach/źródłach w Ustawieniach → Słowniki.

Błąd, przed którym to broni: dwa złączenia do tabel wiążących (firmy i kontakty)
w jednym zapytaniu mnożą wiersze i licznik pokazuje iloczyn zamiast sumy.
Druga pułapka to polska odmiana — „5 firmy" albo „22 firm" wygląda na usterkę.
Uruchomienie: venv/bin/python -m unittest discover tests
"""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class GetTagsCountsTest(unittest.TestCase):
    """Sprawdza kształt zapytania bez dotykania bazy produkcyjnej."""

    def _run(self, **kwargs):
        from models import crm_tags
        cur = mock.MagicMock()
        cur.fetchall.return_value = []
        db = mock.MagicMock()
        db.cursor.return_value.__enter__.return_value = cur
        with mock.patch.object(crm_tags, 'get_db', return_value=db):
            crm_tags.get_tags('tag', **kwargs)
        return cur.execute.call_args[0][0]

    def test_plain_call_stays_minimal(self):
        sql = self._run()
        self.assertNotIn('COUNT', sql)

    def test_counts_use_subqueries_not_joins(self):
        sql = self._run(with_counts=True)
        self.assertIn('crm_company_tags', sql)
        self.assertIn('crm_contact_tags', sql)
        self.assertIn('company_count', sql)
        self.assertIn('contact_count', sql)
        # JOIN do obu tabel naraz zawyżyłby obie liczby.
        self.assertNotIn('JOIN', sql.upper())


class UsageCountMacroTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import app
        cls.macro = app.jinja_env.get_template('settings/_macros.html').module.usage_count

    def render(self, company, contact):
        return str(self.macro({'company_count': company, 'contact_count': contact}))

    def test_companies_only(self):
        self.assertIn('(715 firm)', self.render(715, 0))

    def test_both_sides_listed(self):
        out = self.render(2, 1)
        self.assertIn('2 firmy', out)
        self.assertIn('1 kontakt', out)

    def test_contacts_only_skips_zero_companies(self):
        out = self.render(0, 4)
        self.assertIn('4 kontakty', out)
        self.assertNotIn('firm', out)

    def test_unused_value_shows_zero(self):
        self.assertIn('(0)', self.render(0, 0))

    def test_polish_plural_edge_cases(self):
        self.assertIn('1 firma', self.render(1, 0))
        self.assertIn('3 firmy', self.render(3, 0))
        self.assertIn('5 firm', self.render(5, 0))
        self.assertIn('12 firm', self.render(12, 0))   # nie „12 firmy"
        self.assertIn('22 firmy', self.render(22, 0))
        self.assertIn('112 firm', self.render(112, 0))
        self.assertIn('22 kontakty', self.render(0, 22))
        self.assertIn('15 kontaktów', self.render(0, 15))


if __name__ == '__main__':
    unittest.main()
