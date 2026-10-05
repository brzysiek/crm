-- Uzupełnia datę zamknięcia tam, gdzie jej nigdy nie było.
--
-- `completed_at` doszło do tabeli później niż samo zamykanie zadań, więc 96
-- zadań ze statusem `done` nie ma żadnej daty. Dopóki jej nie ma, każdy widok
-- sortujący po dacie zamknięcia (kolumna „Zrobione” na tablicy, archiwum)
-- musi ratować się COALESCE-em z `updated_at` — a to znaczy, że ćwierć
-- historii układa się według daty ostatniej edycji rekordu, nie zamknięcia.
-- `updated_at` to najbliższe prawdy, co mamy: przy zamykaniu zadania to
-- właśnie ono było dotykane jako ostatnie.
UPDATE tasks
   SET completed_at = updated_at
 WHERE status = 'done'
   AND completed_at IS NULL;
