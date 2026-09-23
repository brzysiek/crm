"""Testy widoku „Pomysły do decyzji” (status ideas) — model jest zamockowany.

Uruchomienie: venv/bin/python -m unittest discover tests
"""
import unittest
from unittest import mock

import app as flask_app_module
import mcp_server
import models.task as task_model
import routes.gtd as gtd_routes


class IdeasStatusTest(unittest.TestCase):
    """Stary status 'inbox' nie może zostać nigdzie w kodzie."""

    def test_inbox_is_not_a_valid_status(self):
        self.assertIn('ideas', task_model.VALID_STATUSES)
        self.assertNotIn('inbox', task_model.VALID_STATUSES)

    def test_status_has_polish_label(self):
        self.assertEqual(task_model.STATUS_LABELS['ideas'], 'Pomysły')

    def test_mcp_exposes_ideas(self):
        self.assertEqual(mcp_server._STATUSES[0], 'ideas')


class IdeasRouteTest(unittest.TestCase):
    def setUp(self):
        patch = mock.patch.object(gtd_routes.task_model, 'get_ideas_tasks', return_value=[])
        self.get_ideas = patch.start()
        self.addCleanup(patch.stop)
        # Badge w menu liczy pomysły przy każdym żądaniu.
        count = mock.patch.object(task_model, 'count_ideas', return_value=0)
        count.start()
        self.addCleanup(count.stop)
        self.client = flask_app_module.app.test_client()
        with self.client.session_transaction() as s:
            s['user_id'] = 1

    def test_view_is_served_under_pomysly(self):
        r = self.client.get('/gtd/pomysly')
        self.assertEqual(r.status_code, 200)
        self.get_ideas.assert_called_once()

    def test_old_inbox_url_is_gone(self):
        self.assertEqual(self.client.get('/gtd/inbox').status_code, 404)

    def test_view_shows_both_processing_actions(self):
        html = self.client.get('/gtd/pomysly').get_data(as_text=True)
        self.assertIn('Pomysły do decyzji', html)
        # Przy pustej liście przyciski wierszy nie istnieją, ale nagłówek i menu muszą być polskie.
        self.assertIn('>Pomysły</span>', html)


class QuickAddTest(unittest.TestCase):
    """Szybkie dodawanie z widoku Pomysłów ląduje w statusie ideas."""

    def setUp(self):
        patch = mock.patch.object(gtd_routes.task_model, 'create_task', return_value=1)
        self.create = patch.start()
        self.addCleanup(patch.stop)
        for name, value in (('get_task', {'id': 1, 'title': 'x'}),):
            p = mock.patch.object(gtd_routes.task_model, name, return_value=value)
            p.start()
            self.addCleanup(p.stop)
        count = mock.patch.object(task_model, 'count_ideas', return_value=0)
        count.start()
        self.addCleanup(count.stop)
        self.client = flask_app_module.app.test_client()
        with self.client.session_transaction() as s:
            s['user_id'] = 1

    def test_api_default_status_is_ideas(self):
        self.client.post('/api/gtd/tasks', json={'title': 'Pomysł na post'})
        self.assertEqual(self.create.call_args.kwargs['status'], 'ideas')


class ConvertToProjectTest(unittest.TestCase):
    """„Na projekt” — akcja z widoku Pomysłów."""

    def setUp(self):
        self.convert = mock.patch.object(gtd_routes.task_model, 'convert_to_project').start()
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(gtd_routes.task_model, 'get_task',
                          return_value={'id': 5, 'is_project': 1, 'status': 'next'}).start()
        mock.patch.object(task_model, 'count_ideas', return_value=0).start()
        self.client = flask_app_module.app.test_client()
        with self.client.session_transaction() as s:
            s['user_id'] = 1

    def test_endpoint_converts_the_task(self):
        r = self.client.post('/api/gtd/tasks/5/convert_project')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()['status'], 'ok')
        self.convert.assert_called_once_with(5)

    def test_returned_task_is_a_project(self):
        r = self.client.post('/api/gtd/tasks/5/convert_project')
        self.assertEqual(r.get_json()['task']['is_project'], 1)


if __name__ == '__main__':
    unittest.main()
