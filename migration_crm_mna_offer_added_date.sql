-- Edytowalna data dodania oferty M&A (niezależna od automatycznego created_at).
ALTER TABLE crm_mna_offers ADD COLUMN added_date DATE NULL;
