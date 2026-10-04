"""Maile, które trzymają logowanie: kod drugiego składnika i link do ustawienia nowego hasła.

Obie wiadomości są celowo ubogie — żadnych obrazków i śledzenia, nazwa aplikacji, jedna
informacja i jedno wyjście. List o dostępie do konta ma wyglądać tak, żeby nie dało się go
pomylić z reklamą, i tak, żeby filtr antyspamowy nie miał o co zaczepić.
"""
import html

from models.auth_token import CODE_TTL_MINUTES, RESET_TTL_MINUTES
from services.mailer import send_email

GREEN = '#0D2820'
LIME = '#B5E619'
MUTED = '#878782'


def _shell(app_name: str, title: str, body: str) -> str:
    return (
        f'<div style="font-family:system-ui,-apple-system,\'Segoe UI\',sans-serif;'
        f'color:{GREEN};max-width:520px">'
        f'<p style="font-size:13px;letter-spacing:.08em;text-transform:uppercase;'
        f'color:{MUTED};margin:0 0 .4rem">{html.escape(app_name)}</p>'
        f'<h2 style="margin:0 0 1rem;font-size:20px;color:{GREEN}">{html.escape(title)}</h2>'
        f'{body}'
        f'<p style="margin:1.6rem 0 0;font-size:12px;color:{MUTED}">'
        f'Jeśli to nie Ty, zignoruj tę wiadomość — bez niej nic się nie wydarzy.</p>'
        f'</div>'
    )


def _app_name() -> str:
    from config import Config
    from models.settings import get_setting
    return get_setting('app_name') or Config.APP_NAME


def send_login_code(user: dict, code: str) -> None:
    app_name = _app_name()
    body = (
        f'<p style="margin:0 0 1rem">Kod do dokończenia logowania:</p>'
        f'<p style="font-size:30px;font-weight:700;letter-spacing:.32em;'
        f'background:{LIME};color:{GREEN};display:inline-block;'
        f'padding:.6rem 1.1rem;border-radius:10px;margin:0">{html.escape(code)}</p>'
        f'<p style="margin:1rem 0 0;font-size:13px;color:{MUTED}">'
        f'Kod jest ważny {CODE_TTL_MINUTES} minut i działa raz.</p>'
    )
    send_email(user['email'], f'{app_name}: kod logowania {code}',
               _shell(app_name, 'Kod logowania', body))


def send_password_reset(user: dict, reset_url: str) -> None:
    app_name = _app_name()
    safe_url = html.escape(reset_url, quote=True)
    hours = RESET_TTL_MINUTES // 60
    validity = f'{hours} godzinę' if hours == 1 else f'{RESET_TTL_MINUTES} minut'
    body = (
        f'<p style="margin:0 0 1.2rem">Ktoś poprosił o ustawienie nowego hasła do konta'
        f' <strong>{html.escape(user["username"])}</strong>.</p>'
        f'<p style="margin:0 0 1.2rem"><a href="{safe_url}" '
        f'style="background:{LIME};color:{GREEN};text-decoration:none;font-weight:600;'
        f'padding:.7rem 1.3rem;border-radius:10px;display:inline-block">Ustaw nowe hasło</a></p>'
        f'<p style="margin:0;font-size:13px;color:{MUTED}">Link jest ważny {validity} i działa raz.'
        f' Gdyby przycisk nie zadziałał, otwórz ten adres:<br>'
        f'<span style="word-break:break-all">{safe_url}</span></p>'
    )
    send_email(user['email'], f'{app_name}: ustawienie nowego hasła',
               _shell(app_name, 'Nowe hasło', body))
