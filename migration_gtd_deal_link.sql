-- Przypisanie deala CRM do zadania GTD (widoczne jako badge na liście zadań).
ALTER TABLE tasks
    ADD COLUMN crm_deal_id INT NULL AFTER crm_company_id,
    ADD KEY idx_tasks_crm_deal (crm_deal_id),
    ADD CONSTRAINT fk_tasks_crm_deal FOREIGN KEY (crm_deal_id) REFERENCES crm_deals(id) ON DELETE SET NULL;
