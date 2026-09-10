-- Konteksty GTD (np. "@dom", "@praca") — grupowanie zadań/projektów, definiowane
-- w Ustawieniach (nazwa + kolor badge'a). Relacja zadanie/projekt -> kontekst: 1-1.
CREATE TABLE IF NOT EXISTS gtd_contexts (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(50) NOT NULL,
    badge_color VARCHAR(7) NOT NULL DEFAULT '#3B82F6',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uniq_gtd_context_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE tasks
    ADD COLUMN context_id INT NULL AFTER crm_deal_id,
    ADD KEY idx_tasks_context (context_id),
    ADD CONSTRAINT fk_tasks_context FOREIGN KEY (context_id) REFERENCES gtd_contexts(id) ON DELETE SET NULL;

INSERT INTO gtd_contexts (name, badge_color) VALUES ('dom', '#3B82F6'), ('praca', '#8B5CF6');
