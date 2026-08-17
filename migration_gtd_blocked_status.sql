-- Dodaje status 'blocked' (zablokowane) do zadań GTD.
ALTER TABLE tasks
    MODIFY COLUMN status ENUM('inbox','next','waiting','someday','done','blocked') NOT NULL DEFAULT 'inbox';
