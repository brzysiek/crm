import csv
import hashlib
import io
import json
import re
from datetime import datetime


def _stable_hash(parts: list) -> str:
    """MD5 z listy stringów po normalizacji whitespace."""
    normalized = '|'.join(re.sub(r'\s+', ' ', str(p)).strip() for p in parts)
    return hashlib.md5(normalized.encode('utf-8')).hexdigest()[:16]


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
            # Hash ze stabilnych pól (raw string kwoty, nie float)
            transaction_id = 'uc_' + _stable_hash(['uc', date_str, line[10].strip(), line[8].strip()])

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

        # Hash z raw amount stringa (nie float) i znormalizowanego opisu
        transaction_id = 'mb_' + _stable_hash(['mb', date_str, amount_raw, description[:60]])

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


def parse_alior(content: str) -> list[dict]:
    """
    Format Alior Bank (separator ;, cp1250):
    Wiersz 1: metadane (Kryteria transakcji…) — pomijamy
    Wiersz 2: nagłówki kolumn
    Wiersze 3+: dane

    Kolumny:
    Data transakcji; Data księgowania; Nazwa nadawcy; Nazwa odbiorcy;
    Szczegóły transakcji; Kwota operacji; Waluta operacji;
    Kwota w walucie rachunku; Waluta rachunku;
    Numer rachunku nadawcy; Numer rachunku odbiorcy

    amount           = Kwota w walucie rachunku (zawsze PLN)
    orig_amount      = Kwota operacji (jeśli waluta != PLN)
    orig_currency    = Waluta operacji (jeśli != PLN, else None)
    """
    rows = []
    lines = content.splitlines()

    # Pomiń wiersz z metadanymi i nagłówek — szukamy wiersza z "Data transakcji"
    data_start = None
    for i, line in enumerate(lines):
        if line.strip().startswith('Data transakcji'):
            data_start = i + 1
            break
    if data_start is None:
        return rows

    def _parse_amount(s: str) -> float:
        return float(s.strip().replace('\xa0', '').replace(' ', '').replace(',', '.'))

    for raw_line in lines[data_start:]:
        stripped = raw_line.strip()
        if not stripped:
            continue

        parts = stripped.split(';')
        if len(parts) < 9:
            continue

        date_raw        = parts[0].strip()   # DD-MM-YYYY
        sender          = parts[2].strip()
        recipient       = parts[3].strip()
        details         = parts[4].strip()
        orig_amount_raw = parts[5].strip()   # kwota w walucie operacji
        orig_curr       = parts[6].strip()   # waluta operacji
        pln_amount_raw  = parts[7].strip()   # kwota w PLN
        sender_acc      = parts[9].strip() if len(parts) > 9 else ''
        recip_acc       = parts[10].strip() if len(parts) > 10 else ''

        # Konwersja daty DD-MM-YYYY → YYYY-MM-DD
        try:
            d, m, y = date_raw.split('-')
            date_str = f'{y}-{m}-{d}'
        except Exception:
            continue

        try:
            pln_amount = _parse_amount(pln_amount_raw)
        except ValueError:
            continue

        try:
            orig_amount_val = _parse_amount(orig_amount_raw)
        except ValueError:
            orig_amount_val = None

        # Waluta oryginalna (None gdy PLN)
        orig_currency = orig_curr if orig_curr and orig_curr != 'PLN' else None
        if orig_currency is None:
            orig_amount_val = None  # nie przechowuj duplikatu

        # Kontrahent: dla debetu — odbiorca, dla kredytu — nadawca
        counterparty = (recipient or sender or details)[:256]

        # Opis: szczegóły + ewentualnie nazwa kontrahenta
        description = details or (recipient if pln_amount < 0 else sender)

        # ID transakcji: hash ze stabilnych pól
        txn_id = 'alior_' + _stable_hash([
            'alior', date_str, orig_amount_raw, pln_amount_raw, details[:60],
            sender_acc[:20], recip_acc[:20],
        ])

        rows.append({
            'bank':           'alior',
            'transaction_id': txn_id,
            'date':           date_str,
            'description':    description,
            'counterparty':   counterparty,
            'amount':         pln_amount,       # zawsze PLN
            'currency':       'PLN',
            'orig_amount':    orig_amount_val,
            'orig_currency':  orig_currency,
            'category':       '',
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
    elif bank_type == 'alior':
        return parse_alior(content)
    return []
