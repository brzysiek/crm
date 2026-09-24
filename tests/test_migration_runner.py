"""Testy dzielenia pliku .sql na instrukcje.

Kiedyś migrację uruchomił ad-hoc splitter po `;`, który zgubił instrukcje
zaczynające się komentarzem — kolejny UPDATE wpisał wtedy wartość spoza ENUM-a
i MySQL ucięło ją do pustego stringa. Stąd te testy.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))

from run_migration import split_statements


class SplitStatementsTest(unittest.TestCase):
    def test_leading_comment_does_not_swallow_statement(self):
        sql = "-- komentarz\nALTER TABLE t ADD COLUMN x INT;\n-- drugi\nUPDATE t SET x = 1;"
        self.assertEqual(split_statements(sql),
                         ['ALTER TABLE t ADD COLUMN x INT', 'UPDATE t SET x = 1'])

    def test_semicolon_inside_string_is_not_a_separator(self):
        sql = "INSERT INTO t (a) VALUES ('raz; dwa');"
        self.assertEqual(split_statements(sql), ["INSERT INTO t (a) VALUES ('raz; dwa')"])

    def test_comment_marker_inside_string_is_kept(self):
        sql = "INSERT INTO t (a) VALUES ('koszt -- nie komentarz');"
        self.assertEqual(split_statements(sql), ["INSERT INTO t (a) VALUES ('koszt -- nie komentarz')"])

    def test_double_dash_without_space_is_an_operator(self):
        self.assertEqual(split_statements("SELECT 1--2;"), ['SELECT 1--2'])

    def test_escaped_and_doubled_quotes(self):
        sql = "INSERT INTO t (a) VALUES ('O\\'Brien'), ('a''b');"
        self.assertEqual(len(split_statements(sql)), 1)

    def test_block_comment_is_dropped(self):
        sql = "/* opis\n wieloliniowy */ SELECT 1; SELECT 2;"
        self.assertEqual(split_statements(sql), ['SELECT 1', 'SELECT 2'])

    def test_backtick_identifier_with_semicolon(self):
        sql = "SELECT `dziwna;nazwa` FROM t;"
        self.assertEqual(split_statements(sql), ['SELECT `dziwna;nazwa` FROM t'])

    def test_trailing_statement_without_semicolon(self):
        self.assertEqual(split_statements('SELECT 1'), ['SELECT 1'])

    def test_empty_and_comment_only_input(self):
        self.assertEqual(split_statements('-- nic tu nie ma\n\n;;'), [])

    def test_real_migration_has_every_statement(self):
        path = Path(__file__).resolve().parent.parent / 'migration_finance_v2.sql'
        statements = split_statements(path.read_text(encoding='utf-8'))
        creates = [s for s in statements if s.upper().startswith('CREATE TABLE')]
        self.assertEqual(len(creates), 10)
        self.assertTrue(any(s.upper().startswith('INSERT INTO FIN_CATEGORIES') for s in statements))


if __name__ == '__main__':
    unittest.main()
