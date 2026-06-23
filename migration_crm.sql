-- Moduł CRM: Firmy (Klienci), Kontakty, Interesy + tagi/branże, notatki, historia zmian

CREATE TABLE IF NOT EXISTS crm_companies (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(256) NOT NULL,
    short_name      VARCHAR(128),
    relation_type   ENUM('lead','client','partner') DEFAULT 'lead',
    country         VARCHAR(64) DEFAULT 'Polska',
    city            VARCHAR(128),
    street          VARCHAR(256),
    house_number    VARCHAR(32),
    flat_number     VARCHAR(32),
    postal_code     VARCHAR(16),
    email           VARCHAR(128),
    phone           VARCHAR(32),
    nip             VARCHAR(32),
    krs             VARCHAR(32),
    description     TEXT,
    source          VARCHAR(128),
    owner_user_id   INT NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE SET NULL,
    KEY idx_relation (relation_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS crm_contacts (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    company_id    INT NULL,
    first_name    VARCHAR(128) NOT NULL,
    last_name     VARCHAR(128) NOT NULL,
    position      VARCHAR(128),
    email         VARCHAR(128),
    phone         VARCHAR(32),
    description   TEXT,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES crm_companies(id) ON DELETE SET NULL,
    KEY idx_company (company_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS crm_deals (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    name           VARCHAR(256) NOT NULL,
    description    TEXT,
    amount         DECIMAL(12,2),
    company_id     INT NULL,
    contact_id     INT NULL,
    stage          ENUM('new','in_progress','won','lost','someday') DEFAULT 'new',
    start_date     DATE,
    end_date       DATE,
    owner_user_id  INT NULL,
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at     DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES crm_companies(id) ON DELETE SET NULL,
    FOREIGN KEY (contact_id) REFERENCES crm_contacts(id) ON DELETE SET NULL,
    FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE SET NULL,
    KEY idx_stage (stage)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Wspólny słownik tagów/branż (z podpowiedziami przy wpisywaniu).
-- "Źródło" jest jednowartościowe na firmie — to zwykła kolumna VARCHAR
-- (crm_companies.source) z podpowiedziami z istniejących wartości, bez tabeli słownikowej.
CREATE TABLE IF NOT EXISTS crm_tags (
    id    INT AUTO_INCREMENT PRIMARY KEY,
    kind  ENUM('tag','industry') NOT NULL,
    name  VARCHAR(128) NOT NULL,
    UNIQUE KEY uq_kind_name (kind, name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS crm_company_tags (
    company_id INT NOT NULL,
    tag_id     INT NOT NULL,
    PRIMARY KEY (company_id, tag_id),
    FOREIGN KEY (company_id) REFERENCES crm_companies(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES crm_tags(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Notatki i historia zmian — wspólne dla firm/kontaktów/interesów
CREATE TABLE IF NOT EXISTS crm_notes (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    entity_type ENUM('company','contact','deal') NOT NULL,
    entity_id   INT NOT NULL,
    user_id     INT NULL,
    body        TEXT NOT NULL,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    KEY idx_entity (entity_type, entity_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS crm_history (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    entity_type ENUM('company','contact','deal') NOT NULL,
    entity_id   INT NOT NULL,
    user_id     INT NULL,
    action      ENUM('create','update','delete') NOT NULL,
    summary     TEXT NOT NULL,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    KEY idx_entity (entity_type, entity_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
