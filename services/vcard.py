"""Budowa wizytówki vCard 3.0 dla kontaktu CRM (do importu np. w Kontaktach iPhone)."""
import html
import re
import unicodedata


def _escape(value: str) -> str:
    return (value or '').replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,').replace('\n', '\\n')


def build_vcard(contact: dict) -> str:
    first = contact.get('first_name') or ''
    last = contact.get('last_name') or ''
    company = contact.get('company_short_name') or contact.get('company_name') or ''
    phone = contact.get('phone') or ''
    email = contact.get('email') or ''
    description = contact.get('description') or ''
    website = contact.get('company_website') or ''
    if website and not re.match(r'^https?://', website, re.IGNORECASE):
        website = 'https://' + website

    lines = [
        'BEGIN:VCARD',
        'VERSION:3.0',
        f'N:{_escape(last)};{_escape(first)};;;',
        f'FN:{_escape((first + " " + last).strip())}',
    ]
    if company:
        lines.append(f'ORG:{_escape(company)}')
    if phone:
        lines.append(f'TEL;TYPE=CELL:{_escape(phone)}')
    if email:
        lines.append(f'EMAIL;TYPE=INTERNET:{_escape(email)}')
    if website:
        lines.append(f'URL:{_escape(website)}')
    if description:
        lines.append(f'NOTE:{_escape(description)}')
    lines.append('END:VCARD')

    return '\r\n'.join(lines) + '\r\n'


def send_vcard_email(contact: dict, to_email: str) -> None:
    """Wysyła wizytówkę kontaktu (.vcf) mailem na wskazany adres — używane po
    dodaniu/edycji kontaktu, gdy w Ustawieniach → CRM włączona jest odpowiednia
    automatyzacja, żeby móc od razu otworzyć załącznik na telefonie i zapisać kontakt."""
    from models.settings import get_setting
    from services.gmail_sender import GmailSender

    sender_email = get_setting('gmail_sender_email', '')
    api_token = get_setting('google_drive_api_token', '')
    if not sender_email or not api_token:
        raise RuntimeError('Brak konfiguracji wysyłki e-mail (Ustawienia → Email).')
    sender_name = get_setting('gmail_sender_name', '') or None

    name = f"{contact.get('first_name') or ''} {contact.get('last_name') or ''}".strip() or 'Kontakt'
    company = contact.get('company_short_name') or contact.get('company_name')
    ascii_name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
    filename = re.sub(r'[^A-Za-z0-9_-]+', '_', ascii_name).strip('_') or 'kontakt'

    body_html = f'<p>W załączniku wizytówka kontaktu <strong>{html.escape(name)}</strong>'
    if company:
        body_html += f' ({html.escape(company)})'
    body_html += '.</p><p>Otwórz załącznik na telefonie, aby zapisać kontakt.</p>'

    GmailSender(api_token, sender_email, sender_name).send(
        to=to_email,
        subject=f'Wizytówka: {name}',
        body_html=body_html,
        attachments=[{
            'mime_type': 'text/vcard',
            'filename': f'{filename}.vcf',
            'data': build_vcard(contact).encode('utf-8'),
        }],
    )
