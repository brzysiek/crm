ALTER TABLE tasks
    ADD COLUMN day_order INT NOT NULL DEFAULT 0 AFTER scheduled_duration_min;
