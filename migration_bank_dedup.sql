-- Deduplication: unikalny indeks na transaction_id
-- Uruchomić przez phpMyAdmin na bazie brzychu_roslinarnia
-- Jeśli są już duplikaty, najpierw usuwa starsze (zachowuje nowsze id przy tym samym transaction_id)

-- Krok 1: usuń ewentualne istniejące duplikaty (zachowaj wiersz z najniższym id)
DELETE t1 FROM bank_transactions t1
  INNER JOIN bank_transactions t2
    ON t1.transaction_id = t2.transaction_id AND t1.id > t2.id;

-- Krok 2: dodaj UNIQUE constraint
ALTER TABLE bank_transactions
  ADD UNIQUE INDEX uq_bank_transaction_id (transaction_id);
