-- Numer oferty M&A w formacie „Ref: <nr w roku>/<rok>", np. „Ref: 3/2026".
-- Nadawany automatycznie przy tworzeniu oferty, ale edytowalny ręcznie.
ALTER TABLE crm_mna_offers ADD COLUMN ref_number VARCHAR(20) NULL AFTER name;
