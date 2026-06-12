-- Historia importów transakcji bankowych
-- Uruchomić przez phpMyAdmin na bazie brzychu_roslinarnia

CREATE TABLE IF NOT EXISTS bank_import_log (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    bank        VARCHAR(50) NOT NULL,
    filename    VARCHAR(255),
    rows_found  INT NOT NULL DEFAULT 0,
    rows_new    INT NOT NULL DEFAULT 0,
    status      VARCHAR(20) NOT NULL DEFAULT 'ok',
    message     TEXT,
    KEY idx_imported_at (imported_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
