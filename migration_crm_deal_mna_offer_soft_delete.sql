-- Soft-delete (archiwizacja) dla deali i ofert M&A, analogicznie do tasks.deleted_at:
-- "Usuń" przestaje być trwałym DELETE, staje się odwracalną archiwizacją.
ALTER TABLE crm_deals ADD COLUMN deleted_at DATETIME NULL;
ALTER TABLE crm_mna_offers ADD COLUMN deleted_at DATETIME NULL;
