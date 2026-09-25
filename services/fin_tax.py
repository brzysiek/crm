"""Silnik podatkowy — symulacja VAT, zaliczki PIT i składki zdrowotnej (JDG, liniowy).

Dwie warstwy, celowo rozdzielone:

* **czyste funkcje** (górna część pliku) — dostają gotowe dane, nie znają bazy,
  nie znają Flaska. To one liczą i to one są testowane na ręcznie policzonych
  przypadkach.
* **`period_overview()`** (na końcu) — spina je z `models.fin_tax`, żeby widok
  i MCP miały jedno wejście.

Zasada nadrzędna: dokument, którego silnik nie umie policzyć (odwrotne
obciążenie, import usług, marża, OSS, zerowy VAT bez znanej podstawy), **trafia
na listę wyjątków, a nie do sumy**. Lepiej pokazać „te trzy sprawdź ręcznie”
niż po cichu podać zaniżoną kwotę. Wszystko tu jest symulacją, nie deklaracją.

Żadna stawka ani kwota progowa nie jest zapisana w kodzie — wszystko przychodzi
z `fin_tax_rates` (patrz `models.fin_tax.get_rates`).
"""
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

ZERO = Decimal('0')

# Terminy ustawowe: VAT-7 i JPK do 25., zaliczka PIT do 20., ZUS do 20.
DUE_DAYS = {'vat': 25, 'pit': 20, 'zus_social': 20, 'zus_health': 20}

OBLIGATION_LABELS = {
    'vat': 'VAT',
    'pit': 'Zaliczka PIT (19%)',
    'zus_social': 'ZUS społeczny + FP',
    'zus_health': 'Składka zdrowotna',
}

# Powody, dla których dokument nie wchodzi do automatu. Kolejność sprawdzania
# ma znaczenie — pierwszy pasujący wygrywa.
EXCEPTION_LABELS = {
    'cancelled': 'Dokument anulowany',
    'excluded': 'W Fakturowni wyłączony z księgowania',
    'margin': 'Procedura marży — VAT od marży, nie od netto',
    'oss': 'Procedura OSS — VAT rozliczany w innym państwie',
    'reverse_charge': 'Odwrotne obciążenie — VAT rozlicza nabywca',
    'self_charge': 'Import usług / WNT — VAT naliczasz i odliczasz sam',
    'zero_vat': 'Zerowy VAT (zw / np / eksport) — sprawdź podstawę',
}

# Rodzaje dokumentów, przy których podatek nalicza się poza zwykłym schematem.
SELF_CHARGE_KINDS = ('wnt', 'import_service', 'import_service_eu', 'import_products')
MARGIN_KINDS = ('vat_margin',)


def vat_exception(doc: dict) -> str | None:
    """Zwraca powód wyłączenia dokumentu z automatu VAT albo None."""
    if doc.get('cancelled'):
        return 'cancelled'
    if doc.get('exclude_from_accounting'):
        return 'excluded'
    kind = doc.get('kind') or ''
    if kind in MARGIN_KINDS:
        return 'margin'
    if doc.get('use_moss'):
        return 'oss'
    if doc.get('reverse_charge'):
        return 'reverse_charge'
    if kind in SELF_CHARGE_KINDS:
        return 'self_charge'
    # Korekty potrafią mieć zerowy VAT przy niezerowym netto i to jest poprawne
    # (korekta samej wartości netto), więc zerowy VAT zgłaszamy tylko tam, gdzie
    # netto jest dodatnie i podatku po prostu nie ma.
    if _dec(doc.get('tax_pln')) == ZERO and _dec(doc.get('net_pln')) > ZERO:
        return 'zero_vat'
    return None


def _dec(value) -> Decimal:
    if value is None or value == '':
        return ZERO
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _zloty(value: Decimal) -> Decimal:
    """Podatki zaokrągla się do pełnych złotych (art. 63 § 1 Ordynacji)."""
    return _dec(value).quantize(Decimal('1'), rounding=ROUND_HALF_UP)


def _grosz(value: Decimal) -> Decimal:
    return _dec(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _doc_summary(doc: dict, reason: str = '') -> dict:
    """Skrót dokumentu na listę wyjątków / rozbicie — bez raw_json i balastu."""
    out = {
        'fakturownia_id': doc.get('fakturownia_id'),
        'number': doc.get('number'),
        'counterparty_name': doc.get('counterparty_name'),
        'kind': doc.get('kind'),
        'net': _dec(doc.get('net_pln')),
        'tax': _dec(doc.get('tax_pln')),
        'is_income': bool(doc.get('is_income')),
    }
    if reason:
        out['reason'] = reason
        out['reason_label'] = EXCEPTION_LABELS.get(reason, reason)
    return out


def vat_estimate(period: str, income_docs: list[dict], cost_docs: list[dict],
                 carry_from_previous: Decimal = ZERO) -> dict:
    """VAT za okres: należny z przychodów minus naliczony z kosztów.

    Naliczony liczymy z `vat_deduction_percent` z metadanych CRM (100/50/0) —
    dlatego kategoryzacja kosztów wprost przekłada się na tę kwotę. Dokumenty
    bez kategorii traktujemy jak 100% odliczenia i **liczymy je osobno**, żeby
    było widać, ile z wyniku stoi na domyśle.
    """
    due, deductible, uncategorized_tax = ZERO, ZERO, ZERO
    exceptions, limited, uncategorized = [], [], []

    for doc in income_docs:
        reason = vat_exception(doc)
        if reason:
            exceptions.append(_doc_summary(doc, reason))
            continue
        due += _dec(doc.get('tax_pln'))

    for doc in cost_docs:
        reason = vat_exception(doc)
        if reason:
            exceptions.append(_doc_summary(doc, reason))
            continue
        tax = _dec(doc.get('tax_pln'))
        percent = doc.get('vat_deduction_percent')
        if percent is None:
            uncategorized_tax += tax
            uncategorized.append(_doc_summary(doc))
            percent = 100
        share = _grosz(tax * _dec(percent) / Decimal('100'))
        deductible += share
        if _dec(percent) != Decimal('100'):
            entry = _doc_summary(doc)
            entry.update({'percent': int(percent), 'deducted': share, 'dropped': _grosz(tax - share)})
            limited.append(entry)

    balance = _grosz(due) - _grosz(deductible) - _dec(carry_from_previous)
    return {
        'period': period,
        'due': _grosz(due),
        'deductible': _grosz(deductible),
        'carry_from_previous': _dec(carry_from_previous),
        'balance': balance,
        'to_pay': _zloty(balance) if balance > ZERO else ZERO,
        'carry_forward': _grosz(-balance) if balance < ZERO else ZERO,
        'income_count': len(income_docs) - len([e for e in exceptions if e['is_income']]),
        'cost_count': len(cost_docs) - len([e for e in exceptions if not e['is_income']]),
        'limited': limited,
        'uncategorized': uncategorized,
        'uncategorized_tax': _grosz(uncategorized_tax),
        'exceptions': exceptions,
        'due_date': due_date('vat', period),
    }


def pit_advance(month: str, income_net: Decimal, cost_net: Decimal,
                social_paid: Decimal, health_deducted: Decimal,
                advances_paid: Decimal, rates: dict) -> dict:
    """Zaliczka PIT liniowa narastająco od początku roku.

    Wszystkie kwoty wejściowe są **narastające** (od stycznia do końca `month`):
    przychód netto, koszty po korekcie o % KUP, zapłacone składki społeczne
    i odliczona składka zdrowotna. Zaliczka = 19% × dochód − zaliczki już
    zapłacone; jeśli wyjdzie ujemnie, nie ma czego płacić (nadpłata zostaje).
    """
    rate = _rate(rates, 'pit_rate')
    base = _dec(income_net) - _dec(cost_net) - _dec(social_paid) - _dec(health_deducted)
    taxable = base if base > ZERO else ZERO
    tax_ytd = _zloty(taxable * rate)
    advance = tax_ytd - _zloty(_dec(advances_paid))
    return {
        'month': month,
        'income_net': _grosz(income_net),
        'cost_net': _grosz(cost_net),
        'social_paid': _grosz(social_paid),
        'health_deducted': _grosz(health_deducted),
        'base': _grosz(base),
        'taxable': _grosz(taxable),
        'rate': rate,
        'tax_ytd': tax_ytd,
        'advances_paid': _zloty(_dec(advances_paid)),
        'to_pay': advance if advance > ZERO else ZERO,
        'overpaid': -advance if advance < ZERO else ZERO,
        'loss': _grosz(-base) if base < ZERO else ZERO,
        'due_date': due_date('pit', month),
    }


def health_contribution(month: str, basis_income: Decimal, rates: dict) -> dict:
    """Składka zdrowotna liniowca: 4,9% dochodu, nie mniej niż minimum.

    Podstawą jest dochód z **miesiąca poprzedzającego** — to `basis_income`,
    wyliczane przez warstwę danych; ta funkcja nie zgaduje, z którego miesiąca
    on jest. Minimum (9% z 75% minimalnego wynagrodzenia) trzymamy jako gotową
    kwotę w stawkach rocznych, bo ustawodawca i tak publikuje ją wprost.
    """
    rate = _rate(rates, 'health_rate')
    minimum = _rate(rates, 'health_min_monthly')
    from_income = _grosz(_dec(basis_income) * rate) if _dec(basis_income) > ZERO else ZERO
    amount = max(from_income, minimum)
    return {
        'month': month,
        'basis_income': _grosz(basis_income),
        'rate': rate,
        'from_income': from_income,
        'minimum': minimum,
        'is_minimum': amount == minimum and from_income < minimum,
        'amount': _grosz(amount),
        'due_date': due_date('zus_health', month),
    }


def social_contribution(month: str, rates: dict) -> dict:
    """ZUS społeczny + Fundusz Pracy — kwoty ryczałtowe z tabeli stawek."""
    social = _rate(rates, 'zus_social_monthly')
    fp = _rate(rates, 'zus_fp_monthly')
    return {
        'month': month,
        'social': social,
        'fp': fp,
        'amount': _grosz(social + fp),
        'due_date': due_date('zus_social', month),
    }


def _rate(rates: dict, key: str) -> Decimal:
    """Stawka ze słownika `models.fin_tax.get_rates`. Brak = twardy błąd.

    Świadomie nie ma tu wartości domyślnych: cicha zerowa stawka dałaby
    wiarygodnie wyglądającą, a fałszywą kwotę podatku.
    """
    entry = (rates or {}).get(key)
    if entry is None:
        raise ValueError(f'Brak stawki „{key}” w tabeli stawek podatkowych — '
                         f'uzupełnij ją w Finanse → Ustawienia.')
    return _dec(entry['value'] if isinstance(entry, dict) else entry)


# ── Terminy ──────────────────────────────────────────────────────────────────

def easter(year: int) -> date:
    """Wielkanoc (algorytm Meeusa/Jonesa/Butchera) — potrzebna do świąt ruchomych."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = (h + l - 7 * m + 114) % 31 + 1
    return date(year, month, day)


def holidays(year: int) -> set:
    """Dni wolne ustawowo w Polsce — poza nie przesuwa się termin podatkowy."""
    easter_sunday = easter(year)
    return {
        date(year, 1, 1), date(year, 1, 6), date(year, 5, 1), date(year, 5, 3),
        date(year, 8, 15), date(year, 11, 1), date(year, 11, 11),
        date(year, 12, 25), date(year, 12, 26),
        easter_sunday + timedelta(days=1),   # poniedziałek wielkanocny
        easter_sunday + timedelta(days=49),  # Zielone Świątki
        easter_sunday + timedelta(days=60),  # Boże Ciało
    }


def next_working_day(day: date) -> date:
    """Termin wypadający w sobotę, niedzielę albo święto przechodzi na kolejny dzień."""
    free = holidays(day.year)
    while day.weekday() >= 5 or day in free:
        day += timedelta(days=1)
        if day.month == 1 and day.day == 1:
            free = holidays(day.year)
    return day


def due_date(kind: str, period: str) -> date | None:
    """Termin zapłaty zobowiązania za okres `YYYY-MM` — miesiąc po okresie."""
    day_of_month = DUE_DAYS.get(kind)
    if not day_of_month:
        return None
    try:
        year, month = int(period[:4]), int(period[5:7])
    except (ValueError, IndexError):
        return None
    year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return next_working_day(date(year, month, day_of_month))


# ── Spięcie z danymi ─────────────────────────────────────────────────────────

def period_overview(period: str) -> dict:
    """Wszystkie zobowiązania za okres `YYYY-MM` naraz — wejście dla widoku i MCP.

    Jedyna funkcja w tym pliku, która dotyka bazy; cała arytmetyka zostaje
    powyżej. Zwraca też `rates_warning`, jeśli stawki na dany rok są
    niepotwierdzone albo przeniesione z wcześniejszego roku — ekran ma o tym
    krzyczeć, zamiast udawać pewność.
    """
    from models import fin_tax as store

    year, month = int(period[:4]), int(period[5:7])
    rates = store.get_rates(year)

    income_docs, cost_docs = store.vat_register(period)
    vat = vat_estimate(period, income_docs, cost_docs)

    ytd = store.income_tax_totals(year, month)
    social_paid = store.paid_amount('zus_social', year, period)
    health_paid = store.paid_amount('zus_health', year, period)
    health_limit = _rate(rates, 'health_deduction_limit')
    pit = pit_advance(period, ytd['income_net'], ytd['cost_net'], social_paid,
                      min(health_paid, health_limit),
                      store.paid_amount('pit', year, period, inclusive=False), rates)

    previous = f'{year - 1}-12' if month == 1 else f'{year}-{month - 1:02d}'
    basis = store.month_income(previous)
    health = health_contribution(period, basis, rates)
    health['basis_month'] = previous
    health['deduction_limit'] = health_limit
    health['deduction_used'] = _grosz(min(health_paid, health_limit))
    social = social_contribution(period, rates)

    return {
        'period': period,
        'vat': vat,
        'pit': pit,
        'health': health,
        'social': social,
        'ytd': ytd,
        'rates': rates,
        'rates_year': year,
        'rates_warning': sorted({r['note'] for r in rates.values()
                                 if not r['is_confirmed'] or r['year'] != year}),
        'obligations': {o['kind']: o for o in store.list_obligations(period=period)},
    }


def obligation_rows(overview: dict) -> list[dict]:
    """Cztery zobowiązania okresu w jednym formacie — na listę i na „Do zapłaty”.

    Kwota z symulacji, status z rejestru: jeśli człowiek wpisał własną kwotę
    (`amount_declared`) albo oznaczył zapłatę, to jego wpis jest tym, co widać,
    a symulacja zostaje obok jako punkt odniesienia.
    """
    saved = overview.get('obligations') or {}
    sources = (
        ('vat', overview['vat']['to_pay'], overview['vat']['due_date']),
        ('pit', overview['pit']['to_pay'], overview['pit']['due_date']),
        ('zus_social', overview['social']['amount'], overview['social']['due_date']),
        ('zus_health', overview['health']['amount'], overview['health']['due_date']),
    )
    rows = []
    for kind, calculated, due in sources:
        entry = saved.get(kind) or {}
        declared = entry.get('amount_declared')
        rows.append({
            'kind': kind,
            'label': OBLIGATION_LABELS[kind],
            'period': overview['period'],
            'calculated': _grosz(calculated),
            'declared': _grosz(declared) if declared is not None else None,
            'amount': _grosz(declared) if declared is not None else _grosz(calculated),
            'due_date': entry.get('due_date') or due,
            'paid_at': entry.get('paid_at'),
        })
    return rows
