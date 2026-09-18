-- Osobne tagi dla firm/kontaktów M&A (mna_companies/mna_contacts) — celowo NIE
-- współdzielone z crm_tags/crm_company_tags/crm_contact_tags, żeby tagowanie
-- leadów/klientów CRM nie mieszało się z tagowaniem celów M&A.

CREATE TABLE IF NOT EXISTS mna_tags (
    id    INT AUTO_INCREMENT PRIMARY KEY,
    name  VARCHAR(255) NOT NULL,
    UNIQUE KEY uniq_mna_tag_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS mna_company_tags (
    company_id  INT NOT NULL,
    tag_id      INT NOT NULL,
    PRIMARY KEY (company_id, tag_id),
    KEY idx_mna_company_tags_tag (tag_id),
    FOREIGN KEY (company_id) REFERENCES mna_companies(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES mna_tags(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS mna_contact_tags (
    contact_id  INT NOT NULL,
    tag_id      INT NOT NULL,
    PRIMARY KEY (contact_id, tag_id),
    KEY idx_mna_contact_tags_tag (tag_id),
    FOREIGN KEY (contact_id) REFERENCES mna_contacts(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES mna_tags(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
