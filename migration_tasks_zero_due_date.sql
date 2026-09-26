-- Naprawa danych: puste terminy zapisane jako 0000-00-00 (pusty string w kolumnie DATE
-- przy wyłączonym strict mode). pymysql oddaje taką wartość jako napis, więc widok dnia
-- wywalał się na porównaniu terminu z dzisiejszą datą (TypeError: str < date).
UPDATE tasks SET due_date = NULL WHERE CAST(due_date AS CHAR) = '0000-00-00';
