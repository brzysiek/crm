"""Konwersja oferty M&A na deal: powiązanie zamiast kopii danych, przepięcie zadań i plików.

Deal dostaje z oferty tylko nazwę i opis. Branża, obroty, EBITDA i target zostają na ofercie
i są czytane przez offer_id — skopiowane rozjechałyby się przy pierwszej korekcie oferty.
Zadania GTD i pliki wiszące przy ofercie przechodzą na deal, bo od jego powstania to on jest
miejscem pracy; droga powrotna do oferty prowadzi przez kartę deala.
Uruchomienie: venv/bin/python -m unittest discover tests
"""
import os
import unittest
from unittest import mock

import models.mna_deal as mna_deal_model

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OFFER = {
    'id': 12, 'name': 'Producent okien', 'description': 'Opis oferty',
    'industry': 'Produkcja', 'revenue': 1000.0, 'ebitda': 100.0,
    'target_company_id': 5, 'ref_number': 'M&A/2026/12',
}


def read(rel: str) -> str:
    with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
        return f.read()


class ConvertOfferToDealTest(unittest.TestCase):
    def setUp(self):
        self.cur = mock.MagicMock()
        self.cur.rowcount = 3
        db = mock.MagicMock()
        db.cursor.return_value.__enter__.return_value = self.cur
        for target, kwargs in (
            ('get_db', {'return_value': db}),
            ('create_mna_deal', {'return_value': 77}),
            ('get_mna_deal_by_id', {'return_value': {'id': 77, 'name': 'Producent okien'}}),
            ('log_history', {}),
        ):
            p = mock.patch.object(mna_deal_model, target, **kwargs)
            setattr(self, target, p.start())
            self.addCleanup(p.stop)
        p = mock.patch('models.crm_mna_offer.get_mna_offer_by_id', return_value=OFFER)
        self.get_offer = p.start()
        self.addCleanup(p.stop)

    def test_deal_bierze_z_oferty_tylko_nazwe_opis_i_powiazanie(self):
        mna_deal_model.convert_offer_to_deal(12, user_id=1)
        data = self.create_mna_deal.call_args.args[0]
        self.assertEqual(data['name'], 'Producent okien')
        self.assertEqual(data['description'], 'Opis oferty')
        self.assertEqual(data['offer_id'], 12)
        for skopiowane in ('industry', 'revenue', 'ebitda', 'target_company_id'):
            self.assertNotIn(skopiowane, data)

    def test_mozna_nadpisac_pola_deala(self):
        mna_deal_model.convert_offer_to_deal(
            12, user_id=1, overrides={'name': 'Inna nazwa', 'amount': 500.0, 'stage': None})
        data = self.create_mna_deal.call_args.args[0]
        self.assertEqual(data['name'], 'Inna nazwa')
        self.assertEqual(data['amount'], 500.0)
        self.assertEqual(data['stage'], 'long_list')  # None nie kasuje domyślnego etapu

    def test_przepina_zadania_i_pliki_omijajac_cudze_powiazania(self):
        result = mna_deal_model.convert_offer_to_deal(12, user_id=1)
        sqls = [c.args[0] for c in self.cur.execute.call_args_list]
        tasks_sql = next(s for s in sqls if s.startswith('UPDATE tasks'))
        files_sql = next(s for s in sqls if s.startswith('UPDATE crm_files'))
        self.assertIn('crm_mna_deal_id = %s, crm_mna_offer_id = NULL', tasks_sql)
        self.assertIn('crm_mna_deal_id IS NULL', tasks_sql)
        self.assertIn('mna_deal_id = %s, mna_offer_id = NULL', files_sql)
        self.assertIn('mna_deal_id IS NULL', files_sql)
        self.assertEqual(result['moved'], {'tasks': 3, 'files': 3})

    def test_move_links_false_zostawia_powiazania_przy_ofercie(self):
        result = mna_deal_model.convert_offer_to_deal(12, user_id=1, move_links=False)
        self.assertEqual(result['moved'], {'tasks': 0, 'files': 0})
        self.assertFalse([c for c in self.cur.execute.call_args_list if 'UPDATE' in c.args[0]])

    def test_brak_oferty_to_blad(self):
        self.get_offer.return_value = None
        with self.assertRaises(ValueError):
            mna_deal_model.convert_offer_to_deal(999, user_id=1)
        self.create_mna_deal.assert_not_called()


class ConversionWiringTest(unittest.TestCase):
    def test_karta_oferty_ma_przycisk_i_liste_deali(self):
        tpl = read('templates/mna_offers/detail.html')
        self.assertIn("url_for('mna_deals.new_deal', offer_id=offer.id)", tpl)
        self.assertIn('Utwórz deal z tej oferty', tpl)
        self.assertIn('Deale z tej oferty', tpl)
        # przycisk konwersji tylko dla żywej oferty — po archiwizacji zostają Przywróć/Usuń
        head = tpl[:tpl.index('{% else %}')]
        self.assertNotIn('Utwórz deal z tej oferty', head)

    def test_karta_deala_czyta_dane_przedmiotu_z_oferty(self):
        tpl = read('templates/mna_deals/detail.html')
        self.assertIn('{% if offer %}', tpl)
        sekcja = tpl[tpl.index('Z oferty'):]
        for pole in ('offer.industry', 'offer.revenue', 'offer.ebitda',
                     'offer.target_company_id', 'offer.source_company_id'):
            self.assertIn(pole, sekcja)

    def test_formularz_pyta_o_przeniesienie_powiazan(self):
        tpl = read('templates/mna_deals/form.html')
        self.assertIn('name="move_links"', tpl)
        self.assertIn('offer_links.other_deals', tpl)  # przy kolejnym dealu domyślnie wyłączone

    def test_trasa_przepina_powiazania_po_zapisie(self):
        src = read('routes/mna_deals.py')
        self.assertIn("request.form.get('move_links')", src)
        self.assertIn('move_offer_links_to_deal', src)
        self.assertIn('count_offer_links', src)

    def test_mcp_wystawia_konwersje(self):
        src = read('mcp_server.py')
        self.assertIn('def convert_mna_offer_to_deal(', src)
        self.assertIn('mna_deal.convert_offer_to_deal(', src)
        self.assertIn('move_links: bool = True', src)

    def test_istniejacy_deal_moze_dociagnac_powiazania(self):
        """Deale sprzed konwersji mają zadania przy ofercie — karta i MCP potrafią je przenieść."""
        self.assertIn('def move_offer_links_view(', read('routes/mna_deals.py'))
        self.assertIn("mna_deals.move_offer_links_view", read('templates/mna_deals/detail.html'))
        self.assertIn('def move_mna_offer_links_to_deal(', read('mcp_server.py'))


if __name__ == '__main__':
    unittest.main()
