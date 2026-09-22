-- Numer oferty M&A w formacie „Ref: <nr w miesiącu>/<miesiąc>/<rok>", np. „Ref: 3/09/2026".
-- Nadawany automatycznie przy tworzeniu oferty, ale edytowalny ręcznie.
ALTER TABLE crm_mna_offers ADD COLUMN ref_number VARCHAR(20) NULL AFTER name;
