"""Testy zestawu formatów plików CRM.

Sedno: jeden słownik rządzi tym, co przechodzi, a komunikat o błędzie jest z
niego generowany — trzy ręcznie pisane kopie listy formatów rozjechały się
kiedyś z zestawem i użytkownik dostawał listę bez połowy obsługiwanych typów.
Uruchomienie: venv/bin/python -m unittest discover tests
"""
import io
import unittest
from unittest import mock

import models.crm_company as crm_company
import models.crm_contact as crm_contact
from app import app
from models.crm_file import (ALLOWED_EXTENSIONS, AUDIO_EXTENSIONS, IMAGE_EXTENSIONS,
                             INLINE_PREVIEW_MIMES, formats_label)
from services.crm_files import mime_for
from services.voice_notes import AUDIO_MIME_BY_EXT


class AllowedExtensionsTest(unittest.TestCase):
    def test_nagrania_przechodza_przez_uploader(self):
        """Użytkownik wgrywał m4a do sekcji Pliki i dostawał odmowę — nagranie
        jest równoprawnym załącznikiem, nie tylko treścią notatki głosowej."""
        self.assertEqual(mime_for('Nota z dyktafonu.m4a'), 'audio/mp4')
        self.assertEqual(mime_for('rozmowa.mp3'), 'audio/mpeg')

    def test_dokumenty_i_zdjecia_nadal_przechodza(self):
        for name, expected in [('nda.pdf', 'application/pdf'),
                               ('skan.JPG', 'image/jpeg'),
                               ('faktura.xml', 'application/xml')]:
            self.assertEqual(mime_for(name), expected, name)

    def test_odrzuca_co_innego(self):
        for name in ('wirus.exe', 'archiwum.zip', 'bez_rozszerzenia'):
            with self.assertRaises(ValueError, msg=name):
                mime_for(name)

    def test_formaty_audio_te_same_co_w_notatkach(self):
        """Plik wgrywalny do notatki głosowej musi przejść też przez sekcję Pliki
        — inaczej wracamy do stanu, w którym jedna ścieżka przyjmuje, a druga nie."""
        self.assertEqual(set(AUDIO_EXTENSIONS), set(AUDIO_MIME_BY_EXT) - {'mp4'})
        for ext, mime in AUDIO_EXTENSIONS.items():
            self.assertEqual(ALLOWED_EXTENSIONS[ext], mime, ext)

    def test_mp4_pozostaje_poza_zestawem(self):
        """.mp4 to prawie zawsze wideo — jako audio/mp4 dałoby odtwarzacz bez obrazu."""
        self.assertNotIn('mp4', ALLOWED_EXTENSIONS)

    def test_komunikat_wymienia_kazdy_obslugiwany_format(self):
        label = formats_label()
        aliases = {'jpeg', 'oga', 'aif'}
        for ext in ALLOWED_EXTENSIONS:
            if ext in aliases:
                continue
            self.assertIn(ext.upper(), label, ext)

    def test_nagrania_odtwarzane_w_podgladzie(self):
        """Inline zamiast załącznika — inaczej nagranie trzeba pobrać, żeby odsłuchać."""
        for mime in AUDIO_EXTENSIONS.values():
            self.assertIn(mime, INLINE_PREVIEW_MIMES, mime)

    def test_zdjecia_sa_podzbiorem_plikow(self):
        for ext, mime in IMAGE_EXTENSIONS.items():
            self.assertEqual(ALLOWED_EXTENSIONS[ext], mime, ext)
        self.assertFalse(set(IMAGE_EXTENSIONS) & set(AUDIO_EXTENSIONS))


class BusinessCardFormatsTest(unittest.TestCase):
    """Wizytówka idzie do OCR-u, więc przyjmuje tylko zdjęcia — po wpuszczeniu
    nagrań do zestawu plików ten endpoint nie może ich zacząć akceptować."""

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
        for patch in (mock.patch.object(crm_contact, 'get_contact_by_id',
                                        return_value={'id': 1, 'company_id': 2}),
                      mock.patch.object(crm_company, 'get_company_by_id',
                                        return_value={'id': 2, 'name': 'Testowa'})):
            patch.start()
            self.addCleanup(patch.stop)

    def post(self, file_name, content_type):
        resp = self.client.post('/api/crm/contacts/1/business-card/upload',
                                data={'file': (io.BytesIO(b'x'), file_name, content_type)},
                                content_type='multipart/form-data')
        return resp.get_json()

    def test_odrzuca_nagranie_i_dokument(self):
        for file_name, content_type in [('rozmowa.mp3', 'audio/mpeg'),
                                        ('nota.m4a', 'audio/mp4'),
                                        ('umowa.pdf', 'application/pdf'),
                                        ('faktura.xml', 'application/xml')]:
            resp = self.post(file_name, content_type)
            self.assertEqual(resp['status'], 'error', file_name)
            self.assertIn('JPG, PNG, HEIC', resp['message'], file_name)


if __name__ == '__main__':
    unittest.main()
