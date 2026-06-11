-- Migracja: dodanie pól kontrahenta i numeru faktury do tabeli expenses
-- Uruchomić przez phpMyAdmin na bazie brzychu_roslinarnia

ALTER TABLE expenses
    ADD COLUMN IF NOT EXISTS contractor_name    VARCHAR(256) AFTER description,
    ADD COLUMN IF NOT EXISTS contractor_nip     VARCHAR(32)  AFTER contractor_name,
    ADD COLUMN IF NOT EXISTS invoice_number     VARCHAR(128) AFTER contractor_nip;
