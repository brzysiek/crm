-- Usuwanie firm/kontaktów w CRM staje się archiwizacją (soft-delete) zamiast
-- trwałego DELETE, tak by dało się bezpiecznie zapytać przy usuwaniu firmy,
-- czy zarchiwizować też jej kontakty (i odwrotnie).
ALTER TABLE crm_companies ADD COLUMN archived_at DATETIME NULL;
ALTER TABLE crm_contacts ADD COLUMN archived_at DATETIME NULL;
