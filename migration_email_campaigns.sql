-- Moduł kampanii email (wysyłka seryjna przez Gmail/Workspace)

CREATE TABLE IF NOT EXISTS crm_contact_tags (
    contact_id INT NOT NULL,
    tag_id INT NOT NULL,
    PRIMARY KEY (contact_id, tag_id),
    FOREIGN KEY (contact_id) REFERENCES crm_contacts(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES crm_tags(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE crm_contacts ADD COLUMN marketing_consent_at DATETIME NULL AFTER is_starred;

CREATE TABLE IF NOT EXISTS email_campaigns (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    subject VARCHAR(500) NOT NULL,
    body_text TEXT NOT NULL,
    status ENUM('draft','sending','sent') NOT NULL DEFAULT 'draft',
    created_by INT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    sent_at DATETIME NULL,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS email_campaign_tags (
    campaign_id INT NOT NULL,
    tag_id INT NOT NULL,
    PRIMARY KEY (campaign_id, tag_id),
    FOREIGN KEY (campaign_id) REFERENCES email_campaigns(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES crm_tags(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS email_campaign_recipients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    campaign_id INT NOT NULL,
    contact_id INT NULL,
    email VARCHAR(255) NOT NULL,
    status ENUM('pending','sent','failed','skipped_unsubscribed') NOT NULL DEFAULT 'pending',
    unsubscribe_token VARCHAR(64) NOT NULL,
    gmail_message_id VARCHAR(255) NULL,
    error_message TEXT NULL,
    sent_at DATETIME NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_unsub_token (unsubscribe_token),
    KEY idx_campaign_status (campaign_id, status),
    FOREIGN KEY (campaign_id) REFERENCES email_campaigns(id) ON DELETE CASCADE,
    FOREIGN KEY (contact_id) REFERENCES crm_contacts(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS email_unsubscribes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    campaign_id INT NULL,
    unsubscribed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_email (email),
    FOREIGN KEY (campaign_id) REFERENCES email_campaigns(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
