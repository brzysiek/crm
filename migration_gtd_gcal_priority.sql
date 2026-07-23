-- Pozwala oznaczyć wydarzenie z Google Calendar gwiazdką jako priorytet dnia,
-- tak samo jak zadania GTD (tasks.is_today_priority).
ALTER TABLE gcal_event_done
    ADD COLUMN is_today_priority TINYINT(1) NOT NULL DEFAULT 0 AFTER done_at;
