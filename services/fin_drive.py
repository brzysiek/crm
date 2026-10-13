"""Dokumenty z Dysku Google w Finansach v2: PDF → OCR (Gemini) → kolejka → dokument.

Fakturownia nie zna wszystkiego — faktury zagraniczne czy rachunki bywają
tylko PDF-em na Dysku. Tu wchodzą do tych samych tabel co lustro Fakturowni,
ale dopiero po zatwierdzeniu odczytu: OCR myli kwoty i daty, a błąd w sumach
i podatkach jest droższy niż jedno kliknięcie.
"""
import json
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import models.fin_audit as fin_audit
import models.fin_bank as fin_bank
import models.fin_document as fin_document
import models.fin_drive as fin_drive
from database import get_db
from models.settings import get_setting
from services.fin_rules import apply_rules
from services.fin_sync import normalize_tax_no

# Rodzaje dokumentów do wyboru przy zatwierdzaniu. Import usług i WNT są tu
# celowo: to typowe PDF-y spoza Fakturowni, a podatki liczą je inaczej.
DRIVE_KINDS = ('vat', 'bill', 'receipt', 'import_service', 'import_service_eu', 'wnt',
               'correction', 'invoice_other')


class FinDriveError(Exception):
    """Błąd importu z Dysku, który ma trafić do użytkownika wprost."""


# ── konfiguracja ─────────────────────────────────────────────────────────────

def is_configured() -> bool:
    return bool(get_setting('google_drive_api_token', '') and get_setting('google_drive_folder_id', ''))


def _client():
    from services.gdrive import GoogleDriveClient
    token = get_setting('google_drive_api_token', '')
    root = get_setting('google_drive_folder_id', '')
    if not token or not root:
        raise FinDriveError('Brak konfiguracji Dysku Google — uzupełnij ją w Ustawieniach → Integracje.')
    return GoogleDriveClient(token, root)


def drive_url(gdrive_file_id: str) -> str:
    return f'https://drive.google.com/file/d/{gdrive_file_id}/view'


# ── przeglądanie Dysku ───────────────────────────────────────────────────────

def browse(folder_id: str = '', client=None) -> dict:
    """Podfoldery i PDF-y jednego folderu, z informacją, co już jest w kolejce."""
    client = client or _client()
    folder_id = (folder_id or '').strip() or client.root_folder_id
    try:
        folders = client.list_subfolders(folder_id)
        files = client.list_pdfs_in_folder(folder_id)
    except Exception as e:
        raise FinDriveError(f'Dysk Google nie odpowiedział: {e}') from e
    states = fin_drive.file_states([f['id'] for f in files])
    for f in files:
        f['state'] = states.get(f['id'], '')
    return {'folder_id': folder_id, 'is_root': folder_id == client.root_folder_id,
            'folders': folders, 'files': files}


# ── OCR ──────────────────────────────────────────────────────────────────────

def _decimal(value) -> Decimal:
    if value in (None, ''):
        return Decimal('0')
    try:
        return Decimal(str(value)).quantize(Decimal('0.01'))
    except InvalidOperation:
        return Decimal('0')


def _iso_date(value):
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value or '')[:10], '%Y-%m-%d').date()
    except ValueError:
        return None


def _modified(value):
    try:
        return datetime.strptime(str(value or '')[:19], '%Y-%m-%dT%H:%M:%S')
    except ValueError:
        return None


def map_ocr(ocr: dict, file_name: str = '', modified=None) -> dict:
    """Odpowiedź Gemini → wiersz kolejki.

    Kontrahentem jest druga strona faktury: przy koszcie sprzedawca, przy
    przychodzie nabywca — tak samo, jak w lustrze Fakturowni.
    """
    is_income = ocr.get('invoice_type') == 'income'
    name = ocr.get('buyer_name') if is_income else ocr.get('vendor_name')
    tax_no = ocr.get('buyer_nip') if is_income else ocr.get('vendor_nip')
    gross, net, tax = (_decimal(ocr.get('amount_gross')), _decimal(ocr.get('amount_net')),
                       _decimal(ocr.get('vat_amount')))
    # Odczyt bywa niepełny: z dwóch znanych kwot trzecia wynika wprost.
    if not net and gross:
        net = gross - tax
    if not gross and net:
        gross = net + tax
    return {
        'file_name': (file_name or '')[:512],
        'file_modified_at': _modified(modified),
        'is_income': 1 if is_income else 0,
        'kind': 'vat',
        'number': str(ocr.get('invoice_number') or '')[:128],
        'counterparty_name': str(name or '')[:256],
        'counterparty_tax_no': str(tax_no or '')[:32],
        'issue_date': _iso_date(ocr.get('issue_date')),
        'payment_to': _iso_date(ocr.get('payment_to')),
        'currency': (str(ocr.get('currency') or 'PLN').strip().upper() or 'PLN')[:3],
        'price_net': net,
        'price_tax': tax,
        'price_gross': gross,
        'ocr_note': str(ocr.get('confidence_note') or '') or None,
        'ocr_raw': json.dumps(ocr, ensure_ascii=False, default=str),
    }


def ocr_file(gdrive_file_id: str, file_name: str = '', modified=None, client=None) -> dict:
    """Pobiera PDF, czyta go Gemini i odkłada wynik do kolejki."""
    gdrive_file_id = (gdrive_file_id or '').strip()
    if not gdrive_file_id:
        raise FinDriveError('Nie wskazałeś pliku.')
    # Zatwierdzonego pliku nie czytamy ponownie — to płatne wywołanie, a wynik
    # i tak nie nadpisałby dokumentu.
    if fin_drive.file_states([gdrive_file_id]).get(gdrive_file_id) == 'accepted':
        return {'outcome': 'accepted', 'file_id': gdrive_file_id, 'file_name': file_name}

    gemini_key = get_setting('gemini_api_key', '')
    if not gemini_key:
        raise FinDriveError('Brak klucza API Gemini — uzupełnij go w Ustawieniach → Integracje.')
    client = client or _client()
    from services.gemini_ocr import ocr_invoice_pdf
    try:
        pdf = client.download_file(gdrive_file_id)
    except Exception as e:
        # Google dokleja do błędu całą odpowiedź JSON — użytkownikowi wystarczy pierwsza linia.
        reason = str(e).split(' — treść')[0].splitlines()[0][:200]
        raise FinDriveError(f'Nie pobrałem pliku z Dysku: {reason}') from e
    ocr = ocr_invoice_pdf(pdf, gemini_key, model=get_setting('gemini_model', 'gemini-2.5-flash'))
    if 'error' in ocr:
        raise FinDriveError(f'OCR się nie udał: {ocr["error"]}')

    row = map_ocr(ocr, file_name=file_name, modified=modified)
    db = get_db()
    try:
        saved = fin_drive.save_ocr(gdrive_file_id, row)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {'outcome': saved['outcome'], 'id': saved['id'], 'file_id': gdrive_file_id,
            'file_name': file_name, 'number': row['number'],
            'counterparty_name': row['counterparty_name'],
            'price_gross': str(row['price_gross']), 'currency': row['currency']}


# ── zatwierdzanie ────────────────────────────────────────────────────────────

def _form_money(value, label: str) -> Decimal:
    text = re.sub(r'[\s\xa0]', '', str(value or '')).replace(',', '.')
    if not text:
        return Decimal('0')
    try:
        return Decimal(text).quantize(Decimal('0.01'))
    except InvalidOperation:
        raise FinDriveError(f'{label}: „{value}” nie jest kwotą.')


def _form_date(value, label: str, required: bool = False):
    text = str(value or '').strip()
    if not text:
        if required:
            raise FinDriveError(f'{label}: podaj datę.')
        return None
    parsed = _iso_date(text)
    if not parsed:
        raise FinDriveError(f'{label}: „{value}” nie jest datą (RRRR-MM-DD).')
    return parsed


def clean_fields(form: dict) -> dict:
    """Pola z formularza kolejki → wartości do zapisu. Rzuca FinDriveError."""
    kind = (form.get('kind') or 'vat').strip()
    if kind not in DRIVE_KINDS:
        raise FinDriveError(f'Nie znam rodzaju dokumentu „{kind}”.')
    gross = _form_money(form.get('price_gross'), 'Brutto')
    tax = _form_money(form.get('price_tax'), 'VAT')
    net = _form_money(form.get('price_net'), 'Netto')
    if gross == 0:
        raise FinDriveError('Brutto: dokument bez kwoty nie ma czego wnieść do finansów.')
    if net == 0:
        net = gross - tax
    if abs(net + tax - gross) > Decimal('0.05'):
        raise FinDriveError(f'Netto {net} + VAT {tax} nie daje brutto {gross} — popraw kwoty.')
    currency = (form.get('currency') or 'PLN').strip().upper()
    if not re.fullmatch(r'[A-Z]{3}', currency):
        raise FinDriveError(f'Waluta: „{currency}” to nie kod waluty (np. PLN, EUR).')
    return {
        'is_income': 1 if str(form.get('is_income')) == '1' else 0,
        'kind': kind,
        'number': (form.get('number') or '').strip()[:128],
        'counterparty_name': (form.get('counterparty_name') or '').strip()[:256],
        'counterparty_tax_no': (form.get('counterparty_tax_no') or '').strip()[:32],
        'issue_date': _form_date(form.get('issue_date'), 'Data wystawienia', required=True),
        'payment_to': _form_date(form.get('payment_to'), 'Termin płatności'),
        'currency': currency,
        'price_net': net,
        'price_tax': tax,
        'price_gross': gross,
    }


def _exchange_rate(currency: str, issue_date, given='') -> Decimal:
    if currency == 'PLN':
        return Decimal('1')
    text = str(given or '').strip().replace(',', '.')
    if text:
        try:
            rate = Decimal(text)
        except InvalidOperation:
            raise FinDriveError(f'Kurs: „{given}” nie jest liczbą.')
        if rate <= 0:
            raise FinDriveError('Kurs musi być dodatni.')
        return rate
    from services.nbp import get_nbp_rate
    rate = get_nbp_rate(currency, issue_date.isoformat())
    if not rate:
        raise FinDriveError(f'NBP nie podał kursu {currency} na {issue_date} — wpisz kurs ręcznie.')
    return Decimal(str(rate))


def build_document(row: dict, rate: Decimal) -> dict:
    """Wiersz kolejki → wiersz `fin_documents`, w tym samym kształcie co lustro."""
    net, tax, gross = (Decimal(str(row['price_net'])), Decimal(str(row['price_tax'])),
                       Decimal(str(row['price_gross'])))
    cent = Decimal('0.01')
    return {
        'fakturownia_id': fin_drive.document_id(row['id']),
        'department_id': None,
        'kind': row['kind'],
        'is_income': row['is_income'],
        'number': row['number'],
        'issue_date': row['issue_date'],
        'sell_date': row['issue_date'],
        'delivery_date': None,
        'payment_to': row['payment_to'],
        'paid_date': None,
        'vat_date': row['issue_date'],
        'income_tax_date': row['issue_date'],
        'status': 'issued',
        'currency': row['currency'],
        'exchange_rate': rate,
        'price_net': net,
        'price_tax': tax,
        'price_gross': gross,
        'paid_amount': Decimal('0'),
        'net_pln': (net * rate).quantize(cent),
        'tax_pln': (tax * rate).quantize(cent),
        'gross_pln': (gross * rate).quantize(cent),
        'counterparty_name': row['counterparty_name'],
        'counterparty_tax_no': row['counterparty_tax_no'],
        'counterparty_tax_no_norm': normalize_tax_no(row['counterparty_tax_no'])[:32],
        'accounting_kind': '',
        'fakturownia_category_id': None,
        'gov_id': '',
        'gov_status': '',
        'gov_send_date': None,
        # Nazwa pliku trafia do opisu, bo dopasowanie przelewów szuka w nim
        # numeru faktury — a pliki często nazywa się właśnie numerem.
        'description': row.get('file_name') or None,
        'oid': '',
        'raw_json': json.dumps({'source': fin_drive.SOURCE,
                                'gdrive_file_id': row['gdrive_file_id'],
                                'file_name': row.get('file_name')}, ensure_ascii=False),
        'fakturownia_updated_at': None,
    }


def accept(queue_id: int, form: dict, actor: str = '') -> dict:
    """Zatwierdza odczyt (z poprawkami z formularza) i tworzy dokument."""
    row = fin_drive.get(queue_id)
    if not row:
        raise FinDriveError(f'Nie znam pozycji {queue_id} w kolejce.')
    if row['status'] == 'accepted':
        raise FinDriveError('Ten plik jest już zatwierdzony.')
    fields = clean_fields(form)
    rate = _exchange_rate(fields['currency'], fields['issue_date'], form.get('exchange_rate'))
    doc = build_document({**row, **fields}, rate)

    db = get_db()
    try:
        fin_drive.update_fields(queue_id, fields)
        fin_document.upsert_document(doc)
        fin_document.mark_source(doc['fakturownia_id'], fin_drive.SOURCE, row['gdrive_file_id'])
        fin_drive.set_status(queue_id, 'accepted', fakturownia_id=doc['fakturownia_id'], actor=actor)
        fin_audit.log('drive_accept', actor=actor, fakturownia_id=doc['fakturownia_id'],
                      payload={'file': row.get('file_name'), **{k: str(v) for k, v in fields.items()}})
        db.commit()
    except Exception:
        db.rollback()
        raise
    categorized = apply_rules(only_ids=[doc['fakturownia_id']])['assigned']
    return {'fakturownia_id': doc['fakturownia_id'], 'number': doc['number'],
            'gross_pln': doc['gross_pln'], 'categorized': categorized}


def reject(queue_id: int, actor: str = '') -> None:
    row = fin_drive.get(queue_id)
    if not row:
        raise FinDriveError(f'Nie znam pozycji {queue_id} w kolejce.')
    if row['status'] == 'accepted':
        raise FinDriveError('Ten plik jest już dokumentem — najpierw cofnij go do kolejki.')
    fin_drive.set_status(queue_id, 'rejected', actor=actor)
    get_db().commit()


def restore(queue_id: int, actor: str = '') -> None:
    row = fin_drive.get(queue_id)
    if not row or row['status'] != 'rejected':
        raise FinDriveError('Przywrócić można tylko odrzuconą pozycję.')
    fin_drive.set_status(queue_id, 'pending', actor=actor)
    get_db().commit()


def return_to_queue(fakturownia_id: int, actor: str = '') -> dict:
    """Cofa zatwierdzenie: dokument znika z finansów, a odczyt wraca do kolejki
    do poprawy. Z rozliczonym przelewem się nie da — najpierw trzeba go odwiązać,
    żeby powiązanie nie zostało bez dokumentu."""
    row = fin_drive.get_by_document(fakturownia_id)
    if not row:
        raise FinDriveError('To nie jest dokument z Dysku.')
    if fin_bank.links_for_document(fakturownia_id):
        raise FinDriveError('Dokument jest powiązany z przelewem — najpierw odwiąż go w zakładce Rozliczenia.')
    db = get_db()
    try:
        fin_document.delete_document(fakturownia_id)
        fin_drive.set_status(row['id'], 'pending', actor=actor)
        fin_audit.log('drive_return', actor=actor, fakturownia_id=int(fakturownia_id),
                      payload={'file': row.get('file_name')})
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {'queue_id': row['id']}
