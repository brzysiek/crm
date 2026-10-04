"""Zdjęcie użytkownika: miniatura, trasa serwująca i ikonka w menu.

Błędy, przed którymi to broni:
— wrzucenie do bazy oryginalnego zdjęcia z telefonu (kilka MB base64 w kolumnie
  i w każdej odpowiedzi HTML-owej);
— zdjęcie nie-kwadratowe wciśnięte w kółko ikonki (spłaszczona twarz);
— ikonka zostająca na starym obrazku po podmianie, bo adres się nie zmienił;
— plik, który nie jest obrazem, przewrócony na 500 zamiast komunikatu.
Uruchomienie: venv/bin/python -m unittest discover tests
"""
import io
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(rel: str) -> str:
    with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
        return f.read()


def jpeg(size=(1200, 800), color=(12, 60, 44)) -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.new('RGB', size, color).save(buf, 'JPEG')
    return buf.getvalue()


class BuildAvatarTest(unittest.TestCase):

    def _open(self, data: bytes):
        from PIL import Image
        return Image.open(io.BytesIO(data))

    def test_result_is_a_square_jpeg_thumbnail(self):
        from services.images import build_avatar
        out = build_avatar(jpeg())
        img = self._open(out)
        self.assertEqual('JPEG', img.format)
        self.assertEqual((256, 256), img.size)

    def test_thumbnail_is_small_enough_to_live_in_a_column(self):
        """Zdjęcie 12 Mpx musi zejść do kilkudziesięciu kB, inaczej data URI
        w bazie i w cache przeglądarki przestaje mieć sens."""
        from services.images import build_avatar
        self.assertLess(len(build_avatar(jpeg(size=(4000, 3000)))), 60_000)

    def test_center_crop_instead_of_squashing(self):
        """Panorama ma zostać przycięta do środka, a nie ściśnięta — pionowy
        pasek na środku źródła musi zostać pionowym paskiem na środku wyniku."""
        from PIL import Image, ImageDraw
        from services.images import build_avatar
        src = Image.new('RGB', (900, 300), (0, 0, 0))
        ImageDraw.Draw(src).rectangle((430, 0, 470, 300), fill=(255, 255, 255))
        buf = io.BytesIO()
        src.save(buf, 'PNG')
        out = self._open(build_avatar(buf.getvalue()))
        self.assertGreater(out.getpixel((128, 128))[0], 200)   # środek — biały pasek
        self.assertLess(out.getpixel((10, 128))[0], 60)        # brzeg — czarne tło

    def test_transparent_png_does_not_explode(self):
        from PIL import Image
        from services.images import build_avatar
        buf = io.BytesIO()
        Image.new('RGBA', (400, 400), (255, 0, 0, 0)).save(buf, 'PNG')
        self.assertEqual((256, 256), self._open(build_avatar(buf.getvalue())).size)

    def test_non_image_raises_a_message_we_can_show(self):
        from services.images import build_avatar
        with self.assertRaises(ValueError):
            build_avatar(b'to zdecydowanie nie jest obraz')


class AvatarModelTest(unittest.TestCase):
    """Kształt zapytań, bez dotykania bazy produkcyjnej."""

    def _cursor(self, row):
        from models import user as user_model
        cur = mock.MagicMock()
        cur.fetchone.return_value = row
        db = mock.MagicMock()
        db.cursor.return_value.__enter__.return_value = cur
        return user_model, cur, mock.patch.object(user_model, 'get_db', return_value=db)

    def test_avatar_is_read_by_a_dedicated_query(self):
        """Kilkanaście kB base64 nie może jechać przy każdym get_user_by_id."""
        from models import user as user_model
        for src in (user_model.get_user_by_id, user_model.get_all_users,
                     user_model.get_user_by_username, user_model.get_active_users):
            import inspect
            self.assertNotIn('avatar', inspect.getsource(src))

    def test_version_changes_with_the_photo(self):
        from datetime import datetime
        user_model, cur, patched = self._cursor({'avatar_updated_at': datetime(2026, 10, 4, 20, 34)})
        with patched:
            self.assertEqual('20261004203400', user_model.get_user_avatar_version(1))
        self.assertIn('avatar IS NOT NULL', cur.execute.call_args[0][0])

    def test_no_photo_means_no_version(self):
        user_model, _cur, patched = self._cursor(None)
        with patched:
            self.assertIsNone(user_model.get_user_avatar_version(1))

    def test_clearing_the_photo_clears_the_timestamp(self):
        user_model, cur, patched = self._cursor(None)
        with patched:
            user_model.set_user_avatar(1, None)
        self.assertEqual((None, None, 1), cur.execute.call_args[0][1])


class AvatarRouteTest(unittest.TestCase):
    """Formularz i trasa serwująca, na zamockowanym modelu."""

    @classmethod
    def setUpClass(cls):
        from app import app
        app.config['TESTING'] = True
        cls.app = app

    def client(self):
        c = self.app.test_client()
        with c.session_transaction() as s:
            s['user_id'] = 7
            s['username'] = 'tester'
            s['full_name'] = 'Test Testowy'
        return c

    def test_upload_stores_a_jpeg_data_uri(self):
        import models.user as user_model
        with mock.patch.object(user_model, 'set_user_avatar') as saved:
            r = self.client().post('/settings/konto', data={
                'form': 'avatar', 'avatar': (io.BytesIO(jpeg()), 'foto.jpg', 'image/jpeg')},
                content_type='multipart/form-data')
        self.assertEqual(302, r.status_code)
        user_id, data_uri = saved.call_args[0]
        self.assertEqual(7, user_id)
        self.assertTrue(data_uri.startswith('data:image/jpeg;base64,'))

    def test_broken_file_is_a_message_not_a_crash(self):
        import models.user as user_model
        with mock.patch.object(user_model, 'set_user_avatar') as saved:
            r = self.client().post('/settings/konto', data={
                'form': 'avatar', 'avatar': (io.BytesIO(b'xxx'), 'foto.jpg', 'image/jpeg')},
                content_type='multipart/form-data', follow_redirects=True)
        self.assertEqual(200, r.status_code)
        saved.assert_not_called()

    def test_foreign_format_is_rejected_before_pillow(self):
        import models.user as user_model
        with mock.patch.object(user_model, 'set_user_avatar') as saved:
            self.client().post('/settings/konto', data={
                'form': 'avatar', 'avatar': (io.BytesIO(b'%PDF-1.4'), 'cv.pdf', 'application/pdf')},
                content_type='multipart/form-data')
        saved.assert_not_called()

    def test_removal_passes_none(self):
        import models.user as user_model
        with mock.patch.object(user_model, 'set_user_avatar') as saved:
            self.client().post('/settings/konto', data={'form': 'avatar', 'remove_avatar': '1'})
        self.assertEqual((7, None), saved.call_args[0])

    def test_route_serves_bytes_with_a_cache_header(self):
        import base64
        import models.user as user_model
        data_uri = 'data:image/jpeg;base64,' + base64.b64encode(jpeg()).decode('ascii')
        with mock.patch.object(user_model, 'get_user_avatar', return_value=data_uri):
            r = self.client().get('/settings/zdjecie/7')
        self.assertEqual(200, r.status_code)
        self.assertEqual('image/jpeg', r.mimetype)
        self.assertIn('max-age', r.headers.get('Cache-Control', ''))

    def test_route_404s_without_a_photo(self):
        import models.user as user_model
        with mock.patch.object(user_model, 'get_user_avatar', return_value=None):
            self.assertEqual(404, self.client().get('/settings/zdjecie/7').status_code)


class AvatarInMenuTest(unittest.TestCase):

    def test_icon_falls_back_to_initials(self):
        base = read('templates/base.html')
        self.assertIn('current_user.avatar_version', base)
        self.assertIn("url_for('settings.avatar'", base)
        # Dwa miejsca: menu boczne i pasek mobilny.
        self.assertEqual(2, base.count("url_for('settings.avatar'"))
        self.assertIn("(current_user.full_name or current_user.username or '?')[:2] | upper", base)

    def test_address_carries_the_version(self):
        """Bez ?v=… przeglądarka trzymałaby stare zdjęcie przez dobę."""
        base = read('templates/base.html')
        for line in base.splitlines():
            if "url_for('settings.avatar'" in line:
                self.assertIn('v=current_user.avatar_version', line)

    def test_context_processor_exposes_the_version(self):
        self.assertIn("'avatar_version': avatar_version", read('app.py'))

    def test_styles_make_the_photo_fill_the_circle(self):
        css = read('static/style.css')
        for cls in ('.sidebar-avatar-img', '.mobile-topbar-avatar-img', '.rd-avatar-preview'):
            self.assertIn(cls, css)
        self.assertIn('object-fit: cover', css)


if __name__ == '__main__':
    unittest.main()
