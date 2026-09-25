-- Etap 3 modułu Finanse v2: silnik podatkowy (VAT / PIT / ZUS).
--
-- 1) Daty księgowe z Fakturowni. Do tej pory liczyliśmy okresy po dacie
--    wystawienia, a Fakturownia trzyma własną datę ujęcia w VAT — dla faktur
--    kosztowych to data otrzymania, od której zależy prawo do odliczenia.
--    W danych 10 dokumentów ma ją w innym miesiącu niż wystawienie (np. faktura
--    z 31.08 z VAT-em wrześniowym), więc bez tego symulacja rozjeżdża się
--    z deklaracją na granicy miesiąca.
ALTER TABLE fin_documents
    ADD COLUMN vat_date        DATE NULL AFTER paid_date,
    ADD COLUMN income_tax_date DATE NULL AFTER vat_date,
    ADD KEY idx_fin_doc_vat_date (vat_date),
    ADD KEY idx_fin_doc_income_tax_date (income_tax_date);

-- Uzupełnienie dla dokumentów już zsynchronizowanych — z zapisanej odpowiedzi API.
UPDATE fin_documents
   SET vat_date = COALESCE(
           NULLIF(LEFT(JSON_UNQUOTE(JSON_EXTRACT(raw_json, '$.accounting_vat_tax_date')), 10), 'null'),
           issue_date),
       income_tax_date = COALESCE(
           NULLIF(LEFT(JSON_UNQUOTE(JSON_EXTRACT(raw_json, '$.accounting_income_tax_date')), 10), 'null'),
           issue_date)
 WHERE raw_json IS NOT NULL;

UPDATE fin_documents SET vat_date = issue_date WHERE vat_date IS NULL;
UPDATE fin_documents SET income_tax_date = issue_date WHERE income_tax_date IS NULL;

-- 2) Stawki i kwoty progowe. Nic podatkowego nie jest w kodzie — wszystko
--    stąd, bo zmienia się co roku. is_confirmed=0 znaczy „wpisane na moje
--    ryzyko, sprawdź przed użyciem”: ekran Podatki krzyczy o takich wierszach.
ALTER TABLE fin_tax_rates
    ADD COLUMN is_confirmed TINYINT(1) NOT NULL DEFAULT 1 AFTER value;

INSERT IGNORE INTO fin_tax_rates (year, `key`, value, is_confirmed, note) VALUES
    (2025, 'pit_rate',                0.1900,   1, 'PIT liniowy 19%'),
    (2025, 'health_rate',             0.0490,   1, 'Zdrowotna dla liniowego: 4,9% dochodu'),
    (2025, 'health_min_monthly',    314.96,     1, 'Minimalna zdrowotna: 9% z 75% minimalnego wynagrodzenia'),
    (2025, 'health_deduction_limit', 12900.00,  1, 'Roczny limit odliczenia zdrowotnej od dochodu (liniowy)'),
    (2025, 'zus_social_monthly',    1646.47,    1, 'Społeczne z chorobowym od podstawy 5203,80'),
    (2025, 'zus_fp_monthly',         127.49,    1, 'Fundusz Pracy i FS: 2,45% podstawy'),
    (2025, 'zus_base',              5203.80,    1, '60% prognozowanego przeciętnego wynagrodzenia (8673 zł)'),
    (2025, 'min_wage',              4666.00,    1, 'Minimalne wynagrodzenie 2025'),
    -- 2026: stawki procentowe wynikają z ustawy i się nie zmieniły, ale kwoty
    -- przeniosłem z 2025 i trzeba je potwierdzić w ZUS albo u księgowej.
    (2026, 'pit_rate',                0.1900,   1, 'PIT liniowy 19%'),
    (2026, 'health_rate',             0.0490,   1, 'Zdrowotna dla liniowego: 4,9% dochodu'),
    (2026, 'health_min_monthly',    314.96,     0, 'PRZENIESIONE Z 2025 — potwierdź minimalną zdrowotną na 2026'),
    (2026, 'health_deduction_limit', 12900.00,  0, 'PRZENIESIONE Z 2025 — potwierdź limit odliczenia na 2026'),
    (2026, 'zus_social_monthly',    1646.47,    0, 'PRZENIESIONE Z 2025 — potwierdź składki społeczne na 2026'),
    (2026, 'zus_fp_monthly',         127.49,    0, 'PRZENIESIONE Z 2025 — potwierdź Fundusz Pracy na 2026'),
    (2026, 'zus_base',              5203.80,    0, 'PRZENIESIONE Z 2025 — potwierdź podstawę wymiaru na 2026'),
    (2026, 'min_wage',              4806.00,    0, 'Minimalne wynagrodzenie 2026 — potwierdź');
