ALTER TABLE crm_tags MODIFY kind ENUM('tag','industry','source','email') NOT NULL;
ALTER TABLE crm_contacts DROP COLUMN marketing_consent_at;
ALTER TABLE email_footers ADD COLUMN kind ENUM('footer','unsubscribe') NOT NULL DEFAULT 'footer' AFTER name;
