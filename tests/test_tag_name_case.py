"""Jednolity zapis wartości słownikowych (tagi, branże, źródła).

Błąd, przed którym to broni: ta sama branża wpisana raz z wielkiej, raz z małej
litery trafiała na listę dwa razy. Druga pułapka jest przeciwna — normalizacja
zbyt gorliwa: wcześniejsza wersja obniżała każde kolejne słowo i robiła
z „Rafał Wiśniewski" → „Rafał wiśniewski", a z „MBA Polska" → „MBA polska".
Dlatego reguła rusza wyłącznie pierwszą literę nazwy.
Uruchomienie: venv/bin/python -m unittest discover tests
"""
import inspect
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _read(rel: str) -> str:
    with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
        return f.read()


class CapitalizeFirstTest(unittest.TestCase):

    def setUp(self):
        from models.crm_tags import capitalize_first
        self.f = capitalize_first

    def test_first_letter_goes_up(self):
        self.assertEqual('Księgowość', self.f('księgowość'))
        self.assertEqual('Fundusze inwestycyjne', self.f('fundusze inwestycyjne'))
        self.assertEqual('3M polska', self.f('3m polska'))

    def test_the_rest_of_the_name_is_left_exactly_as_typed(self):
        """Sedno reguły: poza pierwszą literą nic się nie zmienia, bo z samej
        nazwy nie da się odróżnić nazwiska i nazwy własnej od zwykłego słowa."""
        for name in ('Rafał Wiśniewski', 'MBA Polska', 'Business Mixer Katowice 12/2025',
                     'Zaprosić Na BNI', 'Fundusze Inwestycyjne', 'IT/Edukacja',
                     'SPA & Wellness', 'Piekarnia - Cukiernia', 'Doradztwo biznesowe'):
            self.assertEqual(name, self.f(name))

    def test_acronyms_and_brands_keep_their_own_shape(self):
        """Słowo, które samo niesie wielką literę, zostaje nietknięte — inaczej
        „eCommerce" stałoby się „ECommerce"."""
        for name in ('eCommerce', 'myTherapy', 'BNI', 'M&A', 'B2B SaaS', 'HoReCa'):
            self.assertEqual(name, self.f(name))

    def test_whitespace_is_tidied(self):
        self.assertEqual('Wiele spacji', self.f('  wiele   spacji  '))
        self.assertEqual('', self.f('   '))

    def test_the_first_letter_is_found_past_leading_punctuation(self):
        self.assertEqual('(Kuek) ania', self.f('(kuek) ania'))
        self.assertEqual('„Cytat”', self.f('„cytat”'))
        self.assertEqual('123', self.f('123'))


class TitleCaseForSourcesTest(unittest.TestCase):
    """Źródło to najczęściej osoba polecająca — nazwisko zostaje z wielkiej litery."""

    def test_source_keeps_every_word_capitalized(self):
        from models.crm_tags import normalize_tag_name
        self.assertEqual('Ada Hurbol', normalize_tag_name('ada hurbol', 'source'))
        self.assertEqual('BNI Milion', normalize_tag_name('BNI milion', 'source'))

    def test_other_kinds_only_get_the_first_capital(self):
        from models.crm_tags import normalize_tag_name
        for kind in ('tag', 'industry', 'email'):
            self.assertEqual('Fundusze Inwestycyjne',
                             normalize_tag_name('fundusze Inwestycyjne', kind), kind)

    def test_default_kind_is_not_source(self):
        """Wywołanie bez kind nie może po cichu wrócić do zapisu tytułowego."""
        from models.crm_tags import normalize_tag_name
        self.assertEqual('Doradztwo biznesowe', normalize_tag_name('doradztwo biznesowe'))


class EveryWriteKnowsTheKindTest(unittest.TestCase):
    """Reguła zależy od rodzaju wartości, więc każdy zapis musi go przekazać —
    inaczej źródło zapisane z poziomu firmy dostałoby inną regułę niż w słowniku."""

    def test_tag_writes_pass_the_kind(self):
        import models.crm_tags as crm_tags
        import models.crm_company as crm_company
        for fn in (crm_tags.add_tag, crm_tags.get_or_create_tag_ids,
                   crm_company.bulk_add_tag, crm_company.bulk_remove_tag):
            src = inspect.getsource(fn)
            self.assertIn('normalize_tag_name(', src, fn.__name__)
            self.assertIn('kind)', src.split('normalize_tag_name(')[1][:60], fn.__name__)

    def test_email_tags_are_normalized_as_email(self):
        import models.crm_tags as crm_tags
        self.assertIn("'email')", inspect.getsource(crm_tags.set_contact_email_tags))

    def test_mna_pool_stays_on_title_case(self):
        """229 tagów M&A powstało w zapisie tytułowym — dopisywane mają pasować
        do tego, co już jest, a nie do konwencji słownika CRM."""
        import models.mna_tags as mna_tags
        self.assertIn('title_case_name', inspect.getsource(mna_tags._get_or_create_tag_ids))

    def test_using_a_tag_never_renames_it(self):
        """Dopisanie firmie tagu „cfo" nie ma przemianować wszystkim „CFO" na
        „Cfo" — nazwę zmienia się świadomie, w Słownikach."""
        import models.crm_tags as crm_tags
        src = inspect.getsource(crm_tags.get_or_create_tag_ids)
        self.assertNotIn('UPDATE crm_tags SET name', src)


class RenameInDictionariesTest(unittest.TestCase):
    """Literówkę w pozycji, która jest już w użyciu, trzeba móc poprawić bez
    kasowania — kasowanie odpina wartość od wszystkich firm i kontaktów."""

    @classmethod
    def setUpClass(cls):
        from app import app
        cls.app = app
        cls.macros = _read('templates/settings/_macros.html')

    def test_rename_normalizes_by_the_row_kind(self):
        """Nazwę normalizuje rodzaj z bazy, a nie to, co przyszło z formularza —
        źródło zmieniane z listy ma dostać regułę źródeł."""
        src = inspect.getsource(__import__('models.crm_tags', fromlist=['x']).rename_tag)
        self.assertIn("SELECT kind FROM crm_tags WHERE id=%s", src)
        self.assertIn("normalize_tag_name(name.strip(), row['kind'])", src)

    def test_rename_refuses_an_empty_or_taken_name(self):
        src = inspect.getsource(__import__('models.crm_tags', fromlist=['x']).rename_tag)
        self.assertIn('AND id<>%s', src, 'bez wykluczenia samego siebie zmiana wielkości liter padnie')
        self.assertIn('ValueError', src)

    def test_the_route_exists_and_takes_only_post(self):
        rules = [r for r in self.app.url_map.iter_rules() if r.endpoint == 'settings.tag_rename']
        self.assertEqual(1, len(rules))
        self.assertIn('POST', rules[0].methods)
        self.assertNotIn('GET', rules[0].methods)

    def test_the_list_offers_renaming_next_to_deleting(self):
        card = self.macros[self.macros.index('{% macro tag_card'):]
        self.assertIn("url_for('settings.tag_rename'", card)
        self.assertIn("url_for('settings.tag_delete'", card)
        self.assertIn('toggleDictRename', card)
        self.assertIn('toggleDictRename', _read('static/app.js'))
        self.assertIn('.rd-dict-item.renaming', _read('static/style.css'))


if __name__ == '__main__':
    unittest.main()
