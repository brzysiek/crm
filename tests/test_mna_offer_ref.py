"""Testy numeracji ofert M&A („Ref: <nr w roku>/<rok>”) — baza jest zamockowana.

Uruchomienie: venv/bin/python -m unittest discover tests
"""
import unittest
from datetime import date
from unittest import mock

import models.crm_mna_offer as crm_mna_offer


class NextOfferRefTest(unittest.TestCase):
    def setUp(self):
        self.stored = []
        cursor = mock.MagicMock()
        cursor.__enter__.return_value = cursor
        # Model filtruje po LIKE '%/RRRR' — odtwarzamy to na liście w pamięci.
        cursor.execute.side_effect = lambda sql, params: cursor.fetchall.configure_mock(
            return_value=[{"ref_number": r} for r in self.stored if r.endswith(params[0].lstrip('%'))])
        db = mock.Mock()
        db.cursor.return_value = cursor
        patch = mock.patch.object(crm_mna_offer, "get_db", return_value=db)
        patch.start()
        self.addCleanup(patch.stop)

    def ref(self, on_date=date(2026, 9, 22)):
        return crm_mna_offer.next_mna_offer_ref(on_date)

    def test_first_offer_in_year_starts_at_one(self):
        self.assertEqual(self.ref(), "Ref: 1/2026")

    def test_numbering_continues_after_highest(self):
        self.stored = ["Ref: 1/2026", "Ref: 2/2026", "Ref: 3/2026"]
        self.assertEqual(self.ref(), "Ref: 4/2026")

    def test_gap_does_not_reuse_number(self):
        # Oferta nr 2 została skasowana — kolejny numer i tak jest o jeden większy od maksimum.
        self.stored = ["Ref: 1/2026", "Ref: 3/2026"]
        self.assertEqual(self.ref(), "Ref: 4/2026")

    def test_month_does_not_reset_numbering(self):
        self.stored = ["Ref: 12/2026"]
        self.assertEqual(self.ref(date(2026, 10, 5)), "Ref: 13/2026")

    def test_other_years_do_not_count(self):
        self.stored = ["Ref: 7/2025", "Ref: 9/2024"]
        self.assertEqual(self.ref(), "Ref: 1/2026")

    def test_numbering_restarts_each_year(self):
        self.stored = ["Ref: 40/2026"]
        self.assertEqual(self.ref(date(2027, 1, 2)), "Ref: 1/2027")

    def test_ignores_refs_in_old_monthly_format(self):
        self.stored = ["Ref: 1/2026", "Ref: 8/09/2026"]
        self.assertEqual(self.ref(), "Ref: 2/2026")

    def test_ignores_manually_edited_refs(self):
        self.stored = ["Ref: 1/2026", "Ref: aneks/2026"]
        self.assertEqual(self.ref(), "Ref: 2/2026")

    def test_ref_fits_in_column(self):
        self.stored = ["Ref: 998/2026"]
        self.assertLessEqual(len(self.ref(date(2026, 12, 31))), 20)


class CreateOfferRefTest(unittest.TestCase):
    """create_mna_offer nadaje numer sam, gdy nie przyszedł z formularza."""

    def setUp(self):
        self.cursor = mock.MagicMock()
        self.cursor.__enter__.return_value = self.cursor
        self.cursor.fetchall.return_value = [{"ref_number": "Ref: 2/2026"}]
        self.cursor.lastrowid = 42
        db = mock.Mock()
        db.cursor.return_value = self.cursor
        for p in (mock.patch.object(crm_mna_offer, "get_db", return_value=db),
                  mock.patch.object(crm_mna_offer, "log_history")):
            p.start()
            self.addCleanup(p.stop)

    def insert_call(self):
        return next(c for c in self.cursor.execute.call_args_list if "INSERT" in c.args[0])

    def test_insert_params_match_placeholders(self):
        crm_mna_offer.create_mna_offer({"name": "Firma X"}, user_id=1)
        sql, params = self.insert_call().args
        self.assertEqual(sql.count("%s"), len(params))

    def test_missing_ref_is_generated(self):
        crm_mna_offer.create_mna_offer({"name": "Firma X"}, user_id=1)
        params = self.insert_call().args[1]
        self.assertEqual(params[1], f"Ref: 3/{date.today():%Y}")

    def test_given_ref_is_kept(self):
        crm_mna_offer.create_mna_offer({"name": "Firma X", "ref_number": "Ref: 99/2020"}, user_id=1)
        self.assertEqual(self.insert_call().args[1][1], "Ref: 99/2020")


if __name__ == "__main__":
    unittest.main()
