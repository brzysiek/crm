ALTER TABLE crm_notes
    ADD COLUMN note_type ENUM('phone','meeting','task','other') NOT NULL DEFAULT 'other' AFTER entity_id;
