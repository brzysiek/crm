-- Finanse v2: dokumenty z Dysku Google (PDF → OCR → kolejka → dokument).
-- Fakturownia przestaje być jedynym źródłem dokumentów: to, czego w niej nie
-- ma (np. faktury zagraniczne trzymane tylko jako PDF), wchodzi z Dysku.

-- `source` mówi, skąd dokument pochodzi. Dokument z Dysku nie ma odpowiednika
-- w Fakturowni, więc jego `fakturownia_id` to identyfikator z osobnej puli
-- (9 000 000 000 000 + id z kolejki) — dzięki temu kategorie, powiązania
-- z przelewami i podatki działają na nim bez zmian w tych tabelach.
ALTER TABLE fin_documents
    ADD COLUMN source         VARCHAR(16)  NOT NULL DEFAULT 'fakturownia',
    ADD COLUMN gdrive_file_id VARCHAR(128) NOT NULL DEFAULT '';

-- Kolejka: wynik OCR czeka tu na zatwierdzenie. Dopiero zatwierdzony wiersz
-- staje się dokumentem w `fin_documents` — błędny odczyt nie trafia do sum.
CREATE TABLE IF NOT EXISTS fin_drive_documents (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    gdrive_file_id      VARCHAR(128)  NOT NULL UNIQUE,
    file_name           VARCHAR(512)  NOT NULL DEFAULT '',
    file_modified_at    DATETIME,
    status              VARCHAR(16)   NOT NULL DEFAULT 'pending',
    is_income           TINYINT(1)    NOT NULL DEFAULT 0,
    kind                VARCHAR(32)   NOT NULL DEFAULT 'vat',
    number              VARCHAR(128)  NOT NULL DEFAULT '',
    counterparty_name   VARCHAR(256)  NOT NULL DEFAULT '',
    counterparty_tax_no VARCHAR(32)   NOT NULL DEFAULT '',
    issue_date          DATE,
    payment_to          DATE,
    currency            VARCHAR(3)    NOT NULL DEFAULT 'PLN',
    price_net           DECIMAL(14,2) NOT NULL DEFAULT 0.00,
    price_tax           DECIMAL(14,2) NOT NULL DEFAULT 0.00,
    price_gross         DECIMAL(14,2) NOT NULL DEFAULT 0.00,
    ocr_note            TEXT,
    ocr_raw             LONGTEXT,
    fakturownia_id      BIGINT,
    decided_by          VARCHAR(64)   NOT NULL DEFAULT '',
    created_at          DATETIME      DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_fin_drive_status (status, issue_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
