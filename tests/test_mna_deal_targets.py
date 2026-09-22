"""Testy widoku roboczego long/short listy deala M&A — model jest zamockowany.

Uruchomienie: venv/bin/python -m unittest discover tests
"""
import unittest
from datetime import date
from unittest import mock

import app as flask_app_module
import models.mna_deal as mna_deal
import routes.mna_deals as routes


class OrderByTest(unittest.TestCase):
    """Sortowanie budujemy z białej listy kolumn — nigdy z tego, co przyszło w URL-u."""

    def test_unknown_sort_falls_back_to_score(self):
        self.assertIn(mna_deal.TARGET_SORTS['score'], mna_deal._targets_order_by("dt.id; DROP", "desc"))

    def test_direction_is_whitelisted(self):
        self.assertTrue(mna_deal._targets_order_by("name", "asc").rstrip().endswith("ASC, dt.id ASC"))
        self.assertIn("DESC", mna_deal._targets_order_by("name", "cokolwiek"))

    def test_valuable_always_first(self):
        self.assertTrue(mna_deal._targets_order_by("name", "asc").startswith(" ORDER BY dt.is_valuable DESC"))

    def test_empty_values_land_last(self):
        # Bez scoringu/miasta/kontaktu pozycja ma iść na koniec, także przy sortowaniu rosnącym.
        for sort in ("score", "city", "contacted"):
            self.assertIn("IS NULL)", mna_deal._targets_order_by(sort, "asc"), sort)
        self.assertNotIn("IS NULL)", mna_deal._targets_order_by("name", "asc"))


class _RouteTestCase(unittest.TestCase):
    MOCKED = ("set_target_score", "set_target_interest", "set_target_valuable", "set_target_note",
              "set_target_contacted", "move_target_list", "remove_target")

    def setUp(self):
        self.model = {}
        for name in self.MOCKED:
            patch = mock.patch.object(routes, name)
            self.model[name] = patch.start()
            self.addCleanup(patch.stop)
        self.client = flask_app_module.app.test_client()
        with self.client.session_transaction() as s:
            s["user_id"] = 1

    def assertNoWrites(self):
        for name, fn in self.model.items():
            fn.assert_not_called()


class QuickUpdateTest(_RouteTestCase):
    def post(self, payload):
        return self.client.post("/mna/deals/3/targets/7/quick", json=payload)

    def test_score_is_clamped(self):
        self.post({"field": "score", "value": "500"})
        self.model["set_target_score"].assert_called_once_with(7, 100, 1)

    def test_empty_score_clears_it(self):
        self.post({"field": "score", "value": ""})
        self.model["set_target_score"].assert_called_once_with(7, None, 1)

    def test_nonnumeric_score_clears_it(self):
        self.post({"field": "score", "value": "bardzo dobry"})
        self.model["set_target_score"].assert_called_once_with(7, None, 1)

    def test_interest_must_be_known(self):
        r = self.post({"field": "interest", "value": "moze"})
        self.assertEqual(r.status_code, 400)
        self.assertNoWrites()

    def test_interest_is_saved(self):
        self.post({"field": "interest", "value": "interested"})
        self.model["set_target_interest"].assert_called_once_with(7, "interested", 1)

    def test_unknown_field_is_rejected(self):
        r = self.post({"field": "list_type", "value": "short_list"})
        self.assertEqual(r.status_code, 400)
        self.assertNoWrites()

    def test_valuable_toggles(self):
        self.post({"field": "valuable", "value": "1"})
        self.post({"field": "valuable", "value": "0"})
        self.assertEqual([c.args[1] for c in self.model["set_target_valuable"].call_args_list], [True, False])

    def test_note_and_contact_date(self):
        self.post({"field": "note", "value": "oddzwonić w piątek"})
        self.post({"field": "contacted_at", "value": "2026-09-22"})
        self.model["set_target_note"].assert_called_once_with(7, "oddzwonić w piątek", 1)
        self.model["set_target_contacted"].assert_called_once_with(7, "2026-09-22", 1)

    def test_empty_contact_date_clears_it(self):
        self.post({"field": "contacted_at", "value": ""})
        self.model["set_target_contacted"].assert_called_once_with(7, None, 1)


class BulkActionTest(_RouteTestCase):
    def post(self, action, ids=(4, 5, 6)):
        return self.client.post("/mna/deals/3/targets/bulk",
                                data={"action": action, "target_ids": [str(i) for i in ids]})

    def test_move_to_short_list(self):
        self.post("move_short_list")
        self.assertEqual([c.args[:2] for c in self.model["move_target_list"].call_args_list],
                         [(4, "short_list"), (5, "short_list"), (6, "short_list")])

    def test_bulk_interest(self):
        self.post("interest_not_interested")
        self.assertEqual(self.model["set_target_interest"].call_count, 3)

    def test_unknown_interest_is_rejected(self):
        self.post("interest_wszystko_jedno")
        self.assertNoWrites()

    def test_contacted_today_uses_today(self):
        self.post("contacted_today", ids=(4,))
        self.model["set_target_contacted"].assert_called_once_with(4, date.today().isoformat(), 1)

    def test_remove(self):
        self.post("remove", ids=(4, 5))
        self.assertEqual(self.model["remove_target"].call_count, 2)

    def test_empty_selection_does_nothing(self):
        self.client.post("/mna/deals/3/targets/bulk", data={"action": "remove"})
        self.assertNoWrites()

    def test_unknown_action_does_nothing(self):
        self.post("archiwizuj")
        self.assertNoWrites()

    def test_redirects_back_to_filtered_view(self):
        r = self.client.post("/mna/deals/3/targets/bulk",
                             data={"action": "remove", "target_ids": ["4"],
                                   "back": "/mna/deals/3/lista?list=long_list&min_score=80"})
        self.assertEqual(r.status_code, 302)
        self.assertIn("min_score=80", r.headers["Location"])


if __name__ == "__main__":
    unittest.main()
