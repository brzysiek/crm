-- Dodaje prawdopodobieństwo wygrania deala (5/20/40/60/80/100%, NULL = nieustawione).
-- Wygrane/w toku projektu/zakończone zawsze mają 100%, przegrane zawsze 0%.
ALTER TABLE crm_deals
    ADD COLUMN probability TINYINT UNSIGNED NULL AFTER stage;

UPDATE crm_deals SET probability = 100 WHERE stage IN ('won', 'in_delivery', 'completed');
UPDATE crm_deals SET probability = 0 WHERE stage = 'lost';
