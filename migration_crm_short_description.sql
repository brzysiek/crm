-- Dodaje pole "Krótki opis" do firm CRM (osobne od pełnego pola "Opis").
ALTER TABLE crm_companies ADD COLUMN short_description VARCHAR(255) NULL AFTER description;
