-- ============================================================
-- GTD: zadania i projekty (Getting Things Done)
-- ============================================================

CREATE TABLE IF NOT EXISTS tasks (
    id                     INT AUTO_INCREMENT PRIMARY KEY,
    title                  VARCHAR(500) NOT NULL,
    notes                  TEXT,
    is_project             TINYINT(1) NOT NULL DEFAULT 0,
    parent_id              INT NULL,
    status                 ENUM('inbox','next','waiting','someday','done') NOT NULL DEFAULT 'inbox',
    context_tag_id         INT NULL,
    waiting_on             VARCHAR(256),
    due_date               DATE NULL,
    scheduled_date         DATE NULL,
    scheduled_time         TIME NULL,
    scheduled_duration_min INT NULL,
    gcal_event_id          VARCHAR(255) NULL,
    is_today_priority      TINYINT(1) NOT NULL DEFAULT 0,
    is_week_priority       TINYINT(1) NOT NULL DEFAULT 0,
    completed_at           DATETIME NULL,
    created_by             INT NULL,
    created_at             DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at             DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES tasks(id) ON DELETE SET NULL,
    FOREIGN KEY (context_tag_id) REFERENCES crm_tags(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
    KEY idx_status (status),
    KEY idx_parent (parent_id),
    KEY idx_scheduled_date (scheduled_date),
    KEY idx_context_tag (context_tag_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE crm_tags MODIFY kind ENUM('tag','industry','source','task_context') NOT NULL;

INSERT IGNORE INTO settings (`key`, value) VALUES
    ('gtd_gcal_calendar_id', '');
