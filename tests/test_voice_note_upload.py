"""Testy endpointu notatki głosowej — wgrany plik i nagranie z mikrofonu.

Zapis do bazy jest zamockowany; sprawdzamy, co endpoint przepuszcza, co odrzuca
i w jakiej postaci nagranie trafia do modelu.
Uruchomienie: venv/bin/python -m unittest discover tests
"""
import io
import unittest
from unittest import mock

import models.crm_notes as crm_notes
from app import app
from services.voice_notes import MAX_AUDIO_BYTES, split_data_uri


class VoiceNoteUploadTest(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
        patch = mock.patch.object(crm_notes, 'add_voice_note', return_value=999)
        self.add_voice_note = patch.start()
        self.addCleanup(patch.stop)

    def post(self, entity_type='mna_deal', entity_id=4, file_name='notatka.m4a',
             content=b'udawane audio', content_type='audio/x-m4a'):
        data = {'entity_type': entity_type, 'entity_id': str(entity_id)}
        if file_name is not None:
            data['audio'] = (io.BytesIO(content), file_name, content_type)
        resp = self.client.post('/api/crm/notes/voice', data=data,
                                content_type='multipart/form-data')
        return resp.get_json()

    def test_wgrany_m4a_zapisuje_sie_jako_audio_mp4(self):
        """Regresja: przeglądarka podaje dla m4a audio/x-m4a, którego Gemini nie
        rozpoznaje z nagłówka — endpoint musi znormalizować typ po rozszerzeniu."""
        self.assertEqual(self.post(), {'status': 'ok', 'note_id': 999})
        entity_type, entity_id, user_id, audio_data = self.add_voice_note.call_args[0]
        self.assertEqual((entity_type, entity_id, user_id), ('mna_deal', 4, 1))
        self.assertEqual(split_data_uri(audio_data), (b'udawane audio', 'audio/mp4'))

    def test_mp3(self):
        self.assertEqual(self.post(file_name='dyktafon.mp3', content_type='audio/mpeg')['status'], 'ok')
        self.assertEqual(split_data_uri(self.add_voice_note.call_args[0][3])[1], 'audio/mpeg')

    def test_nagranie_z_mikrofonu(self):
        self.assertEqual(self.post(file_name='notatka.webm', content_type='audio/webm;codecs=opus')['status'], 'ok')
        self.assertEqual(split_data_uri(self.add_voice_note.call_args[0][3])[1], 'audio/webm')

    def test_wszystkie_encje_crm_i_mna(self):
        """Notatki głosowe działają na każdym ekranie z notatkami — lista typów
        w modelu musi pokrywać ENUM w bazie, inaczej M&A dostaje 'Nieprawidłowa encja'."""
        for entity_type in crm_notes.VALID_ENTITY_TYPES:
            self.assertEqual(self.post(entity_type=entity_type)['status'], 'ok', entity_type)

    def test_odrzuca_nieznana_encje(self):
        resp = self.post(entity_type='mna_target')
        self.assertEqual(resp['status'], 'error')
        self.add_voice_note.assert_not_called()

    def test_odrzuca_brak_pliku(self):
        self.assertEqual(self.post(file_name=None)['status'], 'error')
        self.add_voice_note.assert_not_called()

    def test_odrzuca_pdf_z_komunikatem_o_formatach(self):
        """Użytkownik trafiał wcześniej na uploader plików i widział listę
        formatów dokumentów — tu komunikat musi mówić o formatach audio."""
        resp = self.post(file_name='faktura.pdf', content_type='application/pdf')
        self.assertEqual(resp['status'], 'error')
        self.assertIn('M4A', resp['message'])
        self.add_voice_note.assert_not_called()

    def test_odrzuca_za_duzy_plik(self):
        resp = self.post(content=b'x' * (MAX_AUDIO_BYTES + 1))
        self.assertEqual(resp['status'], 'error')
        self.assertIn('MB', resp['message'])
        self.add_voice_note.assert_not_called()

    def test_wymaga_logowania(self):
        with app.test_client() as anon:
            resp = anon.post('/api/crm/notes/voice', data={'entity_type': 'contact', 'entity_id': '1'})
            self.assertEqual(resp.status_code, 401)


if __name__ == '__main__':
    unittest.main()
