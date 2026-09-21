"""Testy narzędzi MCP do plików deali M&A — Drive i baza są zamockowane.

Uruchomienie: venv/bin/python -m unittest discover tests
"""
import base64
import unittest
from unittest import mock

import mcp_server
import services.crm_files as crm_files_service


class MnaDealFileToolsTest(unittest.TestCase):
    def setUp(self):
        self.deal = {"id": 3, "name": "Sprzedaż firmy Gomex", "offer_company_name": "Gomex"}
        self.files = {
            10: {"id": 10, "file_name": "nda.pdf", "drive_file_id": "drv10", "mna_deal_id": 3,
                 "mime_type": "application/pdf", "file_size": 100, "company_id": None},
            11: {"id": 11, "file_name": "umowa.pdf", "drive_file_id": "drv11", "mna_deal_id": None,
                 "mime_type": "application/pdf", "file_size": 100, "company_id": 7},
        }
        patches = [
            mock.patch.object(mcp_server.mna_deal, "get_mna_deal_by_id",
                              side_effect=lambda did: self.deal if did == 3 else None),
            mock.patch.object(mcp_server.crm_file, "get_file_by_id", side_effect=self.files.get),
            mock.patch.object(mcp_server.crm_file, "delete_file"),
            mock.patch.object(mcp_server.crm_file, "rename_file"),
            mock.patch.object(mcp_server.crm_notes, "log_history"),
            mock.patch.object(crm_files_service, "rename_drive_file"),
            mock.patch.object(crm_files_service, "delete_drive_file", return_value=None),
            mock.patch.object(crm_files_service, "upload_mna_deal_file", return_value=10),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def assertRejected(self, fn, message_part, **kwargs):
        with self.assertRaises(ValueError) as ctx:
            fn(**kwargs)
        self.assertIn(message_part, str(ctx.exception))
        crm_files_service.upload_mna_deal_file.assert_not_called()
        crm_files_service.rename_drive_file.assert_not_called()
        crm_files_service.delete_drive_file.assert_not_called()
        mcp_server.crm_file.delete_file.assert_not_called()
        mcp_server.crm_file.rename_file.assert_not_called()

    # struktura folderów

    def test_folder_name_from_offer_company(self):
        self.assertEqual(crm_files_service.mna_deal_folder_name(self.deal), "Gomex")

    def test_folder_name_falls_back_to_deal_name(self):
        self.assertEqual(
            crm_files_service.mna_deal_folder_name({"name": "Deal bez oferty", "offer_company_name": None}),
            "Deal bez oferty")

    def test_drive_path(self):
        client = mock.Mock()
        client.find_or_create_folder.side_effect = ["deals", "company", "files"]
        self.assertEqual(crm_files_service.mna_deal_files_folder_id(client, "root", self.deal), "files")
        self.assertEqual([c.args for c in client.find_or_create_folder.call_args_list],
                         [("Deale M&A", "root"), ("Gomex", "deals"), ("pliki", "company")])

    # upload

    def test_upload_rejects_unsupported_extension(self):
        self.assertRejected(mcp_server.upload_mna_deal_file, "Niedozwolony format",
                            deal_id=3, file_name="wirus.exe", content_base64="AA==")

    def test_upload_rejects_invalid_base64(self):
        self.assertRejected(mcp_server.upload_mna_deal_file, "poprawnym base64",
                            deal_id=3, file_name="nda.pdf", content_base64="to nie base64!!")

    def test_upload_rejects_empty_content(self):
        self.assertRejected(mcp_server.upload_mna_deal_file, "Pusty plik",
                            deal_id=3, file_name="nda.pdf", content_base64="")

    def test_upload_rejects_unknown_deal(self):
        self.assertRejected(mcp_server.upload_mna_deal_file, "Nie znaleziono deala M&A o id=99",
                            deal_id=99, file_name="nda.pdf",
                            content_base64=base64.b64encode(b"x").decode())

    def test_upload_passes_decoded_content(self):
        mcp_server.upload_mna_deal_file(deal_id=3, file_name="nda.pdf",
                                        content_base64=base64.b64encode(b"PDF-bytes").decode())
        crm_files_service.upload_mna_deal_file.assert_called_once_with(
            self.deal, "nda.pdf", b"PDF-bytes", mcp_server._mcp_user_id())

    # rename / delete

    def test_tools_reject_company_file(self):
        self.assertRejected(mcp_server.delete_mna_deal_file, "nie należy do deala M&A", file_id=11)
        self.assertRejected(mcp_server.rename_mna_deal_file, "nie należy do deala M&A",
                            file_id=11, file_name="inna.pdf")

    def test_tools_reject_missing_file(self):
        self.assertRejected(mcp_server.delete_mna_deal_file, "Nie znaleziono pliku o id=999", file_id=999)

    def test_rename_keeps_extension(self):
        self.assertRejected(mcp_server.rename_mna_deal_file, "Nie zmieniaj rozszerzenia",
                            file_id=10, file_name="nda.docx")

    def test_rename_updates_drive_and_db(self):
        mcp_server.rename_mna_deal_file(file_id=10, file_name="NDA Gomex.pdf")
        crm_files_service.rename_drive_file.assert_called_once_with("drv10", "NDA Gomex.pdf")
        mcp_server.crm_file.rename_file.assert_called_once_with(10, "NDA Gomex.pdf")

    def test_delete_removes_from_drive_and_db(self):
        result = mcp_server.delete_mna_deal_file(file_id=10)
        crm_files_service.delete_drive_file.assert_called_once_with("drv10")
        mcp_server.crm_file.delete_file.assert_called_once_with(10)
        self.assertTrue(result["deleted"])
        self.assertNotIn("drive_warning", result)

    def test_delete_warns_when_drive_fails(self):
        crm_files_service.delete_drive_file.return_value = "403 Forbidden"
        result = mcp_server.delete_mna_deal_file(file_id=10)
        mcp_server.crm_file.delete_file.assert_called_once_with(10)
        self.assertIn("403 Forbidden", result["drive_warning"])


if __name__ == "__main__":
    unittest.main()
