"""Wykrywanie duplikatów faktur między źródłami (Fakturownia / Dysk Google).

Dwie faktury uznajemy za duplikat, gdy mają ten sam (znormalizowany) numer
faktury i — jeśli obie strony podają NIP kontrahenta — ten sam NIP (różne
NIP-y przy tym samym numerze faktury to zbieg okoliczności, nie duplikat).
"""
import re

SOURCE_LABELS = {'fakturownia': 'Fakturownia', 'gdrive': 'Dysk'}
STATUS_LABELS = {'pending': 'oczekująca', 'assigned': 'przypisana'}


def _norm_number(s: str) -> str:
    return re.sub(r'\s+', '', (s or '')).upper()


def _norm_nip(s: str) -> str:
    return re.sub(r'[^0-9]', '', (s or ''))


def build_duplicate_map() -> dict:
    """Zwraca {(source, id): [{'source', 'id', 'status'}, ...]} — dla każdej
    faktury listę innych (z dowolnego źródła), które wyglądają na ten sam
    dokument."""
    from models.invoice import get_active_invoices_for_duplicate_check
    from models.gdrive_invoice import get_active_gdrive_invoices_for_duplicate_check

    rows = []
    for r in get_active_invoices_for_duplicate_check():
        rows.append({
            'source': 'fakturownia', 'id': r['id'], 'status': r['status'],
            'invoice_number': r.get('invoice_number'), 'vendor_nip': r.get('vendor_nip'),
        })
    for r in get_active_gdrive_invoices_for_duplicate_check():
        rows.append({
            'source': 'gdrive', 'id': r['id'], 'status': r['status'],
            'invoice_number': r.get('invoice_number'), 'vendor_nip': r.get('vendor_nip'),
        })

    buckets: dict[str, list[dict]] = {}
    for row in rows:
        num = _norm_number(row['invoice_number'])
        if not num:
            continue
        buckets.setdefault(num, []).append(row)

    dup_map = {}
    for group in buckets.values():
        if len(group) < 2:
            continue
        for row in group:
            matches = []
            for other in group:
                if other is row:
                    continue
                nip_a, nip_b = _norm_nip(row['vendor_nip']), _norm_nip(other['vendor_nip'])
                if nip_a and nip_b and nip_a != nip_b:
                    continue
                matches.append(other)
            if matches:
                dup_map[(row['source'], row['id'])] = matches
    return dup_map


def duplicate_label(matches: list[dict]) -> str:
    if not matches:
        return ''
    parts = [
        f"{SOURCE_LABELS.get(m['source'], m['source'])} ({STATUS_LABELS.get(m['status'], m['status'])})"
        for m in matches
    ]
    return ', '.join(parts)
