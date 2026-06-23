-- Płatności (harmonogram przychodów netto) przypisane do interesów CRM

CREATE TABLE IF NOT EXISTS crm_deal_payments (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    deal_id     INT NOT NULL,
    pay_month   DATE NOT NULL,
    amount_net  DECIMAL(12,2) NOT NULL,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (deal_id) REFERENCES crm_deals(id) ON DELETE CASCADE,
    KEY idx_deal (deal_id),
    KEY idx_pay_month (pay_month)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
