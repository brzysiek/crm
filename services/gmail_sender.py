"""Gmail API client — wysyłka "w imieniu" skrzynki Workspace przez domain-wide
delegation (patrz services/google_auth.py::get_service_account_token, param
`subject`). Wymaga w Workspace Admin Console nadania kontu usługi scope'u
`gmail.send` (Security → API Controls → Domain-wide Delegation).
"""
import base64
import json
from email.message import EmailMessage

import requests

from services.google_auth import get_service_account_token

TIMEOUT = 20
GMAIL_SEND_SCOPE = 'https://www.googleapis.com/auth/gmail.send'
GMAIL_API = 'https://gmail.googleapis.com/gmail/v1'


def _raise_for_status(resp: requests.Response) -> None:
    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        raise requests.HTTPError(f'{e} — treść odpowiedzi: {resp.text[:500]}', response=resp) from None


def build_raw_message(sender_email: str, to: str, subject: str, body_text: str, unsubscribe_url: str) -> str:
    msg = EmailMessage()
    msg['From'] = sender_email
    msg['To'] = to
    msg['Subject'] = subject
    msg['List-Unsubscribe'] = f'<{unsubscribe_url}>, <mailto:{sender_email}?subject=unsubscribe>'
    msg['List-Unsubscribe-Post'] = 'List-Unsubscribe=One-Click'

    msg.set_content(f'{body_text}\n\n—\nWypisz się z tej listy: {unsubscribe_url}')
    html_body = body_text.replace('\n', '<br>')
    msg.add_alternative(
        f'<html><body><p>{html_body}</p>'
        f'<p style="color:#888;font-size:12px;margin-top:24px;">'
        f'<a href="{unsubscribe_url}">Wypisz się z tej listy</a></p>'
        f'</body></html>',
        subtype='html',
    )

    return base64.urlsafe_b64encode(msg.as_bytes()).decode()


class GmailSender:
    def __init__(self, api_token: str, sender_email: str):
        token_str = api_token.strip()
        if not token_str.startswith('{'):
            raise ValueError(
                'Wysyłka email wymaga konta usługi (service account JSON) z nadaną delegacją domenową.'
            )
        self._sa_json = json.loads(token_str)
        self.sender_email = sender_email

    def _auth_headers(self) -> dict:
        token = get_service_account_token(self._sa_json, GMAIL_SEND_SCOPE, subject=self.sender_email)
        return {'Authorization': f'Bearer {token}'}

    def send(self, to: str, subject: str, body_text: str, unsubscribe_url: str) -> str:
        """Wysyła wiadomość, zwraca Gmail message id."""
        raw = build_raw_message(self.sender_email, to, subject, body_text, unsubscribe_url)
        resp = requests.post(
            f'{GMAIL_API}/users/me/messages/send',
            headers={**self._auth_headers(), 'Content-Type': 'application/json'},
            json={'raw': raw},
            timeout=TIMEOUT,
        )
        _raise_for_status(resp)
        return resp.json()['id']
