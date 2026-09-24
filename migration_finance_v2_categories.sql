-- Etap 2 modułu Finanse v2: normalizacja NIP kontrahenta + reguły startowe.
--
-- Ten sam kontrahent przychodzi z Fakturowni raz jako "5262544258", raz jako
-- "PL5262544258" (PKP Intercity, Volkswagen, KRAKPIS). Bez znormalizowanej
-- kolumny reguły po NIP-ie łapałyby połowę dokumentów, a widok kontrahenta
-- pokazywałby dwa byty zamiast jednego. Oryginał zostaje nietknięty —
-- normalizacja jest obok, nie zamiast.

ALTER TABLE fin_documents
    ADD COLUMN counterparty_tax_no_norm VARCHAR(32) NOT NULL DEFAULT '' AFTER counterparty_tax_no;

ALTER TABLE fin_documents
    ADD KEY idx_fin_doc_tax_norm (counterparty_tax_no_norm);

-- Reguły startowe: tylko tam, gdzie marka jednoznacznie mówi o kategorii.
-- Wszystko, co wymagałoby zgadywania (hurtownie, sklepy, składki branżowe),
-- zostaje bez reguły i czeka na ręczną decyzję.
INSERT INTO fin_category_rules (priority, match_field, match_type, match_value, category_id)
SELECT * FROM (
    SELECT 10  AS priority, 'counterparty_tax_no_norm' AS f, 'equals'   AS t, '5252822767' AS v, (SELECT id FROM fin_categories WHERE slug='infrastruktura-it') AS c UNION ALL
    SELECT 10, 'counterparty_tax_no_norm', 'equals',   '7792467259', (SELECT id FROM fin_categories WHERE slug='infrastruktura-it') UNION ALL
    SELECT 10, 'counterparty_tax_no_norm', 'equals',   '7162502787', (SELECT id FROM fin_categories WHERE slug='infrastruktura-it') UNION ALL
    SELECT 10, 'counterparty_tax_no_norm', 'equals',   '6751322807', (SELECT id FROM fin_categories WHERE slug='infrastruktura-it') UNION ALL
    SELECT 10, 'counterparty_tax_no_norm', 'equals',   '5261040567', (SELECT id FROM fin_categories WHERE slug='telekomunikacja') UNION ALL
    SELECT 10, 'counterparty_tax_no_norm', 'equals',   '5213704420', (SELECT id FROM fin_categories WHERE slug='subskrypcje') UNION ALL
    SELECT 10, 'counterparty_tax_no_norm', 'equals',   'IE8256796U', (SELECT id FROM fin_categories WHERE slug='subskrypcje') UNION ALL
    SELECT 10, 'counterparty_tax_no_norm', 'equals',   '5213690735', (SELECT id FROM fin_categories WHERE slug='subskrypcje') UNION ALL
    SELECT 10, 'counterparty_tax_no_norm', 'equals',   '6772431973', (SELECT id FROM fin_categories WHERE slug='ksiegowosc-prawo') UNION ALL
    SELECT 10, 'counterparty_tax_no_norm', 'equals',   '5260300517', (SELECT id FROM fin_categories WHERE slug='oplaty-bankowe') UNION ALL
    SELECT 10, 'counterparty_tax_no_norm', 'equals',   '5262544258', (SELECT id FROM fin_categories WHERE slug='podroze') UNION ALL
    SELECT 10, 'counterparty_tax_no_norm', 'equals',   '6891093258', (SELECT id FROM fin_categories WHERE slug='podroze') UNION ALL
    SELECT 10, 'counterparty_tax_no_norm', 'equals',   '5252800978', (SELECT id FROM fin_categories WHERE slug='samochod-eksploatacja') UNION ALL
    SELECT 10, 'counterparty_tax_no_norm', 'equals',   '8722229029', (SELECT id FROM fin_categories WHERE slug='samochod-eksploatacja') UNION ALL
    SELECT 10, 'counterparty_tax_no_norm', 'equals',   '6831769858', (SELECT id FROM fin_categories WHERE slug='samochod-eksploatacja') UNION ALL
    SELECT 10, 'counterparty_tax_no_norm', 'equals',   '6812019085', (SELECT id FROM fin_categories WHERE slug='samochod-paliwo') UNION ALL
    SELECT 10, 'counterparty_tax_no_norm', 'equals',   '5261009190', (SELECT id FROM fin_categories WHERE slug='samochod-paliwo') UNION ALL
    SELECT 10, 'counterparty_tax_no_norm', 'equals',   '7740001454', (SELECT id FROM fin_categories WHERE slug='samochod-paliwo') UNION ALL
    SELECT 10, 'counterparty_tax_no_norm', 'equals',   '8461043678', (SELECT id FROM fin_categories WHERE slug='samochod-paliwo') UNION ALL
    SELECT 50, 'counterparty_name',        'contains', 'stacja paliw', (SELECT id FROM fin_categories WHERE slug='samochod-paliwo') UNION ALL
    SELECT 50, 'counterparty_name',        'contains', 'serwis opon',  (SELECT id FROM fin_categories WHERE slug='samochod-eksploatacja') UNION ALL
    SELECT 60, 'accounting_kind',          'equals',   'fuel_expl75',  (SELECT id FROM fin_categories WHERE slug='samochod-paliwo') UNION ALL
    SELECT 60, 'accounting_kind',          'equals',   'fuel0',        (SELECT id FROM fin_categories WHERE slug='samochod-paliwo')
) AS seed
WHERE seed.c IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM (SELECT * FROM fin_category_rules) r
                  WHERE r.match_field = seed.f AND r.match_value = seed.v);
