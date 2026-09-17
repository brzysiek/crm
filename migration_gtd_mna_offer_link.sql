-- Przypisanie oferty M&A do zadania GTD (widoczne jako badge na liście zadań),
-- analogicznie do migration_gtd_deal_link.sql dla deali.
ALTER TABLE tasks
    ADD COLUMN crm_mna_offer_id INT NULL AFTER crm_deal_id,
    ADD KEY idx_tasks_crm_mna_offer (crm_mna_offer_id),
    ADD CONSTRAINT fk_tasks_crm_mna_offer FOREIGN KEY (crm_mna_offer_id) REFERENCES crm_mna_offers(id) ON DELETE SET NULL;
