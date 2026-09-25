"""Import wyciągów bankowych i dopasowywanie przelewów do dokumentów.

Parsery zwracają jeden, wspólny kształt wiersza (`external_id`, `booked_date`,
`amount`, `counterparty_name`, `counterparty_account`, `title`, …) — cała reszta
modułu nie wie, z jakiego banku przyszły dane. Nowy bank to jedna funkcja
`parse_*` i jeden wpis w `PARSERS`, bez dotykania dopasowywania.

Dopasowanie ma **jedną** implementację (`suggest_matches`) używaną i przez ekran
`/fin/bank`, i przez narzędzia MCP. Stary moduł miał trzy kopie scoringu, które
się rozjechały — to był główny powód, żeby napisać to od nowa.

Znak kwoty niesie kierunek: minus = wypływ (płacimy koszt), plus = wpływ (klient
płaci nam). Dzięki temu przelew nigdy nie zostanie podpowiedziany do dokumentu
z przeciwnej strony.
"""
import csv
import hashlib
import io
import json
import re
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

import models.fin_bank as fin_bank
from database import get_db
from models.fin_document import FINANCIAL_CLAUSE, NON_FINANCIAL_KINDS

AMOUNT_TOLERANCE = Decimal('0.02')     # grosz w jedną i drugą stronę
DATE_WINDOW = 45                       # dni wokół terminu/wystawienia, w których szukamy

BANK_LABELS = {'alior': 'Alior Bank', 'mbank': 'mBank', 'unicredit': 'UniCredit'}


class BankImportError(RuntimeError):
    pass


# ── narzędzia ────────────────────────────────────────────────────────────────

def _hash(parts: list) -> str:
    text = '|'.join(re.sub(r'\s+', ' ', str(p)).strip() for p in parts)
    return hashlib.md5(text.encode('utf-8')).hexdigest()[:16]


def _amount(text: str) -> Decimal:
    clean = (text or '').replace('\xa0', '').replace(' ', '').replace('PLN', '').replace(',', '.')
    try:
        return Decimal(clean).quantize(Decimal('0.01'))
    except (InvalidOperation, ValueError):
        raise ValueError(f'„{text}” to nie kwota')


def _squash(text: str) -> str:
    return re.sub(r'\s+', ' ', (text or '').replace('\xa0', ' ')).strip()


def normalize_tax_no(value) -> str:
    return re.sub(r'\D', '', str(value or ''))


def _number_key(value) -> str:
    """Numer faktury do porównań: bez spacji, wielkimi literami. „3/07/2026”
    w tytule przelewu bywa zapisane jako „FV 3/07/2026” albo „3 / 07 / 2026”."""
    return re.sub(r'\s+', '', str(value or '')).upper()


def _number_is_distinctive(number_key: str) -> bool:
    """Czy numer jest na tyle charakterystyczny, żeby jego obecność w tytule
    przelewu coś znaczyła. Cztery cyfry bez separatora — nie: „1026” siedzi
    w środku numeru „14803/1026/RM” i w połowie numerów rachunków. Numer
    z separatorem (3/05/2026) albo dłuższy (529091120526) — tak."""
    if len(number_key) < 4:
        return False
    if re.search(r'[^0-9A-ZĄĆĘŁŃÓŚŹŻ]', number_key):
        return True
    return len(number_key) >= 6


# ── parsery ──────────────────────────────────────────────────────────────────

def parse_alior(content: str) -> list[dict]:
    """Alior Bank, `Historia_Operacji_*.csv`, separator `;`, cp1250.

    Kolumny: Data transakcji; Data księgowania; Nazwa nadawcy; Nazwa odbiorcy;
    Szczegóły transakcji; Kwota operacji; Waluta operacji; Kwota w walucie
    rachunku; Waluta rachunku; Numer rachunku nadawcy; Numer rachunku odbiorcy.
    Kwotę bierzemy w walucie rachunku — to ta, która faktycznie ruszyła konto.
    """
    lines = content.splitlines()
    start = next((i + 1 for i, line in enumerate(lines)
                  if line.strip().startswith('Data transakcji')), None)
    if start is None:
        return []
    rows = []
    for line in lines[start:]:
        parts = line.strip().split(';')
        if len(parts) < 9 or not parts[0].strip():
            continue
        try:
            day, month, year = parts[0].strip().split('-')
            booked = f'{year}-{month}-{day}'
            datetime.strptime(booked, '%Y-%m-%d')
            amount = _amount(parts[7])
        except (ValueError, IndexError):
            continue
        sender, recipient, details = (_squash(parts[2]), _squash(parts[3]), _squash(parts[4]))
        sender_acc = _squash(parts[9]) if len(parts) > 9 else ''
        recipient_acc = _squash(parts[10]) if len(parts) > 10 else ''
        # Przy wypływie kontrahentem jest odbiorca, przy wpływie — nadawca.
        outgoing = amount < 0
        rows.append({
            'bank': 'alior',
            'external_id': 'alior_' + _hash(['alior', booked, parts[5], parts[7],
                                             details[:60], sender_acc[:20], recipient_acc[:20]]),
            'booked_date': booked,
            'amount': amount,
            'currency': (_squash(parts[8]) or 'PLN')[:3].upper(),
            'counterparty_name': ((recipient if outgoing else sender) or details)[:256],
            'counterparty_account': (recipient_acc if outgoing else sender_acc).replace(' ', '')[:64],
            'title': (details or recipient or sender)[:512],
            'raw_data': json.dumps(parts, ensure_ascii=False),
        })
    return rows


def parse_mbank(content: str) -> list[dict]:
    """mBank, `lista_operacji_*.csv`, separator `;`, nagłówek `#Data operacji`.
    Nazwy kontrahenta w osobnej kolumnie nie ma — zostaje opis operacji."""
    lines = content.splitlines()
    start = next((i + 1 for i, line in enumerate(lines) if '#Data operacji' in line), None)
    if start is None:
        return []
    rows = []
    for line in lines[start:]:
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        parts = stripped.split(';')
        if len(parts) < 5:
            continue
        booked = parts[0].strip().strip('"')
        if not booked[:1].isdigit():
            continue
        booked = booked.replace('.', '-')
        try:
            datetime.strptime(booked, '%Y-%m-%d')
            amount = _amount(parts[4].strip().strip('"'))
        except ValueError:
            continue
        title = _squash(parts[1].strip('"'))
        rows.append({
            'bank': 'mbank',
            'external_id': 'mbank_' + _hash(['mbank', booked, parts[4], title[:60]]),
            'booked_date': booked,
            'amount': amount,
            'currency': 'PLN',
            'counterparty_name': title.split(',')[0][:256],
            'counterparty_account': _squash(parts[2].strip('"')).replace(' ', '')[:64] if len(parts) > 2 else '',
            'title': title[:512],
            'raw_data': json.dumps(parts, ensure_ascii=False),
        })
    return rows


def parse_unicredit(content: str) -> list[dict]:
    """UniCredit, CSV bez nagłówka, separator `,`. Kolumna 9 to UUID operacji —
    naturalny `external_id`, więc nie trzeba hashować."""
    rows = []
    for parts in csv.reader(io.StringIO(content)):
        if len(parts) < 12:
            continue
        try:
            stamp = datetime.fromisoformat(parts[0].strip().replace('Z', '+00:00'))
            amount = _amount(parts[10])
        except (ValueError, IndexError):
            continue
        booked = stamp.strftime('%Y-%m-%d')
        uuid_col = _squash(parts[9])
        counterparty = _squash(parts[4]) or _squash(parts[6])
        rows.append({
            'bank': 'unicredit',
            'external_id': (f'unicredit_{uuid_col}' if uuid_col
                            else 'unicredit_' + _hash(['uc', booked, parts[10], parts[8]]))[:64],
            'booked_date': booked,
            'amount': amount,
            'currency': (_squash(parts[11]) or 'PLN')[:3].upper(),
            'counterparty_name': counterparty[:256],
            'counterparty_account': _squash(parts[5]).replace(' ', '')[:64],
            'title': (_squash(parts[8].strip('"')) or counterparty)[:512],
            'raw_data': json.dumps(parts, ensure_ascii=False),
        })
    return rows


PARSERS = {'alior': parse_alior, 'mbank': parse_mbank, 'unicredit': parse_unicredit}


def detect_bank(content: str) -> str:
    """Rozpoznanie formatu po treści pliku — żeby nikt nie musiał wybierać banku
    z listy i mylić się przy tym."""
    head = content[:4000]
    if 'Data transakcji' in head and 'Kwota w walucie rachunku' in head:
        return 'alior'
    if '#Data operacji' in head or 'mBank S.A.' in head:
        return 'mbank'
    first = head.splitlines()[0] if head.splitlines() else ''
    if first.count(',') >= 11 and re.match(r'^\d{4}-\d{2}-\d{2}T', first.strip()):
        return 'unicredit'
    return ''


def decode(content_bytes: bytes) -> str:
    """Alior eksportuje w cp1250, mBank z BOM, UniCredit w UTF-8."""
    for encoding in ('utf-8-sig', 'utf-8', 'cp1250'):
        try:
            return content_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content_bytes.decode('cp1250', errors='replace')


def parse(content_bytes: bytes, bank: str = '') -> tuple[str, list[dict]]:
    content = decode(content_bytes)
    bank = (bank or '').strip().lower() or detect_bank(content)
    if bank not in PARSERS:
        raise BankImportError('Nie rozpoznaję formatu pliku. Obsługuję wyciągi: '
                              + ', '.join(BANK_LABELS[b] for b in PARSERS))
    rows = PARSERS[bank](content)
    if not rows:
        raise BankImportError(f'Plik wygląda na wyciąg {BANK_LABELS[bank]}, ale nie znalazłem '
                              'w nim ani jednej operacji — sprawdź, czy to pełny eksport CSV.')
    return bank, rows


def import_csv(content_bytes: bytes, bank: str = '') -> dict:
    """Wgrywa wyciąg do `fin_bank_transactions`. Powtórny import tego samego
    pliku jest bezpieczny — `external_id` jest unikalny, a dopasowań nie ruszamy."""
    bank, rows = parse(content_bytes, bank)
    db = get_db()
    counts = {'new': 0, 'updated': 0, 'unchanged': 0}
    try:
        for row in rows:
            counts[fin_bank.upsert_transaction(row)] += 1
        db.commit()
    except Exception:
        db.rollback()
        raise
    dates = sorted(r['booked_date'] for r in rows)
    return {'bank': bank, 'bank_label': BANK_LABELS.get(bank, bank), 'parsed': len(rows),
            **counts, 'date_from': dates[0], 'date_to': dates[-1]}


# ── dopasowywanie ────────────────────────────────────────────────────────────

def _candidates(txn: dict) -> list[dict]:
    """Dokumenty po właściwej stronie i w rozsądnym oknie czasu. Węższego sita
    nie stawiamy w SQL-u — scoring i tak przejrzy każdego kandydata."""
    is_income = 1 if Decimal(str(txn['amount'])) > 0 else 0
    booked = txn['booked_date']
    if isinstance(booked, str):
        booked = datetime.strptime(booked[:10], '%Y-%m-%d').date()
    with get_db().cursor() as cur:
        cur.execute(f"""SELECT d.fakturownia_id, d.number, d.kind, d.is_income, d.issue_date,
                               d.payment_to, d.paid_date, d.status, d.gross_pln, d.paid_amount,
                               d.counterparty_name, d.counterparty_tax_no_norm, d.description
                        FROM fin_documents d
                        WHERE d.is_income = %s AND {FINANCIAL_CLAUSE}
                          AND d.issue_date BETWEEN %s AND %s
                        ORDER BY d.issue_date DESC""",
                    (is_income, NON_FINANCIAL_KINDS,
                     booked - timedelta(days=DATE_WINDOW * 4),
                     booked + timedelta(days=DATE_WINDOW)))
        return [dict(r) for r in cur.fetchall()]


def _name_overlap(a: str, b: str) -> float:
    """Udział wspólnych „słów znaczących”. Nie fuzzy-matching na literach —
    nazwy w wyciągu są skracane i pisane wielkimi literami, więc liczą się
    całe tokeny, bez form prawnych i krótkich śmieci."""
    stop = {'sp', 'z', 'o', 'oo', 'spzoo', 'sa', 'spolka', 'spółka', 'ul', 'sc',
            'akcyjna', 'ograniczona', 'odpowiedzialnoscia', 'odpowiedzialnością', 'jdg'}
    def tokens(text):
        return {t for t in re.split(r'[^0-9a-ząćęłńóśźż]+', (text or '').lower())
                if len(t) > 2 and t not in stop}
    left, right = tokens(a), tokens(b)
    if not left or not right:
        return 0.0
    return len(left & right) / min(len(left), len(right))


def score_match(txn: dict, doc: dict) -> dict:
    """Jedna, wspólna funkcja oceny. Zwraca punkty i czytelne powody — na ekranie
    i w MCP ma być widać, *dlaczego* coś zostało podpowiedziane."""
    title_key = _number_key(f"{txn.get('title','')} {txn.get('counterparty_name','')}")
    digits = normalize_tax_no(txn.get('title'))
    gross = Decimal(str(doc['gross_pln'] or '0'))
    paid = Decimal(str(doc['paid_amount'] or '0'))
    left = gross - paid
    value = abs(Decimal(str(txn['amount'])))

    booked = txn['booked_date']
    if isinstance(booked, str):
        booked = datetime.strptime(booked[:10], '%Y-%m-%d').date()

    score, reasons = 0, []

    number_key = _number_key(doc.get('number'))
    if _number_is_distinctive(number_key) and number_key in title_key:
        score += 55
        reasons.append(f"numer {doc['number']} w tytule przelewu")

    tax_no = doc.get('counterparty_tax_no_norm') or ''
    if len(tax_no) >= 9 and tax_no in digits:
        score += 25
        reasons.append(f'NIP {tax_no} w tytule przelewu')

    if left > 0 and abs(value - left) <= AMOUNT_TOLERANCE:
        score += 30
        reasons.append('kwota równa pozostałej do zapłaty')
    elif abs(value - gross) <= AMOUNT_TOLERANCE:
        score += 25
        reasons.append('kwota równa brutto dokumentu')
    elif gross > 0 and abs(value - gross) / gross <= Decimal('0.01'):
        score += 8
        reasons.append('kwota zgodna z brutto do 1%')
    elif value > gross:
        score -= 10
        reasons.append('przelew większy niż dokument')

    overlap = _name_overlap(txn.get('counterparty_name'), doc.get('counterparty_name'))
    if overlap >= 0.6:
        score += 18
        reasons.append(f"kontrahent „{doc['counterparty_name']}”")
    elif overlap >= 0.3:
        score += 8
        reasons.append('nazwa kontrahenta częściowo zgodna')

    reference = doc.get('payment_to') or doc.get('issue_date')
    if reference:
        distance = abs((booked - reference).days)
        if distance <= 7:
            score += 10
            reasons.append('data w tygodniu od terminu')
        elif distance <= 30:
            score += 5
    if doc.get('issue_date') and booked < doc['issue_date'] - timedelta(days=3):
        score -= 25
        reasons.append('przelew wcześniejszy niż wystawienie dokumentu')

    if doc.get('status') == 'paid' and left <= 0:
        score -= 20
        reasons.append('dokument już oznaczony jako opłacony')

    return {
        'fakturownia_id': doc['fakturownia_id'],
        'number': doc.get('number'),
        'counterparty_name': doc.get('counterparty_name'),
        'is_income': bool(doc.get('is_income')),
        'issue_date': doc.get('issue_date'),
        'payment_to': doc.get('payment_to'),
        'status': doc.get('status'),
        'gross_pln': gross,
        'paid_amount': paid,
        'amount_left': left,
        'score': score,
        'reasons': reasons,
    }


def suggest_matches(txn: dict, limit: int = 5, min_score: int = 25) -> list[dict]:
    """Kandydaci posortowani od najlepszego. `min_score` odcina losowe trafienia
    — lepiej nie podpowiedzieć nic niż podpowiedzieć fakturę obcego dostawcy."""
    linked = {l['fakturownia_id'] for l in fin_bank.links_for_transaction(txn['id'])} \
        if txn.get('id') else set()
    scored = [score_match(txn, doc) for doc in _candidates(txn)]
    scored = [s for s in scored if s['score'] >= min_score and s['fakturownia_id'] not in linked]
    scored.sort(key=lambda s: (-s['score'], s['payment_to'] or s['issue_date'] or datetime.max.date()))
    return scored[:max(1, min(int(limit), 20))]


def suggest_for_pending(limit: int = 25, min_score: int = 25, scan: int = 200) -> list[dict]:
    """Kolejka do zatwierdzenia: niedopasowane przelewy z najlepszą podpowiedzią.

    `limit` to liczba zwróconych przelewów, `scan` — ile najświeższych
    niedopasowanych w ogóle przejrzeć. Te dwie liczby muszą być osobne, bo
    większość przelewów na wyciągu (ZUS, podatki, przelewy własne) nie ma i nie
    będzie miała żadnej faktury; przy `scan` liczonym od `limit` mały `limit`
    po cichu przeszukiwałby tylko początek wyciągu.
    """
    out = []
    for txn in fin_bank.list_transactions(status='pending', limit=max(int(scan), int(limit))):
        matches = suggest_matches(txn, limit=3, min_score=min_score)
        if matches:
            out.append({'transaction': txn, 'matches': matches})
        if len(out) >= limit:
            break
    return out


# ── zapisywanie powiązań ─────────────────────────────────────────────────────

def link_payment(txn_id: int, fakturownia_id: int, amount=None, push: bool = True,
                 actor: str = '') -> dict:
    """Wiąże przelew z dokumentem i — domyślnie — dopisuje zapłatę w Fakturowni.

    Do Fakturowni idzie **suma** wszystkich powiązań tego dokumentu, nie sama
    ta rata: `fin_invoice.mark_paid` ustawia łączną kwotę zapłaconą, więc
    powtórzenie operacji nie podwaja niczego. `push=False` zostawia zapis tylko
    w CRM, gdy chcesz najpierw obejrzeć wynik.
    """
    import models.fin_document as fin_document
    from services import fin_invoice

    txn = fin_bank.get_transaction(txn_id)
    if not txn:
        raise BankImportError(f'Nie znam transakcji {txn_id}.')
    doc = fin_document.get_document(int(fakturownia_id))
    if not doc:
        raise BankImportError(f'Nie znam dokumentu {fakturownia_id} — zsynchronizuj lustro.')

    txn_amount = abs(Decimal(str(txn['amount'])))
    if (Decimal(str(txn['amount'])) > 0) != bool(doc['is_income']):
        side = 'wpływ' if Decimal(str(txn['amount'])) > 0 else 'wypływ'
        kind = 'przychodowy' if doc['is_income'] else 'kosztowy'
        raise BankImportError(f'To {side}, a dokument jest {kind} — nie wiążę przeciwnych stron.')

    links = fin_bank.links_for_transaction(txn_id)
    existing = next((l for l in links if l['fakturownia_id'] == int(fakturownia_id)), None)
    # Miejsce na przelewie liczymy bez tego powiązania — poprawianie kwoty
    # istniejącego powiązania nie może wyglądać jak dokładanie nowej raty.
    other_links = sum((Decimal(str(l['amount_applied'])) for l in links if l is not existing),
                      Decimal('0'))
    doc_left = (Decimal(str(doc['gross_pln'] or '0'))
                - Decimal(str(doc['paid_amount'] or '0')))
    txn_left = txn_amount - other_links

    if amount not in (None, ''):
        applied = abs(Decimal(str(amount))).quantize(Decimal('0.01'))
    else:
        applied = min(txn_left, doc_left) if doc_left > 0 else txn_left
    if applied <= 0:
        raise BankImportError('Nie ma czego powiązać: przelew jest już rozdysponowany '
                              'albo dokument nie ma nic do zapłaty.')
    if applied > txn_left + AMOUNT_TOLERANCE:
        raise BankImportError(f'Przelew ma {txn_amount}, z czego {other_links} jest już '
                              f'powiązane — na to powiązanie zostaje {txn_left}.')

    db = get_db()
    try:
        fin_bank.add_link(txn_id, fakturownia_id, applied, created_by=actor)
        status = fin_bank.refresh_status(txn_id)
        db.commit()
    except Exception:
        db.rollback()
        raise

    result = {'transaction_id': int(txn_id), 'fakturownia_id': int(fakturownia_id),
              'amount_applied': applied, 'transaction_status': status,
              'pushed': False, 'document': None}

    if push:
        total = fin_bank.applied_to_document(fakturownia_id)
        paid = fin_invoice.mark_paid(int(fakturownia_id), amount=total,
                                     paid_date=txn['booked_date'], actor=actor or 'bank')
        result['pushed'] = True
        result['document'] = paid
    return result


def unlink_payment(txn_id: int, fakturownia_id: int) -> dict:
    """Zdejmuje powiązanie w CRM. Zapłaty w Fakturowni **nie cofa** — cofnięcie
    zapisu księgowego musi być świadomą decyzją człowieka, nie skutkiem ubocznym
    porządków w kolejce dopasowań."""
    db = get_db()
    try:
        removed = fin_bank.remove_link(txn_id, fakturownia_id)
        status = fin_bank.refresh_status(txn_id)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {'removed': removed, 'transaction_status': status}
