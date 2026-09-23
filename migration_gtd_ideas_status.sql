-- Zmiana nazwy statusu zadań: 'inbox' -> 'ideas' („Pomysły do decyzji").
-- Najpierw dokładamy nową wartość do enuma, potem przepisujemy wiersze,
-- a na końcu usuwamy starą wartość i przestawiamy domyślną.

ALTER TABLE tasks
    MODIFY status ENUM('inbox','ideas','next','waiting','someday','done') NOT NULL DEFAULT 'inbox';

UPDATE tasks SET status = 'ideas' WHERE status = 'inbox';

ALTER TABLE tasks
    MODIFY status ENUM('ideas','next','waiting','someday','done') NOT NULL DEFAULT 'ideas';
