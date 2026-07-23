-- Dodaje typ deala (szkolenie / M&A / warsztaty / prowizja / partnerstwo / inne).
ALTER TABLE crm_deals
    ADD COLUMN deal_type ENUM('szkolenie','ma','warsztaty','prowizja','partnerstwo','inne')
        NOT NULL DEFAULT 'inne' AFTER stage;
