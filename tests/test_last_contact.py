"""„Ostatni kontakt" i filtr „bez kontaktu od X dni".

Błąd, przed którym to broni: zaniedbana relacja nie zgłasza się sama — na liście
198 firm nie widać, z którymi nikt nie rozmawiał od pół roku. Drugi błąd czai się
w definicji: gdyby kontaktem była każda zmiana rekordu, jedno porządkowanie
danych odświeżyłoby całą bazę i filtr przestałby cokolwiek znaczyć.
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


class WhatCountsAsContactTest(unittest.TestCase):
    """Definicja kontaktu jest decyzją, nie szczegółem — pilnujemy jej wprost."""

    def test_edits_of_the_record_are_not_contact(self):
        from models.crm_activity import company_last_contact_sql, contact_last_contact_sql
        for sql in (company_last_contact_sql(), contact_last_contact_sql()):
            self.assertNotIn('crm_history', sql,
                             'poprawienie NIP-u nie jest rozmową z klientem')

    def test_contact_counts_notes_tasks_and_campaigns(self):
        from models.crm_activity import company_last_contact_sql
        sql = company_last_contact_sql()
        for table in ('crm_notes', 'tasks', 'email_campaign_recipients'):
            self.assertIn(table, sql)

    def test_a_person_does_not_inherit_the_company_note(self):
        """Notatka „spotkanie w Torusie" nie znaczy, że rozmawiało się z każdym
        pracownikiem Torusa — przy osobie liczą się tylko jej własne ślady."""
        from models.crm_activity import contact_last_contact_sql
        self.assertNotIn('company_id', contact_last_contact_sql())

    def test_only_the_three_offered_thresholds_reach_sql(self):
        """Progi wchodzą do zapytania bez parametryzacji, więc lista jest zamknięta."""
        from models.crm_activity import stale_days
        for good in (30, 90, 180, '90'):
            self.assertEqual(int(good), stale_days(good))
        for bad in (None, '', 'abc', 45, '1 OR 1=1', -30, 3650):
            self.assertIsNone(stale_days(bad), bad)


class StaleFilterTest(unittest.TestCase):

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

    @classmethod
    def tearDownClass(cls):
        cls.ctx.pop()

    def test_a_longer_silence_is_a_shorter_list(self):
        d30, d90, d180 = (self.companies(stale=d) for d in (30, 90, 180))
        self.assertGreaterEqual(d30, d90)
        self.assertGreaterEqual(d90, d180)
        self.assertLess(d30, self.companies(), 'filtr, który niczego nie odsiewa, jest bezużyteczny')

    def test_never_contacted_belongs_to_the_silent_ones(self):
        """„Nigdy" to skrajny przypadek „od dawna", nie osobna kategoria —
        inaczej firmy, z którymi nikt nie rozmawiał, wypadłyby z listy."""
        never = [r for r in self.rows(limit=None, stale=180) if r['last_contact'].year <= 1000]
        self.assertTrue(never, 'w bazie są firmy bez śladu kontaktu, mają tu być')

    def test_the_column_agrees_with_the_filter(self):
        from datetime import date, timedelta
        cutoff = date.today() - timedelta(days=90)
        for r in self.rows(limit=None, stale=90):
            self.assertLess(r['last_contact'].date(), cutoff, r['name'])

    def test_a_recent_note_lifts_the_company_out_of_the_filter(self):
        """Druga strona tej samej reguły: kto ma świeży ślad, nie jest zaniedbany."""
        from datetime import date, timedelta
        recent = [r for r in self.rows(limit=None)
                  if r['last_contact'].date() > date.today() - timedelta(days=30)]
        self.assertTrue(recent)
        stale_ids = {r['id'] for r in self.rows(limit=None, stale=30)}
        for r in recent:
            self.assertNotIn(r['id'], stale_ids, r['name'])

    def test_contacts_have_the_same_filter(self):
        self.assertLess(self.contacts(stale=30), self.contacts())

    def test_it_combines_with_the_other_filters(self):
        leads = self.companies(relation_type=['lead'])
        self.assertLessEqual(self.companies(relation_type=['lead'], stale=90), leads)


class ListsShowItTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from app import app
        cls.client = app.test_client()
        with cls.client.session_transaction() as s:
            s['user_id'] = 1
            s['username'] = 'test'
            s['full_name'] = 'Test'

    def test_both_lists_have_the_column_and_the_filter(self):
        for rel in ('templates/crm/companies/list.html', 'templates/crm/contacts/list.html'):
            html = read(rel)
            self.assertIn("data-col=\"last_contact\"", html, rel)
            self.assertIn("name=\"stale\"", html, rel)
            self.assertIn('|since', html, rel)

    def test_never_renders_as_a_word_not_as_the_year_1000(self):
        from app import since
        from datetime import date, datetime, timedelta
        self.assertEqual('nigdy', since(datetime(1000, 1, 1)))
        self.assertEqual('nigdy', since(None))
        self.assertEqual('dziś', since(datetime.now()))
        self.assertEqual('wczoraj', since(date.today() - timedelta(days=1)))
        self.assertEqual('30 dni temu', since(date.today() - timedelta(days=30)))

    def test_the_page_renders_with_the_filter_on(self):
        for url in ('/crm/companies/?stale=90', '/crm/contacts/?stale=30',
                    '/crm/companies/?stale=sqli', '/crm/companies/?sort=last_contact&dir=desc'):
            resp = self.client.get(url)
            self.assertEqual(200, resp.status_code, url)


if __name__ == '__main__':
    unittest.main()
