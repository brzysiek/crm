"""Kontrakt widoku mobilnego: żadna strona nie może zostać pusta, a menu jest jedno.

Dwa błędy, przed którymi to broni:
 1. `.rd-screen .table-wrapper { display: none }` ukrywało tabelę na każdej stronie w .rd-screen,
    także tam, gdzie nie było kart — oferty i deale M&A świeciły na telefonie pustką. Ukrywanie
    musi być uzależnione od obecności `.rd-card-list`.
 2. Dolny pasek zakładek i przyciski „+” zostały zastąpione jednym okrągłym hamburgerem
    w lewym dolnym rogu — nie mogą wrócić bocznymi drzwiami przy kolejnym szablonie.
Uruchomienie: venv/bin/python -m unittest discover tests
"""
import glob
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(rel: str) -> str:
    with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
        return f.read()


class MobileTableHidingTest(unittest.TestCase):
    def setUp(self):
        self.css = read('static/style.css')

    def test_table_hidden_only_when_cards_exist(self):
        self.assertIn('.rd-screen:has(.rd-card-list) .table-wrapper { display: none; }', self.css)
        self.assertIn('.rd-screen:has(.rd-card-list) .table-count { display: none; }', self.css)

    def test_no_unconditional_table_hiding(self):
        self.assertNotRegex(self.css, r'\.rd-screen \.table-wrapper\s*\{\s*display:\s*none')
        self.assertNotRegex(self.css, r'\.rd-screen \.table-count\s*\{\s*display:\s*none')


class MobileNavTest(unittest.TestCase):
    def test_single_hamburger_opens_menu(self):
        base = read('templates/base.html')
        self.assertEqual(base.count('class="rd-menu-fab"'), 1)
        self.assertIn('onclick="toggleMobileMenu(true)"', base)

    def test_hamburger_is_round_lime_bottom_left(self):
        css = read('static/style.css')
        fab = css[css.index('.rd-menu-fab {'):css.index('.rd-menu-fab svg')]
        self.assertIn('border-radius: 50%', fab)
        self.assertIn('background: var(--rd-lime)', fab)
        self.assertIn('left: 18px', fab)
        self.assertNotIn('right:', fab)

    def test_no_tabbar_and_no_plus_fab_left(self):
        files = glob.glob(os.path.join(ROOT, 'templates', '**', '*.html'), recursive=True)
        files += glob.glob(os.path.join(ROOT, 'static', '*.js'))
        files.append(os.path.join(ROOT, 'static', 'style.css'))
        for path in files:
            with open(path, encoding='utf-8') as f:
                content = f.read()
            rel = os.path.relpath(path, ROOT)
            self.assertNotIn('mobile-tabbar', content, f'pozostałość dolnego paska w {rel}')
            self.assertNotIn('rd-fab', content, f'pozostałość przycisku „+” w {rel}')


class MnaListsHaveCardsTest(unittest.TestCase):
    """Widoki, które użytkownik zobaczył puste — muszą mieć karty w tym samym bloku `{% if %}`
    co tabela, żeby stan pusty nie pokazywał dwóch komunikatów."""

    def test_mna_lists_render_cards(self):
        for rel, loop in (('templates/mna_offers/list.html', '{% for o in offers %}'),
                          ('templates/mna_deals/list.html', '{% for d in deals %}')):
            tpl = read(rel)
            self.assertIn('rd-card-list', tpl, rel)
            self.assertIn(loop, tpl[tpl.index('rd-card-list'):], rel)
            self.assertLess(tpl.index('rd-card-list'), tpl.rindex('{% else %}'), rel)


class MobileLiveSearchTest(unittest.TestCase):
    """Szukanie w trakcie pisania musi ruszać karty, nie tylko wiersze tabeli.

    Na telefonie tabela jest schowana, a lista renderuje się jako `.rd-card-list`.
    Filtrowanie samych `<tr>` nie zmieniało tam niczego i wyglądało, jakby
    wyszukiwarka działała dopiero po Enterze — czyli po pełnym przeładowaniu
    strony przez serwer.
    """

    def test_live_search_touches_cards(self):
        js = read('static/app.js')
        body = js[js.index('function initLiveTableSearch'):js.index('function initColumnToggle')]
        self.assertIn('.rd-card-list', body)

    def test_card_and_row_share_the_same_handle(self):
        """Kartę z wierszem łączy `.row-star[data-id]` — bez niego po stronie kart
        albo wierszy skojarzenie cicho przestaje działać."""
        for rel in ('templates/crm/contacts/list.html', 'templates/crm/companies/list.html'):
            tpl = read(rel)
            cards = tpl[tpl.index('rd-card-list'):]
            rows = tpl[tpl.index('<tbody>'):tpl.index('rd-card-list')]
            for part, where in ((rows, 'wiersze'), (cards, 'karty')):
                self.assertIn('class="star-toggle row-star', part, f'{rel}: {where}')
                self.assertIn('data-id="{{ c.id }}"', part, f'{rel}: {where}')


if __name__ == '__main__':
    unittest.main()
