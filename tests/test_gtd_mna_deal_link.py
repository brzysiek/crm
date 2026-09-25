"""Testy powiązania zadań z dealem M&A.

Model zadań jest zamockowany. Sedno: pole crm_mna_deal_id musi przejść przez
endpointy nietknięte — gdy wypadnie, zadanie powstaje jako sierota i nie widać
go w sekcji "Zadania" na deallu, mimo że API odpowiada 'ok'.
Uruchomienie: venv/bin/python -m unittest discover tests
"""
import unittest
from unittest import mock

import models.task as task_model
from app import app
from routes.crm_contacts import build_gtd_items

CRM_LINK_FIELDS = ('crm_contact_id', 'crm_company_id', 'crm_deal_id',
                   'crm_mna_offer_id', 'crm_mna_deal_id')


class CreateTaskLinkTest(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
        create = mock.patch.object(task_model, 'create_task', return_value=1)
        get = mock.patch.object(task_model, 'get_task', return_value={'id': 1})
        self.create_task = create.start()
        get.start()
        self.addCleanup(create.stop)
        self.addCleanup(get.stop)

    def test_przekazuje_wszystkie_powiazania_crm(self):
        payload = {'title': 'Zadanie', 'status': 'next'}
        payload.update({f: i + 10 for i, f in enumerate(CRM_LINK_FIELDS)})
        self.assertEqual(self.client.post('/api/gtd/tasks', json=payload).get_json()['status'], 'ok')
        kwargs = self.create_task.call_args.kwargs
        for i, field in enumerate(CRM_LINK_FIELDS):
            self.assertEqual(kwargs[field], i + 10, field)

    def test_brak_powiazania_to_none_a_nie_zero(self):
        self.client.post('/api/gtd/tasks', json={'title': 'Zadanie'})
        kwargs = self.create_task.call_args.kwargs
        for field in CRM_LINK_FIELDS:
            self.assertIsNone(kwargs[field], field)


class BulkAssignLinkTest(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
        patch = mock.patch.object(task_model, 'update_task')
        self.update_task = patch.start()
        self.addCleanup(patch.stop)

    def test_masowe_przypisanie_do_deala_mna(self):
        resp = self.client.post('/api/gtd/tasks/bulk-assign',
                                json={'ids': [7, 8], 'updates': {'crm_mna_deal_id': 4}})
        self.assertEqual(resp.get_json()['status'], 'ok')
        self.assertEqual([c.args for c in self.update_task.call_args_list],
                         [(7, {'crm_mna_deal_id': 4}), (8, {'crm_mna_deal_id': 4})])


class GtdItemsTest(unittest.TestCase):
    """Sekcja "Zadania" na deallu M&A karmi się build_gtd_items."""

    def test_zadania_deala_mna_trafiaja_na_liste(self):
        tasks = [{'id': 5, 'title': 'Data room', 'is_project': 0, 'status': 'next',
                  'due_date': None, 'completed_at': None, 'created_at': None}]
        with app.test_request_context('/'), \
             mock.patch.object(task_model, 'get_tasks_for_crm', return_value=tasks) as get_tasks:
            items = build_gtd_items(mna_deal_id=4)
        self.assertEqual(get_tasks.call_args.kwargs['mna_deal_id'], 4)
        self.assertEqual([(i['kind'], i['title'], i['url']) for i in items],
                         [('task', 'Data room', '/gtd/zadania/5')])


if __name__ == '__main__':
    unittest.main()
