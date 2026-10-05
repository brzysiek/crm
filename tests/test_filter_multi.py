"""Filtr wielowartościowy: wiele wartości naraz, wykluczanie, liczniki.

Błąd, przed którym to broni: filtr brał jedną wartość na wymiar. „Branża:
produkcja albo logistyka" wymagało dwóch przebiegów i ręcznego sumowania,
a „produkcja, ale nie klient" nie dało się zadać wcale. Drugi błąd: listy
wartości są długie (ponad czterysta branż) i w większości wiszą na jednej
firmie — bez licznika przy wartości wybiera się filtry, które nic nie zwracają.
Testy liczą na produkcyjnej bazie, więc sprawdzają relacje między liczbami.
Uruchomienie: venv/bin/python -m unittest discover tests
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(rel: str) -> str:
    with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
        return f.read()


class ManyValuesTest(unittest.TestCase):
    """Wiele wartości znaczy „albo", wykluczenie znaczy „i nie"."""

    @classmethod
    def setUpClass(cls):
        from app import app
        from models.crm_company import count_companies, get_all_companies
        from models.crm_contact import count_contacts
        cls.ctx = app.app_context()
        cls.ctx.push()
        cls.companies = staticmethod(count_companies)
        cls.rows = staticmethod(get_all_companies)
        cls.contacts = staticmethod(count_contacts)
        cls.total = count_companies()

    @classmethod
    def tearDownClass(cls):
        cls.ctx.pop()

    def test_two_values_mean_either_of_them(self):
        a = self.companies(relation_type=['lead'])
        b = self.companies(relation_type=['partner'])
        both = self.companies(relation_type=['lead', 'partner'])
        self.assertEqual(a + b, both, 'relacja jest jedna, więc suma musi się zgadzać co do jednego')

    def test_either_of_two_tags_is_at_least_as_wide_as_one(self):
        """Tagów firma ma wiele, więc suma może być mniejsza niż a+b (część ma oba),
        ale nigdy mniejsza niż szersza z grup i nigdy większa niż ich suma."""
        a = self.companies(industry=['Konsulting'])
        b = self.companies(industry=['Prawo'])
        both = self.companies(industry=['Konsulting', 'Prawo'])
        self.assertGreaterEqual(both, max(a, b))
        self.assertLessEqual(both, a + b)

    def test_excluding_is_the_complement_of_including(self):
        inside = self.companies(industry=['Konsulting'])
        outside = self.companies(industry_not=['Konsulting'])
        self.assertEqual(self.total, inside + outside,
                         'firma albo ma tę branżę, albo nie — trzeciej możliwości nie ma')

    def test_including_and_excluding_work_together(self):
        """To jest całe pytanie, dla którego ten filtr powstał: „lead, ale nie X"."""
        leads = self.companies(relation_type=['lead'])
        with_it = self.companies(relation_type=['lead'], industry=['Konsulting'])
        without_it = self.companies(relation_type=['lead'], industry_not=['Konsulting'])
        self.assertEqual(leads, with_it + without_it)

    def test_the_count_matches_the_rows_actually_returned(self):
        """Licznik i lista idą z tego samego warunku — paginacja kłamałaby inaczej."""
        kwargs = {'industry': ['Konsulting', 'Prawo']}
        self.assertEqual(self.companies(**kwargs), len(self.rows(limit=None, **kwargs)))

    def test_contacts_inherit_the_exclusion_from_their_company(self):
        total = self.contacts()
        inside = self.contacts(industry=['Konsulting'])
        outside = self.contacts(industry_not=['Konsulting'])
        self.assertEqual(total, inside + outside)

    def test_a_single_value_link_still_works(self):
        """Stare linki i zakładki mają `?tag=X` bez listy — nie wolno ich zepsuć."""
        self.assertEqual(self.companies(industry='Konsulting'),
                         self.companies(industry=['Konsulting']))


class FilterOptionsTest(unittest.TestCase):
    """Słownik filtra pokazuje tylko to, co coś zwróci, i mówi ile."""

    @classmethod
    def setUpClass(cls):
        from app import app
        cls.client = app.test_client()
        with cls.client.session_transaction() as s:
            s['user_id'] = 1
            s['username'] = 'test'
            s['full_name'] = 'Test'

    def _options(self, **params):
        query = '&'.join(f'{k}={v}' for k, v in params.items())
        resp = self.client.get('/api/crm/filter-options?' + query)
        self.assertEqual(200, resp.status_code)
        return resp.get_json()

    def test_every_option_has_a_name_and_a_count(self):
        for kind in ('industry', 'tag', 'source', 'city'):
            options = self._options(kind=kind)
            self.assertTrue(options, kind)
            for o in options:
                self.assertIn('name', o)
                self.assertGreater(o['count'], 0,
                                   f'{kind}: wartość bez trafień zaśmieca listę wyboru')

    def test_contact_counts_differ_from_company_counts(self):
        """Na liście kontaktów licznik ma mówić o ludziach, nie o firmach —
        inaczej „Branża: Prawo (10)" obiecywałoby dziesięć, a dawało trzydzieści."""
        by_company = {o['name']: o['count'] for o in self._options(kind='industry')}
        by_contact = {o['name']: o['count'] for o in self._options(kind='industry', entity='contact')}
        self.assertNotEqual(by_company, by_contact)

    def test_an_unknown_kind_returns_nothing_instead_of_failing(self):
        self.assertEqual([], self._options(kind='nieistniejacy'))

    def test_the_selected_value_really_returns_that_many_records(self):
        """Licznik przy wartości musi zgadzać się z tym, co pokaże filtr."""
        from app import app
        from models.crm_company import count_companies
        name, count = max(((o['name'], o['count']) for o in self._options(kind='industry')),
                          key=lambda x: x[1])
        with app.app_context():
            self.assertEqual(count, count_companies(industry=[name]))


class WidgetIsWiredUpTest(unittest.TestCase):
    """Szablon, JS i CSS muszą mówić o tym samym widżecie — rozjazd widać dopiero
    u użytkownika, w postaci filtra, który nic nie robi."""

    def test_both_lists_use_the_shared_macro(self):
        for rel in ('templates/crm/companies/list.html', 'templates/crm/contacts/list.html'):
            html = read(rel)
            self.assertIn('m.filter_multi(', html, rel)
            self.assertNotIn('<option value="">Wszystkie branże</option>', html,
                             'pojedynczy <select> zastąpiony widżetem')

    def test_the_macro_emits_the_hidden_inputs_the_backend_reads(self):
        macro = read('templates/crm/_macros.html')
        self.assertIn("name=\"{{ name }}\"", macro)
        self.assertIn("name=\"{{ name }}_not\"", macro)

    def test_javascript_and_styles_know_the_widget(self):
        self.assertIn('initFilterMulti', read('static/app.js'))
        self.assertIn('.fmulti-toggle', read('static/style.css'))

    def test_the_backend_accepts_every_dimension_the_templates_offer(self):
        from routes.crm_companies import COMPANY_FILTER_KEYS
        from routes.crm_contacts import CONTACT_FILTER_KEYS
        for key in COMPANY_FILTER_KEYS:
            self.assertIn(f"'{key.replace('_not', '')}'", read('templates/crm/companies/list.html'))
        self.assertIn('email_tag', CONTACT_FILTER_KEYS)

    def test_the_collapsed_filter_bar_says_how_many_filters_are_on(self):
        """Pasek zwija się na telefonie; bez licznika lista skrócona ze 198 do 12
        pozycji wygląda na błąd, a nie na działający filtr."""
        self.assertIn('activeFilterCount', read('static/app.js'))


if __name__ == '__main__':
    unittest.main()
