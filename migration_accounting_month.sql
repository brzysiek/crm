-- Dodaje "miesiąc księgowy" do wydatków i przychodów.
-- Domyślnie (dla istniejących rekordów) = miesiąc pola `date`.
-- Uruchomić ręcznie na produkcji przez phpMyAdmin po wdrożeniu kodu.

ALTER TABLE expenses ADD COLUMN accounting_month VARCHAR(7) NOT NULL DEFAULT '' AFTER date;
ALTER TABLE incomes  ADD COLUMN accounting_month VARCHAR(7) NOT NULL DEFAULT '' AFTER date;

UPDATE expenses SET accounting_month = DATE_FORMAT(date, '%Y-%m') WHERE accounting_month = '';
UPDATE incomes  SET accounting_month = DATE_FORMAT(date, '%Y-%m') WHERE accounting_month = '';

ALTER TABLE expenses ADD INDEX idx_expenses_accounting_month (accounting_month);
ALTER TABLE incomes  ADD INDEX idx_incomes_accounting_month (accounting_month);
