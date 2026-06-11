import csv
import hashlib
import io
import json
import re
from datetime import datetime


def parse_unicredit(content: str) -> list[dict]:
    """
    Format UniCredit (brak nagłówka, separator ,):
    datetime, account_holder, acc_no, acc_iban, counterparty_name, counterparty_iban,
    counterparty_alias, reference, description, transaction_id(UUID),
    amount, currency, fee, fee_currency, unknown, balance
    """
    rows = []
    reader = csv.reader(io.StringIO(content))
    for line in reader:
        if len(line) < 11:
            continue
        try:
            dt = datetime.fromisoformat(line[0].strip().replace('Z', '+00:00'))
            date_str = dt.strftime('%Y-%m-%d')
        except Exception:
            continue
        try:
            amount = float(line[10].strip())
        except (ValueError, IndexError):
            continue

        transaction_id = line[9].strip() if len(line) > 9 else ''
        if not transaction_id:
            src = f"uc|{date_str}|{amount}|{line[8].strip()[:40]}"
            transaction_id = 'uc_' + hashlib.md5(src.encode()).hexdigest()[:16]

        counterparty = (line[4].strip() or line[6].strip())[:256]
        description  = line[8].strip().strip('"')
        currency     = line[11].strip() if len(line) > 11 else 'PLN'
        try:
            balance = float(line[15].strip()) if len(line) > 15 else None
        except (ValueError, IndexError):
            balance = None

        rows.append({
            'bank':           'unicredit',
            'transaction_id': transaction_id,
            'date':           date_str,
            'description':    description,
            'counterparty':   counterparty,
            'amount':         amount,
            'currency':       currency,
            'category':       '',
            'balance':        balance,
            'raw_data':       json.dumps(line, ensure_ascii=False),
        })
    return rows


def parse_mbank(content: str) -> list[dict]:
    """
    Format mBank (separator ;):
    Metadane na początku, nagłówek: #Data operacji;#Opis operacji;#Rachunek;#Kategoria;#Kwota;
    Dane: date;description;account;category;amount PLN;
    """
    rows = []
    lines = content.splitlines()

    # Znajdź wiersz nagłówka danych
    header_idx = None
    for i, line in enumerate(lines):
        if '#Data operacji' in line:
            header_idx = i
            break
    if header_idx is None:
        return rows

    for raw_line in lines[header_idx + 1:]:
        stripped = raw_line.strip()
        if not stripped or stripped.startswith('#'):
            continue

        parts = stripped.split(';')
        if len(parts) < 5:
            continue

        date_str = parts[0].strip().strip('"')
        if not date_str or not date_str[0].isdigit():
            continue

        description = parts[1].strip().strip('"').replace('\xa0', ' ')
        description = re.sub(r'\s+', ' ', description).strip()

        category = parts[3].strip().strip('"') if len(parts) > 3 else ''

        amount_raw = (parts[4].strip().strip('"') if len(parts) > 4 else '').replace('\xa0', '')
        amount_raw = re.sub(r'\s+', '', amount_raw).replace('PLN', '').replace(',', '.')
        try:
            amount = float(amount_raw)
        except ValueError:
            continue

        src = f"mb|{date_str}|{amount}|{description[:50]}"
        transaction_id = 'mb_' + hashlib.md5(src.encode()).hexdigest()[:16]

        # Próba wyciągnięcia nazwy kontrahenta z opisu (pierwsza linia/segment)
        counterparty = description.split(',')[0].strip()[:256]

        rows.append({
            'bank':           'mbank',
            'transaction_id': transaction_id,
            'date':           date_str,
            'description':    description,
            'counterparty':   counterparty,
            'amount':         amount,
            'currency':       'PLN',
            'category':       category,
            'balance':        None,
            'raw_data':       json.dumps(parts, ensure_ascii=False),
        })
    return rows


def parse_file(bank_type: str, content_bytes: bytes) -> list[dict]:
    """Próbuje UTF-8, przy błędzie cp1250."""
    try:
        content = content_bytes.decode('utf-8')
    except UnicodeDecodeError:
        content = content_bytes.decode('cp1250', errors='replace')

    if bank_type == 'unicredit':
        return parse_unicredit(content)
    elif bank_type == 'mbank':
        return parse_mbank(content)
    return []
