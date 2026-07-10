ALTER TABLE crm_history
    ADD COLUMN entry_type VARCHAR(20) NULL AFTER action;

UPDATE crm_history SET entry_type = action WHERE entry_type IS NULL;
