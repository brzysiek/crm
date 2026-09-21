-- Pliki przypięte do deali M&A (Drive: "Deale M&A/<firma z oferty>/pliki").
-- company_id staje się opcjonalne — plik należy albo do firmy CRM, albo do deala M&A.
ALTER TABLE crm_files
    MODIFY COLUMN company_id INT NULL,
    ADD COLUMN mna_deal_id INT NULL AFTER contact_id,
    ADD KEY idx_mna_deal (mna_deal_id),
    ADD CONSTRAINT fk_crm_files_mna_deal
        FOREIGN KEY (mna_deal_id) REFERENCES mna_deals(id) ON DELETE CASCADE;
