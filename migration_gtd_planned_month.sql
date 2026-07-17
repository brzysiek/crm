ALTER TABLE tasks
    ADD COLUMN planned_month DATE NULL AFTER planned_week,
    ADD KEY idx_planned_month (planned_month);
