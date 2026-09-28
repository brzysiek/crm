"""Karta firmy (M&A i CRM) pokazuje też notatki osób z tej firmy, z etykietą kogo dotyczą.

Rozmowa z osobą z firmy jest wiedzą o firmie — wcześniej na karcie firmy M&A widać było
tylko notatki wpisane bezpośrednio na firmie, a reszta siedziała na kartach kontaktów.
Uruchomienie: venv/bin/python -m unittest discover tests
"""
import unittest
from unittest import mock

from app import app
import routes.crm_companies as crm_routes
import routes.mna_companies as mna_routes

COMPANY = {'id': 5, 'name': 'Alfa sp. z o.o.'}
CONTACTS = [{'id': 7, 'first_name': 'Przemysław', 'last_name': 'Łukańko'},
            {'id': 8, 'first_name': 'Ewa', 'last_name': 'Nowak'}]


def _notes(company_type):
    return [
        {'id': 1, 'entity_type': company_type, 'entity_id': 5, 'body': 'Notatka na firmie',
         'created_at': '2026-09-02', 'user_name': 'Łukasz'},
        {'id': 2, 'entity_type': company_type.replace('company', 'contact'), 'entity_id': 7,
         'body': 'Rozmowa z Przemkiem', 'created_at': '2026-09-01', 'user_name': 'Łukasz'},
        {'id': 3, 'entity_type': company_type.replace('company', 'contact'), 'entity_id': 99,
         'body': 'Notatka usuniętego kontaktu', 'created_at': '2026-08-30', 'user_name': 'Łukasz'},
    ]


class MnaCompanyNotesTest(unittest.TestCase):
    def _fake_notes_multi(self, entities):
        self.entities = list(entities)
        return _notes('mna_company')

    def setUp(self):
        self.captured = {}
        self.entities = []

        def fake_render(template, **ctx):
            self.captured = ctx
            return ''

        for target, attr, value in (
            (mna_routes, 'get_mna_company_by_id', lambda cid: COMPANY),
            (mna_routes, 'get_all_mna_contacts', lambda **kw: CONTACTS),
            (mna_routes, 'get_deals_for_company', lambda cid: []),
            (mna_routes, 'get_notes_multi', self._fake_notes_multi),
            (mna_routes, 'get_history', lambda *a: []),
            (mna_routes, 'get_company_tags', lambda cid: []),
            (mna_routes, 'render_template', fake_render),
        ):
            patch = mock.patch.object(target, attr, value)
            patch.start()
            self.addCleanup(patch.stop)

        with app.test_request_context('/mna/firmy/5'):
            mna_routes.view_company(5)

    def test_asks_for_company_and_contact_notes(self):
        self.assertEqual(self.entities,
                         [('mna_company', 5), ('mna_contact', 7), ('mna_contact', 8)])

    def test_labels_say_whose_note_it_is(self):
        labels = [n['source_label'] for n in self.captured['notes']]
        self.assertEqual(labels, ['Notatka firmy',
                                  'Notatka kontaktu: Przemysław Łukańko',
                                  'Notatka kontaktu'])

    def test_contact_note_is_deleted_on_its_own_contact(self):
        urls = [n['delete_url'] for n in self.captured['notes']]
        self.assertIn('/mna/firmy/5/notes/1/delete', urls[0])
        self.assertIn('/mna/kontakty/7/notes/2/delete', urls[1])


class CrmCompanyNotesTest(unittest.TestCase):
    """CRM działał tak od początku — test pilnuje, żeby oba moduły się nie rozjechały."""

    def test_crm_company_merges_contact_notes(self):
        self.assertIn('get_notes_multi', crm_routes.view_company.__code__.co_names)


if __name__ == '__main__':
    unittest.main()
