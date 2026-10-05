"""Filtrowanie kontaktów — własne i odziedziczone po firmie.

Błąd, przed którym to broni: przy firmach dało się filtrować po relacji, branży,
tagu i źródle, a przy kontaktach był tylko wolny tekst. Pytania w tej pracy
zadaje się o ludzi („kto siedzi w private equity”, „kto u partnerów nie ma
maila”), a atrybut wisi przy firmie — bez dziedziczenia takie pytanie wymagało
przejścia przez listę firm i otwierania ich po kolei.
Drugi błąd: filtr brał tylko jedną wartość, więc „PE albo VC albo family office”
trzeba było zadać trzy razy i ręcznie sumować wyniki.
Testy liczą na produkcyjnej bazie, więc sprawdzają relacje między liczbami,
a nie konkretne liczby — te zmieniają się z każdym nowym kontaktem.
Uruchomienie: venv/bin/python -m unittest discover tests
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ContactFilterTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from app import app
        from models.crm_contact import count_contacts, get_all_contacts
        cls.ctx = app.app_context()
        cls.ctx.push()
        # staticmethod, inaczej dostęp przez self przekazałby testcase jako
        # pierwszy argument pozycyjny (search) i każdy filtr zwracałby zero.
        cls.count = staticmethod(count_contacts)
        cls.rows = staticmethod(get_all_contacts)
        cls.total = count_contacts()

    @classmethod
    def tearDownClass(cls):
        cls.ctx.pop()

    def test_every_filter_narrows_the_list(self):
        for label, kwargs in (
            ('relacja', {'relation_type': 'partner'}),
            ('bez maila', {'has_email': 'no'}),
            ('branża', {'industry': 'Private Equity'}),
        ):
            n = self.count(**kwargs)
            self.assertLess(n, self.total, label)
            self.assertGreaterEqual(n, 0, label)

    def test_having_a_mail_and_not_having_one_split_the_whole_base(self):
        """Dwa koszyki bez części wspólnej — pusty string ma liczyć się jako brak."""
        self.assertEqual(self.total,
                         self.count(has_email='yes') + self.count(has_email='no'))

    def test_several_values_in_one_filter_mean_or(self):
        """„PE albo VC” to jedno pytanie: wynik sumy nie może być mniejszy niż
        większy ze składników ani większy niż ich suma (ktoś może mieć obie)."""
        a = self.count(industry='Private Equity')
        b = self.count(industry='Venture Capital')
        both = self.count(industry=['Private Equity', 'Venture Capital'])
        self.assertGreaterEqual(both, max(a, b))
        self.assertLessEqual(both, a + b)

    def test_filters_from_different_dimensions_mean_and(self):
        leads = self.count(relation_type='lead')
        with_mail = self.count(has_email='yes')
        both = self.count(relation_type='lead', has_email='yes')
        self.assertLessEqual(both, min(leads, with_mail))

    def test_a_single_value_still_works_like_before(self):
        """Stare linki `?industry=X` mają działać dalej obok `?industry=X&industry=Y`."""
        self.assertEqual(self.count(industry='Private Equity'),
                         self.count(industry=['Private Equity']))

    def test_no_duplicate_rows_when_a_company_matches_twice(self):
        """Firma z kilkoma branżami nie może wystawiać swojego kontaktu dwa razy —
        dlatego warunek jest EXISTS-em, a nie JOIN-em."""
        names = ['Private Equity', 'Venture Capital', 'Family Office', 'Search Fund']
        rows = self.rows(industry=names, limit=None)
        ids = [r['id'] for r in rows]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), self.count(industry=names))

    def test_an_empty_filter_changes_nothing(self):
        self.assertEqual(self.total, self.count(industry=[], relation_type='', city=None))

    def test_search_also_looks_at_the_position(self):
        import inspect
        from models.crm_contact import _contacts_where
        self.assertIn('ct.position LIKE', inspect.getsource(_contacts_where))


class ContactFilterPageTest(unittest.TestCase):
    """Kontrolki mają stać w pasku filtrów, inaczej model filtruje w próżnię."""

    @classmethod
    def setUpClass(cls):
        from app import app
        cls.client = app.test_client()
        with cls.client.session_transaction() as s:
            s['user_id'] = 1
            s['username'] = 'test'
            s['full_name'] = 'Test'

    def _get(self, url):
        r = self.client.get(url)
        body = r.get_data(as_text=True)
        self.assertEqual(200, r.status_code, url)
        self.assertNotIn('Błąd serwera', body, url)
        return body

    def test_the_filter_bar_offers_the_new_controls(self):
        body = self._get('/crm/contacts/')
        for name in ('name="relation_type"', 'name="industry"', 'name="source"',
                     'name="city"', 'name="has_email"'):
            self.assertIn(name, body, name)

    def test_filtered_urls_render(self):
        for url in ('/crm/contacts/?relation_type=partner',
                    '/crm/contacts/?industry=Private+Equity&industry=Venture+Capital',
                    '/crm/contacts/?has_email=no',
                    '/crm/contacts/?city=Krak%C3%B3w'):
            self._get(url)

    def test_filtering_a_saved_list_keeps_the_list(self):
        """Filtr w widoku listy kontaktów nie może gubić samej listy."""
        from app import app
        from models.crm_contact_list import get_all_lists
        with app.app_context():
            lists = get_all_lists()
        if not lists:
            self.skipTest('brak list kontaktów w bazie')
        body = self._get(f"/crm/contacts/lists/{lists[0]['id']}?has_email=yes")
        self.assertIn(lists[0]['name'], body)


if __name__ == '__main__':
    unittest.main()
