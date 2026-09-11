-- Lokalny cache tytułu/godziny/czasu trwania/statusu odrzucenia wydarzeń
-- z Google Calendar, zapisywany przy okazji każdego ich pobrania (patrz
-- models/gcal_event.py::parse_and_cache). Pozwala pokazać przeszłe
-- wydarzenia na listach GTD (Wszystkie zadania, Wg kontekstu) bez
-- ponownego odpytywania Google Calendar.
ALTER TABLE gcal_event_done
    ADD COLUMN title        VARCHAR(500) NULL AFTER event_date,
    ADD COLUMN event_time   VARCHAR(5)   NULL AFTER title,
    ADD COLUMN duration_min INT          NULL AFTER event_time,
    ADD COLUMN is_declined  TINYINT(1)   NOT NULL DEFAULT 0 AFTER duration_min;
