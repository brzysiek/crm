ALTER TABLE crm_deals
    MODIFY COLUMN stage ENUM('new','in_progress','in_delivery','completed','won','lost','someday') DEFAULT 'new';
