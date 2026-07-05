-- ============================================================
-- RośliNarnia Finanse — usuwa WSZYSTKIE tabele aplikacji z bazy.
-- UWAGA: nieodwracalne — kasuje całą strukturę i dane.
-- Po uruchomieniu bazę można odtworzyć od podstaw plikiem schema.sql.
-- Uruchomić ręcznie przez phpMyAdmin, tylko gdy naprawdę chcesz
-- wyzerować bazę.
-- ============================================================

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS crm_history;
DROP TABLE IF EXISTS crm_notes;
DROP TABLE IF EXISTS crm_company_tags;
DROP TABLE IF EXISTS crm_tags;
DROP TABLE IF EXISTS crm_deal_payments;
DROP TABLE IF EXISTS crm_deals;
DROP TABLE IF EXISTS crm_contacts;
DROP TABLE IF EXISTS crm_companies;

DROP TABLE IF EXISTS gdrive_invoices;
DROP TABLE IF EXISTS bank_import_log;
DROP TABLE IF EXISTS income_transactions;
DROP TABLE IF EXISTS expense_transactions;
DROP TABLE IF EXISTS bank_transactions;
DROP TABLE IF EXISTS sync_log;
DROP TABLE IF EXISTS fakturownia_invoices;
DROP TABLE IF EXISTS incomes;
DROP TABLE IF EXISTS expenses;

DROP TABLE IF EXISTS user_settings;
DROP TABLE IF EXISTS settings;
DROP TABLE IF EXISTS dictionary_items;
DROP TABLE IF EXISTS users;

SET FOREIGN_KEY_CHECKS = 1;
