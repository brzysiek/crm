"""Karta deala i oferty M&A: opis oraz listy jako sekcje zwijane, domyślnie zwinięte.

Stan startowy ustawia szablon (klasa is-collapsed), a nie skrypt — inaczej sekcje mignęłyby
rozwinięte przed uruchomieniem JS. Short lista idzie przed long listą: to na niej toczy się
praca, long lista jest zapleczem.
Uruchomienie: venv/bin/python -m unittest discover tests
"""
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(rel: str) -> str:
    with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
        return f.read()


class CollapsibleSectionsTest(unittest.TestCase):
    def test_deal_sections_start_collapsed(self):
        tpl = read('templates/mna_deals/detail.html')
        self.assertEqual(tpl.count('inv-collapsible is-collapsed'), 2)  # opis + pętla obu list
        self.assertEqual(tpl.count('inv-section-body'), 2)

    def test_offer_description_starts_collapsed(self):
        tpl = read('templates/mna_offers/detail.html')
        self.assertIn('inv-collapsible is-collapsed', tpl)
        self.assertIn('inv-section-body', tpl)

    def test_short_list_comes_before_long_list(self):
        tpl = read('templates/mna_deals/detail.html')
        self.assertIn("[('short_list', short_list), ('long_list', long_list)]", tpl)

    def test_toggle_is_wired_and_spares_buttons(self):
        js = read('static/app.js')
        self.assertIn(".inv-collapsible > .inv-section-header", js)
        self.assertIn("e.target.closest('a, button, input, select, label')", js)

    def test_collapsed_body_is_hidden_by_css(self):
        css = read('static/style.css')
        self.assertIn('.inv-collapsible.is-collapsed > .inv-section-body { display: none; }', css)


if __name__ == '__main__':
    unittest.main()
