-- Nowy moduł Finanse (v2). Fakturownia jest źródłem prawdy dla dokumentów,
-- CRM trzyma lustro + własne metadane analityczne, których w Fakturowni nie ma.
-- Stary moduł (expenses, incomes, fakturownia_invoices, …) zostaje nietknięty.

-- ── Lustro dokumentów z Fakturowni ───────────────────────────────────────────
-- Pola przepisywane z API są VARCHAR, nie ENUM: gdy Fakturownia doda nową
-- wartość, MySQL ma ją zapisać, a nie uciąć do pustego stringa.
CREATE TABLE IF NOT EXISTS fin_documents (
    id                     INT AUTO_INCREMENT PRIMARY KEY,
    fakturownia_id         BIGINT        NOT NULL UNIQUE,
    department_id          INT,
    kind                   VARCHAR(32)   NOT NULL DEFAULT 'vat',
    is_income              TINYINT(1)    NOT NULL DEFAULT 0,
    number                 VARCHAR(128)  NOT NULL DEFAULT '',
    issue_date             DATE,
    sell_date              DATE,
    delivery_date          DATE,
    payment_to             DATE,
    paid_date              DATE,
    status                 VARCHAR(24)   NOT NULL DEFAULT 'issued',
    currency               VARCHAR(3)    NOT NULL DEFAULT 'PLN',
    exchange_rate          DECIMAL(12,6) NOT NULL DEFAULT 1.000000,
    price_net              DECIMAL(14,2) NOT NULL DEFAULT 0.00,
    price_tax              DECIMAL(14,2) NOT NULL DEFAULT 0.00,
    price_gross            DECIMAL(14,2) NOT NULL DEFAULT 0.00,
    paid_amount            DECIMAL(14,2) NOT NULL DEFAULT 0.00,
    -- Kwoty w PLN: dla PLN równe powyższym, dla walut obcych przeliczone kursem.
    net_pln                DECIMAL(14,2) NOT NULL DEFAULT 0.00,
    tax_pln                DECIMAL(14,2) NOT NULL DEFAULT 0.00,
    gross_pln              DECIMAL(14,2) NOT NULL DEFAULT 0.00,
    -- Kontrahent zawsze z buyer_*: przy kosztach Fakturownia trzyma tam dostawcę,
    -- przy przychodach klienta. Jedna reguła, bez wyjątków.
    counterparty_name      VARCHAR(256)  NOT NULL DEFAULT '',
    counterparty_tax_no    VARCHAR(32)   NOT NULL DEFAULT '',
    accounting_kind        VARCHAR(32)   NOT NULL DEFAULT '',
    fakturownia_category_id INT,
    gov_id                 VARCHAR(128)  NOT NULL DEFAULT '',
    gov_status             VARCHAR(40)   NOT NULL DEFAULT '',
    gov_send_date          DATETIME,
    description            TEXT,
    oid                    VARCHAR(128)  NOT NULL DEFAULT '',
    raw_json               LONGTEXT,
    fakturownia_updated_at DATETIME,
    synced_at              DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_at             DATETIME      DEFAULT CURRENT_TIMESTAMP,
    KEY idx_fin_doc_income_issue (is_income, issue_date),
    KEY idx_fin_doc_due (status, payment_to),
    KEY idx_fin_doc_tax_no (counterparty_tax_no),
    KEY idx_fin_doc_updated (fakturownia_updated_at),
    KEY idx_fin_doc_gov (gov_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── Taksonomia kategorii (żyje w CRM, nie w Fakturowni) ──────────────────────
CREATE TABLE IF NOT EXISTS fin_categories (
    id                     INT AUTO_INCREMENT PRIMARY KEY,
    kind                   ENUM('cost','income') NOT NULL DEFAULT 'cost',
    name                   VARCHAR(128)  NOT NULL,
    slug                   VARCHAR(128)  NOT NULL UNIQUE,
    parent_id              INT,
    default_vat_deduction  TINYINT       NOT NULL DEFAULT 100,
    default_tax_deductible TINYINT       NOT NULL DEFAULT 100,
    is_fixed_cost          TINYINT(1)    NOT NULL DEFAULT 0,
    sort_order             INT           NOT NULL DEFAULT 0,
    archived_at            DATETIME,
    created_at             DATETIME      DEFAULT CURRENT_TIMESTAMP,
    KEY idx_fin_cat_kind (kind, sort_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── Metadane analityczne dokumentu ───────────────────────────────────────────
-- Osobna tabela, klucz po fakturownia_id: pełny re-sync lustra nigdy nie kasuje
-- kategoryzacji.
CREATE TABLE IF NOT EXISTS fin_document_meta (
    fakturownia_id         BIGINT        PRIMARY KEY,
    category_id            INT,
    vat_deduction_percent  TINYINT       NOT NULL DEFAULT 100,
    tax_deductible_percent TINYINT       NOT NULL DEFAULT 100,
    is_private_use         TINYINT(1)    NOT NULL DEFAULT 0,
    note                   TEXT,
    source                 ENUM('manual','rule','agent') NOT NULL DEFAULT 'manual',
    rule_id                INT,
    categorized_at         DATETIME      DEFAULT CURRENT_TIMESTAMP,
    updated_at             DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_fin_meta_category (category_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── Reguły auto-kategoryzacji ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fin_category_rules (
    id                     INT AUTO_INCREMENT PRIMARY KEY,
    priority               INT           NOT NULL DEFAULT 100,
    match_field            VARCHAR(32)   NOT NULL DEFAULT 'counterparty_name',
    match_type             VARCHAR(16)   NOT NULL DEFAULT 'contains',
    match_value            VARCHAR(256)  NOT NULL,
    category_id            INT           NOT NULL,
    vat_deduction_percent  TINYINT,
    tax_deductible_percent TINYINT,
    is_active              TINYINT(1)    NOT NULL DEFAULT 1,
    hits                   INT           NOT NULL DEFAULT 0,
    last_hit_at            DATETIME,
    created_at             DATETIME      DEFAULT CURRENT_TIMESTAMP,
    KEY idx_fin_rule_active (is_active, priority)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── Transakcje bankowe (import CSV) ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fin_bank_transactions (
    id                     INT AUTO_INCREMENT PRIMARY KEY,
    external_id            VARCHAR(64)   NOT NULL UNIQUE,
    bank                   VARCHAR(32)   NOT NULL DEFAULT '',
    booked_date            DATE          NOT NULL,
    amount                 DECIMAL(14,2) NOT NULL,
    currency               VARCHAR(3)    NOT NULL DEFAULT 'PLN',
    counterparty_name      VARCHAR(256)  NOT NULL DEFAULT '',
    counterparty_account   VARCHAR(64)   NOT NULL DEFAULT '',
    title                  VARCHAR(512)  NOT NULL DEFAULT '',
    matched_amount         DECIMAL(14,2) NOT NULL DEFAULT 0.00,
    status                 VARCHAR(16)   NOT NULL DEFAULT 'pending',
    raw_data               TEXT,
    imported_at            DATETIME      DEFAULT CURRENT_TIMESTAMP,
    KEY idx_fin_txn_status (status, booked_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS fin_payment_links (
    id                     INT AUTO_INCREMENT PRIMARY KEY,
    transaction_id         INT           NOT NULL,
    fakturownia_id         BIGINT        NOT NULL,
    amount_applied         DECIMAL(14,2) NOT NULL,
    fakturownia_payment_id BIGINT,
    created_by             VARCHAR(64)   NOT NULL DEFAULT '',
    created_at             DATETIME      DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_fin_link (transaction_id, fakturownia_id),
    KEY idx_fin_link_doc (fakturownia_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── Podatki ──────────────────────────────────────────────────────────────────
-- Stawki i progi zmieniają się co roku, więc siedzą w bazie, nie w kodzie.
CREATE TABLE IF NOT EXISTS fin_tax_rates (
    id                     INT AUTO_INCREMENT PRIMARY KEY,
    year                   SMALLINT      NOT NULL,
    `key`                  VARCHAR(64)   NOT NULL,
    value                  DECIMAL(14,4) NOT NULL,
    note                   VARCHAR(256)  NOT NULL DEFAULT '',
    UNIQUE KEY uq_fin_rate (year, `key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS fin_tax_obligations (
    id                     INT AUTO_INCREMENT PRIMARY KEY,
    kind                   VARCHAR(24)   NOT NULL,
    period                 VARCHAR(7)    NOT NULL,
    amount_calculated      DECIMAL(14,2) NOT NULL DEFAULT 0.00,
    amount_declared        DECIMAL(14,2),
    due_date               DATE,
    paid_at                DATE,
    note                   TEXT,
    created_at             DATETIME      DEFAULT CURRENT_TIMESTAMP,
    updated_at             DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_fin_obligation (kind, period),
    KEY idx_fin_obligation_due (paid_at, due_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── Stan synchronizacji i dziennik zapisów ───────────────────────────────────
CREATE TABLE IF NOT EXISTS fin_sync_state (
    resource               VARCHAR(32)   PRIMARY KEY,
    cursor_updated_at      DATETIME,
    last_run_at            DATETIME,
    last_status            VARCHAR(16)   NOT NULL DEFAULT '',
    items_seen             INT           NOT NULL DEFAULT 0,
    items_changed          INT           NOT NULL DEFAULT 0,
    message                TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Każdy zapis CRM → Fakturownia. Agent zewnętrzny rusza prawdziwą księgowość,
-- więc musi po sobie zostawiać ślad.
CREATE TABLE IF NOT EXISTS fin_audit_log (
    id                     INT AUTO_INCREMENT PRIMARY KEY,
    actor                  VARCHAR(64)   NOT NULL DEFAULT '',
    action                 VARCHAR(64)   NOT NULL,
    fakturownia_id         BIGINT,
    payload                TEXT,
    response               TEXT,
    ok                     TINYINT(1)    NOT NULL DEFAULT 1,
    created_at             DATETIME      DEFAULT CURRENT_TIMESTAMP,
    KEY idx_fin_audit_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── Kategorie startowe ───────────────────────────────────────────────────────
INSERT INTO fin_categories (kind, name, slug, default_vat_deduction, default_tax_deductible, is_fixed_cost, sort_order) VALUES
    ('cost', 'Usługi obce i podwykonawcy', 'uslugi-obce',        100, 100, 0, 10),
    ('cost', 'Subskrypcje i SaaS',         'subskrypcje',        100, 100, 1, 20),
    ('cost', 'Infrastruktura IT',          'infrastruktura-it',  100, 100, 1, 30),
    ('cost', 'AI i narzędzia',             'ai-narzedzia',       100, 100, 1, 40),
    ('cost', 'Marketing i reklama',        'marketing',          100, 100, 0, 50),
    ('cost', 'Samochód — paliwo',          'samochod-paliwo',     50,  75, 0, 60),
    ('cost', 'Samochód — eksploatacja',    'samochod-eksploatacja', 50, 75, 0, 70),
    ('cost', 'Podróże służbowe',           'podroze',            100, 100, 0, 80),
    ('cost', 'Reprezentacja',              'reprezentacja',        0,   0, 0, 90),
    ('cost', 'Biuro i media',              'biuro-media',        100, 100, 1, 100),
    ('cost', 'Wyposażenie i sprzęt',       'wyposazenie',        100, 100, 0, 110),
    ('cost', 'Szkolenia i literatura',     'szkolenia',          100, 100, 0, 120),
    ('cost', 'Księgowość i prawo',         'ksiegowosc-prawo',   100, 100, 1, 130),
    ('cost', 'Opłaty bankowe i finansowe', 'oplaty-bankowe',       0, 100, 0, 140),
    ('cost', 'Telekomunikacja',            'telekomunikacja',    100, 100, 1, 150),
    ('cost', 'Ubezpieczenia',              'ubezpieczenia',        0, 100, 1, 160),
    ('cost', 'Podatki i składki',          'podatki-skladki',      0,   0, 1, 170),
    ('cost', 'Do wyjaśnienia',             'do-wyjasnienia',     100, 100, 0, 999),
    ('income', 'Doradztwo i success fee',  'doradztwo',          100, 100, 0, 10),
    ('income', 'Abonament (retainer)',     'abonament',          100, 100, 1, 20),
    ('income', 'Projekty jednorazowe',     'projekty',           100, 100, 0, 30),
    ('income', 'Refaktury',                'refaktury',          100, 100, 0, 40),
    ('income', 'Pozostałe',                'pozostale-przychody',100, 100, 0, 999)
ON DUPLICATE KEY UPDATE name = VALUES(name);
