-- Przypisanie kontaktu/firmy CRM do zadania/projektu GTD oraz do wydarzenia
-- z kalendarza (spotkania). Widoczne pod kontaktem/firmą w nowej sekcji
-- "Zadania/Projekty/Spotkania".
ALTER TABLE tasks
    ADD COLUMN crm_contact_id INT NULL AFTER parent_id,
    ADD COLUMN crm_company_id INT NULL AFTER crm_contact_id,
    ADD KEY idx_tasks_crm_contact (crm_contact_id),
    ADD KEY idx_tasks_crm_company (crm_company_id),
    ADD CONSTRAINT fk_tasks_crm_contact FOREIGN KEY (crm_contact_id) REFERENCES crm_contacts(id) ON DELETE SET NULL,
    ADD CONSTRAINT fk_tasks_crm_company FOREIGN KEY (crm_company_id) REFERENCES crm_companies(id) ON DELETE SET NULL;

ALTER TABLE gcal_event_done
    ADD COLUMN crm_contact_id INT NULL AFTER project_id,
    ADD COLUMN crm_company_id INT NULL AFTER crm_contact_id,
    ADD KEY idx_gcal_crm_contact (crm_contact_id),
    ADD KEY idx_gcal_crm_company (crm_company_id),
    ADD CONSTRAINT fk_gcal_crm_contact FOREIGN KEY (crm_contact_id) REFERENCES crm_contacts(id) ON DELETE SET NULL,
    ADD CONSTRAINT fk_gcal_crm_company FOREIGN KEY (crm_company_id) REFERENCES crm_companies(id) ON DELETE SET NULL;
