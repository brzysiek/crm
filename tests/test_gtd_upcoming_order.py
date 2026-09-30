"""Kolejność listy „Zadania nadchodzące" i oś czasu tego, co już zamknięte.

Jedna oś: w każdym tygodniu najpierw konkretne dni, potem zadania wrzucone do tygodnia,
a za ostatnim tygodniem miesiąca — zadania przypisane tylko do miesiąca. Bez przypisania
lądują na końcu. Sekcja przeszła układa zamknięte zadania po dacie zamknięcia, a wydarzenia
z kalendarza po dacie wydarzenia, od najnowszych.
Uruchomienie: venv/bin/python -m unittest discover tests
"""
import os
import unittest
from datetime import date, datetime
from unittest import mock

import models.task as task_model
from routes.gtd import _past_timeline

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(rel: str) -> str:
    with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
        return f.read()


def t(tytul, due=None, sched=None, week=None, month=None):
    return {'title': tytul, 'due_date': due, 'scheduled_date': sched,
            'planned_week': week, 'planned_month': month}


class UpcomingOrderTest(unittest.TestCase):
    def kolejnosc(self, tasks):
        return [x['title'] for x in sorted(tasks, key=task_model.upcoming_sort_key)]

    def test_w_tygodniu_najpierw_konkretne_dni_potem_caly_tydzien(self):
        # tydzień 28.09–04.10.2026 (poniedziałek 28.09)
        tasks = [
            t('tydzień', week=date(2026, 9, 28)),
            t('czwartek', due=date(2026, 10, 1)),
            t('poniedziałek', due=date(2026, 9, 28)),
        ]
        self.assertEqual(self.kolejnosc(tasks), ['poniedziałek', 'czwartek', 'tydzień'])

    def test_kolejne_tygodnie_ida_po_sobie_dzien_przed_tygodniem(self):
        tasks = [
            t('2 tydz. ogólnie', week=date(2026, 10, 5)),
            t('1 dzień', due=date(2026, 9, 29)),
            t('2 dzień', due=date(2026, 10, 6)),
            t('1 tydz. ogólnie', week=date(2026, 9, 28)),
            t('3 dzień', due=date(2026, 10, 12)),
        ]
        self.assertEqual(self.kolejnosc(tasks),
                         ['1 dzień', '1 tydz. ogólnie', '2 dzień', '2 tydz. ogólnie', '3 dzień'])

    def test_miesiac_laduje_za_ostatnim_tygodniem_swojego_miesiaca(self):
        # październik 2026 kończy się w sobotę 31.10, czyli w tygodniu od 26.10
        tasks = [
            t('miesiąc X', month=date(2026, 10, 1)),
            t('ostatni tydzień X', week=date(2026, 10, 26)),
            t('dzień w ostatnim tygodniu X', due=date(2026, 10, 30)),
            t('pierwszy tydzień XI', week=date(2026, 11, 2)),
        ]
        self.assertEqual(self.kolejnosc(tasks), [
            'dzień w ostatnim tygodniu X', 'ostatni tydzień X', 'miesiąc X', 'pierwszy tydzień XI'])

    def test_zaleglosci_na_gorze_bez_przypisania_na_dole(self):
        tasks = [
            t('bez terminu'),
            t('na jutro', due=date(2026, 10, 1)),
            t('zaległe', due=date(2026, 8, 3)),
        ]
        self.assertEqual(self.kolejnosc(tasks), ['zaległe', 'na jutro', 'bez terminu'])

    def test_liczy_sie_wczesniejsza_z_dat_dziennych(self):
        """Zaplanowane na poniedziałek z terminem w piątek robi się w poniedziałek."""
        klucz = task_model.upcoming_sort_key(
            t('x', due=date(2026, 10, 2), sched=date(2026, 9, 28)))
        self.assertEqual(klucz, (date(2026, 9, 28), 0, date(2026, 9, 28)))


class PastTimelineTest(unittest.TestCase):
    def test_zadania_po_dacie_zamkniecia_wydarzenia_po_dacie_wydarzenia(self):
        tasks = [
            {'title': 'starsze', 'completed_at': datetime(2026, 9, 20, 10, 0)},
            {'title': 'nowsze', 'completed_at': datetime(2026, 9, 28, 9, 0)},
        ]
        events = [{'title': 'spotkanie', 'date': '2026-09-25'}]
        items = _past_timeline(tasks, events)
        self.assertEqual([i.get('task', i.get('event'))['title'] for i in items],
                         ['nowsze', 'spotkanie', 'starsze'])
        self.assertEqual([i['kind'] for i in items], ['task', 'gcal', 'task'])

    def test_zadania_bez_daty_zamkniecia_wracaja_do_updated_at(self):
        """Zamknięte, zanim data zamknięcia była zapisywana — updated_at to najbliższy ślad."""
        items = _past_timeline(
            [{'title': 'stare', 'completed_at': None, 'updated_at': datetime(2026, 9, 26, 8, 0)}],
            [{'title': 'spotkanie', 'date': '2026-09-25'}])
        self.assertEqual([i.get('task', i.get('event'))['title'] for i in items],
                         ['stare', 'spotkanie'])


class CompletedAtTest(unittest.TestCase):
    def setUp(self):
        self.cur = mock.MagicMock()
        self.cur.fetchone.return_value = {'is_project': 0}
        db = mock.MagicMock()
        db.cursor.return_value.__enter__.return_value = self.cur
        p = mock.patch.object(task_model, 'get_db', return_value=db)
        p.start()
        self.addCleanup(p.stop)

    def sql(self):
        return self.cur.execute.call_args_list[0].args[0]

    def test_zamkniecie_przez_formularz_stempluje_date(self):
        task_model.update_task(7, {'status': 'done'})
        self.assertIn('completed_at=COALESCE(completed_at, NOW())', self.sql())

    def test_otwarcie_z_powrotem_kasuje_date(self):
        task_model.update_task(7, {'status': 'next'})
        self.assertIn('completed_at=NULL', self.sql())

    def test_zmiana_innego_pola_nie_rusza_daty(self):
        task_model.update_task(7, {'title': 'nowy tytuł'})
        self.assertNotIn('completed_at', self.sql())


class SectionsTest(unittest.TestCase):
    def test_szablon_ma_obie_sekcje(self):
        tpl = read('templates/gtd/next_actions.html')
        self.assertIn('Zadania nadchodzące', tpl)
        self.assertIn('Zamknięte zadania i przeszłe wydarzenia', tpl)
        self.assertIn('past_items', tpl)

    def test_trasa_wypycha_zamkniete_do_sekcji_przeszlej(self):
        src = read('routes/gtd.py')
        self.assertIn("tasks=[t for t in tasks if t['status'] != 'done']", src)
        self.assertIn('past_items=_past_timeline(done_tasks, past_events)', src)


if __name__ == '__main__':
    unittest.main()
