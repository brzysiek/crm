-- Moduł M&A: ewidencja ofert firm na sprzedaż i firm poszukiwanych.
-- Oba rodzaje ofert to ten sam obiekt, rozróżniany polem offer_type.
CREATE TABLE IF NOT EXISTS crm_mna_offers (
    id                 INT AUTO_INCREMENT PRIMARY KEY,
    name               VARCHAR(256) NOT NULL,
    description        TEXT,
    industry           VARCHAR(128),
    revenue            DECIMAL(14,2),
    ebitda             DECIMAL(14,2),
    offer_type         ENUM('for_sale','wanted') NOT NULL DEFAULT 'for_sale',
    target_contact_id  INT NULL,
    target_company_id  INT NULL,
    source_contact_id  INT NULL,
    source_company_id  INT NULL,
    owner_user_id      INT NULL,
    created_at         DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at         DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (target_contact_id) REFERENCES crm_contacts(id) ON DELETE SET NULL,
    FOREIGN KEY (target_company_id) REFERENCES crm_companies(id) ON DELETE SET NULL,
    FOREIGN KEY (source_contact_id) REFERENCES crm_contacts(id) ON DELETE SET NULL,
    FOREIGN KEY (source_company_id) REFERENCES crm_companies(id) ON DELETE SET NULL,
    FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE SET NULL,
    KEY idx_crm_mna_offers_type (offer_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
