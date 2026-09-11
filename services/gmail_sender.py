"""Gmail API client — wysyłka "w imieniu" skrzynki Workspace przez domain-wide
delegation (patrz services/google_auth.py::get_service_account_token, param
`subject`). Wymaga w Workspace Admin Console nadania kontu usługi scope'u
`gmail.send` (Security → API Controls → Domain-wide Delegation).
"""
import base64
import html as html_module
import json
import re
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid

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


UNSUB_PLACEHOLDER = '__UNSUBSCRIBE_URL__'


def _html_to_text(body_html: str) -> str:
    text = re.sub(r'(?is)<a\s[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', r'\2 (\1)', body_html)
    text = re.sub(r'(?i)<(br|/p|/div|/tr|/li)\s*/?>', '\n', text)
    text = re.sub(r'(?s)<[^>]+>', '', text)
    text = html_module.unescape(text)
    lines = [line.strip() for line in text.splitlines()]
    text = '\n'.join(lines)
    return re.sub(r'\n{3,}', '\n\n', text).strip()


def build_raw_message(sender_email: str, to: str, subject: str, body_html: str, unsubscribe_url: str | None = None,
                       attachments: list[dict] | None = None, sender_name: str | None = None) -> str:
    msg = EmailMessage()
    msg['From'] = formataddr((sender_name, sender_email)) if sender_name else sender_email
    msg['To'] = to
    msg['Subject'] = subject
    msg['Date'] = formatdate(localtime=True)
    msg['Message-ID'] = make_msgid(domain=sender_email.split('@')[-1])
    if unsubscribe_url:
        msg['List-Unsubscribe'] = f'<{unsubscribe_url}>, <mailto:{sender_email}?subject=unsubscribe>'
        msg['List-Unsubscribe-Post'] = 'List-Unsubscribe=One-Click'

    html_body = body_html.replace(UNSUB_PLACEHOLDER, unsubscribe_url) if unsubscribe_url and UNSUB_PLACEHOLDER in body_html else body_html
    msg.set_content(_html_to_text(html_body))
    msg.add_alternative(f'<html><body>{html_body}</body></html>', subtype='html')

    for att in (attachments or []):
        maintype, _, subtype = att['mime_type'].partition('/')
        msg.add_attachment(
            att['data'], maintype=maintype or 'application', subtype=subtype or 'octet-stream',
            filename=att['filename'],
        )

    return base64.urlsafe_b64encode(msg.as_bytes()).decode()


class GmailSender:
    def __init__(self, api_token: str, sender_email: str, sender_name: str | None = None):
        token_str = api_token.strip()
        if not token_str.startswith('{'):
            raise ValueError(
                'Wysyłka email wymaga konta usługi (service account JSON) z nadaną delegacją domenową.'
            )
        self._sa_json = json.loads(token_str)
        self.sender_email = sender_email
        self.sender_name = sender_name

    def _auth_headers(self) -> dict:
        token = get_service_account_token(self._sa_json, GMAIL_SEND_SCOPE, subject=self.sender_email)
        return {'Authorization': f'Bearer {token}'}

    def send(self, to: str, subject: str, body_html: str, unsubscribe_url: str | None = None,
              attachments: list[dict] | None = None) -> str:
        """Wysyła wiadomość, zwraca Gmail message id."""
        raw = build_raw_message(self.sender_email, to, subject, body_html, unsubscribe_url, attachments, self.sender_name)
        resp = requests.post(
            f'{GMAIL_API}/users/me/messages/send',
            headers={**self._auth_headers(), 'Content-Type': 'application/json'},
            json={'raw': raw},
            timeout=TIMEOUT,
        )
        _raise_for_status(resp)
        return resp.json()['id']
