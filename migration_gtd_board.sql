-- Tablica kanban: status „w trakcie” i data jego rozpoczęcia.
--
-- Do tej pory „do zrobienia” i „robię to teraz” były tym samym statusem `next`,
-- więc tablica miałaby dwie kolumny karmione z jednego źródła. Stąd nowa
-- wartość enuma `doing`, wstawiona między `next` a `waiting` — kolejność w
-- ENUM-ie jest kolejnością sortowania, a „w trakcie” stoi w przepływie pracy
-- dokładnie tam.
--
-- `started_at` odpowiada na pytanie „odkąd to ciągnę”. Ustawiane przy wejściu
-- w `doing`, zachowane przy przejściu w `waiting` i `done` (wtedy różnica z
-- `completed_at` to czas realizacji), czyszczone przy powrocie do `next` i do
-- `someday` — bo wtedy praca naprawdę się nie zaczęła.
ALTER TABLE tasks
    MODIFY COLUMN status ENUM('ideas','next','doing','waiting','someday','done')
    NOT NULL DEFAULT 'next';

ALTER TABLE tasks
    ADD COLUMN started_at DATETIME NULL DEFAULT NULL AFTER completed_at;
