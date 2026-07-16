-- Miękkie usuwanie zadań/projektów GTD — pozwala na sekcję "Usunięte" w Archiwum
-- (przywracanie / trwałe kasowanie), zamiast bezpowrotnego DELETE.
ALTER TABLE tasks
    ADD COLUMN deleted_at DATETIME NULL DEFAULT NULL AFTER completed_at;
