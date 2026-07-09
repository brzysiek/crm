-- Umożliwia zapis zakodowanych base64 obrazków (logo aplikacji) w tabeli settings.
-- TEXT ma limit 65 535 bajtów — za mało dla zdjęcia logo. MEDIUMTEXT: do 16 MB.
ALTER TABLE settings MODIFY value MEDIUMTEXT;
