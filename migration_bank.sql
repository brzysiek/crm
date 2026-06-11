-- Migracja: tabela transakcji bankowych
-- Uruchomić przez phpMyAdmin na bazie brzychu_roslinarnia

CREATE TABLE IF NOT EXISTS bank_transactions (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    bank           ENUM('mbank','unicredit') NOT NULL,
    transaction_id VARCHAR(128) UNIQUE NOT NULL,
    date           DATE         NOT NULL,
    description    TEXT,
    counterparty   VARCHAR(256),
    amount         DECIMAL(12,2) NOT NULL,
    currency       VARCHAR(8)   DEFAULT 'PLN',
    category       VARCHAR(128),
    balance        DECIMAL(12,2),
    raw_data       TEXT,
    status         ENUM('pending','assigned','rejected') DEFAULT 'pending',
    assigned_type  ENUM('expense','income'),
    assigned_id    INT,
    imported_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);
