ALTER TABLE crm_deals
    MODIFY COLUMN stage ENUM('new','in_progress','won','in_delivery','completed','someday','lost','unqualified') DEFAULT 'new';
