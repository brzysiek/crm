-- Rozszerza słownik crm_tags o kind='source', żeby "źródła" firm mogły mieć
-- pełny CRUD w Ustawieniach (zakładka CRM), tak samo jak tagi i branże.
ALTER TABLE crm_tags MODIFY kind ENUM('tag','industry','source') NOT NULL;
