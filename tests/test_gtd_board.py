"""Tablica kanban: z czego wynika kolumna i co w niej widać.

Dwie rzeczy, których ta tablica pilnuje i które łatwo zepsuć:

1. Kolumna projektu wynika z jego zadań, a pierwszeństwo jest celowo odwrotne
   do intuicji „jedno zablokowane zadanie blokuje projekt”. Na produkcji taka
   intuicja zabrałaby dwa największe żywe projekty (14 i 13 otwartych zadań,
   w tym kilka czekających) z TODO i położyła je na parkingu.
2. Podzadanie nie ma własnej karty — poza kolumną „Zrobione”, gdzie bez niego
   zniknęłoby z tablicy całkowicie (w dwutygodniowym oknie to 23 z 72 pozycji).

Składanie tablicy testujemy na danych syntetycznych (prawdziwa baza zmienia się
z każdym zamkniętym zadaniem), a na żywej bazie tylko to, czy widok się renderuje.
Uruchomienie: venv/bin/python -m unittest discover tests
"""
import os
import sys
import unittest
from datetime import date, datetime, timedelta
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import models.task as task_model

TODAY = date(2026, 10, 5)          # poniedziałek
LONG_AGO = datetime(2026, 1, 1, 12, 0)


def row(task_id, status='next', is_project=0, parent_id=None, **kw):
    base = {
        'id': task_id, 'title': f'zadanie {task_id}', 'status': status,
        'is_project': is_project, 'parent_id': parent_id, 'context_id': None,
        'context_name': None, 'context_badge_color': None, 'context_text_color': None,
        'started_at': None, 'completed_at': None, 'updated_at': datetime(2026, 10, 5, 9, 0),
        'due_date': None, 'scheduled_date': None, 'is_today_priority': 0, 'is_important': 0,
        'project_title': None, 'crm_company_id': None,
    }
    base.update(kw)
    return base


def board(rows, **kwargs):
    cur = mock.MagicMock()
    cur.fetchall.return_value = rows
    db = mock.MagicMock()
    db.cursor.return_value.__enter__.return_value = cur
    with mock.patch.object(task_model, 'get_db', return_value=db):
        return task_model.get_board(today=TODAY, **kwargs)


def column(data, key):
    return next(c for c in data['columns'] if c['key'] == key)


def titles(data, key):
    return [c['id'] for c in column(data, key)['cards']]


class ProjectColumnTest(unittest.TestCase):
    """Kolumna projektu wynika z zadań, nie z jego własnego statusu."""

    def project(self, own='next', **counts):
        base = {s: 0 for s in task_model.VALID_STATUSES}
        base.update(counts)
        return {'status': own, 'counts': base}

    def test_praca_w_toku_bije_wszystko(self):
        self.assertEqual('doing', task_model.project_board_column(
            self.project(doing=1, waiting=3, next=2)))

    def test_cokolwiek_do_zrobienia_bije_zablokowane(self):
        """Projekt z 11 zadaniami do zrobienia i 2 czekającymi jest żywy, nie zablokowany."""
        self.assertEqual('next', task_model.project_board_column(
            self.project(next=11, waiting=2)))

    def test_zablokowany_dopiero_gdy_nie_ma_czego_ruszyc(self):
        self.assertEqual('waiting', task_model.project_board_column(
            self.project(waiting=2, someday=1)))

    def test_odlozenie_calego_projektu_jest_decyzja_i_wygrywa(self):
        """Inaczej przeciągnięcie projektu na „Kiedyś” byłoby cofane przez jego zadania."""
        self.assertEqual('someday', task_model.project_board_column(
            self.project(own='someday', next=3)))

    def test_projekt_bez_otwartych_zadan_zostaje_przy_swoim(self):
        self.assertEqual('next', task_model.project_board_column(self.project(done=4)))


class StartedAtTest(unittest.TestCase):
    """Zegar „w trakcie od…” rusza raz i nie gubi się po drodze."""

    def test_wejscie_w_trakcie_ustawia_date_tylko_raz(self):
        self.assertIn('COALESCE(started_at, NOW())', task_model.started_at_sql('doing'))

    def test_zablokowanie_i_zamkniecie_nie_kasuje_daty(self):
        for status in ('waiting', 'done'):
            self.assertEqual('', task_model.started_at_sql(status), status)

    def test_odlozenie_z_powrotem_zeruje(self):
        for status in ('next', 'someday', 'ideas'):
            self.assertIn('started_at=NULL', task_model.started_at_sql(status), status)


class BoardLayoutTest(unittest.TestCase):

    def test_ma_szesc_kolumn_w_kolejnosci_przeplywu(self):
        data = board([])
        self.assertEqual(['ideas', 'next', 'doing', 'waiting', 'done', 'someday'],
                         [c['key'] for c in data['columns']])

    def test_podzadanie_nie_dostaje_wlasnej_karty(self):
        data = board([row(1, is_project=1), row(2, parent_id=1), row(3)])
        self.assertEqual([1, 3], sorted(titles(data, 'next')))

    def test_projekt_idzie_za_zadaniem_w_trakcie(self):
        data = board([row(1, is_project=1), row(2, parent_id=1, status='doing'),
                      row(3, parent_id=1, status='waiting')])
        self.assertEqual([1], titles(data, 'doing'))
        self.assertEqual([], titles(data, 'waiting'))

    def test_wiek_projektu_liczy_sie_od_pierwszego_ruszonego_zadania(self):
        data = board([row(1, is_project=1),
                      row(2, parent_id=1, status='doing', started_at=LONG_AGO),
                      row(3, parent_id=1, status='doing', started_at=datetime(2026, 10, 1))])
        self.assertEqual(LONG_AGO, column(data, 'doing')['cards'][0]['started_at'])

    def test_gotowy_do_zamkniecia_to_projekt_ze_wszystkim_zrobionym(self):
        data = board([row(1, is_project=1), row(2, parent_id=1, status='done',
                                                completed_at=datetime(2026, 10, 2, 9, 0)),
                      row(9, is_project=1)])
        cards = {c['id']: c for c in column(data, 'next')['cards']}
        self.assertTrue(cards[1]['ready_to_close'])
        # Projekt, w którym nigdy nic nie było, nie jest „gotowy do zamknięcia”.
        self.assertFalse(cards[9]['ready_to_close'])

    def test_zamkniete_podzadanie_ma_karte_tylko_w_zrobionych(self):
        data = board([row(1, is_project=1),
                      row(2, parent_id=1, status='done', completed_at=datetime(2026, 10, 2, 9, 0))])
        self.assertEqual([2], titles(data, 'done'))
        self.assertEqual([1], titles(data, 'next'))

    def test_zrobione_obejmuja_ten_i_ubiegly_tydzien(self):
        stare = row(5, status='done', completed_at=datetime(2026, 9, 1, 9, 0))
        swieze = row(6, status='done', completed_at=datetime(2026, 10, 2, 9, 0))
        self.assertEqual([6], titles(board([stare, swieze]), 'done'))
        self.assertEqual([6, 5], titles(board([stare, swieze], show_all_done=True), 'done'))

    def test_okno_zrobionych_zaczyna_sie_w_poniedzialek_ubieglego_tygodnia(self):
        self.assertEqual(date(2026, 9, 28), task_model.board_done_since(TODAY))
        self.assertEqual(date(2026, 9, 28), task_model.board_done_since(date(2026, 10, 11)))

    def test_zadanie_bez_daty_zamkniecia_wchodzi_po_dacie_edycji(self):
        """96 zamkniętych zadań nie ma completed_at — bez tego wypadłyby z tablicy."""
        data = board([row(7, status='done', completed_at=None,
                          updated_at=datetime(2026, 10, 1, 9, 0))])
        self.assertEqual([7], titles(data, 'done'))

    def test_zrobione_sa_posortowane_od_najswiezszych(self):
        data = board([row(1, status='done', completed_at=datetime(2026, 9, 29, 9, 0)),
                      row(2, status='done', completed_at=datetime(2026, 10, 3, 9, 0))])
        self.assertEqual([2, 1], titles(data, 'done'))

    def test_filtr_kontekstu_lapie_projekt_po_jego_zadaniu(self):
        data = board([row(1, is_project=1, context_id=None), row(2, parent_id=1, context_id=3)],
                     context_ids=[3])
        self.assertEqual([1], titles(data, 'next'))

    def test_filtr_gotowych_do_zamkniecia_nie_wpuszcza_zrobionych(self):
        data = board([row(1, is_project=1), row(2, parent_id=1, status='done',
                                                completed_at=datetime(2026, 10, 2, 9, 0))],
                     only_ready=True)
        self.assertEqual([1], titles(data, 'next'))
        self.assertEqual([], titles(data, 'done'))

    def test_zadna_karta_nie_stoi_w_dwoch_kolumnach(self):
        data = board([row(1, is_project=1), row(2, parent_id=1, status='doing'),
                      row(3), row(4, status='waiting'), row(5, status='someday'),
                      row(6, status='ideas')])
        ids = [c['id'] for col in data['columns'] for c in col['cards']]
        self.assertEqual(len(ids), len(set(ids)))


class StatusStaysVisibleTest(unittest.TestCase):
    """„W trakcie” to wciąż next action — zadanie nie może wypaść z innych widoków."""

    def test_wszystkie_zadania_pokazuja_tez_zadania_w_trakcie(self):
        import inspect
        for fn in (task_model.get_next_actions, task_model.find_tasks):
            self.assertIn("'doing'", inspect.getsource(fn), fn.__name__)

    def test_plakietka_statusu_zna_czwarty_stan(self):
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               'templates', 'gtd', '_macros.html'), encoding='utf-8') as f:
            macros = f.read()
        self.assertIn("'doing': 'W TRAKCIE'", macros)
        # Jedna plakietka dla wszystkich widoków — druga kopia zostałaby trójstanowa.
        self.assertEqual(1, macros.count('gtd-status-badge badge {{ cls }}'))


class BoardPageTest(unittest.TestCase):
    """Widok na żywej bazie — czy w ogóle się renderuje."""

    @classmethod
    def setUpClass(cls):
        from app import app
        cls.client = app.test_client()
        with cls.client.session_transaction() as s:
            s['user_id'] = 1
            s['username'] = 'test'
            s['full_name'] = 'Test'

    def _get(self, url):
        r = self.client.get(url)
        body = r.get_data(as_text=True)
        self.assertEqual(200, r.status_code, url)
        self.assertNotIn('Błąd serwera', body, url)
        return body

    def test_tablica_ma_wszystkie_kolumny(self):
        body = self._get('/gtd/tablica')
        for label in ('Pomysły', 'TODO', 'W trakcie', 'Zablokowane', 'Zrobione', 'Kiedyś'):
            self.assertIn(label, body, label)

    def test_filtry_sie_renderuja(self):
        for url in ('/gtd/tablica?q=strona', '/gtd/tablica?ready=1', '/gtd/tablica?blocked=1',
                    '/gtd/tablica?all_done=1', '/gtd/tablica?ctx=0'):
            self._get(url)

    def test_tablica_jest_w_menu(self):
        self.assertIn('/gtd/tablica', self._get('/gtd/dzis'))

    def test_baza_zna_status_w_trakcie(self):
        from app import app
        from database import get_db
        with app.app_context():
            with get_db().cursor() as cur:
                cur.execute("SHOW COLUMNS FROM tasks LIKE 'status'")
                self.assertIn("'doing'", cur.fetchone()['Type'])
                cur.execute("SHOW COLUMNS FROM tasks LIKE 'started_at'")
                self.assertIsNotNone(cur.fetchone())


if __name__ == '__main__':
    unittest.main()
