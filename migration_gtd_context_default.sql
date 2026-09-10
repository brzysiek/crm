-- Domyślny kontekst GTD — jeden kontekst może być oznaczony jako domyślny;
-- przypisywany automatycznie nowym zadaniom/projektom/firmom/kontaktom/dealom,
-- gdy nie da się go odziedziczyć (np. z projektu nadrzędnego, deala czy firmy).
ALTER TABLE gtd_contexts
    ADD COLUMN is_default TINYINT(1) NOT NULL DEFAULT 0;
