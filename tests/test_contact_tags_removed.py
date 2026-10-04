"""Tagi (rodzaj 'tag') należą do firm, nie do osób.

Błąd, przed którym to broni: pole „Tagi" w formularzu kontaktu dublowało tagi
firmy — ta sama pula wartości opisywała raz organizację, raz osobę, więc filtr
firm po tagu gubił część danych. Po migracji przypisania osób przeszły na ich
firmy i żadna ścieżka zapisu nie może ich tam wrócić. Tagi rodzaju 'email'
(zgody marketingowe) to osobny mechanizm i zostają przy kontaktach.
Uruchomienie: venv/bin/python -m unittest discover tests
"""
import inspect
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(rel: str) -> str:
    with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
        return f.read()


class NoContactTagWritesTest(unittest.TestCase):
    def test_model_has_no_contact_tag_setter(self):
        import models.crm_tags as crm_tags
        self.assertFalse(hasattr(crm_tags, 'set_contact_tags'))
        self.assertFalse(hasattr(crm_tags, 'get_contact_tags'))
        # Zgody email zostają — to inny rodzaj tagu i inna funkcja biznesowa.
        self.assertTrue(hasattr(crm_tags, 'set_contact_email_tags'))

    def test_contact_crud_takes_no_tags(self):
        from models.crm_contact import create_contact, merge_contacts, update_contact
        for fn in (create_contact, update_contact, merge_contacts):
            self.assertNotIn('tags', inspect.signature(fn).parameters, fn.__name__)

    def test_contact_form_has_only_email_tag_input(self):
        form = read('templates/crm/contacts/form.html')
        self.assertNotIn("'tag'", form)
        self.assertIn("'email'", form)


class BusinessCardTagsGoToCompanyTest(unittest.TestCase):
    """Tagi z wizytówki opisują firmę — także wtedy, gdy firma już istnieje."""

    def _run(self, existing_company):
        import services.business_card as bc
        with mock.patch.multiple(
            bc,
            lookup_by_nip=mock.DEFAULT, build_company_profile=mock.DEFAULT,
            get_company_by_nip=mock.DEFAULT, get_company_by_domain=mock.DEFAULT,
            search_companies=mock.DEFAULT, search_contacts=mock.DEFAULT,
            create_company=mock.DEFAULT, create_contact=mock.DEFAULT,
            bulk_add_tag=mock.DEFAULT, set_contact_email_tags=mock.DEFAULT,
        ) as m:
            m['lookup_by_nip'].return_value = {'ok': False}
            m['build_company_profile'].return_value = {'ok': False}
            m['get_company_by_nip'].return_value = existing_company
            m['get_company_by_domain'].return_value = None
            m['search_companies'].return_value = []
            m['search_contacts'].return_value = []
            m['create_company'].return_value = 7
            m['create_contact'].return_value = 70
            bc._process_extracted(
                {'company_name': 'Acme', 'company_nip': '1234567890',
                 'first_name': 'Jan', 'last_name': 'Kowalski'},
                'key', 'model', '', '', user_id=1, uploads=[], tags=['VIP'])
            return m

    def test_new_company_gets_the_tags(self):
        m = self._run(existing_company=None)
        self.assertEqual(m['create_company'].call_args.kwargs['tags'], ['VIP'])

    def test_existing_company_gets_the_tags_added(self):
        m = self._run(existing_company={'id': 9, 'name': 'Acme', 'short_name': 'Acme'})
        m['bulk_add_tag'].assert_called_once_with([9], 'tag', 'VIP', 1)

    def test_contact_is_created_without_tags(self):
        m = self._run(existing_company=None)
        self.assertNotIn('tags', m['create_contact'].call_args.kwargs)


class TagLinksToCompaniesTest(unittest.TestCase):
    """Kliknięcie wartości ma prowadzić do listy firm zawężonej tym filtrem."""

    @classmethod
    def setUpClass(cls):
        from app import app
        cls.app = app

    def test_dictionary_value_links_to_filtered_companies(self):
        macros = self.app.jinja_env.get_template('settings/_macros.html').module
        with self.app.test_request_context():
            html = str(macros.tag_card('Branże', 'branze', 'industry',
                                        [{'id': 1, 'name': 'Doradztwo', 'company_count': 3,
                                          'contact_count': 0}], 'np. Produkcja'))
        self.assertIn('/crm/companies/?industry=Doradztwo', html)

    def test_unused_value_is_not_a_link(self):
        macros = self.app.jinja_env.get_template('settings/_macros.html').module
        with self.app.test_request_context():
            html = str(macros.tag_card('Tagi', 'tagi', 'tag',
                                        [{'id': 2, 'name': 'Nieużywany', 'company_count': 0,
                                          'contact_count': 0}], 'np. VIP'))
        self.assertNotIn('?tag=', html)

    def test_classification_badges_are_links(self):
        for rel, needles in (
            ('templates/crm/companies/detail.html', ("list_companies', tag=t", "list_companies', industry=i")),
            ('templates/crm/contacts/detail.html', ("list_companies', tag=t", "list_companies', industry=i",
                                                     "list_companies', source=s")),
        ):
            html = read(rel)
            for needle in needles:
                self.assertIn(needle, html, rel)


if __name__ == '__main__':
    unittest.main()
