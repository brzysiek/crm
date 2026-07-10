-- ============================================================
-- RośliNarnia Finanse — pełny schemat bazy danych
-- Tworzy całą bazę od podstaw (stan po wszystkich migracjach).
-- Uruchomić przez phpMyAdmin na PUSTEJ bazie (baza musi już istnieć
-- na serwerze — bez CREATE DATABASE / CREATE USER).
-- ============================================================

-- ── Użytkownicy ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(64)  NOT NULL UNIQUE,
    full_name     VARCHAR(128) NOT NULL,
    email         VARCHAR(128),
    password_hash VARCHAR(256) NOT NULL,
    role          ENUM('admin','owner','cashier') DEFAULT 'cashier',
    is_active     TINYINT(1) DEFAULT 1,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Domyślny użytkownik: login=aadmin, hasło=12345678
INSERT IGNORE INTO users (username, full_name, role, password_hash) VALUES (
    'aadmin',
    'Administrator',
    'admin',
    'scrypt:32768:8:1$JxE8ts3xeIuIWpYR$b7dece926c2e8c733e0f3f1cfe51f0c6828ec8e1d1f3c8f5b71ad5be05c0207a94f3d3bc98bf08c6065f3c7aafba42f76deaf8f7ba8ada449994b556172f9185'
);

-- ── Słowniki (stawki VAT, formy płatności) ───────────────────────────────────
CREATE TABLE IF NOT EXISTS dictionary_items (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    dict_type  VARCHAR(50)  NOT NULL,
    value      VARCHAR(255) NOT NULL,
    label      VARCHAR(255) DEFAULT NULL,
    sort_order INT          DEFAULT 0,
    UNIQUE KEY uq_dict_type_value (dict_type, value)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT IGNORE INTO dictionary_items (dict_type, value, label, sort_order) VALUES
('vat_rate', '23',  '23%',          1),
('vat_rate', '8',   '8%',           2),
('vat_rate', '5',   '5%',           3),
('vat_rate', '0',   '0%',           4),
('vat_rate', '-1',  'zw.',          5),
('payment_method', 'transfer', 'Przelew / karta', 1),
('payment_method', 'cash',     'Gotówka',         2),
('expense_category', 'wewnętrzne', 'wewnętrzne', 1),
('income_category',  'wewnętrzne', 'wewnętrzne', 1);

-- ── Ustawienia aplikacji ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS settings (
    `key`      VARCHAR(128) PRIMARY KEY,
    value      MEDIUMTEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT IGNORE INTO settings (`key`, value) VALUES
    ('fakturownia_subdomain',       ''),
    ('fakturownia_api_key',         ''),
    ('fakturownia_sync_schedule',   'manual'),
    ('fakturownia_last_sync',       NULL),
    ('fakturownia_filter_category', 'all'),
    ('google_drive_folder_id',      ''),
    ('google_drive_api_token',      ''),
    ('gemini_api_key',              ''),
    ('gemini_model',                'gemini-2.5-flash');

-- ── Ustawienia użytkownika (np. widoczność/kolejność kolumn w tabelach) ─────
CREATE TABLE IF NOT EXISTS user_settings (
    user_id     INT NOT NULL,
    `key`       VARCHAR(128) NOT NULL,
    value       TEXT,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, `key`),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── Wydatki ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS expenses (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    date                DATE          NOT NULL,
    accounting_month    VARCHAR(7)    NOT NULL DEFAULT '',
    payment_due_date    DATE,
    responsible_person  VARCHAR(128)  NOT NULL,
    contractor_name     VARCHAR(256),
    contractor_nip      VARCHAR(32),
    invoice_number      VARCHAR(128),
    description         TEXT          NOT NULL,
    amount_gross        DECIMAL(12,2) NOT NULL,
    vat_rate            DECIMAL(5,2)  NOT NULL,
    amount_net          DECIMAL(12,2) NOT NULL,
    orig_amount         DECIMAL(12,2),
    orig_currency       VARCHAR(8),
    payment_percent     DECIMAL(5,2)  DEFAULT 0.00,
    invoice_status      ENUM('ksef','disk','none') DEFAULT 'none',
    invoice_ref         VARCHAR(256),
    paid_by             VARCHAR(128),
    payment_method      ENUM('transfer','card','cash') DEFAULT NULL,
    is_recurring        TINYINT(1) DEFAULT 0,
    category            VARCHAR(64),
    notes               TEXT,
    source              VARCHAR(128),
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_expenses_accounting_month (accounting_month)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── Przychody ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS incomes (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    date             DATE          NOT NULL,
    accounting_month VARCHAR(7)    NOT NULL DEFAULT '',
    payment_due_date DATE,
    client_name      VARCHAR(256),
    client_nip       VARCHAR(32),
    description      TEXT          NOT NULL,
    invoice_number   VARCHAR(128),
    amount_gross     DECIMAL(12,2) NOT NULL,
    vat_rate         DECIMAL(5,2)  NOT NULL DEFAULT 23.00,
    amount_net       DECIMAL(12,2) NOT NULL,
    orig_amount      DECIMAL(12,2),
    orig_currency    VARCHAR(8),
    invoice_status   ENUM('ksef','disk','none') DEFAULT 'none',
    invoice_ref      VARCHAR(256),
    payment_method   ENUM('transfer','card','cash') DEFAULT NULL,
    payment_status   ENUM('paid','unpaid','partial') DEFAULT 'unpaid',
    category         VARCHAR(64),
    fakturownia_id   VARCHAR(64) UNIQUE,
    notes            TEXT,
    paid_by          VARCHAR(128),
    source           VARCHAR(128),
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_incomes_accounting_month (accounting_month)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── Faktury z Fakturowni (bufor) ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fakturownia_invoices (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    fakturownia_id      VARCHAR(64)   UNIQUE NOT NULL,
    invoice_number      VARCHAR(64)   NOT NULL,
    vendor_name         VARCHAR(256),
    vendor_nip          VARCHAR(32),
    issue_date          DATE,
    payment_to          DATE,
    amount_gross        DECIMAL(12,2),
    amount_net          DECIMAL(12,2),
    vat_amount          DECIMAL(12,2),
    ksef_number         VARCHAR(128),
    invoice_type        ENUM('income','expense') DEFAULT 'expense',
    currency            VARCHAR(3)    NOT NULL DEFAULT 'PLN',
    orig_amount         DECIMAL(12,2),
    exchange_rate       DECIMAL(10,6),
    raw_json            LONGTEXT,
    status              ENUM('pending','assigned','rejected') DEFAULT 'pending',
    assigned_expense_id INT,
    synced_at           DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── Log synchronizacji Fakturowni ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sync_log (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    synced_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
    invoices_fetched INT DEFAULT 0,
    invoices_new     INT DEFAULT 0,
    invoices_pending INT DEFAULT 0,
    status           ENUM('ok','error') NOT NULL,
    message          TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── Transakcje bankowe ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bank_transactions (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    bank           VARCHAR(50)   NOT NULL,
    transaction_id VARCHAR(128)  NOT NULL,
    date           DATE          NOT NULL,
    description    TEXT,
    counterparty   VARCHAR(256),
    amount         DECIMAL(12,2) NOT NULL,
    orig_amount    DECIMAL(12,2),
    currency       VARCHAR(8)    DEFAULT 'PLN',
    orig_currency  VARCHAR(8),
    category       VARCHAR(128),
    balance        DECIMAL(12,2),
    raw_data       TEXT,
    status         VARCHAR(20)   NOT NULL DEFAULT 'pending',
    assigned_type  VARCHAR(20),
    assigned_id    INT,
    imported_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE INDEX uq_bank_transaction_id (transaction_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── Powiązania wydatek ↔ transakcja bankowa ──────────────────────────────────
CREATE TABLE IF NOT EXISTS expense_transactions (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    expense_id  INT NOT NULL,
    bank_txn_id INT NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_expense_txn (expense_id, bank_txn_id),
    KEY idx_expense_id  (expense_id),
    KEY idx_bank_txn_id (bank_txn_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── Powiązania przychód ↔ transakcja bankowa ─────────────────────────────────
CREATE TABLE IF NOT EXISTS income_transactions (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    income_id   INT NOT NULL,
    bank_txn_id INT NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_income_txn (income_id, bank_txn_id),
    KEY idx_income_id   (income_id),
    KEY idx_bank_txn_id (bank_txn_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── Log importów bankowych ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bank_import_log (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    bank        VARCHAR(50)  NOT NULL,
    filename    VARCHAR(255),
    rows_found  INT NOT NULL DEFAULT 0,
    rows_new    INT NOT NULL DEFAULT 0,
    status      VARCHAR(20)  NOT NULL DEFAULT 'ok',
    message     TEXT,
    KEY idx_imported_at (imported_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── Faktury z Google Drive (OCR) ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS gdrive_invoices (
    id                 INT AUTO_INCREMENT PRIMARY KEY,
    gdrive_file_id     VARCHAR(255)  NOT NULL UNIQUE,
    file_name          VARCHAR(500)  NOT NULL,
    file_modified_at   DATETIME,
    gdrive_year        INT,
    gdrive_month       INT,
    invoice_number     VARCHAR(255),
    vendor_name        VARCHAR(500),
    vendor_nip         VARCHAR(50),
    issue_date         DATE,
    payment_to         DATE,
    amount_gross       DECIMAL(12,2),
    amount_net         DECIMAL(12,2),
    vat_amount         DECIMAL(12,2),
    invoice_type       ENUM('expense','income') DEFAULT 'expense',
    currency           VARCHAR(3)    NOT NULL DEFAULT 'PLN',
    orig_amount        DECIMAL(12,2),
    exchange_rate      DECIMAL(10,6),
    ocr_raw            TEXT,
    status             ENUM('pending','assigned','rejected') DEFAULT 'pending',
    assigned_record_id INT DEFAULT NULL,
    created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_status     (status),
    INDEX idx_year_month (gdrive_year, gdrive_month)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── CRM: Firmy ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS crm_companies (
    id                 INT AUTO_INCREMENT PRIMARY KEY,
    name               VARCHAR(256) NOT NULL,
    short_name         VARCHAR(128),
    relation_type      ENUM('lead','client','partner','inne','dostawca') DEFAULT 'lead',
    country            VARCHAR(64) DEFAULT 'Polska',
    city               VARCHAR(128),
    voivodeship        VARCHAR(64),
    street             VARCHAR(256),
    house_number       VARCHAR(32),
    flat_number        VARCHAR(32),
    postal_code        VARCHAR(16),
    email              VARCHAR(128),
    phone              VARCHAR(32),
    nip                VARCHAR(32),
    krs                VARCHAR(32),
    website            VARCHAR(255),
    linkedin_url       VARCHAR(255),
    favicon_url        MEDIUMTEXT,
    description        TEXT,
    short_description  VARCHAR(255),
    is_starred         TINYINT(1) NOT NULL DEFAULT 0,
    archived_at        DATETIME NULL,
    owner_user_id      INT NULL,
    created_at         DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at         DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE SET NULL,
    KEY idx_relation (relation_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── CRM: Kontakty ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS crm_contacts (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    company_id        INT NULL,
    first_name        VARCHAR(128) NOT NULL,
    last_name         VARCHAR(128) NOT NULL,
    position          VARCHAR(128),
    email             VARCHAR(128),
    phone             VARCHAR(32),
    linkedin_url      VARCHAR(255),
    description       TEXT,
    is_starred        TINYINT(1) NOT NULL DEFAULT 0,
    archived_at       DATETIME NULL,
    created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at        DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES crm_companies(id) ON DELETE SET NULL,
    KEY idx_company (company_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── CRM: Interesy ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS crm_deals (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    name           VARCHAR(256) NOT NULL,
    description    TEXT,
    amount         DECIMAL(12,2),
    company_id     INT NULL,
    contact_id     INT NULL,
    stage          ENUM('new','in_progress','won','lost','someday') DEFAULT 'new',
    start_date     DATE,
    end_date       DATE,
    owner_user_id  INT NULL,
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at     DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES crm_companies(id) ON DELETE SET NULL,
    FOREIGN KEY (contact_id) REFERENCES crm_contacts(id) ON DELETE SET NULL,
    FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE SET NULL,
    KEY idx_stage (stage)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── CRM: Harmonogram płatności interesów ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS crm_deal_payments (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    deal_id     INT NOT NULL,
    pay_month   DATE NOT NULL,
    amount_net  DECIMAL(12,2) NOT NULL,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (deal_id) REFERENCES crm_deals(id) ON DELETE CASCADE,
    KEY idx_deal (deal_id),
    KEY idx_pay_month (pay_month)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── CRM: Wspólny słownik tagów/branż/źródeł (z podpowiedziami) ──────────────
CREATE TABLE IF NOT EXISTS crm_tags (
    id    INT AUTO_INCREMENT PRIMARY KEY,
    kind  ENUM('tag','industry','source') NOT NULL,
    name  VARCHAR(128) NOT NULL,
    UNIQUE KEY uq_kind_name (kind, name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS crm_company_tags (
    company_id INT NOT NULL,
    tag_id     INT NOT NULL,
    PRIMARY KEY (company_id, tag_id),
    FOREIGN KEY (company_id) REFERENCES crm_companies(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES crm_tags(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── CRM: Notatki i historia zmian — wspólne dla firm/kontaktów/interesów ────
CREATE TABLE IF NOT EXISTS crm_notes (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    entity_type    ENUM('company','contact','deal') NOT NULL,
    entity_id      INT NOT NULL,
    note_type      ENUM('phone','meeting','task','other') NOT NULL DEFAULT 'other',
    user_id        INT NULL,
    body           TEXT NOT NULL,
    audio_data     MEDIUMTEXT NULL,
    transcribed_at DATETIME NULL,
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    KEY idx_entity (entity_type, entity_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── CRM: Pliki — przetrzymywane na Google Drive (CRM/<firma>/pliki) ────────
CREATE TABLE IF NOT EXISTS crm_files (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    company_id    INT NOT NULL,
    contact_id    INT NULL,
    category      VARCHAR(20) NOT NULL DEFAULT 'file',
    file_name     VARCHAR(255) NOT NULL,
    drive_file_id VARCHAR(128) NOT NULL,
    mime_type     VARCHAR(128),
    file_size     INT,
    user_id       INT NULL,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES crm_companies(id) ON DELETE CASCADE,
    FOREIGN KEY (contact_id) REFERENCES crm_contacts(id) ON DELETE SET NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    KEY idx_company (company_id),
    KEY idx_contact_category (contact_id, category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS crm_history (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    entity_type ENUM('company','contact','deal') NOT NULL,
    entity_id   INT NOT NULL,
    user_id     INT NULL,
    action      ENUM('create','update','delete','file') NOT NULL,
    summary     TEXT NOT NULL,
    file_id     INT NULL,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (file_id) REFERENCES crm_files(id) ON DELETE SET NULL,
    KEY idx_entity (entity_type, entity_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS agent_tasks (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NULL,
    input_text  TEXT NOT NULL,
    intent      ENUM('note','create') NOT NULL,
    entity_type ENUM('company','contact','deal') NOT NULL,
    entity_id   INT NULL,
    summary     TEXT NOT NULL,
    status      ENUM('done','error') NOT NULL DEFAULT 'done',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
