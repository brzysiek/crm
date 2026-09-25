"""Test usuwania plików z Google Drive.

Regresja: DELETE zwracał 404 na dysku współdzielonym (brak roli organizatora), więc
pliki usuwane w CRM zostawały na Drive. Usuwamy przez kosz.
Uruchomienie: venv/bin/python -m unittest discover tests
"""
import json
import unittest
from unittest import mock

import services.gdrive as gdrive


class DriveDeleteTest(unittest.TestCase):
    def setUp(self):
        self.client = gdrive.GoogleDriveClient(json.dumps({'client_email': 'x@y.iam'}), 'root')
        patches = [
            mock.patch.object(gdrive, 'get_service_account_token', return_value='tok'),
            mock.patch.object(gdrive.requests, 'patch'),
            mock.patch.object(gdrive.requests, 'delete'),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        gdrive.requests.patch.return_value = mock.Mock(status_code=200, json=lambda: {'id': 'f1'})

    def test_usuwa_przez_kosz_a_nie_przez_delete(self):
        self.client.delete_file('f1')
        gdrive.requests.delete.assert_not_called()
        url, = gdrive.requests.patch.call_args.args
        self.assertTrue(url.endswith('/files/f1'))
        self.assertEqual(gdrive.requests.patch.call_args.kwargs['json'], {'trashed': True})

    def test_obsługuje_dyski_współdzielone(self):
        """Bez supportsAllDrives Drive udaje, że pliku nie ma."""
        self.client.delete_file('f1')
        self.assertEqual(gdrive.requests.patch.call_args.kwargs['params']['supportsAllDrives'], 'true')

    def test_klucz_api_nie_wystarcza_do_usuwania(self):
        with self.assertRaises(ValueError):
            gdrive.GoogleDriveClient('AIzaKlucz', 'root').delete_file('f1')
        gdrive.requests.patch.assert_not_called()


if __name__ == '__main__':
    unittest.main()
