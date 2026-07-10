ALTER TABLE crm_history
    ADD COLUMN file_id INT NULL AFTER summary;

ALTER TABLE crm_history
    ADD CONSTRAINT fk_crm_history_file FOREIGN KEY (file_id) REFERENCES crm_files(id) ON DELETE SET NULL;
