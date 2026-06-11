-- Uruchomienie: mysql -u root -p < setup_db.sql
-- UWAGA: Skopiuj ten plik do setup_db.sql i wpisz prawdziwe hasło.
--        setup_db.sql jest w .gitignore — nie commituj go.

CREATE DATABASE IF NOT EXISTS roslinnarnia_finance
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'roslinnarnia_user'@'localhost'
    IDENTIFIED BY 'ZMIEN_NA_SWOJE_HASLO';

GRANT ALL PRIVILEGES ON roslinnarnia_finance.*
    TO 'roslinnarnia_user'@'localhost';

FLUSH PRIVILEGES;

USE roslinnarnia_finance;

-- ── Użytkownicy ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(64)  NOT NULL UNIQUE,
    full_name     VARCHAR(128) NOT NULL,
    email         VARCHAR(128),
    password_hash VARCHAR(256) NOT NULL,
    role          ENUM('admin', 'owner', 'cashier') DEFAULT 'cashier',
    is_active     TINYINT(1) DEFAULT 1,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- ── Wydatki ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS expenses (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    date                DATE         NOT NULL,
    responsible_person  VARCHAR(128) NOT NULL,
    description         TEXT         NOT NULL,
    amount_gross        DECIMAL(12,2) NOT NULL,
    vat_rate            DECIMAL(5,2)  NOT NULL,
    amount_net          DECIMAL(12,2) NOT NULL,
    payment_percent     DECIMAL(5,2)  DEFAULT 0.00,
    invoice_status      ENUM('ksef','disk','none') DEFAULT 'none',
    invoice_ref         VARCHAR(256),
    paid_by             VARCHAR(128),
    payment_method      ENUM('transfer','card','cash') DEFAULT NULL,
    is_recurring        TINYINT(1) DEFAULT 0,
    category            VARCHAR(64),
    fakturownia_id      VARCHAR(64) UNIQUE,
    fakturownia_status  ENUM('manual','imported','pending_review') DEFAULT 'manual',
    notes               TEXT,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- ── Faktury z Fakturowni (bufor) ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fakturownia_invoices (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    fakturownia_id      VARCHAR(64)   UNIQUE NOT NULL,
    invoice_number      VARCHAR(64)   NOT NULL,
    vendor_name         VARCHAR(256),
    vendor_nip          VARCHAR(32),
    issue_date          DATE,
    amount_gross        DECIMAL(12,2),
    amount_net          DECIMAL(12,2),
    vat_amount          DECIMAL(12,2),
    ksef_number         VARCHAR(128),
    raw_json            LONGTEXT,
    status              ENUM('pending','assigned','rejected') DEFAULT 'pending',
    assigned_expense_id INT REFERENCES expenses(id),
    synced_at           DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ── Ustawienia aplikacji ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS settings (
    `key`      VARCHAR(128) PRIMARY KEY,
    value      TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

INSERT IGNORE INTO settings (`key`, value) VALUES
    ('fakturownia_subdomain',       ''),
    ('fakturownia_api_key',         ''),
    ('fakturownia_sync_schedule',   'manual'),
    ('fakturownia_last_sync',       NULL),
    ('fakturownia_filter_category', 'expense');

-- ── Log synchronizacji ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sync_log (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    synced_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
    invoices_fetched INT DEFAULT 0,
    invoices_new     INT DEFAULT 0,
    invoices_pending INT DEFAULT 0,
    status           ENUM('ok','error') NOT NULL,
    message          TEXT
);
