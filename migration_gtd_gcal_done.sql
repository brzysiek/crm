-- Lokalne oznaczanie wydarzeń z Google Calendar jako "zrobione" w widokach GTD.
-- Nie modyfikuje samego kalendarza — obecność wiersza = zdarzenie oznaczone jako done w aplikacji.
CREATE TABLE IF NOT EXISTS gcal_event_done (
    event_id   VARCHAR(255) NOT NULL PRIMARY KEY,
    event_date DATE NOT NULL,
    done_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    KEY idx_event_date (event_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
