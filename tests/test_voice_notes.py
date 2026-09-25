"""Testy reguł notatek głosowych — format, rozmiar i pakowanie w data URI.

Serwis jest czysty (bez bazy i sieci), więc testy liczą na prawdziwych bajtach.
Uruchomienie: venv/bin/python -m unittest discover tests
"""
import base64
import unittest

from services.voice_notes import (AudioNoteError, MAX_AUDIO_BYTES, audio_mime,
                                   build_data_uri, split_data_uri)


class AudioMimeTest(unittest.TestCase):
    def test_rozpoznaje_formaty_po_rozszerzeniu(self):
        for name, expected in [('notatka.mp3', 'audio/mpeg'),
                               ('notatka.m4a', 'audio/mp4'),
                               ('notatka.wav', 'audio/wav'),
                               ('notatka.opus', 'audio/ogg'),
                               ('notatka.webm', 'audio/webm'),
                               ('notatka.flac', 'audio/flac')]:
            self.assertEqual(audio_mime(name), expected, name)

    def test_rozszerzenie_wielkimi_literami_i_kropki_w_nazwie(self):
        self.assertEqual(audio_mime('Dyktafon 2026.09.25.M4A'), 'audio/mp4')

    def test_rozszerzenie_wygrywa_z_typem_przegladarki(self):
        """Przeglądarki podają dla m4a byle co (audio/x-m4a, pusty string),
        a Gemini wymaga typu, który zna — rozszerzenie jest wiarygodniejsze."""
        self.assertEqual(audio_mime('notatka.m4a', 'audio/x-m4a'), 'audio/mp4')
        self.assertEqual(audio_mime('notatka.m4a', ''), 'audio/mp4')
        self.assertEqual(audio_mime('notatka.m4a', 'application/octet-stream'), 'audio/mp4')

    def test_typ_przegladarki_gdy_brak_rozszerzenia(self):
        self.assertEqual(audio_mime('blob', 'audio/webm;codecs=opus'), 'audio/webm')

    def test_odrzuca_nieaudio(self):
        for name, declared in [('faktura.pdf', 'application/pdf'),
                               ('skan.jpg', 'image/jpeg'),
                               ('blob', ''),
                               ('', '')]:
            with self.assertRaises(AudioNoteError):
                audio_mime(name, declared)

    def test_komunikat_wymienia_obslugiwane_formaty(self):
        with self.assertRaises(AudioNoteError) as ctx:
            audio_mime('plik.pdf')
        self.assertIn('M4A', str(ctx.exception))


class DataUriTest(unittest.TestCase):
    def test_pakuje_i_rozpakowuje_bez_straty(self):
        raw = b'\x00\x01ID3 udawane audio \xff\xfb'
        uri = build_data_uri(raw, 'audio/mpeg')
        self.assertTrue(uri.startswith('data:audio/mpeg;base64,'))
        self.assertEqual(split_data_uri(uri), (raw, 'audio/mpeg'))

    def test_odrzuca_puste_nagranie(self):
        with self.assertRaises(AudioNoteError):
            build_data_uri(b'', 'audio/mp4')

    def test_limit_rozmiaru(self):
        """Granica jest ostra: MEDIUMTEXT nie zgłasza błędu, tylko ucina dane."""
        build_data_uri(b'x' * MAX_AUDIO_BYTES, 'audio/mp4')
        with self.assertRaises(AudioNoteError) as ctx:
            build_data_uri(b'x' * (MAX_AUDIO_BYTES + 1), 'audio/mp4')
        self.assertIn('10 MB', str(ctx.exception))

    def test_base64_miesci_sie_w_mediumtext(self):
        uri = build_data_uri(b'x' * MAX_AUDIO_BYTES, 'audio/mp4')
        self.assertLess(len(uri.encode('utf-8')), 16 * 1024 * 1024)

    def test_rozpakowanie_smieci(self):
        for bad in ['', 'brak przecinka', 'data:audio/mp4;base64']:
            with self.assertRaises(AudioNoteError):
                split_data_uri(bad)

    def test_rozpakowuje_stare_nagrania_z_przegladarki(self):
        """Notatki zapisane przed wprowadzeniem serwisu mają w nagłówku codecs."""
        raw = b'webm bytes'
        uri = 'data:audio/webm;codecs=opus;base64,' + base64.b64encode(raw).decode()
        self.assertEqual(split_data_uri(uri), (raw, 'audio/webm'))


if __name__ == '__main__':
    unittest.main()
