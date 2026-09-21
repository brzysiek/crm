"""Wspólna logika plików CRM na Google Drive — używana zarówno przez endpointy webowe
(app.py, routes/*), jak i przez serwer MCP.

Układ folderów na Drive:
  <folder CRM z Ustawień>/CRM/<firma>/pliki/…            — pliki firmy CRM (i jej kontaktów)
  <folder CRM z Ustawień>/Deale M&A/<firma>/pliki/…      — pliki deala M&A

Dla deala M&A „firma” to firma z powiązanej oferty M&A (sprzedawany podmiot); gdy deal nie ma
oferty ani firmy, folder nazywa się jak sam deal.
"""
from models.crm_file import ALLOWED_EXTENSIONS, add_file, delete_file, files_word  # noqa: F401
from models.crm_notes import log_history
from models.settings import get_setting
from services.gdrive import GoogleDriveClient
from services.images import resize_jpeg_if_needed

MNA_DEALS_FOLDER = 'Deale M&A'
FILES_SUBFOLDER = 'pliki'


class DriveNotConfigured(Exception):
    """Brak tokenu lub ID folderu CRM w Ustawieniach."""


def drive_client() -> tuple[GoogleDriveClient, str]:
    api_token = get_setting('google_drive_api_token', '')
    crm_root_id = get_setting('google_drive_crm_folder_id', '')
    if not api_token or not crm_root_id:
        raise DriveNotConfigured(
            'Skonfiguruj Google Drive w Ustawieniach (token oraz ID folderu CRM).'
        )
    return GoogleDriveClient(api_token, crm_root_id), crm_root_id


def file_extension(file_name: str) -> str:
    return file_name.rsplit('.', 1)[-1].lower() if file_name and '.' in file_name else ''


def mime_for(file_name: str) -> str:
    """Zwraca typ MIME po rozszerzeniu; podnosi ValueError dla nieobsługiwanych formatów."""
    ext = file_extension(file_name)
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f'Niedozwolony format pliku: {file_name}. '
            f"Obsługiwane: {', '.join(sorted(ALLOWED_EXTENSIONS)).upper()}."
        )
    return ALLOWED_EXTENSIONS[ext]


def mna_deal_folder_name(deal: dict) -> str:
    """Nazwa podfolderu dla deala M&A — firma z oferty, a w ostateczności nazwa deala."""
    return deal.get('offer_company_name') or deal['name']


def mna_deal_files_folder_id(client: GoogleDriveClient, crm_root_id: str, deal: dict) -> str:
    deals_folder_id = client.find_or_create_folder(MNA_DEALS_FOLDER, crm_root_id)
    company_folder_id = client.find_or_create_folder(mna_deal_folder_name(deal), deals_folder_id)
    return client.find_or_create_folder(FILES_SUBFOLDER, company_folder_id)


def upload_mna_deal_file(deal: dict, file_name: str, content: bytes, user_id: int | None) -> int:
    """Wrzuca plik do folderu deala M&A na Drive, zapisuje go w crm_files i w historii deala.
    Zwraca id nowego rekordu crm_files."""
    mime_type = mime_for(file_name)
    if file_extension(file_name) in ('jpg', 'jpeg'):
        content = resize_jpeg_if_needed(content)
    client, crm_root_id = drive_client()
    folder_id = mna_deal_files_folder_id(client, crm_root_id, deal)
    result = client.upload_file(file_name, mime_type, content, folder_id)
    file_id = add_file(None, None, file_name, result['id'], mime_type, len(content), user_id,
                       mna_deal_id=deal['id'])
    log_history('mna_deal', deal['id'], user_id, 'file', f'Dodano plik: {file_name}', file_id=file_id)
    return file_id


def delete_drive_file(drive_file_id: str) -> str | None:
    """Usuwa plik z Drive. Zwraca treść błędu, jeśli się nie udało — rekord w bazie usuwamy
    tak czy inaczej, żeby nie zostawiać wpisu bez możliwości usunięcia."""
    try:
        client, _ = drive_client()
        client.delete_file(drive_file_id)
        return None
    except Exception as e:
        return str(e)


def rename_drive_file(drive_file_id: str, file_name: str) -> None:
    client, _ = drive_client()
    client.rename_file(drive_file_id, file_name)
