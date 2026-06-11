-- Migracja: tabela powiązań wydatek ↔ transakcja bankowa
-- Uruchomić przez phpMyAdmin na bazie brzychu_roslinarnia

CREATE TABLE IF NOT EXISTS expense_transactions (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    expense_id  INT NOT NULL,
    bank_txn_id INT NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_expense_txn (expense_id, bank_txn_id),
    KEY idx_expense_id  (expense_id),
    KEY idx_bank_txn_id (bank_txn_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Upewniamy się, że kolumna status jest VARCHAR (nie ENUM)
-- żeby dało się dodać wartość 'accepted'
ALTER TABLE bank_transactions
    MODIFY COLUMN status VARCHAR(20) NOT NULL DEFAULT 'pending';
