-- Historia zadań asystenta AI (strona "Agent" → "Historia").
CREATE TABLE IF NOT EXISTS agent_tasks (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NULL,
    input_text  TEXT NOT NULL,
    intent      ENUM('note','create') NOT NULL,
    entity_type ENUM('company','contact','deal') NOT NULL,
    entity_id   INT NULL,
    summary     TEXT NOT NULL,
    status      ENUM('done','error') NOT NULL DEFAULT 'done',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
