-- Przypisanie kontekstu GTD do firm i kontaktów (1 kontekst na rekord) —
-- ustawialne ręcznie w formularzu oraz przy imporcie wizytówki, filtrowalne
-- na listach firm i kontaktów.
ALTER TABLE crm_companies
    ADD COLUMN context_id INT NULL AFTER owner_user_id,
    ADD KEY idx_crm_companies_context (context_id),
    ADD CONSTRAINT fk_crm_companies_context FOREIGN KEY (context_id) REFERENCES gtd_contexts(id) ON DELETE SET NULL;

ALTER TABLE crm_contacts
    ADD COLUMN context_id INT NULL AFTER description,
    ADD KEY idx_crm_contacts_context (context_id),
    ADD CONSTRAINT fk_crm_contacts_context FOREIGN KEY (context_id) REFERENCES gtd_contexts(id) ON DELETE SET NULL;
