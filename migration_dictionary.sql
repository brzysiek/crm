-- Tabela słowników aplikacji (kategorie, stawki VAT, formy płatności)

CREATE TABLE IF NOT EXISTS dictionary_items (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    dict_type  VARCHAR(50)  NOT NULL,
    value      VARCHAR(255) NOT NULL,
    label      VARCHAR(255) DEFAULT NULL,
    sort_order INT          DEFAULT 0,
    UNIQUE KEY uq_dict_type_value (dict_type, value)
);

INSERT IGNORE INTO dictionary_items (dict_type, value, label, sort_order) VALUES
('vat_rate', '23',  '23%',          1),
('vat_rate', '8',   '8%',           2),
('vat_rate', '5',   '5%',           3),
('vat_rate', '0',   '0%',           4),
('vat_rate', '-1',  'zw.',          5),
('payment_method', 'transfer', 'Przelew / karta', 1),
('payment_method', 'cash',     'Gotówka',         2);
