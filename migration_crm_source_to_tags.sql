-- Przenosi "Źródło" z wolnej kolumny crm_companies.source do relacyjnego
-- słownika (crm_tags kind='source' + crm_company_tags), tak samo jak
-- tagi i branże.

-- 1) Upewnij się, że każda używana wartość źródła istnieje w słowniku.
INSERT IGNORE INTO crm_tags (kind, name)
SELECT 'source', source FROM crm_companies
WHERE source IS NOT NULL AND source <> ''
GROUP BY source;

-- 2) Podepnij każdą firmę pod odpowiadający jej tag źródła.
INSERT IGNORE INTO crm_company_tags (company_id, tag_id)
SELECT c.id, t.id
FROM crm_companies c
JOIN crm_tags t ON t.kind = 'source' AND t.name = c.source
WHERE c.source IS NOT NULL AND c.source <> '';

-- 3) Kolumna nie jest już potrzebna — źródło jest teraz w pełni słownikowe.
ALTER TABLE crm_companies DROP COLUMN source;
