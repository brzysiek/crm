-- Dodanie daty płatności do faktur, wydatków i przychodów

ALTER TABLE fakturownia_invoices
    ADD COLUMN payment_to DATE DEFAULT NULL AFTER issue_date;

ALTER TABLE gdrive_invoices
    ADD COLUMN payment_to DATE DEFAULT NULL AFTER issue_date;

ALTER TABLE expenses
    ADD COLUMN payment_due_date DATE DEFAULT NULL AFTER date;

ALTER TABLE incomes
    ADD COLUMN payment_due_date DATE DEFAULT NULL AFTER date;

-- Backfill payment_to w fakturownia_invoices z raw_json
UPDATE fakturownia_invoices
SET payment_to = NULLIF(TRIM(JSON_UNQUOTE(JSON_EXTRACT(raw_json, '$.payment_to'))), '')
WHERE payment_to IS NULL
  AND JSON_EXTRACT(raw_json, '$.payment_to') IS NOT NULL
  AND TRIM(JSON_UNQUOTE(JSON_EXTRACT(raw_json, '$.payment_to'))) != '';

-- Backfill payment_due_date w expenses z powiązanych faktur Fakturowni
UPDATE expenses e
JOIN fakturownia_invoices fi
    ON fi.assigned_expense_id = e.id
   AND fi.status = 'assigned'
   AND fi.invoice_type = 'expense'
SET e.payment_due_date = fi.payment_to
WHERE e.payment_due_date IS NULL
  AND fi.payment_to IS NOT NULL;

-- Backfill payment_due_date w incomes z powiązanych faktur Fakturowni
UPDATE incomes i
JOIN fakturownia_invoices fi
    ON fi.assigned_expense_id = i.id
   AND fi.status = 'assigned'
   AND fi.invoice_type = 'income'
SET i.payment_due_date = fi.payment_to
WHERE i.payment_due_date IS NULL
  AND fi.payment_to IS NOT NULL;
