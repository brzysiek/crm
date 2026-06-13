-- Czyszczenie całej bazy danych (reset aplikacji)
-- Zachowuje tabelę users wraz z danymi.

SET FOREIGN_KEY_CHECKS = 0;

TRUNCATE TABLE income_transactions;
TRUNCATE TABLE expense_transactions;
TRUNCATE TABLE bank_import_log;
TRUNCATE TABLE bank_transactions;
TRUNCATE TABLE gdrive_invoices;
TRUNCATE TABLE fakturownia_invoices;
TRUNCATE TABLE sync_log;
TRUNCATE TABLE incomes;
TRUNCATE TABLE expenses;

SET FOREIGN_KEY_CHECKS = 1;
