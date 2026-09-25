"""Testy list kontaktów — baza i historia są zamockowane.

Uruchomienie: venv/bin/python -m unittest discover tests
"""
import unittest
from unittest import mock

import models.crm_contact as crm_contact
import models.crm_contact_list as cl


class FakeCursor:
    """Kursor zwracający kolejne przygotowane wyniki i zapamiętujący zapytania."""

    def __init__(self, results, rowcounts=None):
        self.results = list(results)
        self.rowcounts = list(rowcounts or [])
        self.sql = []
        self.rowcount = 1

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self.sql.append((sql, params))
        if self.rowcounts:
            self.rowcount = self.rowcounts.pop(0)

    def fetchall(self):
        return self.results.pop(0) if self.results else []

    def fetchone(self):
        rows = self.results.pop(0) if self.results else None
        return rows


class ListModelTest(unittest.TestCase):
    def setUp(self):
        self.history = []
        patch = mock.patch.object(cl, 'log_history',
                                  side_effect=lambda *a, **kw: self.history.append((a, kw)))
        patch.start()
        self.addCleanup(patch.stop)

    def use_cursor(self, results, rowcounts=None):
        cur = FakeCursor(results, rowcounts)
        db = mock.Mock()
        db.cursor.return_value = cur
        patch = mock.patch.object(cl, 'get_db', return_value=db)
        patch.start()
        self.addCleanup(patch.stop)
        self.db = db
        return cur

    def test_counts_are_added_only_on_request(self):
        cur = self.use_cursor([[]])
        cl.get_all_lists()
        self.assertNotIn('member_count', cur.sql[0][0])
        cur.results = [[]]
        cl.get_all_lists(with_counts=True)
        self.assertIn('member_count', cur.sql[1][0])

    def test_counts_skip_archived_contacts(self):
        """Lista z 10 członkami, z których 8 jest w archiwum, ma pokazywać 2."""
        cur = self.use_cursor([[]])
        cl.get_all_lists(with_counts=True)
        self.assertIn('archived_at IS NULL', cur.sql[0][0])

    def test_lists_for_contacts_groups_by_contact(self):
        rows = [
            {'contact_id': 1, 'id': 5, 'name': 'A', 'badge_color': '#111', 'text_color': '#222'},
            {'contact_id': 1, 'id': 6, 'name': 'B', 'badge_color': '#111', 'text_color': '#222'},
            {'contact_id': 2, 'id': 5, 'name': 'A', 'badge_color': '#111', 'text_color': '#222'},
        ]
        self.use_cursor([rows])
        out = cl.get_lists_for_contacts([1, 2])
        self.assertEqual([l['id'] for l in out[1]], [5, 6])
        self.assertEqual([l['id'] for l in out[2]], [5])

    def test_lists_for_contacts_without_ids_does_not_query(self):
        db = mock.Mock()
        with mock.patch.object(cl, 'get_db', return_value=db):
            self.assertEqual(cl.get_lists_for_contacts([]), {})
        db.cursor.assert_not_called()

    def test_set_contact_lists_noop_when_unchanged(self):
        # fetchall(): obecne listy kontaktu
        cur = self.use_cursor([[{'id': 5, 'name': 'Klienci'}]])
        cl.set_contact_lists(7, [5], user_id=1)
        self.assertEqual(len(cur.sql), 1)          # tylko odczyt, żadnego zapisu
        self.db.commit.assert_not_called()
        self.assertEqual(self.history, [])

    def test_set_contact_lists_logs_add_and_remove(self):
        cur = self.use_cursor([
            [{'id': 5, 'name': 'Klienci'}],        # obecne
            [{'id': 6, 'name': 'Newsletter'}, {'id': 5, 'name': 'Klienci'}],   # get_all_lists
        ])
        cl.set_contact_lists(7, [6], user_id=1)
        entry_types = [kw['entry_type'] for _a, kw in self.history]
        self.assertEqual(entry_types, ['list_add', 'list_remove'])
        self.assertIn('Newsletter', self.history[0][0][4])
        self.assertIn('Klienci', self.history[1][0][4])
        self.db.commit.assert_called_once()

    def test_set_contact_lists_ignores_vanished_list(self):
        """Lista usunięta w innej zakładce nie może wywalić zapisu kontaktu."""
        self.use_cursor([
            [],                                     # kontakt bez list
            [{'id': 5, 'name': 'Klienci'}],         # id 99 już nie istnieje
        ])
        cl.set_contact_lists(7, [5, 99], user_id=1)
        self.assertEqual([kw['entry_type'] for _a, kw in self.history], ['list_add'])

    def test_add_contacts_counts_only_new_members(self):
        """INSERT IGNORE: kontakt już na liście nie jest logowany drugi raz."""
        self.use_cursor([{'id': 5, 'name': 'Klienci'}], rowcounts=[1, 0, 1])
        added = cl.add_contacts_to_list(5, [1, 2, 3], user_id=1)
        self.assertEqual(added, 2)
        self.assertEqual(len(self.history), 2)

    def test_add_contacts_to_missing_list_does_nothing(self):
        self.use_cursor([None])
        self.assertEqual(cl.add_contacts_to_list(999, [1], user_id=1), 0)
        self.assertEqual(self.history, [])

    def test_remove_contacts_logs_only_actual_members(self):
        self.use_cursor([
            {'id': 5, 'name': 'Klienci'},           # get_list
            [{'contact_id': 2}],                    # tylko 2 był na liście
        ])
        removed = cl.remove_contacts_from_list(5, [1, 2], user_id=1)
        self.assertEqual(removed, 1)
        self.assertEqual([kw['entry_type'] for _a, kw in self.history], ['list_remove'])


class ContactFilterTest(unittest.TestCase):
    """Widok listy to widok kontaktów zawężony przez EXISTS na członkostwie."""

    def test_list_filter_adds_exists(self):
        where, params = crm_contact._contacts_where(list_id=5)
        self.assertIn('crm_contact_list_members', where)
        self.assertIn(5, params)

    def test_no_list_filter_by_default(self):
        where, params = crm_contact._contacts_where()
        self.assertNotIn('crm_contact_list_members', where)

    def test_list_filter_combines_with_search(self):
        where, params = crm_contact._contacts_where(search='kowalski', list_id=5)
        self.assertIn('crm_contact_list_members', where)
        self.assertEqual(params[-1], 5)


class HistoryLabelTest(unittest.TestCase):
    def test_list_events_have_own_labels(self):
        from models.crm_notes import HISTORY_BADGE_LABELS
        self.assertEqual(HISTORY_BADGE_LABELS['list_add'], 'Dodano do listy')
        self.assertEqual(HISTORY_BADGE_LABELS['list_remove'], 'Usunięto z listy')


if __name__ == '__main__':
    unittest.main()
