-- Sprząta tagi/branże/źródła, które po imporcie wylądowały jako jeden sklejony
-- wpis z przecinkami (np. "Prawo własności przemysłowej, patenty, znaki towarowe").
-- Rozdziela taki wpis na osobne tagi (bez duplikatów, jeśli już istnieją),
-- przepina powiązania firm z sklejonego tagu na nowo powstałe, a na końcu
-- usuwa sklejony tag (kaskadowo czyści też stare powiązania w crm_company_tags).
--
-- Bezpieczne do wielokrotnego uruchomienia — INSERT IGNORE pomija duplikaty.

DROP TEMPORARY TABLE IF EXISTS tmp_tag_split;
CREATE TEMPORARY TABLE tmp_tag_split AS
SELECT
  t.id   AS old_tag_id,
  t.kind AS kind,
  TRIM(SUBSTRING_INDEX(SUBSTRING_INDEX(t.name, ',', n.n), ',', -1)) AS part
FROM crm_tags t
JOIN (
  SELECT 1 n UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL SELECT 5
  UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9 UNION ALL SELECT 10
  UNION ALL SELECT 11 UNION ALL SELECT 12 UNION ALL SELECT 13 UNION ALL SELECT 14 UNION ALL SELECT 15
  UNION ALL SELECT 16 UNION ALL SELECT 17 UNION ALL SELECT 18 UNION ALL SELECT 19 UNION ALL SELECT 20
) n ON CHAR_LENGTH(t.name) - CHAR_LENGTH(REPLACE(t.name, ',', '')) >= n.n - 1
WHERE t.name LIKE '%,%';

DELETE FROM tmp_tag_split WHERE part = '';

-- 1) Utwórz brakujące tagi powstałe z podziału (pomija te, które już istnieją).
INSERT IGNORE INTO crm_tags (kind, name)
SELECT DISTINCT kind, part FROM tmp_tag_split;

-- 2) Przypisz firmom, które miały sklejony tag, wszystkie tagi powstałe z podziału.
INSERT IGNORE INTO crm_company_tags (company_id, tag_id)
SELECT ct.company_id, nt.id
FROM crm_company_tags ct
JOIN tmp_tag_split s ON s.old_tag_id = ct.tag_id
JOIN crm_tags nt ON nt.kind = s.kind AND nt.name = s.part;

-- 3) Usuń sklejone tagi (ON DELETE CASCADE usuwa też stare wpisy w crm_company_tags).
DELETE FROM crm_tags WHERE id IN (SELECT DISTINCT old_tag_id FROM tmp_tag_split);

DROP TEMPORARY TABLE IF EXISTS tmp_tag_split;
