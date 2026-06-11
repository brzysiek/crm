-- Migracja: dodanie pola osoby odpowiedzialnej do tabeli incomes
-- Uruchomić przez phpMyAdmin na bazie brzychu_roslinarnia

ALTER TABLE incomes
    ADD COLUMN IF NOT EXISTS paid_by VARCHAR(128) AFTER notes;
