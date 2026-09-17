-- Rozszerza moduł M&A o własne firmy/kontakty (long list/short list) oraz
-- deale M&A — osobne od CRM-owych crm_companies/crm_contacts/crm_deals,
-- żeby nie mieszać kontaktów partnerów/leadów/klientów z celami M&A.

-- ── M&A: Firmy (cele long/short list) ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS mna_companies (
    id                 INT AUTO_INCREMENT PRIMARY KEY,
    name               VARCHAR(256) NOT NULL,
    short_name         VARCHAR(128),
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
    description        TEXT,
    short_description  VARCHAR(255),
    is_starred         TINYINT(1) NOT NULL DEFAULT 0,
    archived_at        DATETIME NULL,
    owner_user_id      INT NULL,
    created_at         DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at         DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── M&A: Kontakty ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS mna_contacts (
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
    FOREIGN KEY (company_id) REFERENCES mna_companies(id) ON DELETE SET NULL,
    KEY idx_company (company_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── M&A: Dealy (proces transakcyjny, opcjonalnie powiązany z ofertą M&A) ──────
CREATE TABLE IF NOT EXISTS mna_deals (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    name           VARCHAR(256) NOT NULL,
    description    TEXT,
    offer_id       INT NULL,
    stage          ENUM('long_list','short_list','kontakt_nawiazany','nda','ioi',
                         'due_diligence','loi','zamkniety','przegrany') NOT NULL DEFAULT 'long_list',
    amount         DECIMAL(14,2),
    start_date     DATE,
    end_date       DATE,
    owner_user_id  INT NULL,
    archived_at    DATETIME NULL,
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at     DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (offer_id) REFERENCES crm_mna_offers(id) ON DELETE SET NULL,
    FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE SET NULL,
    KEY idx_stage (stage)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── M&A: Pozycje long/short listy na dealu (firma i/lub kontakt) ─────────────
CREATE TABLE IF NOT EXISTS mna_deal_targets (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    deal_id         INT NOT NULL,
    company_id      INT NULL,
    contact_id      INT NULL,
    list_type       ENUM('long_list','short_list') NOT NULL DEFAULT 'long_list',
    interest_status ENUM('unknown','interested','not_interested') NOT NULL DEFAULT 'unknown',
    is_valuable     TINYINT(1) NOT NULL DEFAULT 0,
    sort_order      INT NOT NULL DEFAULT 0,
    added_by        INT NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (deal_id) REFERENCES mna_deals(id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES mna_companies(id) ON DELETE CASCADE,
    FOREIGN KEY (contact_id) REFERENCES mna_contacts(id) ON DELETE CASCADE,
    FOREIGN KEY (added_by) REFERENCES users(id) ON DELETE SET NULL,
    KEY idx_deal (deal_id, list_type),
    KEY idx_company (company_id),
    KEY idx_contact (contact_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── Rozszerzenie wspólnego słownika encji notatek/historii o firmy/kontakty/deale M&A ──
ALTER TABLE crm_notes
    MODIFY COLUMN entity_type ENUM('company','contact','deal','mna_offer','mna_company','mna_contact','mna_deal') NOT NULL;

ALTER TABLE crm_history
    MODIFY COLUMN entity_type ENUM('company','contact','deal','mna_offer','mna_company','mna_contact','mna_deal') NOT NULL;
