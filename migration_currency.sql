-- Dodanie obsługi walut obcych do tabel faktur
-- currency: kod waluty oryginalnej (np. PLN, EUR, USD)
-- orig_amount: kwota brutto w oryginalnej walucie (NULL jeśli PLN)
-- exchange_rate: kurs NBP użyty do przeliczenia (NULL jeśli PLN)

ALTER TABLE fakturownia_invoices
  ADD COLUMN IF NOT EXISTS currency      VARCHAR(3)     NOT NULL DEFAULT 'PLN',
  ADD COLUMN IF NOT EXISTS orig_amount   DECIMAL(12,2)  DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS exchange_rate DECIMAL(10,6)  DEFAULT NULL;

ALTER TABLE gdrive_invoices
  ADD COLUMN IF NOT EXISTS currency      VARCHAR(3)     NOT NULL DEFAULT 'PLN',
  ADD COLUMN IF NOT EXISTS orig_amount   DECIMAL(12,2)  DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS exchange_rate DECIMAL(10,6)  DEFAULT NULL;
