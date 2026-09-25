-- Listy kontaktów — nazwane grupy definiowane w Ustawieniach (nazwa + kolory,
-- tak jak konteksty GTD). Kontakt może należeć do wielu list naraz, więc relacja
-- jest M:N — inaczej niż kontekst, którego kontakt ma najwyżej jeden.
CREATE TABLE IF NOT EXISTS crm_contact_lists (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(80) NOT NULL,
    badge_color VARCHAR(7) NOT NULL DEFAULT '#3B82F6',
    text_color  VARCHAR(7) NOT NULL DEFAULT '#1F2937',
    description VARCHAR(255) NULL,
    sort_order  INT NOT NULL DEFAULT 0,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uniq_crm_contact_list_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS crm_contact_list_members (
    list_id    INT NOT NULL,
    contact_id INT NOT NULL,
    added_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (list_id, contact_id),
    KEY idx_ccl_members_contact (contact_id),
    CONSTRAINT fk_ccl_members_list FOREIGN KEY (list_id)
        REFERENCES crm_contact_lists(id) ON DELETE CASCADE,
    CONSTRAINT fk_ccl_members_contact FOREIGN KEY (contact_id)
        REFERENCES crm_contacts(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
