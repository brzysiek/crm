-- Migracja: dodanie tabeli przychodów + kolumny invoice_type w fakturownia_invoices
-- Uruchomić przez phpMyAdmin na bazie brzychu_roslinarnia

-- ── 1. Dodaj kolumnę invoice_type do fakturownia_invoices ────────────────────
ALTER TABLE fakturownia_invoices
    ADD COLUMN IF NOT EXISTS invoice_type ENUM('income','expense') DEFAULT 'expense'
    AFTER ksef_number;

-- ── 2. Tabela przychodów ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS incomes (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    date             DATE          NOT NULL,
    client_name      VARCHAR(256),
    client_nip       VARCHAR(32),
    description      TEXT          NOT NULL,
    invoice_number   VARCHAR(128),
    amount_gross     DECIMAL(12,2) NOT NULL,
    vat_rate         DECIMAL(5,2)  NOT NULL DEFAULT 23.00,
    amount_net       DECIMAL(12,2) NOT NULL,
    invoice_status   ENUM('ksef','disk','none') DEFAULT 'none',
    invoice_ref      VARCHAR(256),
    payment_method   ENUM('transfer','card','cash') DEFAULT NULL,
    payment_status   ENUM('paid','unpaid','partial') DEFAULT 'unpaid',
    category         VARCHAR(64),
    fakturownia_id   VARCHAR(64) UNIQUE,
    notes            TEXT,
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
