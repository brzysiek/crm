ALTER TABLE tasks
    ADD COLUMN is_important TINYINT(1) NOT NULL DEFAULT 0 AFTER is_week_priority;
