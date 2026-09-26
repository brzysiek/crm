"""Puste daty w zadaniach GTD muszą trafiać do bazy jako NULL.

Regresja: pusty string w kolumnie DATE zapisywał się (bez strict mode) jako 0000-00-00,
pymysql oddawał go jako napis i widok dnia kończył się 500 na porównaniu str < date.
Uruchomienie: venv/bin/python -m unittest discover tests
"""
import unittest
from unittest import mock

import models.task as task_model


class UpdateTaskEmptyDatesTest(unittest.TestCase):
    def setUp(self):
        self.cur = mock.MagicMock()
        db = mock.MagicMock()
        db.cursor.return_value.__enter__.return_value = self.cur
        patch = mock.patch.object(task_model, 'get_db', return_value=db)
        patch.start()
        self.addCleanup(patch.stop)

    def written(self, data):
        task_model.update_task(7, data)
        sql, params = self.cur.execute.call_args.args
        keys = [part.split('=')[0].strip() for part in sql.split('SET', 1)[1].split('WHERE')[0].split(',')]
        return dict(zip(keys, params))

    def test_puste_daty_ida_jako_null(self):
        values = self.written({'due_date': '', 'scheduled_date': '', 'scheduled_time': '',
                               'planned_week': '', 'planned_month': ''})
        self.assertEqual(set(values.values()), {None})

    def test_konkretne_daty_przechodza_bez_zmian(self):
        values = self.written({'due_date': '2026-10-01', 'scheduled_time': '09:30'})
        self.assertEqual(values['due_date'], '2026-10-01')
        self.assertEqual(values['scheduled_time'], '09:30')

    def test_puste_oczekiwanie_tez_jest_nullem(self):
        self.assertIsNone(self.written({'waiting_on': ''})['waiting_on'])


if __name__ == '__main__':
    unittest.main()
