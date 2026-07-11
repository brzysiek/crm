"""Google Drive API client.

Supports two authentication modes:
- Service account JSON  → if api_token starts with '{'
- Simple API key        → otherwise (pass as ?key= query param)

Service account uses JWT-based OAuth2 (no extra packages — uses `cryptography`
which is already in requirements.txt).
"""
import json
import uuid
from typing import Optional

import requests

from services.google_auth import get_service_account_token

TIMEOUT = 20

DRIVE_SCOPE = 'https://www.googleapis.com/auth/drive'


def _raise_for_status(resp: requests.Response) -> None:
    """Jak resp.raise_for_status(), ale dołącza treść odpowiedzi Google (zawiera
    dokładny powód błędu, np. 'Drive API has not been used...' albo
    'insufficientFilePermissions') — sam kod statusu (403 Forbidden) tego nie mówi."""
    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        raise requests.HTTPError(f'{e} — treść odpowiedzi: {resp.text[:500]}', response=resp) from None


class GoogleDriveClient:
    DRIVE_API = 'https://www.googleapis.com/drive/v3'

    def __init__(self, api_token: str, root_folder_id: str):
        self.root_folder_id = root_folder_id.strip()
        token_str = api_token.strip()

        if token_str.startswith('{'):
            # Service account JSON
            self._sa_json = json.loads(token_str)
            self._api_key: Optional[str] = None
        else:
            self._sa_json = None
            self._api_key = token_str

    def _auth_headers(self) -> dict:
        if self._sa_json:
            token = get_service_account_token(self._sa_json, DRIVE_SCOPE)
            return {'Authorization': f'Bearer {token}'}
        return {}

    def _auth_params(self) -> dict:
        if self._api_key:
            return {'key': self._api_key}
        return {}

    def _get(self, path: str, params: dict = None) -> requests.Response:
        url = f'{self.DRIVE_API}{path}'
        # supportsAllDrives/includeItemsFromAllDrives: wymagane, żeby pliki/foldery
        # leżące na Dysku współdzielonym (Shared Drive) w ogóle pojawiały się w wynikach.
        p = {
            **self._auth_params(),
            'supportsAllDrives': 'true',
            'includeItemsFromAllDrives': 'true',
            **(params or {}),
        }
        resp = requests.get(url, headers=self._auth_headers(), params=p, timeout=TIMEOUT)
        _raise_for_status(resp)
        return resp

    def list_subfolders(self, folder_id: str) -> list[dict]:
        """Return immediate subfolders of folder_id sorted by name."""
        q = (
            f"'{folder_id}' in parents "
            "and mimeType = 'application/vnd.google-apps.folder' "
            "and trashed = false"
        )
        params = {
            'q':        q,
            'fields':   'files(id,name,modifiedTime)',
            'orderBy':  'name',
            'pageSize': 200,
        }
        resp = self._get('/files', params)
        return resp.json().get('files', [])

    def list_pdf_files(self, folder_id: str) -> list[dict]:
        """Return all PDF files recursively under folder_id."""
        results = []
        self._collect_pdfs(folder_id, results)
        return results

    def _collect_pdfs(self, folder_id: str, out: list) -> None:
        q = (
            f"'{folder_id}' in parents "
            "and trashed = false"
        )
        params = {
            'q':        q,
            'fields':   'files(id,name,mimeType,modifiedTime,size)',
            'pageSize': 500,
        }
        resp = self._get('/files', params)
        items = resp.json().get('files', [])
        for item in items:
            mime = item.get('mimeType', '')
            if mime == 'application/vnd.google-apps.folder':
                self._collect_pdfs(item['id'], out)
            elif mime == 'application/pdf' or item.get('name', '').lower().endswith('.pdf'):
                out.append(item)

    def download_file(self, file_id: str) -> bytes:
        """Download the binary content of a file."""
        url = f'{self.DRIVE_API}/files/{file_id}'
        p = {**self._auth_params(), 'alt': 'media', 'supportsAllDrives': 'true'}
        resp = requests.get(url, headers=self._auth_headers(), params=p, timeout=60)
        _raise_for_status(resp)
        return resp.content

    def _require_write_capable(self) -> None:
        if self._api_key:
            raise ValueError(
                'Zapis do Google Drive wymaga konta usługi (service account JSON), '
                'prosty klucz API nie pozwala na zapis.'
            )

    def find_folder(self, name: str, parent_id: str) -> Optional[str]:
        """Find an immediate subfolder of parent_id by exact name. Returns its id or None."""
        safe_name = name.replace("\\", "\\\\").replace("'", "\\'")
        q = (
            f"'{parent_id}' in parents "
            "and mimeType = 'application/vnd.google-apps.folder' "
            f"and name = '{safe_name}' and trashed = false"
        )
        params = {'q': q, 'fields': 'files(id,name)', 'pageSize': 1}
        resp = self._get('/files', params)
        files = resp.json().get('files', [])
        return files[0]['id'] if files else None

    def create_folder(self, name: str, parent_id: str) -> str:
        self._require_write_capable()
        body = {
            'name': name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id],
        }
        resp = requests.post(
            f'{self.DRIVE_API}/files',
            headers={**self._auth_headers(), 'Content-Type': 'application/json'},
            params={**self._auth_params(), 'supportsAllDrives': 'true'},
            json=body,
            timeout=TIMEOUT,
        )
        _raise_for_status(resp)
        return resp.json()['id']

    def find_or_create_folder(self, name: str, parent_id: str) -> str:
        existing = self.find_folder(name, parent_id)
        if existing:
            return existing
        return self.create_folder(name, parent_id)

    def upload_file(self, name: str, mime_type: str, content: bytes, parent_id: str) -> dict:
        self._require_write_capable()
        metadata = {'name': name, 'parents': [parent_id]}
        boundary = uuid.uuid4().hex
        body = (
            f'--{boundary}\r\n'
            'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            f'{json.dumps(metadata)}\r\n'
            f'--{boundary}\r\n'
            f'Content-Type: {mime_type}\r\n\r\n'
        ).encode() + content + f'\r\n--{boundary}--'.encode()
        headers = {
            **self._auth_headers(),
            'Content-Type': f'multipart/related; boundary={boundary}',
        }
        resp = requests.post(
            'https://www.googleapis.com/upload/drive/v3/files',
            headers=headers,
            params={**self._auth_params(), 'uploadType': 'multipart', 'supportsAllDrives': 'true'},
            data=body,
            timeout=60,
        )
        _raise_for_status(resp)
        return resp.json()

    def delete_file(self, file_id: str) -> None:
        self._require_write_capable()
        resp = requests.delete(
            f'{self.DRIVE_API}/files/{file_id}',
            headers=self._auth_headers(),
            params={**self._auth_params(), 'supportsAllDrives': 'true'},
            timeout=TIMEOUT,
        )
        _raise_for_status(resp)
