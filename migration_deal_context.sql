-- Przypisanie kontekstu GTD do deala (1 kontekst na deal) — widoczne i filtrowalne
-- na liście/kanbanie deali.
ALTER TABLE crm_deals
    ADD COLUMN context_id INT NULL AFTER owner_user_id,
    ADD KEY idx_crm_deals_context (context_id),
    ADD CONSTRAINT fk_crm_deals_context FOREIGN KEY (context_id) REFERENCES gtd_contexts(id) ON DELETE SET NULL;
