ALTER TABLE crm_companies ADD COLUMN is_starred TINYINT(1) NOT NULL DEFAULT 0 AFTER short_description;
ALTER TABLE crm_contacts ADD COLUMN is_starred TINYINT(1) NOT NULL DEFAULT 0 AFTER description;
