"""„Wszystkie zadania”: filtry z adresu muszą trafić do właściwych parametrów zapytania.

Widok przekazywał je do get_next_actions pozycyjnie. Po dodaniu contact_id w środku
sygnatury wszystko przesunęło się o jedno miejsce: fraza szła jako kontakt (zawsze
pusta lista), „pokaż zakończone” jako fraza, a konteksty jako „pokaż zakończone”
(pełna lista plus wszystkie zamknięte zadania). Nic się nie wywracało — filtry po
prostu nie filtrowały.
Uruchomienie: venv/bin/python -m unittest discover tests
"""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
import routes.gtd as gtd_routes


class NextActionsFilterArgs(unittest.TestCase):
    def _get(self, query):
        client = app.test_client()
        with client.session_transaction() as s:
            s['user_id'] = 1
        with mock.patch.object(gtd_routes.task_model, 'get_next_actions', return_value=[]) as tasks, \
             mock.patch.object(gtd_routes.gcal_event_model, 'get_cached_past_events', return_value=[]) as events, \
             mock.patch.object(gtd_routes, 'render_template', return_value=''):
            client.get('/gtd/next' + query)
        return tasks, events

    def test_search_and_contexts_reach_their_own_parameters(self):
        tasks, events = self._get('?q=faktura&contexts=2,0&project=7&company=9')
        tasks.assert_called_once_with(project_id=7, deal_id=None, company_id=9,
                                      search='faktura', include_done=False, context_ids=[2, 0])
        events.assert_called_once_with([2, 0], project_id=7, company_id=9, search='faktura')

    def test_done_checkbox_is_not_confused_with_contexts(self):
        tasks, _ = self._get('?done=1')
        self.assertEqual(tasks.call_args.kwargs['include_done'], True)
        self.assertIsNone(tasks.call_args.kwargs['context_ids'])
        self.assertIsNone(tasks.call_args.kwargs['search'])

    def test_deal_filter_hides_calendar_events(self):
        _, events = self._get('?deal=3')
        events.assert_not_called()


class BulkDelete(unittest.TestCase):
    """Zbiorcze usuwanie ma być tym samym miękkim usunięciem co pojedyncze — do Archiwum."""

    def _post(self, payload):
        client = app.test_client()
        with client.session_transaction() as s:
            s['user_id'] = 1
        with mock.patch.object(gtd_routes.task_model, 'delete_task') as delete:
            resp = client.post('/api/gtd/tasks/bulk-delete', json=payload)
        return resp, delete

    def test_each_selected_task_is_soft_deleted(self):
        resp, delete = self._post({'ids': [4, 9]})
        self.assertEqual(resp.get_json(), {'status': 'ok', 'deleted': 2})
        self.assertEqual([c.args for c in delete.call_args_list], [(4,), (9,)])

    def test_empty_or_malformed_selection_deletes_nothing(self):
        for payload in ({}, {'ids': []}, {'ids': ['x', None, True]}):
            resp, delete = self._post(payload)
            self.assertEqual(resp.status_code, 400)
            delete.assert_not_called()


if __name__ == '__main__':
    unittest.main()
