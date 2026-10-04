-- Zdjęcie użytkownika: data URI (base64) w kolumnie tekstowej, tak samo jak logo
-- aplikacji w tabeli settings. Osobnej tabeli ani plików na dysku nie zakładamy —
-- zdjęć jest tyle, ilu użytkowników, a hosting współdzielony nie ma trwałego
-- katalogu na uploady poza repozytorium.
ALTER TABLE users
  ADD COLUMN avatar MEDIUMTEXT NULL,
  ADD COLUMN avatar_updated_at DATETIME NULL;
