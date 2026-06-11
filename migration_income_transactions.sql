-- Migracja: tabela powiązań przychód ↔ transakcja bankowa
-- Uruchomić przez phpMyAdmin na bazie brzychu_roslinarnia

CREATE TABLE IF NOT EXISTS income_transactions (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    income_id   INT NOT NULL,
    bank_txn_id INT NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_income_txn (income_id, bank_txn_id),
    KEY idx_income_id   (income_id),
    KEY idx_bank_txn_id (bank_txn_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
