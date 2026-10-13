-- Finanse v2: rozliczenie dokumentu bez przelewu.
-- Nie każdy dokument ma operację na wyciągu: gotówka, karta prywatna,
-- kompensata, konto spoza wgranych wyciągów. Taki dokument dostaje tu decyzję
-- „rozliczony bez przelewu” z powodem i wychodzi z kolejki rozliczeń — bez
-- udawania powiązania z operacją, której nie było.
CREATE TABLE IF NOT EXISTS fin_settlements (
    fakturownia_id  BIGINT       NOT NULL PRIMARY KEY,
    reason          VARCHAR(24)  NOT NULL,
    settled_date    DATE,
    note            VARCHAR(512) NOT NULL DEFAULT '',
    -- 1 = przy tej decyzji dopisaliśmy zapłatę; cofnięcie wie wtedy, że ma ją
    -- przeliczyć (dokument z Dysku) albo o niej przypomnieć (Fakturownia).
    payment_marked  TINYINT(1)   NOT NULL DEFAULT 0,
    created_by      VARCHAR(64)  NOT NULL DEFAULT '',
    created_at      DATETIME     DEFAULT CURRENT_TIMESTAMP,
    KEY idx_fin_settlements_reason (reason)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
