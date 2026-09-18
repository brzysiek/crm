-- Przypisanie deala M&A (mna_deals) do zadania GTD, analogicznie do
-- migration_gtd_mna_offer_link.sql dla ofert M&A.
ALTER TABLE tasks
    ADD COLUMN crm_mna_deal_id INT NULL AFTER crm_mna_offer_id,
    ADD KEY idx_tasks_crm_mna_deal (crm_mna_deal_id),
    ADD CONSTRAINT fk_tasks_crm_mna_deal FOREIGN KEY (crm_mna_deal_id) REFERENCES mna_deals(id) ON DELETE SET NULL;
