-- Tagi przestają być przypinane do osób: zostają tylko na firmach.
--
-- Powód: w formularzu kontaktu pole „Tagi" dublowało to samo pojęcie co tagi
-- firmy (lista kontaktów i tak pokazywała kolumnę „Tagi (firma)"), a branże
-- i źródła od zawsze były wyłącznie firmowe. Istniejące przypisania przechodzą
-- na firmę kontaktu; tagi rodzaju 'email' (zgody marketingowe) zostają przy
-- kontaktach — to osobny mechanizm.

INSERT IGNORE INTO crm_company_tags (company_id, tag_id)
SELECT c.company_id, ct.tag_id
FROM crm_contact_tags ct
JOIN crm_tags t ON t.id = ct.tag_id AND t.kind = 'tag'
JOIN crm_contacts c ON c.id = ct.contact_id
WHERE c.company_id IS NOT NULL;

DELETE ct FROM crm_contact_tags ct
JOIN crm_tags t ON t.id = ct.tag_id
WHERE t.kind = 'tag';
