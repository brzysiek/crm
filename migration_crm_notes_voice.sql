ALTER TABLE crm_notes
    ADD COLUMN audio_data MEDIUMTEXT NULL AFTER body,
    ADD COLUMN transcribed_at DATETIME NULL AFTER audio_data;
