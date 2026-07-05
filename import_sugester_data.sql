-- Import danych z Sugester2 (Klienci + Kontakty) do CRM.
-- Wygenerowane automatycznie na podstawie eksportu z 2026-07-05.
-- Wymaga wcześniejszego uruchomienia migration_crm_sugester_import.sql.
-- Przejrzyj przed uruchomieniem — całość w jednej transakcji, można bezpiecznie ROLLBACK.

START TRANSACTION;

-- Słownik tagów
INSERT IGNORE INTO crm_tags (kind, name) VALUES ('tag', 'BCC'), ('tag', 'BNI'), ('tag', 'BNI+'), ('tag', 'Blacklist'), ('tag', 'Business Mixer Katowice 12/2025'), ('tag', 'EMBA'), ('tag', 'Gość BNI'), ('tag', 'KSB'), ('tag', 'Kontakt Rafała'), ('tag', 'LI Local Katowice 12/25'), ('tag', 'Lewiatan'), ('tag', 'M&A'), ('tag', 'MBA Polska'), ('tag', 'MBONy'), ('tag', 'Reko'), ('tag', 'Reko BNI'), ('tag', 'Smartsist'), ('tag', 'kuek'), ('tag', 'poszukiwania nabywcy myTherapy');

-- Słownik branż
INSERT IGNORE INTO crm_tags (kind, name) VALUES ('industry', 'AI, agenci AI'), ('industry', 'Agencja SEO'), ('industry', 'Audyt, Doradztwo biznesowe, Księgowość, Finanse'), ('industry', 'B+R, bony, dofinansowania'), ('industry', 'BNI, HoReCa, Newsletter'), ('industry', 'Bayer, fundusze inwestycyjne, big pharma'), ('industry', 'Budownictwo'), ('industry', 'Building Cost Estimation'), ('industry', 'Business Consulting'), ('industry', 'Chłodnictwo i Klimatyzacja'), ('industry', 'Consulting M&A'), ('industry', 'Deweloperka, rewitalizacja miejska, nieruchomości komercyjne i mieszkaniowe'), ('industry', 'Dofianansowania'), ('industry', 'Doradztwo finansowe, Analityka biznesowa, Wyceny spółek, Doradztwo kapitałowe'), ('industry', 'Doradztwo i szkolenia'), ('industry', 'Doradztwo/Jakość'), ('industry', 'Drewno, płyty drewniane'), ('industry', 'Edukacja, Kursy online, E-learning, Korepetycje'), ('industry', 'Edukacja, jęzuk angielski'), ('industry', 'Energetyka, Odnawialne Źródła Energii, Handel Energią, Zarządzanie Ryzykiem'), ('industry', 'Energia odnawialna i klimat'), ('industry', 'Finanse, Media internetowe, Edukacja finansowa'), ('industry', 'Finanse/Księgowość'), ('industry', 'HR'), ('industry', 'HR, Newsletter'), ('industry', 'HoReCa, sala, konferencje, szkolenia'), ('industry', 'IT, Konsulting, Oprogramowanie, Usługi cyfrowe'), ('industry', 'IT, usługi konsultingowe, technologie informatyczne, cyfrowa transformacja'), ('industry', 'IT/Edukacja'), ('industry', 'IT/Technologie'), ('industry', 'Księgowość, Doradztwo podatkowe, Kadry i płace'), ('industry', 'Marketing / Komunikacja PR'), ('industry', 'Marketing / Reklama'), ('industry', 'Meble'), ('industry', 'Medycyna/Zdrowie'), ('industry', 'Motoryzacja'), ('industry', 'Nieruchomości'), ('industry', 'Nieruchomości komercyjne, Doradztwo inwestycyjne, Zarządzanie nieruchomościami'), ('industry', 'Nieruchomości, Pośrednictwo, Doradztwo finansowe, Usługi prawne'), ('industry', 'Ochrona, Monitoring wizyjny'), ('industry', 'Opakowania tekturowe, Produkcja kartonów, E-commerce, Przemysł papierniczy'), ('industry', 'PR'), ('industry', 'Piekarnia - Cukiernia'), ('industry', 'Prawo'), ('industry', 'Prawo / Usługi prawnicze'), ('industry', 'Prawo własności przemysłowej, patenty, znaki towarowe'), ('industry', 'Prawo/Legal'), ('industry', 'Produkcja części do pojazdów silnikowych'), ('industry', 'Produkcja i Handel'), ('industry', 'Przemysł'), ('industry', 'Przemysł, plastik, produkcja'), ('industry', 'Psychoterapia, Psychologia, Psychiatria, Zdrowie psychiczne'), ('industry', 'Psychoterapia, Psychologia, Seksuologia, Dietetyka'), ('industry', 'Rekrutacja, Executive Search, IT staffing, Outsourcing HR, Konsulting biznesowy'), ('industry', 'SEO/SEM, pozycjonowanie stron'), ('industry', 'Serwis urządzeń gazowych'), ('industry', 'Sztuczna inteligencja, IT, Automatyzacja, Oprogramowanie'), ('industry', 'Transport'), ('industry', 'Ubezpieczenia'), ('industry', 'Ubezpieczenia, Finanse, Doradztwo ubezpieczeniowe'), ('industry', 'Wykończenia wnętrz'), ('industry', 'agencja 360, marketing'), ('industry', 'agencja pracy'), ('industry', 'analityka biznesowa'), ('industry', 'bezpieczeństwo, monitoring'), ('industry', 'bhp, hurtownia'), ('industry', 'biuro księgowe, audyty, hr, payroll'), ('industry', 'budowlanka'), ('industry', 'chłodnictwo, pompy ciepła, Newsletter'), ('industry', 'coaching, szkolenia, HR, leaderdship'), ('industry', 'coachng, szkolenia, HR, leaderdship'), ('industry', 'cold calling'), ('industry', 'cyberbezpieczeństwo'), ('industry', 'doradztwo biznesowe, business consulting'), ('industry', 'doradztwo podatkowe, celne'), ('industry', 'doradztwo, coaching, strategie'), ('industry', 'doradztwo, m&a, fuzje i przejęcia'), ('industry', 'doradztwo, wyjście na rynki skandynawskie'), ('industry', 'drukarnia, koszulki, ciuchy'), ('industry', 'esg, Newsletter'), ('industry', 'finanse'), ('industry', 'firma budowlana'), ('industry', 'firma konstrukcyjno-budowlana, duża'), ('industry', 'fotowoltaika, pompy ciepła, instalacje, Newsletter'), ('industry', 'internacjonalizacja, wyjście na rynki zagraniczne'), ('industry', 'kancelaria prawna'), ('industry', 'karty dostępu'), ('industry', 'kontroling finansowy, finanse'), ('industry', 'księgowość'), ('industry', 'marketing, reklama'), ('industry', 'markety'), ('industry', 'meble'), ('industry', 'medycyna, przychodnia zdrowia, zdrowie, Newsletter'), ('industry', 'nieruchomości'), ('industry', 'obróbka szkła, hurtownie elektryczne'), ('industry', 'odzież robocza'), ('industry', 'oprogramowanie, nauka, Szwecja, bodyleasing, python'), ('industry', 'organizator konferencji online'), ('industry', 'oświetlenie przemysłowe, Newsletter'), ('industry', 'pizzeria, restauracja, Newsletter'), ('industry', 'prawo, adwokat'), ('industry', 'produkcja hamulców, automotive'), ('industry', 'produkcja materace'), ('industry', 'produkcja opakowań, Newsletter'), ('industry', 'produkcja oprogramowania, software, CRM'), ('industry', 'produkcja urządzeń laboratoryjnych'), ('industry', 'psychoterapia'), ('industry', 'psychoterapia dla dzieci'), ('industry', 'psychoterapia, psychiatria, medycyna, centrum medyczne'), ('industry', 'skład budowlany, Newsletter'), ('industry', 'software house, CRM, ERP, oprogramowanie'), ('industry', 'software house, oprogramowanie'), ('industry', 'sport, Newsletter'), ('industry', 'sprzątanie, zieleń'), ('industry', 'startupy'), ('industry', 'stolarka alumioniowa, ogrody zimowe, elewacje domów'), ('industry', 'system CRM'), ('industry', 'szkolenia, coaching, przywództwo'), ('industry', 'szkolenia, testy osobowości, Bridge, DISC, Galloup'), ('industry', 'transport, logistyka, spedycja'), ('industry', 'transport, logistyka, spedycja, TLS'), ('industry', 'trener, szkolenia, psycholog, Newsletter'), ('industry', 'turystyka, podróże dla firm'), ('industry', 'tłumaczenia, inwestycje, finanse'), ('industry', 'ubezpieczenia'), ('industry', 'usczelki, produkcja'), ('industry', 'weryfikacja podmiotów'), ('industry', 'wprawadzają firmy irlandzkie do Polski'), ('industry', 'zaopatrzenie biurowe'), ('industry', 'Środki czystości, producent');

-- Firma: Open Education Group Spółka Z Ograniczoną Odpowiedzialnością (Sugester ID 26986322)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Open Education Group Spółka Z Ograniczoną Odpowiedzialnością', 'Open Education Group Spółka Z Ograniczoną Odpowiedzialnością', 'partner', 'Polska', 'Białystok', 'PODLASKIE', 'Ul. Jagienki 4', '15-480', 'e.poplawska@openeducation.pl', '+48664705711', '9661811272', 'http://openeducation.pl', NULL, NULL, 'Bartek Stodulski', NULL, '2026-05-21 14:08:19');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Edukacja, jęzuk angielski');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Ewelina', 'Popławska', NULL, 'e.poplawska@openeducation.pl', '+48664705711', NULL, 'Edukacja, Szkolenia, Doradztwo unijne, Rekrutacja');

-- Firma: Decyzja Komunikacyjna (Sugester ID 26952181)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Decyzja Komunikacyjna', 'Michał Krzak', 'lead', 'Polska', 'Kraków', 'MAŁOPOLSKIE', 'Krowoderska 63B/6', '31-158', 'michal@krzak.pro', '+48667720320', NULL, 'http://krzak.pro', NULL, NULL, NULL, NULL, '2026-05-13 11:55:58');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Marketing / Komunikacja PR');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Michał', 'Krzak', NULL, 'michal@krzak.pro', '+48667720320', NULL, NULL);

-- Firma: GOMEX BHP (Sugester ID 26948732)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('GOMEX BHP', 'GOMEX BHP', 'client', 'Polska', 'Dąbrowa Górnicza', 'ŚLĄSKIE', 'Emilii Zawidzkiej 10', '41-300', NULL, '+48507170444', '6292492638', 'https://gomex.com.pl/', NULL, NULL, 'BNI', (SELECT id FROM users WHERE full_name IN ('Lukasz Brzyski','Łukasz Brzyski') LIMIT 1), '2026-05-12 15:43:26');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('M&A');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('bhp, hurtownia');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Krzysztof', 'Ociepka', NULL, NULL, '+48507170444', NULL, NULL);

-- Firma: PPHU DREWNOTECH (Sugester ID 26918964)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('PPHU DREWNOTECH', 'PPHU DREWNOTECH', 'lead', 'Polska', 'Rzeszów', 'PODKARPACKIE', 'Mielecka 37', '35-504', 'b.flis01@gmail.com', '+48601095050', '8130139031', NULL, NULL, NULL, 'Wojciech Lelito', (SELECT id FROM users WHERE full_name IN ('Lukasz Brzyski','Łukasz Brzyski') LIMIT 1), '2026-05-05 13:08:41');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('M&A');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Drewno, płyty drewniane');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Bartosz', 'Flis', 'Właściciel', 'b.flis01@gmail.com', '+48601095050', NULL, NULL);
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Michał', 'Flis', NULL, 'flis12@wp.pl', NULL, NULL, NULL);

-- Firma: Jarkom (Sugester ID 26859751)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Jarkom', 'Jarkom', 'lead', 'Polska', 'Radom', 'MAZOWIECKIE', 'Grabowska 22', '26-611', 'komasara.agata@gmail.com', '+48504720400', '7961011406', NULL, NULL, NULL, 'Agnieszka Rożek', NULL, '2026-04-21 09:53:57');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('MBONy');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Transport');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Agata', 'Komasara', 'Usługi Transportowe', 'komasara.agata@gmail.com', '+48504720400', NULL, 'Mbony - odezwać się w lipcu 2026');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Jarosław', 'Komasara', NULL, NULL, '507471272', NULL, NULL);

-- Firma: Kancelaria Dbs (Sugester ID 26823346)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Kancelaria Dbs', 'Kancelaria Dbs', 'lead', 'Polska', 'Poznań', 'WIELKOPOLSKIE', 'Ul. Wojskowa 6/B2', '60-792', 'alicjarutkowska@kancelariadbs.pl', '513144548', '5213433604', 'http://www.kancelariadbs.pl', NULL, NULL, 'Agnieszka Rożek', NULL, '2026-04-13 12:39:18');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('MBONy');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Prawo / Usługi prawnicze');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Alicja', 'Rutkowska', NULL, 'alicjarutkowska@kancelariadbs.pl', '513144548', NULL, 'Prawo, Life Sciences, Farmacja, Medycyna');

-- Firma: Techlabee.Ai (Sugester ID 26817082)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Techlabee.Ai', 'Techlabee.Ai', 'lead', 'Litwa', 'Vilnius', NULL, 'Vilniaus G. 33', '01402', 'bartosz@techlabee.ai', '+48608041825', 'LT100015147310', 'http://www.techlabee.ai', NULL, NULL, NULL, NULL, '2026-04-11 13:49:48');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('IT/Technologie');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Bartosz', 'Bliuj-Stodulski', NULL, 'bartosz@techlabee.ai', '+48608041825', NULL, 'Sztuczna Inteligencja, IT, Machine Learning, Doradztwo technologiczne');

-- Firma: Nowe Kompetencje (Sugester ID 26817078)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Nowe Kompetencje', 'Nowe Kompetencje', 'lead', 'Polska', 'Warszawa', 'MAZOWIECKIE', 'Prosta 70', '00-838', 'kamila@nowekompetencje.ai', '+48600689609', '5214013697', 'http://www.nowekompetencje.ai', NULL, NULL, NULL, NULL, '2026-04-11 13:46:37');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('IT/Edukacja');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Kamila', 'Krawiec', NULL, 'kamila@nowekompetencje.ai', '+48600689609', NULL, 'AI, Doradztwo technologiczne, Szkolenia IT');

-- Firma: DareMedia (Sugester ID 26817071)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('DareMedia', 'DareMedia', 'lead', 'Polska', 'Poznań', 'WIELKOPOLSKIE', 'Wojskowa 6', '60-792', 'pawel.pomin@daremedia.pl', '+48792440566', '5170396933', 'http://daremedia.pl', NULL, NULL, NULL, NULL, '2026-04-11 13:43:05');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Marketing / Reklama');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Paweł', 'Pomin', 'Ceo / Co-Founder', 'pawel.pomin@daremedia.pl', '+48792440566', NULL, 'Marketing, Analityka danych, E-commerce, AI');

-- Firma: Axpo Polska sp. z o.o. (Sugester ID 26492004)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Axpo Polska sp. z o.o.', 'Axpo Polska sp. z o.o.', 'lead', 'Polska', 'New York', NULL, NULL, '10017', 'malgorzata.cabak@partneraxpo.pl', '+48668321507', NULL, 'http://www.axpo.com', NULL, NULL, NULL, NULL, '2026-02-21 18:59:34');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Energetyka, Odnawialne Źródła Energii, Handel Energią, Zarządzanie Ryzykiem');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Małgorzata', 'Cabak', 'Doradca ds. sprzedaży energii i gazu', 'malgorzata.cabak@partneraxpo.pl', '+48668321507', 'https://drive.google.com/file/d/14faL6PgvKCVotxykuQYB7RDCcx2o7uC9/view?usp=sharing', 'Energetyka, Odnawialne Źródła Energii, Handel Energią, Zarządzanie Ryzykiem');

-- Firma: Veryhome Real Estate (Sugester ID 26484264)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Veryhome Real Estate', 'Veryhome Real Estate', 'lead', 'Polska', 'Kraków', NULL, NULL, '30-081', 'marta.lasak@veryhome.pl', '+48696464688', '6792754660', 'http://www.veryhome.pl', NULL, NULL, NULL, NULL, '2026-02-19 13:48:33');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Nieruchomości, Pośrednictwo, Doradztwo finansowe, Usługi prawne');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Marta', 'Lasak', 'Pośrednik w obrocie nieruchomościami | CEO', 'marta.lasak@veryhome.pl', '+48696464688', 'https://drive.google.com/file/d/1E02W8wcw3ctMZmLuUWPV7_8C_Zp6llYz/view?usp=sharing', 'Nieruchomości, Pośrednictwo, Doradztwo finansowe, Usługi prawne');

-- Firma: Vesta Bezpieczenia (Sugester ID 26484230)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Vesta Bezpieczenia', 'Vesta Bezpieczenia', 'lead', 'Polska', 'Warszawa', NULL, 'Południowa 10', '32-010', 'jg@vestabezpieczenia.pl', '+48535556674', '5213636540', 'http://www.vestabezpieczenia.pl', NULL, 'Kompleksowe doradztwo w zakresie ubezpieczeń komunikacyjnych, majątkowych oraz życiowych. Oferta obejmuje produkty finansowe dla klientów indywidualnych i biznesowych przy współpracy z czołowymi towarzystwami ubezpieczeniowymi.



Członek BNI Victoria', 'BNI Victoria', NULL, '2026-02-19 13:44:34');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Ubezpieczenia, Finanse, Doradztwo ubezpieczeniowe');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Jan', 'Gorczyca', NULL, 'jg@vestabezpieczenia.pl', '+48535556674', 'https://drive.google.com/file/d/1eyV-SKTQEm7694qi0MqiIlMV3kkVONCh/view?usp=sharing', 'Ubezpieczenia, Finanse, Doradztwo ubezpieczeniowe');

-- Firma: Firma Produkcyjno Handlowo Usługowa Sigern Wojciech Fałowski Sp K (Sugester ID 26341672)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Firma Produkcyjno Handlowo Usługowa Sigern Wojciech Fałowski Sp K', 'Adriana Fałowska', 'lead', 'Polska', 'Wielogłowy', 'MAŁOPOLSKIE', 'Wielopole 86', '33-311', 'adriana@sigern.pl', '+48608580403', '7343136277', 'http://www.sigern.pl', NULL, NULL, NULL, NULL, '2026-01-18 21:28:55');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Produkcja i Handel');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Adriana', 'Fałowska', NULL, 'adriana@sigern.pl', '+48608580403', NULL, NULL);

-- Firma: Perspecto (Sugester ID 26339875)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Perspecto', 'Perspecto', 'partner', 'Polska', 'Katowice', NULL, NULL, '40-007', 'k.blazenek@perspecto.ba', '+48500160662', '6342934440', 'https://perspecto.ba', NULL, NULL, NULL, NULL, '2026-01-17 11:51:23');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('M&A', 'BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('doradztwo, m&a, fuzje i przejęcia');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Konrad', 'Blazenek', NULL, 'k.blazenek@perspecto.ba', '+48500160662', NULL, NULL);

-- Firma: Centrum Zarządzania Jakością "INFOX" Spółka z ograniczoną odpowiedzialnością (Sugester ID 26339862)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Centrum Zarządzania Jakością "INFOX" Spółka z ograniczoną odpowiedzialnością', 'Centrum Zarządzania Jakością "INFOX" Spółka z ograniczoną odpowiedzialnością', 'lead', 'Polska', 'Bochnia', NULL, 'Brzeska 95', '32-700', 'ewa.mysliwy@czj-infox.pl', '+48506140460', NULL, 'https://czj-infox.pl', NULL, NULL, NULL, NULL, '2026-01-17 11:34:32');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Doradztwo/Jakość');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Ewa', 'Myśliwy', NULL, 'ewa.mysliwy@czj-infox.pl', '+48506140460', NULL, NULL);
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Magdalena', 'Polek', NULL, 'sekretariat@czj-infox.pl', '+48518925841', NULL, 'dofinansowania dla firm - pracownik Ewy Myśliwy');

-- Firma: MDDP (Sugester ID 26328563)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('MDDP', 'MDDP', 'inne', 'Poland', 'Warszawa', 'MASOWIECKIE', 'Senatorska 18a', '02-677', 'michal.niton@mddp.pl', '+48503976057', '521-33-0-28-56', 'https://mddp.pl', NULL, NULL, NULL, NULL, '2026-01-14 14:59:23');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Business Mixer Katowice 12/2025');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Nieruchomości');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Michał', 'Nitoń', NULL, 'michal.niton@mddp.pl', '+48503976057', 'https://drive.google.com/file/d//view?usp=sharing', NULL);

-- Firma: Toyota Dobrygowski (Sugester ID 26275254)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Toyota Dobrygowski', 'Toyota Dobrygowski', 'inne', 'Polska', 'Modlnica', 'MAŁOPOLSKIE', 'ul. Częstochowska 30', '32-085', 'a.kolodziej@toyotadobrygowski.pl', '+48881212086', '9441999719', 'https://toyotadobrygowski.pl', NULL, NULL, NULL, NULL, '2026-01-10 14:33:53');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Motoryzacja');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Adam', 'Kołodziej', NULL, 'a.kolodziej@toyotadobrygowski.pl', '+48881212086', 'https://drive.google.com/file/d/unique_file_id_example/view?usp=sharing', NULL);

-- Firma: Cztery Strony Zmian (Sugester ID 26275248)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Cztery Strony Zmian', 'CzteryStronyZmian', 'dostawca', 'PL', NULL, NULL, NULL, '31-826', 'ania@4sz.pl', '+48694593617', '6783182186', 'https://4sz.pl', NULL, NULL, 'BNI', NULL, '2026-01-10 14:31:58');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('cold calling');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Anna', 'Szczepanek', NULL, 'ania@4sz.pl', '+48694593617', 'https://drive.google.com/file/d//view?usp=sharing', NULL);

-- Firma: Baav Studio (Sugester ID 26275247)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Baav Studio', 'BaavStudio', 'inne', 'Polska', 'Kraków', NULL, NULL, '31-153', 'ad@baavstudio.pl', '+48507725189', '6762512192', 'https://baavstudio.pl', NULL, NULL, NULL, NULL, '2026-01-10 14:31:51');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Agata', 'Doroszewska-Curzytek', NULL, 'ad@baavstudio.pl', '+48507725189', 'https://drive.google.com/file/d//view?usp=sharing', NULL);

-- Firma: Ster24 (Sugester ID 26275245)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Ster24', 'sterBiuroRachunkoweSos24', 'client', 'polska', 'krakow', 'MALOPOLSKIE', 'ulJugowicka6B', '30-443', 'marcin.rej@ster24.com.pl', '+48512449070', '6751769655', 'https://ster24.com.pl', NULL, NULL, NULL, NULL, '2026-01-10 14:31:21');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Finanse/Księgowość');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Marcin', 'Rej', NULL, 'marcin.rej@ster24.com.pl', '+48512449070', 'https://drive.google.com/file/d//view?usp=sharing', NULL);

-- Firma: Miśkowicz Pach I Partnerzy Kancelaria Radców Prawnych (Sugester ID 26275233)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Miśkowicz Pach I Partnerzy Kancelaria Radców Prawnych', 'MiśkowiczPach I Partnerzy KancelariaRadcówPrawnych', 'partner', 'Polska', 'Kraków', NULL, 'ArmiiKrajowej 19', '30-150', 'anna.pach@miskowicz-pach.pl', '+48668811379', '6762414775', 'https://miskowicz-pach.pl', NULL, NULL, NULL, NULL, '2026-01-10 14:23:33');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Prawo/Legal');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Anna', 'Pach-Kustra', NULL, 'anna.pach@miskowicz-pach.pl', '+48668811379', 'https://drive.google.com/file/d//view?usp=sharing', NULL);

-- Firma: SolMeb Ewelina Przybyś (Sugester ID 26275232)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('SolMeb Ewelina Przybyś', 'Sol Meb', 'lead', 'Polska', 'Wieliczka', 'MAŁOPOLSKIE', 'ulTkosciuszki39', '32-020', 'biuro@meblemarzen.com', '+48517893510', '5662013149', 'https://meblemarzen.com', NULL, NULL, NULL, NULL, '2026-01-10 14:21:14');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Meble');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Ewelina', 'Przybyś', NULL, 'biuro@meblemarzen.com', '+48517893510', 'https://drive.google.com/file/d//view?usp=sharing', NULL);

-- Firma: Adwokatura (Sugester ID 26275230)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Adwokatura', 'Adwokatura', 'lead', 'Polska', 'Warszawa', 'Mazowieckie', 'ul. Wiejska 15', '00-480', 'katarzyna.kawalec@adwokatura.pl', '606734059', '5252007890', 'https://adwokatura.pl', NULL, NULL, NULL, NULL, '2026-01-10 14:20:33');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Prawo');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Katarzyna', 'Kawalec Gwiazdowska', NULL, 'katarzyna.kawalec@adwokatura.pl', '606734059', 'https://drive.google.com/file/d/a1b2c3d4e5f6g7h8i9j0/view?usp=sharing', 'Prawnik ZLSP');

-- Firma: ZLSP (Sugester ID 26275229)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('ZLSP', 'Zlsp', 'lead', 'Polska', 'Warszawa', NULL, NULL, '00-680', 'b.piaskowy@zlsp.org.pl', '+48501699763', '5260002164', 'https://zlsp.org.pl', NULL, NULL, NULL, NULL, '2026-01-10 14:20:31');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Bożena', 'Piaskowy', NULL, 'b.piaskowy@zlsp.org.pl', '+48501699763', 'https://drive.google.com/file/d//view?usp=sharing', NULL);

-- Firma: Online Group (Sugester ID 26275221)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Online Group', 'Joanna Wojtyszyn', 'inne', 'Polska', 'Kraków', NULL, 'Bronowicka 23 lok. 10', NULL, 'joanna.wojtyszyn@onlinegroup.pl', '+48728631202', NULL, 'http://onlinegroup.pl', NULL, NULL, NULL, NULL, '2026-01-10 14:17:09');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Agencja SEO');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Joanna', 'Wojtyszyn', NULL, 'joanna.wojtyszyn@onlinegroup.pl', '+48728631202', NULL, NULL);

-- Firma: mieszkanie.com (Sugester ID 26275218)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('mieszkanie.com', 'mieszkanie.com', 'inne', 'Polska', 'Kraków', NULL, 'ul. Kazimierza Wielkiego 18', '30-074', 'ks@mieszkanie.com', '+48606836656', '6772467936', 'https://mieszkanie.com', NULL, NULL, NULL, NULL, '2026-01-10 14:14:08');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Nieruchomości');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Katarzyna', 'Sonik', NULL, 'ks@mieszkanie.com', '+48606836656', 'https://drive.google.com/file/d/10SiSTX-_SS-fK2147H1_UVLXFZS3XiTU/view?usp=sharing', NULL);

-- Firma: Mixtum (Sugester ID 26275177)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Mixtum', 'Mixtum', 'client', 'Polska', 'Rzezawa', 'MAŁOPOLSKIE', 'Przemysłowa 35', '32-765', 'stanislaw.skura@mixtum.pl', '+48691408482', '9252033878', 'https://mixtum.pl', NULL, NULL, NULL, NULL, '2026-01-10 13:38:13');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Kontakt Rafała');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Środki czystości, producent');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Stanisław', 'Skura', NULL, 'stanislaw.skura@mixtum.pl', '+48691408482', 'https://drive.google.com/file/d//view?usp=sharing', NULL);

-- Firma: Plastcard (Sugester ID 26275096)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Plastcard', 'Plastcard', 'client', 'Polska', 'Kraków', 'MAŁOPOLSKIE', 'Ul Balicka 100', '30-150', 'ajanuszkiewicz@plastcard.pl', '+48515125906', '5512117562', 'https://plastcard.pl', NULL, NULL, 'BIAN', NULL, '2026-01-10 12:41:13');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Reko');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('karty dostępu');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Anna', 'JanuszkiewiczKowalczyk', NULL, 'ajanuszkiewicz@plastcard.pl', '+48515125906', 'https://drive.google.com/file/d//view?usp=sharing', NULL);
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Agnieszka', 'Hondel', NULL, 'ahondel@plastcard.pl', '+48572502015', 'https://drive.google.com/file/d//view?usp=sharing', 'pracuje w Plastcard i Qtubes');

-- Firma: Biuro Informacji i Analiz Naukowych BIAN (Sugester ID 26275052)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Biuro Informacji i Analiz Naukowych BIAN', 'Aneta Januszko-Szakiel', 'partner', 'Polska', NULL, NULL, NULL, NULL, 'aneta.szakiel@bian.pl', NULL, NULL, 'http://www.bian.pl', NULL, NULL, NULL, NULL, '2026-01-10 12:14:33');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('B+R, bony, dofinansowania');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Aneta', 'Januszko-Szakiel', NULL, 'aneta.szakiel@bian.pl', NULL, NULL, NULL);

-- Firma: GigaCon (Sugester ID 26273591)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('GigaCon', 'GigaCon', 'inne', 'Polska', 'Warszawa', 'MAZOWIECKIE', 'Bonifraterska6/8', '00-213', 'anna.karasinska@gigacon.org', '+48506981902', '7010350325', 'https://gigacon.org', NULL, NULL, NULL, NULL, '2026-01-09 20:40:42');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('organizator konferencji online');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Anna', 'Karasińska', NULL, 'anna.karasinska@gigacon.org', '+48506981902', 'https://drive.google.com/file/d//view?usp=sharing', NULL);

-- Firma: Złocień Ubezpieczenia (Sugester ID 26273587)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Złocień Ubezpieczenia', 'ZlocienUbezpieczenia', 'inne', 'Polska', 'Krakow', 'MALOPOLSKIE', 'UlZlocień22Lok2', '30-798', 'info@zlocienubezpieczenia.pl', '+48506979487', '6791436400', 'https://gigacon.org', NULL, NULL, NULL, NULL, '2026-01-09 20:38:16');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('ubezpieczenia');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Bogusława', 'Kusak', NULL, 'info@zlocienubezpieczenia.pl', '+48506979487', 'https://drive.google.com/file/d//view?usp=sharing', NULL);

-- Firma: Witold Sadecki (Sugester ID 26273578)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Witold Sadecki', 'Witold Sadecki', 'partner', 'Polska', 'Kraków', NULL, NULL, '31-826', 'witold@sadecki.org', '+48783942427', '6782740266', 'https://sadecki.org', NULL, NULL, NULL, NULL, '2026-01-09 20:31:27');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Witold', 'Sadecki', NULL, 'witold@sadecki.org', '+48783942427', 'https://drive.google.com/file/d//view?usp=sharing', NULL);

-- Firma: FOGS (Sugester ID 26273433)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('FOGS', 'fogs', 'partner', 'Polska', NULL, NULL, NULL, NULL, 'p.baczewski@fogs.pl', '+48533055750', NULL, 'https://fogs.pl', NULL, NULL, NULL, NULL, '2026-01-09 18:29:49');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Paweł', 'Baczewski', NULL, 'p.baczewski@fogs.pl', '+48533055750', 'https://drive.google.com/file/d//view?usp=sharing', NULL);

-- Firma: AbiFlow sp. z o.o. (Sugester ID 26273430)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('AbiFlow sp. z o.o.', 'AbiFlow sp. z o.o.', 'inne', 'Polska', 'Rzeszów', 'PODKARPACKIE', 'Langiewicza 50', '35-021', 'mm@abiflow.com', '+48500248888', '6463004655', 'http://www.abiflow.com', NULL, NULL, NULL, NULL, '2026-01-09 18:27:54');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('produkcja oprogramowania, software, CRM');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Mateusz', 'Misiuda', 'Business Development Manager', 'mm@abiflow.com', '+48500248888', 'https://drive.google.com/file/d//view?usp=sharing', NULL);

-- Firma: Inwentaryzacje Pro (Sugester ID 26273429)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Inwentaryzacje Pro', 'inwentaryzacjeProSpZoo', 'inne', 'Polska', 'warszawa', 'MAZOWIECKIE', 'ulChroscickiego83Lok16', '02-414', 'wiktoria.staniewska@inwentaryzacjepro.pl', '+48662190997', '5252671274', 'http://www.inwentaryzacjepro.pl', NULL, NULL, NULL, NULL, '2026-01-09 18:27:30');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BCC');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Wiktoria', 'Staniewska', 'Asystentka Zarzadu', 'wiktoria.staniewska@inwentaryzacjepro.pl', '+48662190997', NULL, NULL);

-- Firma: Proinnowacja (Sugester ID 26273425)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Proinnowacja', 'proinnowacja', 'partner', 'Polska', 'Kraków', 'Małopolskie', 'ul. Przykładowa 1', '30-001', 'biuro@proinnowacja.pl', '+48500123456', '6762345678', 'http://proinnowacja.pl', NULL, NULL, NULL, NULL, '2026-01-09 18:22:32');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Dofianansowania');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Agnieszka', 'Rożek', 'Właściciel', 'biuro@proinnowacja.pl', '+48500123456', 'https://drive.google.com/file/d/file123abc/view?usp=sharing', NULL);

-- Firma: Peak11 (Sugester ID 26273422)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Peak11', 'peak11', 'inne', 'Polska', 'Wrocław', NULL, NULL, '50-024', 'dominik.rogoz@peak11.com', '+48698060808', '8971839391', 'http://www.peak11.com', NULL, NULL, NULL, NULL, '2026-01-09 18:21:02');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('produkcja oprogramowania, software, CRM');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Dominik', 'Rogóż', 'CEO', 'dominik.rogoz@peak11.com', '+48698060808', 'https://drive.google.com/file/d//view?usp=sharing', NULL);

-- Firma: CM Damiana (Sugester ID 26273394)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('CM Damiana', 'CM Damiana', 'partner', 'Polska', 'Warszawa', NULL, NULL, '02-739', 'radoslaw.rozek@damian.pl', '+48668344832', '5210336507', 'http://www.damian.pl', NULL, NULL, 'Piotr Szczęch', NULL, '2026-01-09 18:08:16');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('M&A');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('psychoterapia, psychiatria, medycyna, centrum medyczne');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Radosław', 'Rożek', 'Dyrektor Generalny', 'radoslaw.rozek@damian.pl', '+48668344832', 'https://drive.google.com/file/d//view?usp=sharing', 'może kupią MyTherapy');

-- Firma: AdAc Advanced Accounting (Sugester ID 26208406)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('AdAc Advanced Accounting', 'AdAcAdvancedAccounting', 'inne', 'Polska', 'Kraków', NULL, 'Walerego Sławka 5', '30-633', 'marek.szpala@adac.pl', '+48509137593', '6762234509', 'http://adac.pl', NULL, NULL, NULL, NULL, '2026-01-05 11:12:11');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Smartsist');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('księgowość');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Marek', 'Szpala', 'Księgowość spółek', 'marek.szpala@adac.pl', '+48509137593', 'https://drive.google.com/file/d/1zwkyA2ACozXVfG5TkKMNBtkocA8OdBMN/view?usp=sharing', NULL);

-- Firma: B-secure (Sugester ID 26208398)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('B-secure', 'B-secure', 'inne', 'Polska', NULL, NULL, NULL, NULL, 'dawid.mrowiec@bsecure.pl', '+48667051794', '6351743129', 'http://www.bsecure.pl', NULL, NULL, NULL, NULL, '2026-01-05 11:11:13');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Smartsist');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('cyberbezpieczeństwo');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Dawid', 'Mrowiec', NULL, 'dawid.mrowiec@bsecure.pl', '+48667051794', 'https://drive.google.com/file/d/1eijWSgx1F10Sv-FXu0qUsC5PmW4LPxPs/view?usp=sharing', NULL);

-- Firma: ProFM Facility Management (Sugester ID 26208387)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('ProFM Facility Management', 'profmFacilityManagement', 'lead', 'Polska', NULL, NULL, NULL, NULL, 'd.malysa@profm.com.pl', '+48504326028', NULL, 'http://profm.com.pl', NULL, NULL, NULL, NULL, '2026-01-05 11:10:05');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Daniel', 'Małysa', 'Prezes Zarządu', 'd.malysa@profm.com.pl', '+48504326028', 'https://drive.google.com/file/d/1ah0ADYG92sh-QIHaV1lT6gMOv3WAF--a/view?usp=sharing', NULL);

-- Firma: Wellness Travel (Sugester ID 26200324)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Wellness Travel', 'Wellness Travel', 'inne', 'Polska', 'Kraków', NULL, NULL, '31-153', 'kontakt@wellness.travel.pl', '+48698782032', '6762648796', 'http://www.wellness.travel.pl', NULL, NULL, NULL, NULL, '2025-12-31 15:46:48');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('turystyka, podróże dla firm');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Małgorzata', 'Kryczka', 'CEO', 'kontakt@wellness.travel.pl', '+48698782032', 'https://drive.google.com/file/d/1M643U-lnvw1nkIOeMT90gC97b3woKt-M/view?usp=sharing', NULL);

-- Firma: Konsultant Kanada (Sugester ID 26200280)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Konsultant Kanada', 'Konsultant Kanada', 'partner', 'PL', NULL, NULL, NULL, NULL, 'kristof.connect@gmail.com', '+48730186147', NULL, NULL, NULL, NULL, 'BNI Ania Watza', NULL, '2025-12-31 15:29:16');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Reko BNI');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Kristof', 'Grudniewicz', 'International Sales and Customer Service, Support and Training', 'kristof.connect@gmail.com', '+48730186147', 'https://drive.google.com/file/d/1q-pzMZSuDoWXN18WNcueYJRURlstoCRy/view?usp=sharing', NULL);

-- Firma: Itgt (Sugester ID 26200279)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Itgt', 'Itgt', 'inne', 'Polska', 'Kraków', 'MAŁOPOLSKIE', 'ul. Pleszowska 13', '31-228', 'lukasz.walczyk@itgt.pl', '+48606303178', '945-150-14-18', 'http://www.itgt.pl', NULL, NULL, NULL, NULL, '2025-12-31 15:29:04');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('IT, usługi konsultingowe, technologie informatyczne, cyfrowa transformacja');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Łukasz', 'Walczyk', 'Właściciel', 'lukasz.walczyk@itgt.pl', '+48606303178', 'https://drive.google.com/file/d/1a_sjwZUKXukLrHhlqNn-6YlI7eIs40L0/view?usp=sharing', NULL);

-- Firma: Midero S. A. (Sugester ID 26200278)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Midero S. A.', 'Midero S. A.', 'dostawca', 'Polska', 'Kraków', 'MAŁOPOLSKIE', 'Zabłocie 23/23', '30-701', 'a.swierczek@midero.io', '+48535588571', '6762499946', 'http://www.midero.io', NULL, NULL, 'Patrycja Hrabiec-Hojda', NULL, '2025-12-31 15:28:46');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('SEO/SEM, pozycjonowanie stron');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Anna', 'Świerczek', 'COO', 'a.swierczek@midero.io', '+48535588571', 'https://drive.google.com/file/d/1GVSiODjQGOGFTZolIrwxDGahhEyPeYTW/view?usp=sharing', NULL);

-- Firma: Cmw Sp. Zoo. Sp. K. (Sugester ID 26200275)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Cmw Sp. Zoo. Sp. K.', 'Cmw Sp. Zoo. Sp. K.', 'client', 'Polska', 'Kraków', 'MAŁOPOLSKIE', 'Aleja Pokoju 57', '31-564', 'anna@cmw24.pl', '+48696686391', '6751671324', 'http://www.cmw24.pl', NULL, NULL, NULL, NULL, '2025-12-31 15:28:05');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI+');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Ochrona, Monitoring wizyjny');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Anna', 'Setkowicz', 'Wiceprezes Zarządu', 'anna@cmw24.pl', '+48696686391', 'https://drive.google.com/file/d/1TxEWLAtrGaQNpgI0IfimCBD8KSSrW9vn/view?usp=sharing', NULL);

-- Firma: Widacki, Widacka, Podsiedlik Kancelaria Prawna Spółka Komandytowo-Akcyjna (Sugester ID 26200273)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Widacki, Widacka, Podsiedlik Kancelaria Prawna Spółka Komandytowo-Akcyjna', 'Widacki, Widacka, Podsiedlik Kancelaria Prawna Spółka Komandytowo-Akcyjna', 'inne', 'Polska', 'Kraków', 'MAŁOPOLSKIE', 'ul. Karmelicka 47', '31-128', 'monika.widacka@wwpkancelaria.pl', '+48509650419', '676-247-23-44', 'http://www.wwpkancelaria.pl', NULL, NULL, NULL, NULL, '2025-12-31 15:27:48');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI', 'Lewiatan');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('prawo, adwokat');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Monika', 'Widacka', 'Partner, Adwokat', 'monika.widacka@wwpkancelaria.pl', '+48509650419', 'https://drive.google.com/file/d/1iKRREhWdZQK0WLkZdLBVbbT27GrwJSdZ/view?usp=sharing', NULL);

-- Firma: Celion Finanse (Sugester ID 26200271)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Celion Finanse', 'Celion Finanse', 'lead', 'Polska', 'Wrocław', 'DOLNOŚLĄSKIE', 'ul. Kawalerzystów 24/8', '53-004', 'a.rozanski@celion.pl', '+48504214170', '8133604084', 'https://www.celion.pl', NULL, NULL, NULL, NULL, '2025-12-31 15:27:20');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('finanse');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Andrzej', 'Różański', 'Właściciel', 'a.rozanski@celion.pl', '+48504214170', 'https://drive.google.com/file/d/1KGBoQOmzVTHQQt1aiNeWxE9Qeq28aAq4/view?usp=sharing', NULL);

-- Firma: Academy Business Intelligence (Sugester ID 26200269)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Academy Business Intelligence', 'Academy Business Intelligence', 'lead', 'Polska', 'Kraków', NULL, NULL, '31-873', 'elzbieta@jachymczak.pl', '+48793144371', '6792881270', 'http://www.jachymczak.pl', NULL, NULL, NULL, NULL, '2025-12-31 15:27:07');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('szkolenia, coaching, przywództwo');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Elżbieta', 'Jachymczak', 'Prezes Zarządu', 'elzbieta@jachymczak.pl', '+48793144371', 'https://drive.google.com/file/d/1N1wAgD8pqoYtTq8cz4_n_RpLG7XSOAav/view?usp=sharing', NULL);

-- Firma: Five Elements (Sugester ID 26199893)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Five Elements', 'Five Elements', 'lead', 'Polska', 'Warszawa', NULL, NULL, '02-676', 'barbara.giernat@aheadgroup.com.pl', '+48603632166', '5213645396', 'http://aheadgroup.com.pl', NULL, NULL, NULL, NULL, '2025-12-31 13:17:46');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('MBA Polska');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('szkolenia, coaching, przywództwo');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Barbara', 'Majer-Giernat', 'Partner Zarządzający', 'barbara.giernat@aheadgroup.com.pl', '+48603632166', 'https://drive.google.com/file/d/1p-4B6rUEb7y-7Quscr8qRuXQ_ZwBZU_8/view?usp=sharing', NULL);

-- Firma: Marifa (Joanna Chudoba) (Sugester ID 26199658)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Marifa (Joanna Chudoba)', 'Marifa (Joanna Chudoba)', 'partner', 'Polska', 'Katowice', NULL, NULL, '40-145', 'joanna@marifa.com.pl', '+48698003830', '9542385317', 'http://www.marifa.com.pl', NULL, NULL, 'gość BNI', NULL, '2025-12-31 13:09:13');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Gość BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('doradztwo, coaching, strategie');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Joanna', 'Chudoba-Czernecka', 'Doradztwo Biznesowe', 'joanna@marifa.com.pl', '+48698003830', 'https://drive.google.com/file/d/1E-HVPCxMLQ-r6sKPt1hf2dD7bTAhcrtw/view?usp=sharing', NULL);

-- Firma: Złoty Kłos (Sugester ID 26199655)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Złoty Kłos', 'Złoty Kłos', 'inne', 'Polska', 'Dobczyce', 'MAŁOPOLSKIE', 'ul. Jagiellońska 39A', '32-410', 'zlotyklos@interia.eu', '+48502831888', '6811003450', 'https://zlotyklos.com.pl', NULL, NULL, NULL, NULL, '2025-12-31 13:08:47');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Gość BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Piekarnia - Cukiernia');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Tomasz', 'Brożek', 'Współwłaściciel', 'zlotyklos@interia.eu', '+48502831888', 'https://drive.google.com/file/d/1BoceQfa7jqbP1GLx-HNA9-3lLAt5S72X/view?usp=sharing', NULL);

-- Firma: Vaillant & Saunier Duval (Sugester ID 26199650)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Vaillant & Saunier Duval', 'Vaillant & Saunier Duval', 'inne', 'Polska', 'Kraków', NULL, NULL, '31-873', 'sekulowiczpawel@o2.pl', '+48503133849', '6791484501', 'http://www.vaillant-duval.pl', NULL, NULL, NULL, NULL, '2025-12-31 13:07:48');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Gość BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Serwis urządzeń gazowych');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Paweł', 'Sekułowicz', NULL, 'sekulowiczpawel@o2.pl', '+48503133849', 'https://drive.google.com/file/d/1LmZK4NnjrjzSSX4vyTh0U0l5hwieXDP-/view?usp=sharing', NULL);

-- Firma: Estimate (Sugester ID 26199646)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Estimate', 'Estimate', 'lead', 'Polska', 'Gdańsk', NULL, NULL, '80-034', 'wojtek@i-estimate.pl', '+48606195589', '5832533956', 'http://www.i-estimate.pl', NULL, NULL, NULL, NULL, '2025-12-31 13:06:01');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Building Cost Estimation');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Wojciech', 'Brzeziński', NULL, 'wojtek@i-estimate.pl', '+48606195589', 'https://drive.google.com/file/d/15QtxMrJFlyhbIcb4XSMeZKocRvfqys_S/view?usp=sharing', NULL);

-- Firma: Human Craft (Sugester ID 26199645)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Human Craft', 'Human Craft', 'inne', 'Polska', 'Kraków', NULL, NULL, '31-511', 'p.inna@human-craft.pl', '+48790884943', '6762584897', 'http://human-craft.pl', NULL, NULL, NULL, NULL, '2025-12-31 13:05:46');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Gość BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('agencja pracy');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Inna', 'Kowalska', 'Development Manager', 'p.inna@human-craft.pl', '+48790884943', 'https://drive.google.com/file/d/1HvYcJFGaWEHsQv7PxfE-f_zc0eZGh4SI/view?usp=sharing', NULL);

-- Firma: J Dauman Group (Sugester ID 26199639)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('J Dauman Group', 'JDaumanGroup', 'inne', 'United Kingdom', 'London', NULL, 'CravenHouse,40-44UxbridgeRoad', 'W52BS', 'a.crich@jdauman.com', '+48505717215', '5252839352', 'http://jdauman.com', NULL, NULL, NULL, NULL, '2025-12-31 13:02:48');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Lewiatan');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('księgowość');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Aleksandra', 'Crich', 'HeadOfSales', 'a.crich@jdauman.com', '+48505717215', 'https://drive.google.com/file/d/1qEEtgePRK1aPaAhyc7kvwagZXcz5MO5e/view?usp=sharing', 'robiła mi zdjęcie z Buzkiem. :)');

-- Firma: 5DGroup (Sugester ID 26199617)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('5DGroup', 'Engineering Construction Solutions', 'lead', 'Polska', 'Katowice', 'ŚLĄSKIE', 'ul. Mickiewicza29', '40-085', 'mateusz.marciniak@5dgroup.pl', '+48690566094', '787-210-52-74', 'http://www.5dgroup.pl', NULL, NULL, 'członek BNI Milion', NULL, '2025-12-31 12:55:47');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('budowlanka');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Mateusz', 'Marciniak', 'DyrektorOperacyjny', 'mateusz.marciniak@5dgroup.pl', '+48690566094', 'https://drive.google.com/file/d/18mHC9BF1eRv6L5oAVbUIBL32hxyGBTEO/view?usp=sharing', NULL);

-- Firma: KRK Novum (Sugester ID 26199613)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('KRK Novum', 'KRK Novum', 'inne', 'Polska', 'Kraków', NULL, NULL, '30-206', 'andrzej.krupinski@krknovum.pl', '+48601934002', '6793181829', 'https://exnatura.pl', NULL, NULL, 'członek BNI Milion', NULL, '2025-12-31 12:53:46');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('sprzątanie, zieleń');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Andrzej', 'Krupiński', NULL, 'andrzej.krupinski@krknovum.pl', '+48601934002', 'https://drive.google.com/file/d/1Yhfcv8_f_D5y10OBZKZtiRiUbOj49U-m/view?usp=sharing', NULL);

-- Firma: LeadeRevolution (Sugester ID 26199607)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('LeadeRevolution', 'LeadeRevolution', 'partner', 'Polska', 'Warszawa', NULL, NULL, '02-798', 'ania@leaderevolution.pl', '+48512973303', '9512211905', 'https://leaderevolution.pl', NULL, NULL, 'gość BNI', NULL, '2025-12-31 12:51:45');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Gość BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('coachng, szkolenia, HR, leaderdship');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Ania', 'Sidorowicz', NULL, 'ania@leaderevolution.pl', '+48512973303', 'https://drive.google.com/file/d/1fj9SInBc4PNLHa2ce1vbXXkv6NSNFrEr/view?usp=sharing', NULL);

-- Firma: Desi9n Sp Z O. O. (Sugester ID 26199567)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Desi9n Sp Z O. O.', 'Desi9n Sp Z O. O.', 'inne', 'Polska', 'Kraków', 'MAŁOPOLSKIE', 'Ul. Królewska 65a', '30-081', 'kontakt@desi9n.pl', '+48505097797', '6772377357', 'https://desi9n.pl', NULL, NULL, NULL, NULL, '2025-12-31 12:47:47');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Lewiatan');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('software house, oprogramowanie');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Adrian', 'Gadzina', 'Inż. , CEO, Fullstack Developer At Design.pl', 'kontakt@desi9n.pl', '+48505097797', 'https://drive.google.com/file/d/1SW-V9QI5dJSb0I0d98BI8GB1vCX3RFxK/view?usp=sharing', NULL);

-- Firma: Kancelaria Patentowa LEDREMS® (Sugester ID 26199563)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Kancelaria Patentowa LEDREMS®', 'Kancelaria Patentowa LEDREMS®', 'inne', 'Polska', 'Kraków', 'MAŁOPOLSKIE', 'ul. Twardowskiego 57', '30-346', 'jolanta.wrobel@pirp.org.pl', '+48600852802', '6280009145', 'http://www.pirp.org.pl', NULL, NULL, NULL, NULL, '2025-12-31 12:46:49');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Lewiatan');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Prawo własności przemysłowej, patenty, znaki towarowe');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Jolanta', 'Wróbel', 'Europejski Rzecznik Patentowy', 'jolanta.wrobel@pirp.org.pl', '+48600852802', 'https://drive.google.com/file/d/1zITjR_Gli6eSW-tkckatHf8rRlaEfCuI/view?usp=sharing', NULL);

-- Firma: SEMA-PRINT (Sugester ID 26186342)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('SEMA-PRINT', 'SEMA-PRINT', 'inne', 'Polska', 'Kraków', 'MAŁOPOLSKIE', 'Wadowska 2', '31-990', 'jarek@semaprint.com.pl', '+48501496754', '6782676587', 'https://semaprint.com.pl', NULL, NULL, NULL, (SELECT id FROM users WHERE full_name IN ('Lukasz Brzyski','Łukasz Brzyski') LIMIT 1), '2025-12-27 21:23:46');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI+', 'BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('drukarnia, koszulki, ciuchy');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Jarosław', 'Kochman', NULL, 'jarek@semaprint.com.pl', '+48501496754', NULL, NULL);
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Marcin', 'Mazurek', NULL, 'marcin@semaprint.com.pl', '501496753', NULL, NULL);

-- Firma: Maylane Polska (Sugester ID 26186307)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Maylane Polska', 'F. M. Dudhia', 'inne', 'Polska', 'Kraków', 'MAŁOPOLSKIE', 'Rynek Główny 33', '31-010', 'CONTACT@MAYLANE.COM (fdudhia@maylane.pl)', NULL, '6762235176 (6762235176)', 'http://www.maylane.pl/', NULL, NULL, 'EMBA', (SELECT id FROM users WHERE full_name IN ('Lukasz Brzyski','Łukasz Brzyski') LIMIT 1), '2025-12-27 20:36:28');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('KSB');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('nieruchomości');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Max', 'Dudhia', NULL, 'CONTACT@MAYLANE.COM (fdudhia@maylane.pl)', NULL, NULL, NULL);

-- Firma: Nexia Global (Sugester ID 26185022)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Nexia Global', 'NexiaGlobal', 'inne', 'Polska', 'Opole', 'OPOLSKIE', 'Technologiczna 2', '45-839', 'm.stelmach@nexia.global', '+48607057157', '7543363294', 'http://www.nexia.global', NULL, NULL, NULL, NULL, '2025-12-25 16:03:51');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Gość BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('internacjonalizacja, wyjście na rynki zagraniczne');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Marta', 'Stelmach', 'Co Founder CEO', 'm.stelmach@nexia.global', '+48607057157', NULL, 'poznana na BNI, wyprowadza klientów do Dubaju, Arabii Saudyjskiej');

-- Firma: Tomex Brakes Sp. z o.o. Sp.k. (Sugester ID 26184578)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Tomex Brakes Sp. z o.o. Sp.k.', 'Tomex Brakes Sp. z o.o. Sp.k.', 'lead', 'Poland', 'Budzyń', NULL, 'os. Cechowe 8', '64-840', 'b.nowak@tomexbrakes.pl', '+48695205611', '6070055512', 'http://tomexbrakes.pl', NULL, NULL, 'MBA Polska', NULL, '2025-12-24 12:24:57');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('MBA Polska');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('produkcja hamulców, automotive');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Bartosz', 'Nowak', 'Kierownik Sprzedaży i Marketingu', 'b.nowak@tomexbrakes.pl', '+48695205611', 'xxx', NULL);

-- Firma: Reklamini.pl (Sugester ID 26184576)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Reklamini.pl', 'Reklamini.pl', 'inne', 'Polska', 'Gdańsk', NULL, NULL, '80-407', 'andrzej@reklamini.pl', NULL, '5842491108', 'https://reklamini.pl', NULL, NULL, NULL, NULL, '2025-12-24 12:24:45');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('MBA Polska');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('marketing, reklama');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Andrzej', 'Żurawik', NULL, 'andrzej@reklamini.pl', NULL, NULL, NULL);

-- Firma: Explore Markets (Sugester ID 26184575)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Explore Markets', 'ExploreMarkets', 'inne', 'Poland', 'Warsaw', 'MAZOWIECKIE', 'ul. Flory 7/30', '00-586', 'fredrik.udd@exploremarkets.pl', '+48602417917', '7011046162', 'http://exploremarkets.eu', NULL, NULL, NULL, NULL, '2025-12-24 12:24:32');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('MBA Polska');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('doradztwo, wyjście na rynki skandynawskie');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Fredrik', 'Udd', 'ManagingPartner', 'fredrik.udd@exploremarkets.pl', '+48602417917', NULL, NULL);

-- Firma: Next Level Academy by ModraSova (Sugester ID 26184574)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Next Level Academy by ModraSova', 'Next Level Academy by ModraSova', 'lead', 'Polska', 'Inowrocław', NULL, NULL, '88-100', 'info@nextlevelacademy.pl', '+48504463920', '5562791834', 'https://nextlevelacademy.pl', NULL, NULL, NULL, NULL, '2025-12-24 12:24:18');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Alexandra', 'Kunowska', 'Founder', 'info@nextlevelacademy.pl', '+48504463920', NULL, NULL);

-- Firma: Atneo Doradztwo Cło Podatki Prawo Sp. z o.o. (Sugester ID 26184573)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Atneo Doradztwo Cło Podatki Prawo Sp. z o.o.', 'Atneo Doradztwo Cło Podatki Prawo Sp. z o.o.', 'lead', 'Polska', 'Warszawa', 'MAZOWIECKIE', 'ul. Śniadeckich 17', '00-654', 'rafal.pogorzelski@atneo.pl', '+48664154217', '7010827182', 'http://www.atneo.pl', NULL, NULL, NULL, NULL, '2025-12-24 12:23:46');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('doradztwo podatkowe, celne');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Rafał', 'Pogorzelski', 'Partner, Doradca Podatkowy nr 12102', 'rafal.pogorzelski@atneo.pl', '+48664154217', NULL, NULL);

-- Firma: Waterwalk Partners (Sugester ID 26184572)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Waterwalk Partners', 'Waterwalk® Partners', 'inne', 'Poland', 'Warsaw', NULL, 'ul. Śniadeckich 17', '00-654', 'mariusz.kowalski@waterwalk.partners', '+48661929486', '5252818967', 'http://waterwalk.partners', NULL, NULL, NULL, NULL, '2025-12-24 12:23:35');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('MBA Polska');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('doradztwo biznesowe, business consulting');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Mariusz', 'Kowalski', 'Partner & Founder', 'mariusz.kowalski@waterwalk.partners', '+48661929486', NULL, NULL);

-- Firma: Eden Millenia (Sugester ID 26184571)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Eden Millenia', 'EdenMilleniaSpZoO', 'lead', 'Polska', 'Kraków', 'MAŁOPOLSKIE', 'Retoryka 1', '33-332', 'm.krupa@eden-millenia.com', '+48570710546', '5262594611', 'http://eden-millenia.com', NULL, NULL, NULL, NULL, '2025-12-24 12:23:23');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('nieruchomości');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Michał', 'Krupa', 'CeoFounder', 'm.krupa@eden-millenia.com', '+48570710546', NULL, NULL);

-- Firma: Kls S.J. (Sugester ID 26184564)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Kls S.J.', 'Kls S.J.', 'lead', 'Polska', 'Bytom', 'ŚLĄSKIE', 'ul. Musialika 53', '41-902', 'k.bochenek@kls.pl', '+48578600440', '626-26-93-007', 'http://www.kls.pl', NULL, NULL, NULL, NULL, '2025-12-24 12:16:03');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Smartsist');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('odzież robocza');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Krzysztof', 'Bochenek', NULL, 'k.bochenek@kls.pl', '+48578600440', NULL, NULL);

-- Firma: m Finanse (Sugester ID 26184563)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('m Finanse', 'm Finanse', 'lead', 'Poland', 'Warszawa', 'MAZOWIECKIE', 'ul. Skorupki 5', '00-546', 'edyta.fiet@mfinanse.pl', '+48606563626', '7251903631', 'https://mfinanse.pl', NULL, NULL, NULL, NULL, '2025-12-24 12:15:31');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('finanse');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Edyta', 'Fiet', 'Właściciel', 'edyta.fiet@mfinanse.pl', '+48606563626', NULL, NULL);

-- Firma: Indywidualny Kadr (Sugester ID 26184562)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Indywidualny Kadr', 'Indywidualny Kadr', 'lead', 'Polska', NULL, NULL, NULL, NULL, 'indywidualnykadr@gmail.com', '+48732492964', NULL, NULL, NULL, NULL, NULL, NULL, '2025-12-24 12:15:17');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Amina', 'Dadache', NULL, 'indywidualnykadr@gmail.com', '+48732492964', NULL, NULL);

-- Firma: Be Partners (Sugester ID 26184561)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Be Partners', 'Be Partners', 'lead', 'Polska', 'Warszawa', 'MAZOWIECKIE', 'Wołoska 9', '02-583', 'pawel.nurzynski@bepartners.pl', '+48502558309', '6762446700', 'http://www.bepartners.pl', NULL, NULL, NULL, NULL, '2025-12-24 12:15:06');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Doradztwo i szkolenia');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Paweł', 'Nurzyński', 'Partner & Founder', 'pawel.nurzynski@bepartners.pl', '+48502558309', NULL, NULL);

-- Firma: Baront (Sugester ID 26184560)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Baront', 'Baront', 'lead', 'Polska', 'Sękowa', NULL, NULL, '38-307', 'a.sieklucki@icloud.com', '+48501777746', '7380004052', 'http://www.baront.pl', NULL, NULL, NULL, NULL, '2025-12-24 12:14:54');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Wykończenia wnętrz');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Artur', 'Sieklucki', 'Business Owner', 'a.sieklucki@icloud.com', '+48501777746', NULL, NULL);

-- Firma: Corporate Connections (Sugester ID 26184559)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Corporate Connections', 'CorporateConnections™', 'lead', 'Poland', 'Warsaw', 'MAZOWIECKIE', 'Chłodna 51', '00-867', 'l.olenski@cc.pl', '+48602239460', '5252796191', 'http://www.cc.pl', NULL, NULL, NULL, NULL, '2025-12-24 12:14:42');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Łukasz', 'Oleński', 'RelationshipManager', 'l.olenski@cc.pl', '+48602239460', NULL, NULL);

-- Firma: Free Wolf (Sugester ID 26184558)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Free Wolf', 'Free Wolf', 'lead', 'Polska', 'Sosnowiec', NULL, NULL, '41-200', 'maciej.dybczynski@freewolf.pl', '+48504014390', '6443577742', 'https://freewolf.pl', NULL, NULL, NULL, NULL, '2025-12-24 12:14:28');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('MBA Polska');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('turystyka, podróże dla firm');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Maciej', 'Dybczyński', NULL, 'maciej.dybczynski@freewolf.pl', '+48504014390', NULL, NULL);

-- Firma: Raytheon An Rtx Business (Sugester ID 26184557)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Raytheon An Rtx Business', 'RaytheonAnRtxBusiness', 'lead', 'Poland', 'Warsaw', 'MAZOWIECKIE', 'Mokotowska 49 (5th Floor)', '00-542', 'Kamil.J.Ziarnowski@rtx.com', '+48880733998', '5262799341', 'https://www.rtx.com', NULL, NULL, NULL, NULL, '2025-12-24 12:14:17');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Kamil', 'Ziarnowski', 'PrincipalSpecialistInSales/BusinessDevelopment', 'Kamil.J.Ziarnowski@rtx.com', '+48880733998', NULL, NULL);

-- Firma: Dagessa Business Consulting / Dagessa Sp. z o.o. (Sugester ID 26184555)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Dagessa Business Consulting / Dagessa Sp. z o.o.', 'Dagessa Business Consulting / Dagessa Sp. z o.o.', 'lead', 'Polska', 'Katowice', 'ŚLĄSKIE', 'ul. Kościuszki 11 lok. 4', '40-049', 'piotr.nowak@dagessa.pl', '+48503090800', '9542456079', 'http://www.dagessa.pl', NULL, NULL, NULL, NULL, '2025-12-24 12:13:54');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Piotr', 'Nowak', 'Prezes Zarządu', 'piotr.nowak@dagessa.pl', '+48503090800', NULL, NULL);

-- Firma: Dobre Strony (Sugester ID 26184554)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Dobre Strony', 'Dobre Strony', 'lead', 'Polska', 'Kraków', NULL, NULL, '30-740', 'karolina@dobrestrony.it', '+48502989093', '6811904257', 'http://www.dobrestrony.it', NULL, NULL, NULL, NULL, '2025-12-24 12:13:42');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Karolina', 'Marzyńska', NULL, 'karolina@dobrestrony.it', '+48502989093', NULL, NULL);

-- Firma: Adams Group (Sugester ID 26184549)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Adams Group', 'AdamsGroup', 'lead', 'Poland', 'Kobyla Góra', NULL, 'Ligota 59b', '63-507', 'lukasz.kucinski@adamsgroup.pl', '+48795072534', '5140284879', 'http://www.adamsgroup.pl', NULL, NULL, NULL, NULL, '2025-12-24 12:02:12');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('MBA Polska');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('meble');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Łukasz', 'Kuciński', 'Dyrektor Sprzedaży i Marketingu', 'lukasz.kucinski@adamsgroup.pl', '+48795072534', NULL, NULL);

-- Firma: Womar Sp. Z O.o. (Sugester ID 26184540)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Womar Sp. Z O.o.', 'WOMAR Sp. z o.o.', 'lead', 'Polska', 'Kraków', 'MAŁOPOLSKIE', 'ul. Przykopy 5', '30-612', 'jszkaradek@womar.com', '+48601442418', '5130238837', 'http://www.womar.com', NULL, NULL, NULL, NULL, '2025-12-24 11:56:00');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Energia odnawialna i klimat');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Jerzy', 'Szkaradek', 'Opiekun Klienta Kluczowego', 'jszkaradek@womar.com', '+48601442418', NULL, NULL);

-- Firma: PKO Bank Polski (Sugester ID 26184537)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('PKO Bank Polski', 'PKO Bank Polski', 'lead', 'Polska', 'Poznań', 'WIELKOPOLSKIE', 'ul. Roosevelta 22', '60-829', 'joanna.kucharska2@pkobp.pl', '+48600481206', '5250007738', 'http://www.pkobp.pl', NULL, NULL, NULL, NULL, '2025-12-24 11:54:01');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Joanna', 'Kucharska', 'Dyrektor', 'joanna.kucharska2@pkobp.pl', '+48600481206', NULL, NULL);

-- Firma: Itek Green Technologies (Sugester ID 26184535)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Itek Green Technologies', 'ItekGreenTechnologies', 'lead', 'Polska', 'Gdynia', 'POMORSKIE', 'Chwarznieńska 170A/5', '81602', 'szymon@itek.green', '+48604599739', '9571072753', 'http://itek.green', NULL, NULL, NULL, NULL, '2025-12-24 11:52:00');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Szymon', 'Kosiarz', 'Business Development Manager, Poland', 'szymon@itek.green', '+48604599739', NULL, NULL);

-- Firma: Aldi Sp. z o.o. (Sugester ID 26184534)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Aldi Sp. z o.o.', 'Aldi Sp. Z O.o.', 'lead', 'Polska', 'Sopot', 'POMORSKIE', 'ul. Generała Władysława Sikorskiego 8/10', '81-827', 'przemyslaw.bednarski@aldi.pl', '+48881971207', '6292248566', 'http://www.aldi.pl', NULL, NULL, NULL, NULL, '2025-12-24 11:51:01');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('markety');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Przemysław', 'Bednarski', 'Real Estate & Expansion Manager', 'przemyslaw.bednarski@aldi.pl', '+48881971207', NULL, NULL);

-- Firma: Krajowy Instytut Prawa Gospodarczego Sp z o.o. (Sugester ID 26184532)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Krajowy Instytut Prawa Gospodarczego Sp z o.o.', 'Krajowy Instytut Prawa Gospodarczego Sp z o.o.', 'lead', 'Polska', 'Warszawa', 'MAZOWIECKIE', 'Grzybowska 87', '00-844', 'pawel.juskowiak@kipg.pl', '+48602210006', '5272757671', 'http://www.kipg.pl', NULL, NULL, NULL, NULL, '2025-12-24 11:50:01');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('MBA Polska');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('weryfikacja podmiotów');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Paweł', 'Juskowiak', 'Prezes Zarządu', 'pawel.juskowiak@kipg.pl', '+48602210006', NULL, NULL);

-- Firma: Elżbieta Dönmez (Sugester ID 26184490)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Elżbieta Dönmez', 'Elżbieta Dönmez', 'lead', 'Polska', NULL, NULL, NULL, NULL, 'elzbieta.donmez@gmail.com', '+48508127555', NULL, NULL, NULL, NULL, NULL, NULL, '2025-12-24 10:13:35');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Elżbieta', 'Dönmez', 'Trener Rozwoju Osobowości i Dynamiki Stresu', 'elzbieta.donmez@gmail.com', '+48508127555', NULL, NULL);

-- Firma: Strefa life (Sugester ID 26184486)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Strefa life', 'Strefa life', 'partner', 'PL', 'Kraków', NULL, NULL, '31-025', 'sierka.anna@gmail.com', '+48609632747', '6762243763', 'https://strefalife.com/', NULL, NULL, 'BNI Szulc', NULL, '2025-12-24 09:47:34');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Reko BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('psychoterapia');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Anna', 'Sierka', NULL, 'sierka.anna@gmail.com', '+48609632747', NULL, NULL);

-- Firma: Księgowość (Led-pol) (Sugester ID 26184485)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Księgowość (Led-pol)', 'Księgowość (Led-pol)', 'partner', 'PL', NULL, NULL, NULL, NULL, 'malgorzata.biuromm@wp.pl', '+48607594338', NULL, NULL, NULL, NULL, 'Wojciech Lelito', NULL, '2025-12-24 09:47:34');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Małgorzata', 'Martko', NULL, 'malgorzata.biuromm@wp.pl', '+48607594338', NULL, NULL);

-- Firma: LUX MED Sp. z o.o. (Sugester ID 26184483)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('LUX MED Sp. z o.o.', 'Luxmed', 'client', 'Polska', 'Warszawa', 'MAZOWIECKIE', 'Szturmowa 2', '02-676', 'Radoslaw.Fratczak@luxmed.pl', '+48695090319', '5272528741', 'http://www.luxmed.pl', NULL, NULL, 'Mytherapy', NULL, '2025-12-24 09:47:34');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('M&A');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Medycyna/Zdrowie');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Radosław', 'Frątczak', 'Menedżerka Ds Akwizycji I Rozwoju', 'Radoslaw.Fratczak@luxmed.pl', '+48695090319', 'https://drive.google.com/file/d//view?usp=sharing', NULL);
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Małgorzata', 'Adamiec', NULL, 'malgorzata.adamiec@luxmed.pl', '+48724445884', 'https://drive.google.com/file/d//view?usp=sharing', NULL);

-- Firma: proflow.pl (Sugester ID 26184482)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('proflow.pl', 'proflow.pl', 'dostawca', 'PL', 'Chrzanów', 'Województwo małopolskie', NULL, '40-085', NULL, '+48505476464', '6342825447', 'https://proflow.pl', NULL, NULL, 'BNI', NULL, '2025-12-24 09:47:34');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('system CRM');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Mirosław', 'Kryska', NULL, NULL, '+48505476464', NULL, NULL);

-- Firma: Software Mansion (Sugester ID 26184480)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Software Mansion', 'Software Mansion', 'lead', 'PL', 'Kraków', NULL, NULL, '30-701', 'julianna.lekarczyk@swmansion.com', '+48530243548', '6762464105', 'http://www.swmansion.com', NULL, NULL, 'Kokurewicz', NULL, '2025-12-24 09:47:34');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Reko BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('software house, oprogramowanie');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Julianna', 'Lekarczyk-Kękuś', NULL, 'julianna.lekarczyk@swmansion.com', '+48530243548', NULL, NULL);

-- Firma: Anna Kruk (Sugester ID 26184479)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Anna Kruk', 'Anna Kruk', 'partner', 'PL', 'Kraków', NULL, NULL, NULL, 'anetpol@gmail.com', '+48508896205', NULL, NULL, NULL, NULL, NULL, NULL, '2025-12-24 09:47:34');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Gość BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('kontroling finansowy, finanse');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Anna', 'Kruk', NULL, 'anetpol@gmail.com', '+48508896205', NULL, NULL);

-- Firma: Aberit (Sugester ID 26184478)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Aberit', 'Aberit', 'partner', 'PL', 'Rzeszów', NULL, NULL, '54-204', 'm.misiuda@aberit.eu', '+48500248888', '8971735161', 'http://www.aberit.eu', NULL, NULL, NULL, NULL, '2025-12-24 09:47:34');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('software house, CRM, ERP, oprogramowanie');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Mateusz', 'Misiuda', NULL, 'm.misiuda@aberit.eu', '+48500248888', NULL, NULL);

-- Firma: Inspire Sourcing (Sugester ID 26184477)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Inspire Sourcing', 'Inspire Sourcing', 'partner', 'PL', 'Kraków', NULL, NULL, '31-202', 'sylwia.leniartek@isourcing.pl', '+48124292021', '9452144869', 'http://www.isourcing.pl', NULL, NULL, NULL, NULL, '2025-12-24 09:47:34');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Reko BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('szkolenia, testy osobowości, Bridge, DISC, Galloup');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Sylwia', 'Leniartek', NULL, 'sylwia.leniartek@isourcing.pl', '+48124292021', NULL, NULL);

-- Firma: LTV Project (Sugester ID 26184476)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('LTV Project', 'LTV Project', 'lead', 'PL', 'Oświęcim', NULL, NULL, '44-100', 'jmoldoch@ltvprojekt.pl', '+48664474367', '6312662991', 'http://www.ltvproject.co.uk', NULL, NULL, NULL, NULL, '2025-12-24 09:47:34');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Reko BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('oświetlenie przemysłowe, Newsletter');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Joanna', 'Mołdoch', NULL, 'jmoldoch@ltvprojekt.pl', '+48664474367', NULL, NULL);

-- Firma: WESTA GROUP (Sugester ID 26184475)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('WESTA GROUP', 'WESTA GROUP', 'client', 'PL', 'Wola Rzędzińska', NULL, NULL, '33-150', 'grzegorz.syrek@westagroup.pl', '+48606176209', '8733251761', 'https://www.westagroup.pl/', NULL, NULL, 'Ania Gustak', NULL, '2025-12-24 09:47:33');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Reko BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('skład budowlany, Newsletter');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Grzegorz', 'Syrek', NULL, 'grzegorz.syrek@westagroup.pl', '+48606176209', NULL, NULL);

-- Firma: Proenergy (Sugester ID 26184474)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Proenergy', 'Proenergy', 'lead', 'PL', 'Kraków', NULL, NULL, '30-698', 'karolmiskiewicz@proenergy.com.pl', '+48500331722', '6793102379', 'http://www.proenergy.com.pl', NULL, NULL, 'Aneta Januszko-Szakiel', NULL, '2025-12-24 09:47:33');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('fotowoltaika, pompy ciepła, instalacje, Newsletter');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Karol', 'Miśkiewicz', NULL, 'karolmiskiewicz@proenergy.com.pl', '+48500331722', NULL, NULL);

-- Firma: Uni-Box (Sugester ID 26184473)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Uni-Box', 'Uni-Box', 'lead', 'PL', 'Kobylany', NULL, NULL, NULL, 'urszula.kielar@uni-box.pl', '+48501777705', '1251624647', 'https://uni-box.pl/', NULL, NULL, 'Alicja Łapińska', NULL, '2025-12-24 09:47:33');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('produkcja opakowań, Newsletter');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Urszula', 'Kielar', NULL, 'urszula.kielar@uni-box.pl', '+48501777705', NULL, NULL);

-- Firma: BeCool (Sugester ID 26184472)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('BeCool', 'BeCool', 'client', 'PL', 'Kraków', 'MAŁOPOLSKIE', 'Stojałowskiego 35/30', '30-611', 'biuro@becool.com.pl', '+48607312718', '6793260376', 'https://becool.com.pl/', NULL, NULL, NULL, NULL, '2025-12-24 09:47:33');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Chłodnictwo i Klimatyzacja');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Bartosz', 'Baran', NULL, 'biuro@becool.com.pl', '+48607312718', NULL, NULL);

-- Firma: Stan Trans (Sugester ID 26184471)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Stan Trans', 'Stan Trans', 'lead', 'PL', 'Kraków', NULL, NULL, '31-752', 's.grabiec@stantrans.com.pl', '+48451059885', '6783115340', 'http://www.stantrans.com.pl', NULL, NULL, NULL, NULL, '2025-12-24 09:47:33');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Reko BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('transport, logistyka, spedycja, TLS');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Sławomir', 'Grabiec', NULL, 's.grabiec@stantrans.com.pl', '+48451059885', NULL, NULL);

-- Firma: Kedarix (Sugester ID 26184470)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Kedarix', 'Kedarix', 'lead', 'PL', 'Zabierzów Bocheński', NULL, NULL, '32-007', 'aszewczyk@kedarix.com', '+48696030900', '6831861751', 'https://kedarix.com/', NULL, NULL, 'Aneta Januszko-Szakiel', NULL, '2025-12-24 09:47:33');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Reko BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('usczelki, produkcja');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Agnieszka', 'Szewczyk', NULL, 'aszewczyk@kedarix.com', '+48696030900', NULL, NULL);

-- Firma: CMW Ochrona (Sugester ID 26184469)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('CMW Ochrona', 'CMW Ochrona', 'client', 'PL', 'Kraków', NULL, NULL, '31-623', 'anna@altes.pl', '+48696686391', '6782806259', 'https://altes.pl/', NULL, NULL, NULL, NULL, '2025-12-24 09:47:33');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('bezpieczeństwo, monitoring');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Anna', 'Setkowicz', NULL, 'anna@altes.pl', '+48696686391', NULL, NULL);

-- Firma: Hat-Trick (Sugester ID 26184468)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Hat-Trick', 'Hat-Trick', 'lead', 'PL', 'Zator', NULL, NULL, '32-640', 'janusz@hattrick.net.pl', '+48606460806', '5492193568', 'https://hattrick.net.pl/', NULL, NULL, NULL, NULL, '2025-12-24 09:47:33');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Przemysł, plastik, produkcja');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Janusz', 'Płonka', NULL, 'janusz@hattrick.net.pl', '+48606460806', NULL, NULL);

-- Firma: S2Innovation (Sugester ID 26184467)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('S2Innovation', 'S2Innovation', 'client', 'PL', 'Kraków', NULL, NULL, '30-348', 'piotr.goryl@s2innovation.com', '+48795794004', '6762562470', 'https://s2innovation.com', NULL, NULL, 'Łukasz Żytniak', NULL, '2025-12-24 09:47:33');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('EMBA');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('oprogramowanie, nauka, Szwecja, bodyleasing, python');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Piotr', 'Goryl', NULL, 'piotr.goryl@s2innovation.com', '+48795794004', NULL, NULL);
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Łukasz', 'Żytniak', NULL, 'lukasz.zytniak@s2innovation.com', '511049397', NULL, NULL);

-- Firma: Raben Group (Sugester ID 26184466)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Raben Group', 'Raben Group', 'lead', 'PL', 'Robakowo', NULL, NULL, '62-023', 'katarzyna.ostojska@raben-group.com', '+48693800072', '7770005553', 'https://raben-group.com', NULL, NULL, 'Ania Pabian', NULL, '2025-12-24 09:47:33');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Reko BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('transport, logistyka, spedycja');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Katarzyna', 'Ostojska', NULL, 'katarzyna.ostojska@raben-group.com', '+48693800072', NULL, NULL);

-- Firma: Systemcold Solutions (Sugester ID 26184465)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Systemcold Solutions', 'Systemcold Solutions', 'client', 'PL', 'Szczepanowice (Słomniki)', NULL, NULL, '30-698', 'j.clapa@systemcold.pl', '+48575991121', '6793108603', 'https://systemcold.pl', NULL, NULL, NULL, NULL, '2025-12-24 09:47:33');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('chłodnictwo, pompy ciepła, Newsletter');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Janusz', 'Cłapa', NULL, 'j.clapa@systemcold.pl', '+48575991121', NULL, NULL);

-- Firma: HR BeeHive (Sugester ID 26184464)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('HR BeeHive', 'HR BeeHive', 'partner', 'PL', 'Warszawa', NULL, NULL, '00-105', 'contact@hrbeehive.com', '+48784408548', '5213904669', 'http://www.hrbeehive.pl', NULL, NULL, 'EMBA28', NULL, '2025-12-24 09:47:33');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('EMBA');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('HR');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Dominika', 'Korneta-Golec', NULL, 'contact@hrbeehive.com', '+48784408548', NULL, NULL);

-- Firma: Katarzyna Kiszkiel | Analityk Biznesowy (Sugester ID 26184463)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Katarzyna Kiszkiel | Analityk Biznesowy', 'Katarzyna Kiszkiel | Analityk Biznesowy', 'partner', 'PL', 'Komorów', NULL, NULL, '05-806', 'katarzyna.kiszkiel@analitykbiznesowy.com', '+48501961504', '1181652434', 'http://www.analitykbiznesowy.com', NULL, NULL, NULL, NULL, '2025-12-24 09:47:32');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('analityka biznesowa');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Katarzyna', 'Kiszkiel', NULL, 'katarzyna.kiszkiel@analitykbiznesowy.com', '+48501961504', NULL, NULL);

-- Firma: KAMIL ZOŃ ROYAL SERVICE (Kamil Zoń) (Sugester ID 26184462)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('KAMIL ZOŃ ROYAL SERVICE (Kamil Zoń)', 'KAMIL ZOŃ ROYAL SERVICE (Kamil Zoń)', 'lead', 'PL', 'Kraków', NULL, NULL, NULL, 'kamilzon@vp.pl', '+48669430090', NULL, NULL, NULL, NULL, NULL, NULL, '2025-12-24 09:47:32');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Reko BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('pizzeria, restauracja, Newsletter');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Kamil', 'Zoń', NULL, 'kamilzon@vp.pl', '+48669430090', NULL, NULL);

-- Firma: Magda Jarczak (Sugester ID 26184461)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Magda Jarczak', 'Magda Jarczak', 'partner', 'PL', 'Kraków', NULL, NULL, '30-384', 'magdalena.jarczak@digilkd.pl', '+48690644494', '6792687989', 'https://digilkd.pl', NULL, NULL, NULL, NULL, '2025-12-24 09:47:32');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('HR');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Magdalena', 'Jarczak', NULL, 'magdalena.jarczak@digilkd.pl', '+48690644494', NULL, NULL);

-- Firma: ATJ GROUP (Sugester ID 26184460)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('ATJ GROUP', 'ATJ GROUP', 'client', 'PL', 'Zabierzów', NULL, NULL, '32-080', 'biuro@atjgroup.pl', '+48509705110', '5130235332', 'https://atjgroup.pl', NULL, NULL, NULL, NULL, '2025-12-24 09:47:32');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Kontakt Rafała');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('stolarka alumioniowa, ogrody zimowe, elewacje domów');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Tomasz', 'Janik', NULL, 'biuro@atjgroup.pl', '+48509705110', NULL, NULL);

-- Firma: Grupa Taka (Sugester ID 26184459)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Grupa Taka', 'Grupa Taka', 'partner', 'PL', 'Gliwice', NULL, NULL, '44-100', 'mateusz.kopacz@grupataka.pl', '+48730060644', '6312662991', 'http://www.grupataka.pl', NULL, NULL, NULL, NULL, '2025-12-24 09:47:32');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('agencja 360, marketing');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Mateusz', 'Kopacz', NULL, 'mateusz.kopacz@grupataka.pl', '+48730060644', NULL, NULL);

-- Firma: Katarzyna Rapacz ESG (Sugester ID 26184458)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Katarzyna Rapacz ESG', 'Katarzyna Rapacz ESG', 'client', 'PL', NULL, NULL, NULL, NULL, 'franczyk.katarzyna@gmail.com', '+48888730925', NULL, NULL, NULL, NULL, NULL, NULL, '2025-12-24 09:47:32');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('esg, Newsletter');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Katarzyna', 'Rapacz', NULL, 'franczyk.katarzyna@gmail.com', '+48888730925', NULL, NULL);

-- Firma: Wojciech Buda (Sugester ID 26184457)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Wojciech Buda', 'Wojciech Buda', 'partner', 'PL', NULL, NULL, NULL, NULL, 'wojciech.budakontakt@gmail.com', '+48502427406', NULL, NULL, NULL, NULL, NULL, NULL, '2025-12-24 09:47:32');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('trener, szkolenia, psycholog, Newsletter');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Wojciech', 'Buda', NULL, 'wojciech.budakontakt@gmail.com', '+48502427406', NULL, NULL);

-- Firma: ASK Atelier Aleksandra Skrzypek-Kwiecien (Sugester ID 26184456)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('ASK Atelier Aleksandra Skrzypek-Kwiecien', 'ASK Atelier Aleksandra Skrzypek-Kwiecien', 'client', 'PL', 'Kraków', NULL, NULL, NULL, 'aleksandra.skrzypek.landscape@gmail.com', '+48533685503', NULL, NULL, NULL, NULL, 'Sebastian Łączny', NULL, '2025-12-24 09:47:32');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('BNI, HoReCa, Newsletter');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Aleksandra', 'Skrzypek Kwiecień', NULL, 'aleksandra.skrzypek.landscape@gmail.com', '+48533685503', NULL, NULL);

-- Firma: KS Dynamika (Sugester ID 26184455)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('KS Dynamika', 'KS Dynamika', 'client', 'PL', 'Krzeszowice', NULL, NULL, NULL, 'dorota.gorska@gmail.com', '+48', NULL, NULL, NULL, NULL, NULL, NULL, '2025-12-24 09:47:32');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('sport, Newsletter');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Dorota', 'Górska', NULL, 'dorota.gorska@gmail.com', '+48', NULL, NULL);

-- Firma: Planet Partners (Sugester ID 26184454)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Planet Partners', 'Ania Watza', 'partner', 'PL', NULL, NULL, NULL, NULL, 'a.watza@planetpartners.pl', '+48516086086', NULL, 'http://planetpartners.pl', NULL, NULL, NULL, NULL, '2025-12-24 09:47:32');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('PR');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Anna', 'Watza', 'Partner & Founder', 'a.watza@planetpartners.pl', '+48516086086', NULL, NULL);

-- Firma: Hotel City & Spa (Sugester ID 26184453)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Hotel City & Spa', 'Hotel City & Spa', 'partner', 'PL', 'Kraków', NULL, NULL, '30-426', 'mmis@hotelcity.pl', '+48797648637', '6792683050', 'https://hotelcity.pl', NULL, NULL, NULL, NULL, '2025-12-24 09:47:32');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('HoReCa, sala, konferencje, szkolenia');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Malwina', 'Tołwińska-Miś', NULL, 'mmis@hotelcity.pl', '+48797648637', NULL, NULL);

-- Firma: HR Idea Anna Badek (Sugester ID 26184451)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('HR Idea Anna Badek', 'HR Idea Anna Badek', 'partner', 'PL', 'Wieliczka', NULL, NULL, '32-020', 'anna.badek@hridea.pl', '+48720889669', '9442188414', 'http://hridea.pl', NULL, NULL, NULL, NULL, '2025-12-24 09:47:31');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('HR, Newsletter');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Anna', 'Badek', NULL, 'anna.badek@hridea.pl', '+48720889669', NULL, NULL);

-- Firma: Maszachaba (Sugester ID 26184450)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Maszachaba', 'Maszachaba', 'client', 'PL', 'Kraków', NULL, NULL, '31-202', 'wisniewska@maszachaba.com.pl', '+48504775005', '6772111161', 'https://maszachaba.com.pl', NULL, NULL, NULL, NULL, '2025-12-24 09:47:31');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('medycyna, przychodnia zdrowia, zdrowie, Newsletter');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Renata', 'Wiśniewska', NULL, 'wisniewska@maszachaba.com.pl', '+48504775005', NULL, NULL);

-- Firma: AI4App (Sugester ID 26184447)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('AI4App', 'AI4App', 'lead', 'Polska', 'Brzeg', NULL, NULL, 'Polska', 't.sokol@ai4app.pl', '+48661115910', '7471930156', 'https://ai4app.pl', NULL, NULL, NULL, NULL, '2025-12-24 09:43:26');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Blacklist');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('AI, agenci AI');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Tomasz', 'Sokół', NULL, 't.sokol@ai4app.pl', '+48661115910', NULL, NULL);

-- Firma: Smart-HR (Sugester ID 26184446)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Smart-HR', 'Smart-HR', 'lead', 'Polska', 'Katowice', 'ŚLĄSKIE', 'ul. Dąbrówki 16', 'Polska', 'apycia@smart-hr.pl', '+48608609397', '9542761899', 'http://www.smart-hr.pl', NULL, NULL, 'Anka Badek', NULL, '2025-12-24 09:43:26');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Reko BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('HR');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Anna', 'Pyciak-Pytlik', 'ManagingDirector', 'apycia@smart-hr.pl', '+48608609397', NULL, NULL);

-- Firma: Kancelaria Zysk (Sugester ID 26184445)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Kancelaria Zysk', 'Kancelaria Zysk', 'lead', 'Polska', 'Kraków', NULL, NULL, 'Polska', 'klc@biurorachunkowezysk.pl', '+48609405091', '9452031124', 'https://biurorachunkowezysk.pl/', NULL, NULL, NULL, NULL, '2025-12-24 09:43:26');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Katarzyna', 'Ludwikowska-Cyganek', NULL, 'klc@biurorachunkowezysk.pl', '+48609405091', NULL, NULL);

-- Firma: Ecopak Daniel Czernecki (Sugester ID 26184444)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Ecopak Daniel Czernecki', 'ecopak Daniel Czernecki', 'lead', 'Polska', 'Podegrodzie', NULL, NULL, 'Polska', 'ecopak.ns@gmail.com', '+48604572570', '7343611116', 'https://ecopak-ns.pl/', NULL, NULL, NULL, NULL, '2025-12-24 09:43:26');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Opakowania tekturowe, Produkcja kartonów, E-commerce, Przemysł papierniczy');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Daniel', 'Czernecki', NULL, 'ecopak.ns@gmail.com', '+48604572570', NULL, NULL);

-- Firma: ESTEGH Sp. z o.o. (Sugester ID 26184443)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('ESTEGH Sp. z o.o.', 'ESTEGH Sp. z o.o.', 'lead', 'Polska', 'Skawina', NULL, NULL, 'Polska', 't.slizowski@wynajemlasera.pl', '+48533313575', '9512491178', 'https://wynajemlasera.pl', NULL, NULL, NULL, NULL, '2025-12-24 09:43:25');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Reko BNI');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Tomek', 'Ślizowski', NULL, 't.slizowski@wynajemlasera.pl', '+48533313575', NULL, NULL);

-- Firma: HR NAVIGATOR BEATA SIADEK (Sugester ID 26184442)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('HR NAVIGATOR BEATA SIADEK', 'HR NAVIGATOR BEATA SIADEK', 'lead', 'Polska', 'Siepraw', NULL, NULL, 'Polska', 'kontakt@hrnavigator.com.pl', '+48502190639', '9452175330', 'https://hrnavigator.com.pl', NULL, NULL, NULL, NULL, '2025-12-24 09:43:25');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Reko BNI');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Beata', 'Siadek', NULL, 'kontakt@hrnavigator.com.pl', '+48502190639', NULL, NULL);

-- Firma: HarmonyHi (Sugester ID 26184441)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('HarmonyHi', 'HarmonyHi', 'lead', 'Polska', 'Kraków', NULL, NULL, 'Polska', 'julia@harmonyhi.com', '+48692003208', '6792781428', 'http://www.harmonyhi.com', NULL, NULL, NULL, NULL, '2025-12-24 09:43:25');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('kuek');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Julia', 'Reguła-Bruzda', NULL, 'julia@harmonyhi.com', '+48692003208', NULL, NULL);

-- Firma: Phormy (Sugester ID 26184440)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Phormy', 'Phormy', 'lead', 'Polska', 'Bochnia', 'Województwo małopolskie', NULL, 'Polska', 'phormy@phormy.com', '+48662189142', '9451914946', 'https://phormy.com/', NULL, NULL, NULL, NULL, '2025-12-24 09:43:25');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Max', 'Kobiela', NULL, 'phormy@phormy.com', '+48662189142', NULL, NULL);

-- Firma: Daria Frank (Sugester ID 26184439)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Daria Frank', 'Daria Frank', 'lead', 'Polska', 'Bielsko-Biała', NULL, NULL, 'Polska', 'biuro@dariafrank.pl', '+48664302678', NULL, NULL, NULL, NULL, NULL, NULL, '2025-12-24 09:43:25');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Daria', 'Frank', NULL, 'biuro@dariafrank.pl', '+48664302678', NULL, NULL);

-- Firma: Inner Home (Sugester ID 26184438)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Inner Home', 'Inner Home', 'lead', 'Polska', 'Kraków', 'Województwo małopolskie', NULL, 'Polska', 'mariola@innerhome.pl', '+48660265117', '6792759556', 'https://innerhome.pl', NULL, NULL, NULL, NULL, '2025-12-24 09:43:25');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Psychoterapia, Psychologia, Seksuologia, Dietetyka');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Mariola', 'Tempska', NULL, 'mariola@innerhome.pl', '+48660265117', NULL, NULL);

-- Firma: Kamila Kabzińska (Sugester ID 26184437)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Kamila Kabzińska', 'Kamila Kabzińska', 'lead', 'Polska', 'Kraków', 'Województwo małopolskie', NULL, 'Polska', 'kabzinska.kamila@gmail.com', '+48664008914', NULL, NULL, 'https://www.linkedin.com/in/kamila-kabzi%C5%84ska/', NULL, NULL, NULL, '2025-12-24 09:43:25');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Gość BNI');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Kamila', 'Kabzińska', NULL, 'kabzinska.kamila@gmail.com', '+48664008914', NULL, NULL);

-- Firma: APP SystemsAI (Sugester ID 26184436)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('APP SystemsAI', 'APP SystemsAI', 'lead', 'Polska', 'Kraków', 'Województwo małopolskie', NULL, 'Polska', 'piotr.gawronski@interia.pl', '+48577821187', '5213934538', 'http://app-systemai.com', 'https://www.linkedin.com/in/piotr-gawro%C5%84ski-45922331b/', NULL, NULL, NULL, '2025-12-24 09:43:25');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Gość BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Sztuczna inteligencja, IT, Automatyzacja, Oprogramowanie');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Piotr', 'Gawroński', NULL, 'piotr.gawronski@interia.pl', '+48577821187', NULL, NULL);

-- Firma: Piwne Eventy Firmowe (Sugester ID 26184435)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Piwne Eventy Firmowe', 'Piwne Eventy Firmowe', 'lead', 'Polska', 'Kraków', 'Województwo małopolskie', NULL, 'Polska', 'tomek@jakzarobicpiwo.pl', '+48662031145', '8133544453', 'https://jakzarobicpiwo.pl', NULL, NULL, NULL, NULL, '2025-12-24 09:43:25');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Finanse, Media internetowe, Edukacja finansowa');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Tomasz', 'Buczek', NULL, 'tomek@jakzarobicpiwo.pl', '+48662031145', NULL, NULL);

-- Firma: Beata Morsztyn (Sugester ID 26184434)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Beata Morsztyn', 'Beata Morsztyn', 'inne', 'Polska', 'Kraków', 'Województwo małopolskie', NULL, 'Polska', 'bm@beatamorsztyn.pl', '+48501381600', '6772134446', 'https://beatamorsztyn.pl', NULL, NULL, NULL, NULL, '2025-12-24 09:43:25');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI', 'Smartsist');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('coaching, szkolenia, HR, leaderdship');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Beata', 'Morsztyn', 'Maxwell Leadership Certified Team', 'bm@beatamorsztyn.pl', '+48501381600', NULL, NULL);

-- Firma: I Tak Zdasz (Sugester ID 26184433)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('I Tak Zdasz', 'I Tak Zdasz', 'lead', 'Polska', 'Kraków', 'Województwo małopolskie', NULL, 'Polska', NULL, '+48727933310', '6772242371', 'https://itakzdasz.pl', NULL, NULL, NULL, NULL, '2025-12-24 09:43:25');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Reko BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Edukacja, Kursy online, E-learning, Korepetycje');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Robert', 'Berger', NULL, NULL, '+48727933310', NULL, NULL);

-- Firma: Kancelaria Magnet (Sugester ID 26184432)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Kancelaria Magnet', 'Kancelaria Magnet', 'lead', 'Polska', 'Kraków', 'Województwo małopolskie', NULL, 'Polska', 'monika.wolczynska@magnetaudit.eu', '+48663366494', '5272945890', 'https://magnetaudit.eu', NULL, NULL, 'Maja Drexler', NULL, '2025-12-24 09:43:25');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Reko BNI', 'BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Audyt, Doradztwo biznesowe, Księgowość, Finanse');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Monika', 'Wołczyńska', NULL, 'monika.wolczynska@magnetaudit.eu', '+48663366494', NULL, 'Audyt, Doradztwo biznesowe, Księgowość, Finanse');

-- Firma: TNK Consulting (Sugester ID 26184431)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('TNK Consulting', 'TNK Consulting', 'lead', 'Polska', 'Warszawa', 'Województwo mazowieckie', NULL, 'Polska', NULL, '+48608583433', '8971866763', 'https://tnkc.pl/', 'https://www.linkedin.com/company/tnkc/', NULL, 'MBA Polska', NULL, '2025-12-24 09:43:25');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('poszukiwania nabywcy myTherapy', 'M&A', 'MBA Polska');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Doradztwo finansowe, Analityka biznesowa, Wyceny spółek, Doradztwo kapitałowe');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Piotr', 'Teleon', NULL, NULL, '+48608583433', 'https://www.linkedin.com/in/piotr-teleon/', NULL);

-- Firma: MyTherapy (Sugester ID 26184430)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('MyTherapy', 'MyTherapy', 'lead', 'Polska', 'Kraków', 'Województwo małopolskie', NULL, 'Polska', 'rafal.wlodarczyk@mytherapy.com.pl', '+48791296012', '6793216171', 'https://mytherapy.com.pl', NULL, NULL, 'Ela Poroś', NULL, '2025-12-24 09:43:24');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('M&A');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Psychoterapia, Psychologia, Psychiatria, Zdrowie psychiczne');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Rafał', 'Włodarczyk', NULL, 'rafal.wlodarczyk@mytherapy.com.pl', '+48791296012', NULL, 'Psychoterapia, Psychologia, Psychiatria, Zdrowie psychiczne');

-- Firma: BLDG (Sugester ID 26184425)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('BLDG', 'Mariusz Bajor', 'lead', 'Polska', 'Kraków', 'MAŁOPOLSKIE', 'Zabłocie 43A', '30-701', 'mariusz.bajor@bldg.pl', '+48509242646', NULL, 'https://bldg.pl', NULL, NULL, 'Patrycja Hrabiec-Hojda', NULL, '2025-12-24 09:38:24');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Reko');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Budownictwo');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Mariusz', 'Bajor', NULL, 'mariusz.bajor@bldg.pl', '+48509242646', 'https://drive.google.com/file/d//view?usp=sharing', NULL);
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Dariusz', 'Lipka', NULL, 'dariusz.lipka@bldg.pl', '+48609353305', NULL, NULL);

-- Firma: Bayer (Sugester ID 26184424)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Bayer', 'Christopher Pawlak', 'lead', 'PL', 'Warszawa', NULL, NULL, '02-326', 'ch.pawlak10@gmail.com', '+41794346506', '5260019068', 'https://www.bayer.com/', 'https://www.linkedin.com/in/christopherpawlak/', NULL, 'kuek', NULL, '2025-12-24 09:38:24');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('poszukiwania nabywcy myTherapy', 'M&A');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Bayer, fundusze inwestycyjne, big pharma');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Christopher', 'Pawlak', NULL, 'ch.pawlak10@gmail.com', '+41794346506', NULL, 'Farmaceutyczna, Biotechnologiczna, Rolnicza, Chemiczna');

-- Firma: Partner Papes (Sugester ID 26184423)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Partner Papes', 'Sebastian Bigos', 'lead', 'PL', 'Wrocław', 'Województwo dolnośląskie', NULL, '91-341', 's.bigos@partnerpapes.pl', '+48600305288', '7282513460', 'https://partnerpapes.pl/', 'https://www.linkedin.com/in/sebastianbigos/', NULL, 'MBA Polska', NULL, '2025-12-24 09:38:24');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('poszukiwania nabywcy myTherapy', 'M&A');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('zaopatrzenie biurowe');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Sebastian', 'Bigos', NULL, 's.bigos@partnerpapes.pl', '+48600305288', NULL, 'Artykuły biurowe, Wyposażenie biur, Artykuły papiernicze, BHP');

-- Firma: Vision East Advisory (Sugester ID 26184422)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Vision East Advisory', 'Jakub Kowalski', 'lead', 'PL', 'Warszawa', 'Województwo mazowieckie', NULL, NULL, NULL, '+48507024418', '5252818160', 'https://www.visioneastadvisory.com/', 'https://www.linkedin.com/company/vision-east-advisory/', NULL, 'Ania Polak (kuek)', NULL, '2025-12-24 09:38:23');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('poszukiwania nabywcy myTherapy', 'M&A');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Consulting M&A');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Jakub', 'Kowalski', NULL, NULL, '+48507024418', NULL, NULL);

-- Firma: WLC (Sugester ID 26184421)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('WLC', 'Wojciech Lelito', 'lead', 'PL', 'Kraków', 'Województwo małopolskie', NULL, '02-676', 'wojciech.lelito@wlc.com.pl', '+48601961378', '5213484988', 'https://wlc.com.pl', NULL, NULL, 'Anna Watza', NULL, '2025-12-24 09:38:23');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Reko BNI');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Business Consulting');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Wojciech', 'Lelito', NULL, 'wojciech.lelito@wlc.com.pl', '+48601961378', NULL, 'Transport, Logistyka, Spedycja, TSL');

-- Firma: OP Mobility (Sugester ID 26184420)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('OP Mobility', 'Damian Dobosz', 'lead', 'PL', 'Niemce', 'Województwo lubelskie', NULL, '41-200', NULL, '+48535511906', '6342371994', 'https://www.opmobility.com/en/', 'https://www.linkedin.com/company/opmobility/', NULL, 'Monika Firlińska (EMBA29)', NULL, '2025-12-24 09:38:23');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('EMBA');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Produkcja części do pojazdów silnikowych');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Damian', 'Dobosz', NULL, NULL, '+48535511906', NULL, NULL);

-- Firma: Urpgor Systems (Sugester ID 26184419)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Urpgor Systems', 'Paweł Darasz-Mól', 'lead', 'PL', 'Wrocław', 'Województwo dolnośląskie', NULL, '54-427', 'contact@urpgorsystems.com', '+48730133748', '8943164926', 'https://urpgorsystems.com/', 'https://www.linkedin.com/company/urpgor-systems/about/', NULL, 'MBA Polska', NULL, '2025-12-24 09:38:23');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('MBA Polska');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('produkcja urządzeń laboratoryjnych');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Paweł', 'Darasz-Mól', NULL, 'contact@urpgorsystems.com', '+48730133748', NULL, 'Elektronika, Aparatura pomiarowa, Badania i rozwój, Edukacja techniczna');

-- Firma: Optimum Materace (Sugester ID 26184418)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Optimum Materace', 'Anna Warchoł', 'lead', 'PL', 'Zarzecze', 'Województwo podkarpackie', NULL, '37-100', 'anna@optimum-materace.pl', '+48604259966', '8133863484', 'https://optimum-materace.pl/', NULL, NULL, 'BNI+', NULL, '2025-12-24 09:38:23');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('BNI+');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('produkcja materace');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Anna', 'Warchoł', NULL, 'anna@optimum-materace.pl', '+48604259966', NULL, 'Produkcja materacy, Wyposażenie sypialni, Meble hotelowe');

-- Firma: Confessor Capital (Sugester ID 26184417)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Confessor Capital', 'Dawid Lisowski', 'lead', 'PL', 'Jasionka', NULL, NULL, '36-002', 'dawid.lisowski@confessor-capital.com', '+48531667424', '5170402447', 'https://confessor-capital.com/', 'https://www.linkedin.com/company/confessorcapitalgroup/', NULL, 'LI Local Katowice', NULL, '2025-12-24 09:38:23');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('LI Local Katowice 12/25');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('startupy');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Dawid', 'Lisowski', NULL, 'dawid.lisowski@confessor-capital.com', '+48531667424', NULL, 'Sztuczna inteligencja, Analityka wideo, Przemysł 4.0, IT');

-- Firma: Fiklon (Sugester ID 26184416)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Fiklon', 'Hubert Turaj', 'lead', 'PL', 'Kraków', NULL, NULL, '30-552', 'hubert.turaj@fiklon.pl', '+48728350897', '6793292415', 'http://fiklon.pl/', NULL, NULL, 'Rafał Włodarczyk', NULL, '2025-12-24 09:38:23');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Reko');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('psychoterapia dla dzieci');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Hubert', 'Turaj', NULL, 'hubert.turaj@fiklon.pl', '+48728350897', NULL, 'Opieka zdrowotna, Rehabilitacja, Psychologia dziecięca, Diagnostyka');

-- Firma: Kraków Nowa Huta Przyszłości S.A. (Sugester ID 26184285)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Kraków Nowa Huta Przyszłości S.A.', 'KrakówNowaHutaPrzyszłościS.A.', 'lead', 'PL', '[object Object]', 'MAŁOPOLSKIE', '[object Object]', '31-902', 'jacek.bielawski@knhp.com.pl', '+48696456680', '6783153839', 'http://www.knhp.com.pl', NULL, NULL, NULL, NULL, '2025-12-23 22:50:50');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Deweloperka, rewitalizacja miejska, nieruchomości komercyjne i mieszkaniowe');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Jacek', 'Bielawski', NULL, 'jacek.bielawski@knhp.com.pl', '+48696456680', NULL, NULL);

-- Firma: Aspergo (Sugester ID 26184283)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Aspergo', 'Aspergo', 'lead', 'Polska', 'Łódź', 'ŁÓDZKIE', 'ul. Ks. Piotra Skargi 8/10', '90-059', 'gszwejser@aspergo.pl', '+48607078116', '7251957636', 'https://aspergo.pl', NULL, NULL, NULL, NULL, '2025-12-23 22:45:48');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Ubezpieczenia');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Grzegorz', 'Szwejser', 'Prezes Zarządu, Broker Ubezpieczeniowy', 'gszwejser@aspergo.pl', '+48607078116', NULL, 'Ubezpieczenia, Broker ubezpieczeniowy, Doradztwo biznesowe, Zarządzanie ryzykiem');

-- Firma: Infinity Blue (Sugester ID 26184280)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Infinity Blue', 'Infinity Blue', 'inne', 'PL', 'Manchester', NULL, NULL, 'M40 5BJ', 'pawel@infinitybluegroup.com', '+48602489094', NULL, 'https://infinitybluegroup.com', 'https://www.linkedin.com/in/pawelbilczynski/', NULL, NULL, NULL, '2025-12-23 22:41:05');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Business Mixer Katowice 12/2025');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Rekrutacja, Executive Search, IT staffing, Outsourcing HR, Konsulting biznesowy');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Pawel', 'Bilczynski', 'Head of Central & Eastern Europe', 'pawel@infinitybluegroup.com', '+48602489094', NULL, 'konsulting - pomagają firmom wyjść z e-commerce za granicę');

-- Firma: Diagnostyka Consilio (Sugester ID 26184274)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Diagnostyka Consilio', 'Robert Głuszak', 'lead', 'PL', 'Warszawa', 'Województwo mazowieckie', NULL, 'Polska', 'adrobny@interia.pl', '+48506159733', '6751265009', 'https://diag.pl/', 'https://www.linkedin.com/in/andrzej-drobny-292229a7/', NULL, 'klient MH', NULL, '2025-12-23 22:21:32');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('M&A', 'Business Mixer Katowice 12/2025');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('tłumaczenia, inwestycje, finanse');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Andrzej', 'Drobny', NULL, 'adrobny@interia.pl', '+48506159733', NULL, 'tłumaczenia, ale też inwestor w spółki');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Timea', 'Balajcza', NULL, NULL, NULL, NULL, 'tłumaczenia');

-- Firma: Amber Glass, Karel hurtownie (Sugester ID 26184273)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Amber Glass, Karel hurtownie', 'Marcin Karel', 'lead', 'PL', 'Rybnik', NULL, NULL, '44-203', NULL, NULL, '6420013894', 'https://karel2.pl/', 'https://www.linkedin.com/in/marcin-karel-411bb894/', NULL, NULL, NULL, '2025-12-23 22:21:32');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Business Mixer Katowice 12/2025', 'M&A');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('obróbka szkła, hurtownie elektryczne');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Marcin', 'Karel', NULL, NULL, NULL, NULL, 'ma firmę na zprzedaż - hurtownie elektryczne w Bielsku (oboroty 20mln)');

-- Firma: Lafrentz (Sugester ID 26184272)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Lafrentz', 'Mateusz Durski', 'inne', 'PL', 'Poznań', NULL, NULL, '60-179', NULL, NULL, '7791998348', 'https://lafrentz.pl/', 'https://www.linkedin.com/in/mateusz-durski-299106153/', NULL, NULL, NULL, '2025-12-23 22:21:32');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Business Mixer Katowice 12/2025');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('firma konstrukcyjno-budowlana, duża');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Mateusz', 'Durski', NULL, NULL, NULL, NULL, 'Wiceprezes zarządu w firmie konkstrukcyjnej. Młody chłopak');

-- Firma: Accounting & Corporate Services (Sugester ID 26184271)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Accounting & Corporate Services', 'Ewa Ogłozińska', 'partner', 'PL', 'Warszawa', 'MAZOWIECKIE', 'Aleje Ujazdowskie 41', '00-540', 'eoglozinska@acs-group.pl', '+48729859891', '7010831278', 'https://acs-group.pl', 'https://www.linkedin.com/in/ewa-og%C5%82ozi%C5%84ska-933b96117/', NULL, NULL, NULL, '2025-12-23 22:21:32');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Business Mixer Katowice 12/2025', 'M&A');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('biuro księgowe, audyty, hr, payroll');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Ewa', 'Ogłozińska', 'Finance Vice President', 'eoglozinska@acs-group.pl', '+48729859891', NULL, 'biuro księgowe, mogą mieć klientów pod M&amp;A');

-- Firma: Enterprise Ireland (Sugester ID 26184270)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Enterprise Ireland', 'Bartosz Siepracki', 'partner', 'PL', 'Dublin 3', NULL, NULL, 'D03 E5R6', 'bartosz.siepracki@enterprise-ireland.com', '+48608024264', 'IE9590828H', 'http://www.enterprise-ireland.com', 'https://www.linkedin.com/in/barteksiepracki/', NULL, NULL, NULL, '2025-12-23 22:21:32');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Business Mixer Katowice 12/2025', 'M&A');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('wprawadzają firmy irlandzkie do Polski');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Bartosz', 'Siepracki', NULL, 'bartosz.siepracki@enterprise-ireland.com', '+48608024264', NULL, 'firma wprowadzają');

-- Firma: Sopra Steria Polska Sp. z o.o. (Sugester ID 26184269)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Sopra Steria Polska Sp. z o.o.', 'Dorota Butryn', 'inne', 'Polska', 'Katowice', 'ŚLĄSKIE', 'Uniwersytecka 13', '40-007', 'dorota.butryn@soprasteria.com', '+48698097108', '5262886585', 'http://www.soprasteria.com', 'https://www.linkedin.com/in/dorota-butryn-79188174/', NULL, NULL, NULL, '2025-12-23 22:21:31');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Business Mixer Katowice 12/2025');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('IT, Konsulting, Oprogramowanie, Usługi cyfrowe');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Dorota', 'Butryn', 'Program Director', 'dorota.butryn@soprasteria.com', '+48698097108', NULL, 'brak specjalnych możliwości współpracy');

-- Firma: Tomczykowski Tomczykowska (Sugester ID 26184268)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Tomczykowski Tomczykowska', 'Damian Libertowski', 'partner', 'PL', 'Warszawa', NULL, NULL, '00-339', 'd.libertowski@tomczykowscy.pl', '+48512761270', '5252516427', 'http://www.tomczykowscy.pl', 'https://www.linkedin.com/in/damian-libertowski-283992197/', NULL, NULL, NULL, '2025-12-23 22:21:31');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Business Mixer Katowice 12/2025', 'M&A');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('kancelaria prawna');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Damian', 'Libertowski', NULL, 'd.libertowski@tomczykowscy.pl', '+48512761270', NULL, 'prawnik, słaba relacja');

-- Firma: Anzena (Sugester ID 26184266)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Anzena', 'Beata Kurek', 'inne', 'Polska', 'Katowice', 'ŚLĄSKIE', 'ul. Pszczyńska 15', '40-478', 'kurek.b@anzena.pl', '+48538506809', '9542740925', 'http://www.anzena.pl', 'https://www.linkedin.com/in/beata-kurek-a41493200/', NULL, NULL, NULL, '2025-12-23 22:21:31');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Business Mixer Katowice 12/2025');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Przemysł');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Beata', 'Kurek', 'Zastępca Dyrektora', 'kurek.b@anzena.pl', '+48538506809', NULL, 'robią audyty cyfrowe i cyberbezpieczeństwa, godna polecenia firma');

-- Firma: Taxsafe (Sugester ID 26184265)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Taxsafe', 'Svitlana Genna', 'partner', 'Polska', 'Warszawa', 'MAZOWIECKIE', 'Ul. Floriańska 6 Lok. U2', '03-707', 'svitlana.genina@taxsafe.pl', '+48573664879', '5252823430', 'http://www.taxsafe.pl', NULL, NULL, NULL, NULL, '2025-12-23 22:21:31');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Business Mixer Katowice 12/2025');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Księgowość, Doradztwo podatkowe, Kadry i płace');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Svitlana', 'Genina', 'Dyrektor Ds. Rozwoju Biznesu', 'svitlana.genina@taxsafe.pl', '+48573664879', NULL, 'biuro księgowe, mogą mieć klientów pod M&A');

-- Firma: Colliers (Sugester ID 26184264)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('Colliers', 'Tadeusz Kowalczyk', 'partner', 'Polska', 'Warszawa', 'MAZOWIECKIE', 'ul. Pańska 97', '00-834', 'tadeusz.kowalczyk@colliers.com', '+48539538359', '5262263063', 'https://www.colliers.com', 'https://www.linkedin.com/in/tadeusz-kowalczyk-524195166/', NULL, NULL, NULL, '2025-12-23 22:21:31');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Business Mixer Katowice 12/2025', 'M&A');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('Nieruchomości komercyjne, Doradztwo inwestycyjne, Zarządzanie nieruchomościami');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Tadeusz', 'Kowalczyk', 'Associate', 'tadeusz.kowalczyk@colliers.com', '+48539538359', NULL, 'skupują nieruchomości komercyjne');

-- Firma: GFS Engineering (Sugester ID 26184263)
INSERT INTO crm_companies (name, short_name, relation_type, country, city, voivodeship, street, postal_code, email, phone, nip, website, linkedin_url, description, source, owner_user_id, created_at) VALUES ('GFS Engineering', 'Monika Wójcik', 'inne', 'PL', 'Katowice', NULL, NULL, '40-085', 'monika.wojcik@gfs-eng.com', '+48453072702', '6342838323', 'https://www.gfs-eng.com', NULL, NULL, NULL, NULL, '2025-12-23 22:21:31');
SET @cid := LAST_INSERT_ID();
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='tag' AND name IN ('Business Mixer Katowice 12/2025');
INSERT INTO crm_company_tags (company_id, tag_id) SELECT @cid, id FROM crm_tags WHERE kind='industry' AND name IN ('firma budowlana');
INSERT INTO crm_contacts (company_id, first_name, last_name, position, email, phone, business_card_url, description) VALUES (@cid, 'Monika', 'Wójcik', 'Director Of Contract Execution', 'monika.wojcik@gfs-eng.com', '+48453072702', NULL, 'poznana w Katowicach na Business Mixer 2025 - bez szczególnej relacji');

COMMIT;
