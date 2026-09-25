-- Pliki przypięte do ofert M&A (Drive: "Oferty M&A/<numer oferty> <nazwa>/pliki").
-- Trzeci możliwy właściciel pliku obok firmy CRM i deala M&A — dokumenty oferty
-- (teaser, sprawozdania, NDA) trafiały dotąd na dysk poza CRM-em.
ALTER TABLE crm_files
    ADD COLUMN mna_offer_id INT NULL AFTER mna_deal_id,
    ADD KEY idx_mna_offer (mna_offer_id),
    ADD CONSTRAINT fk_crm_files_mna_offer
        FOREIGN KEY (mna_offer_id) REFERENCES crm_mna_offers(id) ON DELETE CASCADE;
