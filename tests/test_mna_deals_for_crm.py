"""Karta firmy i kontaktu CRM listuje też deale M&A.

Deal M&A nie trzyma firmy CRM — wiąże go z nią oferta (target/source), więc zapytanie
musi iść przez crm_mna_offers i pomijać deale zarchiwizowane.
Uruchomienie: venv/bin/python -m unittest discover tests
"""
import unittest
from unittest import mock

import models.mna_deal as mna_deal_model


class DealsForCrmEntityTest(unittest.TestCase):
    def setUp(self):
        self.cur = mock.MagicMock()
        self.cur.fetchall.return_value = [{'id': 4, 'name': 'Torus → GCS'}]
        db = mock.MagicMock()
        db.cursor.return_value.__enter__.return_value = self.cur
        patch = mock.patch.object(mna_deal_model, 'get_db', return_value=db)
        patch.start()
        self.addCleanup(patch.stop)

    def query(self):
        return self.cur.execute.call_args.args

    def test_firma_szuka_po_target_i_source_oferty(self):
        rows = mna_deal_model.get_deals_for_crm_company(188)
        self.assertEqual(rows, [{'id': 4, 'name': 'Torus → GCS'}])
        sql, params = self.query()
        self.assertIn('o.target_company_id=%s OR o.source_company_id=%s', sql)
        self.assertIn('JOIN crm_mna_offers o ON o.id = d.offer_id', sql)
        self.assertIn('d.archived_at IS NULL', sql)
        self.assertEqual(params, (188, 188))

    def test_kontakt_szuka_po_kolumnach_kontaktu(self):
        mna_deal_model.get_deals_for_crm_contact(200)
        sql, params = self.query()
        self.assertIn('o.target_contact_id=%s OR o.source_contact_id=%s', sql)
        self.assertEqual(params, (200, 200))

    def test_nie_myli_sie_z_targetami_dealu_mna(self):
        """get_deals_for_company dotyczy firm z modułu M&A — to inne zapytanie."""
        mna_deal_model.get_deals_for_company(188)
        sql, _ = self.query()
        self.assertIn('mna_deal_targets', sql)


if __name__ == '__main__':
    unittest.main()
