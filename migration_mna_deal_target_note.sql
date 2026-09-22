-- Robocze pola pozycji long/short listy deala M&A: krótka notatka i data ostatniego
-- kontaktu. Trzymamy je przy pozycji listy (nie przy firmie), bo dotyczą pracy nad
-- konkretnym dealem — ta sama firma może być celem w kilku dealach.
ALTER TABLE mna_deal_targets
    ADD COLUMN note VARCHAR(500) NULL AFTER score,
    ADD COLUMN contacted_at DATE NULL AFTER note;
