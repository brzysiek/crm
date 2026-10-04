"""Jedno wyjście na pojedynczego maila: konfigurację nadawcy czyta z ustawień, wysyłkę zleca
Gmail API (services/gmail_sender.py).

Powstało, bo ten sam kawałek — „weź nadawcę i token z ustawień, sprawdź, czy są, zbuduj
GmailSender” — zaczynał się powtarzać przy każdej nowej wysyłce (wizytówki, kody logowania,
reset hasła). Kampanie mailowe mają własną drogę: tam liczą się limity i partie, nie jeden list.
"""
from models.settings import get_setting

SETUP_HINT = 'Brak konfiguracji wysyłki e-mail (Ustawienia → Email).'


def _config() -> tuple[str, str, str | None]:
    sender_email = get_setting('gmail_sender_email', '')
    api_token = get_setting('google_drive_api_token', '')
    if not sender_email or not api_token:
        raise RuntimeError(SETUP_HINT)
    return sender_email, api_token, get_setting('gmail_sender_name', '') or None


def is_configured() -> bool:
    return bool(get_setting('gmail_sender_email', '') and get_setting('google_drive_api_token', ''))


def send_email(to: str, subject: str, body_html: str, attachments: list[dict] | None = None) -> str:
    """Wysyła jedną wiadomość, zwraca id wiadomości w Gmailu. Rzuca RuntimeError, gdy wysyłka
    nie jest skonfigurowana — wołający ma wtedy powiedzieć o tym wprost, a nie udawać sukces."""
    from services.gmail_sender import GmailSender

    sender_email, api_token, sender_name = _config()
    return GmailSender(api_token, sender_email, sender_name).send(
        to=to, subject=subject, body_html=body_html, attachments=attachments)
