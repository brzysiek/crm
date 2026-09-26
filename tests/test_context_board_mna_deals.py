"""Tablica „Wg kontekstu” grupuje zadania po dealu CRM, ofercie M&A i dealu M&A.

Deale M&A doszły jako trzecia encja, do której można przypiąć zadanie — wcześniej takie
zadania lądowały w koszu „bez niczego”, mimo że badge dealu był widoczny w wierszu.
Uruchomienie: venv/bin/python -m unittest discover tests
"""
import unittest
from unittest import mock

import models.task as task_model


def task(tid, **links):
    row = {'id': tid, 'title': f'Zadanie {tid}', 'status': 'next', 'parent_id': None,
           'crm_deal_id': None, 'crm_deal_name': None,
           'crm_mna_offer_id': None, 'crm_mna_offer_name': None,
           'crm_mna_deal_id': None, 'crm_mna_deal_name': None,
           'crm_company_id': None, 'crm_contact_id': None}
    row.update(links)
    return row


class ContextGroupSplitTest(unittest.TestCase):
    def setUp(self):
        for module, name, info in (
            (task_model.crm_deal_model, 'get_deals_by_ids', {7: {'task_total': 2, 'task_done': 1}}),
            (task_model.crm_mna_offer_model, 'get_mna_offers_by_ids', {8: {'task_total': 3, 'task_done': 0}}),
            (task_model.mna_deal_model, 'get_mna_deals_by_ids', {9: {'task_total': 5, 'task_done': 4}}),
        ):
            patch = mock.patch.object(module, name, side_effect=lambda ids, info=info: {
                i: info.get(i, {}) for i in ids})
            patch.start()
            self.addCleanup(patch.stop)

    def group(self, tasks):
        return task_model._build_context_group(None, [], tasks, None)

    def test_zadanie_dealu_mna_trafia_do_wlasnej_grupy(self):
        g = self.group([task(1, crm_mna_deal_id=9, crm_mna_deal_name='Torus → GCS')])
        self.assertEqual(len(g['mna_deals']), 1)
        self.assertEqual(g['mna_deals'][0]['entity_id'], 9)
        self.assertEqual(g['mna_deals'][0]['entity_name'], 'Torus → GCS')
        self.assertEqual([t['id'] for t in g['mna_deals'][0]['tasks']], [1])
        self.assertEqual(g['mna_deals'][0]['task_done'], 4)
        self.assertEqual(g['mna_deals'][0]['task_total'], 5)
        self.assertEqual(g['tasks'], [])

    def test_kazda_encja_ma_swoja_grupe_a_reszta_zostaje_luzna(self):
        g = self.group([
            task(1, crm_deal_id=7, crm_deal_name='Deal CRM'),
            task(2, crm_mna_offer_id=8, crm_mna_offer_name='Oferta'),
            task(3, crm_mna_deal_id=9, crm_mna_deal_name='Deal M&A'),
            task(4),
        ])
        self.assertEqual([d['entity_id'] for d in g['deals']], [7])
        self.assertEqual([o['entity_id'] for o in g['mna_offers']], [8])
        self.assertEqual([d['entity_id'] for d in g['mna_deals']], [9])
        self.assertEqual([t['id'] for t in g['tasks']], [4])

    def test_deal_crm_ma_pierwszenstwo_przed_encjami_mna(self):
        """Zadanie przypięte i do dealu CRM, i do dealu M&A ma się pokazać raz."""
        g = self.group([task(1, crm_deal_id=7, crm_deal_name='Deal CRM',
                             crm_mna_deal_id=9, crm_mna_deal_name='Deal M&A')])
        self.assertEqual([t['id'] for t in g['deals'][0]['tasks']], [1])
        self.assertEqual(g['mna_deals'], [])
        self.assertEqual(g['tasks'], [])

    def test_filtr_wymienia_deale_mna_obecne_w_kontekscie(self):
        g = self.group([task(1, crm_mna_deal_id=9, crm_mna_deal_name='Torus → GCS')])
        self.assertEqual(g['filter_mna_deals'], [(9, 'Torus → GCS')])


class BoardMacroTest(unittest.TestCase):
    """Makro tabeli jest wspólne dla ofert i deali M&A — renderuje właściwy adres encji."""

    def setUp(self):
        from app import app
        self.app = app

    def render(self, endpoint, id_arg, key_prefix):
        macros = self.app.jinja_env.get_template('gtd/_macros.html').module
        items = [{'entity_id': 9, 'entity_name': 'Torus → GCS', 'tasks': [],
                  'task_total': 5, 'task_done': 4}]
        with self.app.test_request_context('/gtd/wg-kontekstu'):
            return str(macros.mna_group_table(items, 'c1', '', 'Deal M&A', endpoint, id_arg, key_prefix))

    def test_tabela_dealu_mna_linkuje_do_dealu(self):
        html = self.render('mna_deals.view_deal', 'deal_id', 'mnad')
        self.assertIn('/mna/deals/9', html)
        self.assertIn('Torus → GCS', html)
        self.assertIn('4/5 zadań', html)
        self.assertIn("gtdBoardToggleDeal('c1_mnad_9')", html)
        self.assertIn('id="gtdBoardDealSubtasksc1_mnad_9"', html)

    def test_to_samo_makro_linkuje_oferte(self):
        html = self.render('mna_offers.view_mna_offer', 'offer_id', 'mna')
        self.assertIn('/mna/9', html)
        self.assertIn("gtdBoardToggleDeal('c1_mna_9')", html)


if __name__ == '__main__':
    unittest.main()
