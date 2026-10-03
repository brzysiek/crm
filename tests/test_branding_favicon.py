"""Favikona ma docierać do przeglądarki także wtedy, gdy nie ma sesji.

Błąd, przed którym to broni: `/branding/icon`, `/manifest.webmanifest` i domyślne
`/favicon.ico` wpadały w `require_login` i kończyły się przekierowaniem na ekran logowania.
Przeglądarka pytała o favikonę właśnie tam — przed zalogowaniem — dostawała HTML i na długo
zapamiętywała, że ta domena ikony nie ma. Ustawienie logo w aplikacji niczego nie zmieniało.
Uruchomienie: venv/bin/python -m unittest discover tests
"""
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(rel: str) -> str:
    with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
        return f.read()


class OpenEndpointsTest(unittest.TestCase):
    def setUp(self):
        self.src = read('app.py')

    def test_icon_endpoints_are_public(self):
        for ep in ("'branding_icon'", "'favicon_ico'", "'web_manifest'"):
            self.assertIn(ep, self.src.split('def require_login')[1].split('def inject_globals')[0],
                          f'{ep} musi być w open_endpoints')

    def test_favicon_ico_route_exists(self):
        self.assertIn("@app.route('/favicon.ico')", self.src)
        self.assertIn('def favicon_ico():', self.src)

    def test_both_icon_routes_serve_the_same_bytes(self):
        body = self.src.split('def branding_icon():')[1].split('@app.route')[0]
        self.assertIn('_branding_icon_response()', body)
        body = self.src.split('def favicon_ico():')[1].split('@app.route')[0]
        self.assertIn('_branding_icon_response()', body)


class IconVersionTest(unittest.TestCase):
    """Adres ikony niesie odcisk ustawionego logo — inaczej `max-age=3600` i własny cache
    favikon w przeglądarce trzymałyby starą ikonę po podmianie w ustawieniach."""

    def test_version_changes_with_the_icon(self):
        from app import _branding_version
        a = _branding_version('data:image/png;base64,AAAA')
        b = _branding_version('data:image/png;base64,BBBB')
        self.assertTrue(a and b and a != b)
        self.assertEqual(a, _branding_version('data:image/png;base64,AAAA'))
        self.assertEqual('', _branding_version(None))

    def test_context_processor_exposes_version(self):
        self.assertIn("'logo_version'", read('app.py'))

    def test_manifest_icon_url_is_versioned(self):
        src = read('app.py').split('def web_manifest():')[1]
        self.assertIn("url_for('branding_icon', v=_branding_version(data_uri))", src)


class TemplatesTest(unittest.TestCase):
    def test_app_pages_link_versioned_icon(self):
        base = read('templates/base.html')
        self.assertIn("""<link rel="icon" href="{{ url_for('branding_icon', v=logo_version) }}">""", base)
        self.assertIn("""<link rel="apple-touch-icon" href="{{ url_for('branding_icon', v=logo_version) }}">""", base)

    def test_login_page_links_icon(self):
        login = read('templates/login.html')
        self.assertIn("url_for('branding_icon', v=logo_version)", login)
        self.assertIn('rel="icon"', login)


if __name__ == '__main__':
    unittest.main()
