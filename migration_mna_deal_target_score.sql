-- Scoring firm/kontaktów na long liście deala M&A (1-100), niezależny od
-- interest_status/is_valuable — pozwala liczbowo ocenić i posortować cele.
ALTER TABLE mna_deal_targets
    ADD COLUMN score TINYINT UNSIGNED NULL AFTER is_valuable,
    ADD CONSTRAINT chk_mna_deal_targets_score CHECK (score IS NULL OR (score BETWEEN 1 AND 100));
