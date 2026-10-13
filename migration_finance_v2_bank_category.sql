-- Finanse v2: kategoria na operacji bankowej.
-- Operacje bez dokumentu (opłaty bankowe, ZUS, podatki, przelewy własne) też
-- trzeba umieć opisać — kategoria dokumentu im nie pomoże, bo dokumentu nie ma.
-- Uruchomienie: venv/bin/python scripts/run_migration.py migration_finance_v2_bank_category.sql

ALTER TABLE fin_bank_transactions
    ADD COLUMN category_id INT NULL,
    ADD KEY idx_fin_bank_category (category_id);
