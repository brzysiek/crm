-- Kolor tekstu badge'a kontekstu (niezależny od koloru tła) + możliwość
-- przypisania kontekstu do wydarzeń z Google Calendar na listach dzień/tydzień/miesiąc.
ALTER TABLE gtd_contexts
    ADD COLUMN text_color VARCHAR(7) NOT NULL DEFAULT '#1F2937' AFTER badge_color;

UPDATE gtd_contexts SET text_color = badge_color;

ALTER TABLE gcal_event_done
    ADD COLUMN context_id INT NULL,
    ADD KEY idx_gcal_event_done_context (context_id),
    ADD CONSTRAINT fk_gcal_event_done_context FOREIGN KEY (context_id) REFERENCES gtd_contexts(id) ON DELETE SET NULL;
