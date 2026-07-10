ALTER TABLE crm_files
    ADD COLUMN category VARCHAR(20) NOT NULL DEFAULT 'file' AFTER contact_id;

ALTER TABLE crm_files
    ADD KEY idx_contact_category (contact_id, category);

ALTER TABLE crm_contacts
    DROP COLUMN business_card_url;
