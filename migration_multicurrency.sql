-- Obsługa transakcji i dokumentów w walutach obcych
-- amount / amount_gross pozostaje ZAWSZE w PLN (waluta rozliczeniowa)
-- orig_amount / orig_currency przechowuje oryginalną kwotę w walucie obcej (NULL = PLN)

ALTER TABLE bank_transactions
    ADD COLUMN orig_amount   DECIMAL(12,2) DEFAULT NULL AFTER amount,
    ADD COLUMN orig_currency VARCHAR(8)    DEFAULT NULL AFTER currency;

ALTER TABLE expenses
    ADD COLUMN orig_amount   DECIMAL(12,2) DEFAULT NULL AFTER amount_net,
    ADD COLUMN orig_currency VARCHAR(8)    DEFAULT NULL AFTER orig_amount;

ALTER TABLE incomes
    ADD COLUMN orig_amount   DECIMAL(12,2) DEFAULT NULL AFTER amount_net,
    ADD COLUMN orig_currency VARCHAR(8)    DEFAULT NULL AFTER orig_amount;
