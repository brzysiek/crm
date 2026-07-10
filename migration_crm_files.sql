ALTER TABLE crm_history MODIFY COLUMN action ENUM('create','update','delete','file') NOT NULL;

CREATE TABLE IF NOT EXISTS crm_files (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    company_id    INT NOT NULL,
    contact_id    INT NULL,
    file_name     VARCHAR(255) NOT NULL,
    drive_file_id VARCHAR(128) NOT NULL,
    mime_type     VARCHAR(128),
    file_size     INT,
    user_id       INT NULL,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES crm_companies(id) ON DELETE CASCADE,
    FOREIGN KEY (contact_id) REFERENCES crm_contacts(id) ON DELETE SET NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    KEY idx_company (company_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
