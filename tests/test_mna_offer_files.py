"""Testy plików ofert M&A — folder na Drive, zapis i endpoint uploadu.

Drive i baza są zamockowane; sprawdzamy, czy plik oferty ląduje we właściwym folderze,
z właściwym powiązaniem w crm_files i we właściwej historii.
Uruchomienie: venv/bin/python -m unittest discover tests
"""
import io
import unittest
from unittest import mock

import services.crm_files as crm_files_service
from app import app

OFFER = {'id': 15, 'ref_number': 'Ref: 1/2026', 'name': 'Przetwórstwo owocowe — sprzedaż udziałów',
         'target_company_short_name': 'Owocex', 'target_company_name': 'Owocex sp. z o.o.'}


class MnaOfferFolderTest(unittest.TestCase):
    def test_folder_name_łączy_numer_i_firmę(self):
        self.assertEqual(crm_files_service.mna_offer_folder_name(OFFER), '1-2026 Owocex')

    def test_folder_name_bez_firmy_bierze_nazwę_oferty(self):
        offer = {'id': 9, 'ref_number': 'Ref: 2/2026', 'name': 'Przetwórstwo owocowe'}
        self.assertEqual(crm_files_service.mna_offer_folder_name(offer), '2-2026 Przetwórstwo owocowe')

    def test_ukośnik_w_numerze_nie_tworzy_podfolderu(self):
        """Drive traktuje '/' jako separator ścieżki, a numery ofert mają format 1/2026."""
        self.assertNotIn('/', crm_files_service.mna_offer_folder_name(OFFER))

    def test_folder_name_bez_numeru_i_nazwy(self):
        self.assertEqual(crm_files_service.mna_offer_folder_name({'id': 9, 'ref_number': None, 'name': ''}),
                         'Oferta 9')

    def test_folder_name_sama_nazwa(self):
        self.assertEqual(crm_files_service.mna_offer_folder_name({'id': 9, 'name': 'Hotel nad morzem'}),
                         'Hotel nad morzem')

    def test_drive_path(self):
        client = mock.Mock()
        client.find_or_create_folder.side_effect = ['offers', 'offer', 'files']
        self.assertEqual(crm_files_service.mna_offer_files_folder_id(client, 'root', OFFER), 'files')
        self.assertEqual([c.args for c in client.find_or_create_folder.call_args_list],
                         [('Oferty M&A', 'root'), ('1-2026 Owocex', 'offers'), ('pliki', 'offer')])

    def test_oferty_nie_mieszają_się_z_dealami(self):
        """Gdyby oba trafiały do 'Deale M&A', teaser oferty wylądowałby w folderze deala."""
        self.assertNotEqual(crm_files_service.MNA_OFFERS_FOLDER, crm_files_service.MNA_DEALS_FOLDER)


class UploadMnaOfferFileTest(unittest.TestCase):
    def setUp(self):
        client = mock.Mock()
        client.find_or_create_folder.side_effect = ['offers', 'offer', 'files']
        client.upload_file.return_value = {'id': 'drv77'}
        patches = [
            mock.patch.object(crm_files_service, 'drive_client', return_value=(client, 'root')),
            mock.patch.object(crm_files_service, 'add_file', return_value=77),
            mock.patch.object(crm_files_service, 'log_history'),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.drive = client

    def test_zapisuje_powiązanie_z_ofertą(self):
        """Plik oferty nie może wylądować z pustymi powiązaniami — wtedy nie widać go nigdzie."""
        file_id = crm_files_service.upload_mna_offer_file(OFFER, 'teaser.pdf', b'PDF', 1)
        self.assertEqual(file_id, 77)
        self.drive.upload_file.assert_called_once_with('teaser.pdf', 'application/pdf', b'PDF', 'files')
        self.assertEqual(crm_files_service.add_file.call_args.kwargs['mna_offer_id'], 15)

    def test_wpis_w_historii_oferty(self):
        crm_files_service.upload_mna_offer_file(OFFER, 'teaser.pdf', b'PDF', 1)
        args = crm_files_service.log_history.call_args.args
        self.assertEqual(args[:2], ('mna_offer', 15))
        self.assertIn('teaser.pdf', args[4])

    def test_odrzuca_nieobsługiwany_format(self):
        with self.assertRaises(ValueError):
            crm_files_service.upload_mna_offer_file(OFFER, 'wirus.exe', b'x', 1)
        crm_files_service.add_file.assert_not_called()


class OfferUploadEndpointTest(unittest.TestCase):
    """Endpoint /api/crm/files/upload obsługuje firmę, deala i ofertę jedną ścieżką —
    testy pilnują, żeby oferta nie trafiła do gałęzi firmy (i odwrotnie)."""

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
        patches = [
            mock.patch('models.crm_mna_offer.get_mna_offer_by_id',
                       side_effect=lambda oid: OFFER if oid == 15 else None),
            mock.patch('services.crm_files.upload_mna_offer_file', return_value=77),
            mock.patch('services.crm_files.upload_mna_deal_file', return_value=78),
        ]
        self.offer_getter, self.upload_offer, self.upload_deal = (p.start() for p in patches)
        for p in patches:
            self.addCleanup(p.stop)

    def post(self, data, file_name='teaser.pdf'):
        payload = dict(data)
        payload['files'] = (io.BytesIO(b'PDF'), file_name, 'application/pdf')
        return self.client.post('/api/crm/files/upload', data=payload,
                                content_type='multipart/form-data').get_json()

    def test_upload_do_oferty(self):
        self.assertEqual(self.post({'mna_offer_id': '15'}),
                         {'status': 'ok', 'saved': 1, 'rejected': [], 'message': 'Dodano 1 plik.'})
        self.upload_offer.assert_called_once_with(OFFER, 'teaser.pdf', b'PDF', 1)
        self.upload_deal.assert_not_called()

    def test_nieznana_oferta(self):
        resp = self.post({'mna_offer_id': '99'})
        self.assertEqual(resp['status'], 'error')
        self.assertIn('Oferta M&A nie istnieje', resp['message'])
        self.upload_offer.assert_not_called()

    def test_odrzucony_format(self):
        resp = self.post({'mna_offer_id': '15'}, file_name='wirus.exe')
        self.assertEqual(resp['status'], 'error')
        self.assertIn('Niedozwolony format', resp['message'])
        self.upload_offer.assert_not_called()

    def test_brak_encji(self):
        resp = self.post({})
        self.assertEqual(resp['status'], 'error')
        self.assertIn('oferty M&A', resp['message'])


if __name__ == '__main__':
    unittest.main()
