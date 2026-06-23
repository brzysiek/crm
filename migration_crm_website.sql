-- Dodanie strony WWW do firm CRM (do automatycznego pobierania danych ze strony)

ALTER TABLE crm_companies
    ADD COLUMN website VARCHAR(255) DEFAULT NULL AFTER krs;
