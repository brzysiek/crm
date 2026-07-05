-- Przygotowanie modelu CRM pod import danych z Sugester2:
-- rozszerzenie relacji o kategorie bez odpowiednika oraz nowe pola
-- (LinkedIn, województwo, link do zeskanowanej wizytówki).

ALTER TABLE crm_companies
    MODIFY COLUMN relation_type ENUM('lead','client','partner','inne','dostawca') DEFAULT 'lead';

ALTER TABLE crm_companies
    ADD COLUMN linkedin_url VARCHAR(255) DEFAULT NULL AFTER website,
    ADD COLUMN voivodeship  VARCHAR(64)  DEFAULT NULL AFTER city;

ALTER TABLE crm_contacts
    ADD COLUMN business_card_url VARCHAR(255) DEFAULT NULL;
