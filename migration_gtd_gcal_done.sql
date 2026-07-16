-- Lokalne metadane wydarzeń z Google Calendar w widokach GTD: oznaczenie "zrobione"
-- oraz przypisanie wydarzenia (spotkania) do projektu. Nie modyfikuje samego
-- kalendarza — to tylko lokalne dane aplikacji.
CREATE TABLE IF NOT EXISTS gcal_event_done (
    event_id   VARCHAR(255) NOT NULL PRIMARY KEY,
    event_date DATE NOT NULL,
    project_id INT NULL,
    done_at    DATETIME NULL,
    KEY idx_event_date (event_date),
    KEY idx_project (project_id),
    FOREIGN KEY (project_id) REFERENCES tasks(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
