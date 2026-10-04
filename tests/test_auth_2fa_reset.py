"""Logowanie dwuetapowe i odzyskiwanie hasła — kontrakt bezpieczeństwa tych dwóch ścieżek.

Czego pilnują te testy:
 * samo hasło nie wpuszcza do aplikacji — `session['user_id']` zapada dopiero po kodzie,
 * sekrety leżą w bazie wyłącznie jako skrót SHA-256,
 * kod ma termin, jedno użycie i limit prób, po którym przepada,
 * link do resetu działa raz i godzinę, a formularz odzyskiwania odpowiada tak samo
   dla konta istniejącego i nieistniejącego (inaczej byłby listą kont).
Uruchomienie: venv/bin/python -m unittest discover tests
"""
import hashlib
import os
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import models.auth_token as at

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(rel: str) -> str:
    with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
        return f.read()


class FakeCursor:
    """Kursor, który zapamiętuje zapytania i oddaje kolejno podstawione wiersze."""

    def __init__(self, rows):
        self.rows = list(rows)
        self.queries = []
        self.rowcount = 1

    def execute(self, sql, params=None):
        self.queries.append((' '.join(sql.split()), params))

    def fetchone(self):
        return self.rows.pop(0) if self.rows else None

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def fake_db(rows=()):
    cur = FakeCursor(rows)
    db = MagicMock()
    db.cursor.return_value = cur
    return db, cur


class CodeShapeTest(unittest.TestCase):
    def test_six_alphanumeric_characters(self):
        db, _ = fake_db()
        with patch.object(at, 'get_db', return_value=db):
            codes = {at.issue_login_code(1) for _ in range(50)}
        for code in codes:
            self.assertEqual(6, len(code))
            self.assertTrue(code.isalnum())
            self.assertTrue(all(c in at.CODE_ALPHABET for c in code))
        self.assertGreater(len(codes), 40, 'kody muszą być losowe, nie przewidywalne')

    def test_alphabet_has_no_confusable_characters(self):
        for ch in '01OIL':
            self.assertNotIn(ch, at.CODE_ALPHABET)

    def test_code_is_stored_only_as_hash(self):
        db, cur = fake_db()
        with patch.object(at, 'get_db', return_value=db):
            code = at.issue_login_code(7, ip='1.2.3.4')
        insert = [q for q in cur.queries if q[0].startswith('INSERT INTO auth_tokens')][0]
        self.assertNotIn(code, str(insert[1]), 'jawny kod nie może trafić do bazy')
        self.assertIn(hashlib.sha256(code.encode()).hexdigest(), insert[1])

    def test_new_code_invalidates_the_previous_one(self):
        db, cur = fake_db()
        with patch.object(at, 'get_db', return_value=db):
            at.issue_login_code(7)
        self.assertTrue(any(q[0].startswith('UPDATE auth_tokens SET used_at = NOW()')
                            for q in cur.queries))

    def test_code_from_email_is_read_regardless_of_case_and_spaces(self):
        self.assertEqual('GJ7BHR', at.normalize_code(' gj7 bhr '))
        self.assertEqual('GJ7BHR', at.normalize_code('GJ7-BHR'))


class ConsumeCodeTest(unittest.TestCase):
    def _row(self, code, **over):
        row = {'id': 5, 'user_id': 1, 'attempts': 0,
               'token_hash': hashlib.sha256(code.encode()).hexdigest(),
               'expires_at': datetime.now() + timedelta(minutes=5)}
        row.update(over)
        return row

    def _consume(self, row, code):
        db, cur = fake_db([row] if row else [])
        with patch.object(at, 'get_db', return_value=db):
            return at.consume_login_code(1, code), cur

    def test_correct_code_passes_and_is_burned(self):
        result, cur = self._consume(self._row('ABC234'), 'abc234')
        self.assertEqual('ok', result)
        self.assertTrue(any('SET used_at = NOW() WHERE id' in q[0] for q in cur.queries))

    def test_wrong_code_counts_an_attempt(self):
        result, cur = self._consume(self._row('ABC234'), 'ZZZ999')
        self.assertEqual('invalid', result)
        self.assertIn(('UPDATE auth_tokens SET attempts = %s WHERE id = %s', (1, 5)), cur.queries)

    def test_last_attempt_burns_the_code(self):
        result, cur = self._consume(self._row('ABC234', attempts=at.MAX_ATTEMPTS - 1), 'ZZZ999')
        self.assertEqual('blocked', result)
        self.assertTrue(any('attempts = %s, used_at = NOW()' in q[0] for q in cur.queries))

    def test_expired_code_is_rejected(self):
        row = self._row('ABC234', expires_at=datetime.now() - timedelta(minutes=1))
        self.assertEqual('expired', self._consume(row, 'ABC234')[0])

    def test_no_pending_code(self):
        self.assertEqual('missing', self._consume(None, 'ABC234')[0])


class ResetTokenTest(unittest.TestCase):
    def test_link_is_valid_for_one_hour(self):
        self.assertEqual(60, at.RESET_TTL_MINUTES)

    def test_token_is_long_and_stored_as_hash(self):
        db, cur = fake_db()
        with patch.object(at, 'get_db', return_value=db):
            token = at.issue_password_reset(3)
        self.assertGreaterEqual(len(token), 32)
        insert = [q for q in cur.queries if q[0].startswith('INSERT INTO auth_tokens')][0]
        self.assertNotIn(token, str(insert[1]))
        self.assertIn(hashlib.sha256(token.encode()).hexdigest(), insert[1])

    def test_expired_link_does_not_open_the_form(self):
        row = {'id': 1, 'user_id': 2, 'attempts': 0, 'token_hash': 'x',
               'expires_at': datetime.now() - timedelta(minutes=1)}
        db, _ = fake_db([row])
        with patch.object(at, 'get_db', return_value=db):
            self.assertIsNone(at.peek_reset_token('cokolwiek'))

    def test_link_works_once(self):
        """Drugie użycie nie może zmienić hasła — UPDATE trafia w zero wierszy."""
        row = {'id': 1, 'user_id': 2, 'attempts': 0, 'token_hash': 'x',
               'expires_at': datetime.now() + timedelta(minutes=5)}
        db, cur = fake_db([row])
        cur.rowcount = 0
        with patch.object(at, 'get_db', return_value=db), \
             patch.object(at, 'peek_reset_token', return_value=2):
            self.assertIsNone(at.consume_reset_token('token'))


class LoginFlowTest(unittest.TestCase):
    """Kolejność kroków w trasach — tu mieszka realne bezpieczeństwo tej funkcji."""

    def setUp(self):
        self.src = read('routes/auth.py')

    def test_password_alone_does_not_create_a_session(self):
        branch = self.src.split('if user:')[1].split('else:')[0]
        self.assertIn('_two_factor_enabled(user)', branch)
        self.assertIn("session['pending_2fa']", branch)
        self.assertNotIn("session['user_id'] =", branch)

    def test_session_is_cleared_before_login(self):
        finish = self.src.split('def _finish_login')[1].split('def ')[0]
        self.assertLess(finish.index('session.clear()'), finish.index("session['user_id']"))

    def test_password_change_invalidates_pending_secrets(self):
        reset = self.src.split('def reset_password')[1]
        self.assertIn('invalidate_user_tokens(user_id)', reset)
        self.assertLess(reset.index('change_password(user_id, password)'),
                        reset.index('invalidate_user_tokens(user_id)'))

    def test_forgot_password_answers_the_same_for_unknown_accounts(self):
        forgot = self.src.split('def forgot_password')[1].split('@bp.route')[0]
        self.assertEqual(1, forgot.count("render_template('auth/forgot.html', sent=True)"),
                         'jedna odpowiedź dla wszystkich — inaczej formularz zdradza konta')

    def test_auth_blueprint_is_public(self):
        app_src = read('app.py').split('def require_login')[1].split('def inject_globals')[0]
        self.assertIn("ep.startswith('auth.')", app_src)

    def test_two_factor_needs_an_address_and_a_working_mailer(self):
        guard = self.src.split('def _two_factor_enabled')[1].split('def ')[0]
        self.assertIn("get_setting('login_2fa', 'on') == 'off'", guard)
        self.assertIn("user.get('email')", guard)
        self.assertIn('is_configured()', guard)


class AuthScreensTest(unittest.TestCase):
    """Ekrany logowania chodzą po tej samej palecie co reszta aplikacji."""

    def test_pages_share_the_application_stylesheet(self):
        layout = read('templates/auth/_layout.html')
        self.assertIn("url_for('static', filename='style.css')", layout)
        self.assertIn('auth-body', layout)

    def test_styles_use_redesign_tokens_not_hardcoded_colors(self):
        css = read('static/style.css').split('/* ── Ekrany logowania')[1]
        self.assertIn('background: var(--rd-deep-green)', css)
        self.assertIn('background: var(--rd-lime)', css)
        self.assertIn('font-family: var(--rd-font)', css)

    def test_login_offers_password_recovery(self):
        login = read('templates/auth/login.html')
        self.assertIn("url_for('auth.forgot_password')", login)
        self.assertIn('Zapomniałeś hasła', login)

    def test_every_auth_screen_extends_the_shared_layout(self):
        for name in ('login', 'code', 'forgot', 'reset'):
            self.assertIn("{% extends 'auth/_layout.html' %}", read(f'templates/auth/{name}.html'))


if __name__ == '__main__':
    unittest.main()
