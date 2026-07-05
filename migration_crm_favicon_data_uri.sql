-- favicon_url będzie teraz przechowywać obrazek jako data URI (base64), a nie
-- tylko adres URL do niego, więc VARCHAR(512) nie wystarczy.
ALTER TABLE crm_companies MODIFY COLUMN favicon_url MEDIUMTEXT NULL;
