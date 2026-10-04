"""Jednolity zapis wartości słownikowych (tagi, branże, źródła).

Błąd, przed którym to broni: ta sama branża wpisana w trzech miejscach trafiała
na listę trzy razy („biuro księgowe", „Biura Rachunkowe", „Biuro Księgowe").
Druga pułapka to normalizacja zbyt gorliwa — akronimy (BNI, M&A, SaaS) i marki
(eCommerce, myTherapy) muszą przetrwać zapis bez zmian, a źródła, w których
siedzą imiona i nazwiska, nie mogą dostać małej litery w nazwisku.
Uruchomienie: venv/bin/python -m unittest discover tests
"""
import inspect
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class SentenceCaseTest(unittest.TestCase):

    def setUp(self):
        from models.crm_tags import sentence_case_name
        self.f = sentence_case_name

    def test_only_the_first_word_gets_a_capital(self):
        self.assertEqual('Fundusze inwestycyjne', self.f('Fundusze Inwestycyjne'))
        self.assertEqual('Doradztwo biznesowe', self.f('doradztwo Biznesowe'))
        self.assertEqual('Usługi dla firm', self.f('Usługi Dla Firm'))

    def test_lowercase_input_gets_the_first_capital(self):
        self.assertEqual('Księgowość', self.f('księgowość'))
        self.assertEqual('Cold calling', self.f('cold calling'))

    def test_acronyms_survive(self):
        self.assertEqual('Zaprosić na BNI', self.f('Zaprosić Na BNI'))
        self.assertEqual('Rozwiązania IT', self.f('Rozwiązania IT'))
        self.assertEqual('B2B SaaS', self.f('B2B SaaS'))
        self.assertEqual('MŚP i HR', self.f('MŚP i HR'))
        self.assertEqual('Newsletter M&A', self.f('Newsletter M&A'))

    def test_brands_with_an_inner_capital_are_left_alone(self):
        """„eCommerce" i „myTherapy" nie są zdaniem — podniesienie pierwszej
        litery zrobiłoby z nich „ECommerce" i „MyTherapy"."""
        self.assertEqual('eCommerce', self.f('eCommerce'))
        self.assertEqual('Poszukiwania nabywcy myTherapy', self.f('poszukiwania nabywcy myTherapy'))
        self.assertEqual('HoReCa', self.f('HoReCa'))

    def test_compounds_are_judged_member_by_member(self):
        self.assertEqual('IT/edukacja', self.f('IT/Edukacja'))
        self.assertEqual('E-commerce', self.f('E-Commerce'))
        self.assertEqual('Medycyna/zdrowie', self.f('Medycyna/Zdrowie'))
        self.assertEqual('Firma konstrukcyjno-budowlana', self.f('Firma Konstrukcyjno-Budowlana'))

    def test_separators_and_whitespace(self):
        self.assertEqual('Piekarnia - cukiernia', self.f('Piekarnia - Cukiernia'))
        self.assertEqual('SPA & wellness', self.f('SPA & Wellness'))
        self.assertEqual('Wiele spacji', self.f('  wiele   spacji  '))
        self.assertEqual('', self.f('   '))

    def test_digits_before_the_first_letter(self):
        self.assertEqual('3M polska', self.f('3m Polska'))


class TitleCaseForSourcesTest(unittest.TestCase):
    """Źródło to najczęściej osoba polecająca — nazwisko zostaje z wielkiej litery."""

    def test_source_keeps_every_word_capitalized(self):
        from models.crm_tags import normalize_tag_name
        self.assertEqual('Ada Hurbol', normalize_tag_name('ada hurbol', 'source'))
        self.assertEqual('BNI Milion', normalize_tag_name('BNI milion', 'source'))

    def test_other_kinds_use_sentence_case(self):
        from models.crm_tags import normalize_tag_name
        for kind in ('tag', 'industry', 'email'):
            self.assertEqual('Fundusze inwestycyjne',
                             normalize_tag_name('Fundusze Inwestycyjne', kind), kind)

    def test_default_kind_is_not_source(self):
        """Wywołanie bez kind nie może po cichu wrócić do zapisu tytułowego."""
        from models.crm_tags import normalize_tag_name
        self.assertEqual('Fundusze inwestycyjne', normalize_tag_name('Fundusze Inwestycyjne'))


class EveryWriteKnowsTheKindTest(unittest.TestCase):
    """Reguła zależy od rodzaju wartości, więc każdy zapis musi go przekazać —
    inaczej źródło zapisane z poziomu firmy dostałoby małą literę w nazwisku."""

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


if __name__ == '__main__':
    unittest.main()
