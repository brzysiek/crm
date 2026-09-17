-- Rozszerza wspólny słownik encji notatek/historii o oferty M&A, żeby
-- widok pojedynczej oferty mógł korzystać z tych samych sekcji Notatki/Historia,
-- co firmy/kontakty/deale.
ALTER TABLE crm_notes
    MODIFY COLUMN entity_type ENUM('company','contact','deal','mna_offer') NOT NULL;

ALTER TABLE crm_history
    MODIFY COLUMN entity_type ENUM('company','contact','deal','mna_offer') NOT NULL;
