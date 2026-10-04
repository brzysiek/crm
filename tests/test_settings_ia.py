"""Układ Ustawień: wąski zakres, nawigacja w menu głównym, żywe linki.

Błąd, przed którym to broni: Ustawienia urosły do jedenastu pozycji własnego,
wewnętrznego podmenu i zbierały rzeczy, które edytuje się w trakcie pracy
(listy kontaktów, konteksty GTD, stopki kampanii). Przy rozbiciu tego na moduły
łatwo zostawić `url_for` wskazujący na trasę, której już nie ma — a taki błąd
wychodzi dopiero przy renderowaniu strony, u użytkownika.
Uruchomienie: venv/bin/python -m unittest discover tests
"""
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL_FOR = re.compile(r"url_for\(\s*'([a-zA-Z_]\w*(?:\.\w+)?)'")


def read(rel: str) -> str:
    with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
        return f.read()


def walk(subdir: str, suffix: str):
    base = os.path.join(ROOT, subdir)
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in ('__pycache__', 'node_modules')]
        for name in files:
            if name.endswith(suffix):
                path = os.path.join(root, name)
                with open(path, encoding='utf-8') as f:
                    yield os.path.relpath(path, ROOT), f.read()


class EndpointsExistTest(unittest.TestCase):
    """Każdy `url_for` w szablonach i trasach musi trafiać w istniejący endpoint."""

    @classmethod
    def setUpClass(cls):
        from app import app
        cls.endpoints = {r.endpoint for r in app.url_map.iter_rules()}

    def _check(self, sources):
        dangling = []
        for rel, text in sources:
            for line_no, line in enumerate(text.splitlines(), 1):
                for m in URL_FOR.finditer(line):
                    if m.group(1) not in self.endpoints:
                        dangling.append(f'{rel}:{line_no} → {m.group(1)}')
        self.assertEqual([], dangling)

    def test_templates(self):
        self._check(walk('templates', '.html'))

    def test_routes_and_services(self):
        self._check(list(walk('routes', '.py')) + list(walk('services', '.py')))


class SettingsScopeTest(unittest.TestCase):
    """Ustawienia trzymają konfigurację; rzeczy edytowane w trakcie pracy mieszkają
    przy swoich widokach."""

    def test_settings_blueprint_has_only_configuration_routes(self):
        src = read('routes/settings.py')
        for gone in ('def contact_list', 'def gtd_context', 'def email_footer',
                     'def email_settings', 'def finance', 'def crm_settings'):
            self.assertNotIn(gone, src, f'{gone} nie należy już do Ustawień')

    def test_moved_features_live_next_to_their_views(self):
        self.assertIn("@bp.route('/listy')", read('routes/crm_contacts.py'))
        self.assertIn("@bp.route('/gtd/konteksty')", read('routes/gtd.py'))
        self.assertIn("@bp.route('/stopki')", read('routes/email_campaigns.py'))

    def test_moved_templates_exist(self):
        for rel in ('templates/crm/contacts/lists.html',
                    'templates/gtd/contexts.html',
                    'templates/email_campaigns/footers.html',
                    'templates/email_campaigns/footer_form.html'):
            self.assertTrue(os.path.exists(os.path.join(ROOT, rel)), rel)

    def test_dead_settings_templates_are_gone(self):
        for rel in ('bank', 'fakturownia', 'gdrive', 'email', 'email_footer_form',
                    'finance', 'dictionary', 'crm', 'contact_lists', 'gtd_contexts'):
            path = os.path.join(ROOT, 'templates/settings', rel + '.html')
            self.assertFalse(os.path.exists(path), path)


class SettingsNavigationTest(unittest.TestCase):
    """Nawigacja po ustawieniach wisi w menu głównym — w samym widoku nie ma już
    drugiego menu."""

    def setUp(self):
        self.base = read('templates/base.html')
        self.layout = read('templates/settings/_layout.html')

    def test_main_menu_has_settings_with_subitems(self):
        self.assertIn("url_for('settings.account')", self.base)
        for endpoint in ('settings.appearance', 'settings.general', 'settings.dictionaries',
                         'users.list_users', 'settings.logs'):
            self.assertIn(endpoint, self.base, f'brak podelementu {endpoint} w menu')

    def test_settings_layout_has_no_own_nav(self):
        self.assertNotIn('settings-sidebar', self.layout)
        self.assertNotIn('settings-nav-item', self.layout)

    def test_gtd_still_uses_the_shared_sidebar_classes(self):
        """`.settings-sidebar` zostaje w CSS, bo GTD buduje na niej swoje menu."""
        self.assertIn('settings-sidebar', read('templates/gtd/_layout.html'))
        self.assertIn('.settings-sidebar', read('static/style.css'))


class SettingsStylingTest(unittest.TestCase):
    """Widoki ustawień są w palecie redesignu, jak reszta aplikacji."""

    def test_layout_wraps_content_in_rd_screen(self):
        self.assertIn('rd-screen rd-settings', read('templates/settings/_layout.html'))

    def test_settings_classes_are_defined(self):
        css = read('static/style.css')
        for cls in ('.rd-settings-lead', '.rd-settings-grid', '.rd-settings-body',
                    '.rd-dict-list', '.rd-inline-add', '.rd-log-output', '.rd-logo-preview'):
            self.assertIn(cls, css, f'brak reguły {cls}')

    def test_every_settings_view_extends_the_layout(self):
        for rel, text in walk('templates/settings', '.html'):
            name = os.path.basename(rel)
            if name.startswith('_'):
                continue
            self.assertIn("{% extends 'settings/_layout.html' %}", text, rel)


if __name__ == '__main__':
    unittest.main()
