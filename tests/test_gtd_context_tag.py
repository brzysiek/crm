import unittest

from models.task import extract_context_tag

CONTEXTS = [{'id': 1, 'name': 'BNI'}, {'id': 2, 'name': 'bp'}, {'id': 3, 'name': 'priv'}]


class ContextTagTest(unittest.TestCase):
    def tag(self, title):
        return extract_context_tag(title, CONTEXTS)

    def test_tag_sets_context_and_leaves_the_title(self):
        self.assertEqual(self.tag('Zadzwonić do Piotra @bp'), ('Zadzwonić do Piotra', 2))

    def test_tag_anywhere_and_any_case(self):
        self.assertEqual(self.tag('@bni spotkanie  w piątek'), ('spotkanie w piątek', 1))
        self.assertEqual(self.tag('Wysłać @BP ofertę'), ('Wysłać ofertę', 2))

    def test_unknown_tag_and_email_stay_untouched(self):
        self.assertEqual(self.tag('Napisać do jan@firma.pl @jutro'), ('Napisać do jan@firma.pl @jutro', None))

    def test_first_known_tag_wins_and_all_are_removed(self):
        self.assertEqual(self.tag('Coś @priv @bp'), ('Coś', 3))

    def test_tag_alone_is_not_swallowed_into_an_empty_title(self):
        self.assertEqual(self.tag('@bp'), ('@bp', None))


if __name__ == '__main__':
    unittest.main()
