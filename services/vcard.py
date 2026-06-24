"""Budowa wizytówki vCard 3.0 dla kontaktu CRM (do importu np. w Kontaktach iPhone)."""
import re


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
