-- Cofnięcie zapisu zdaniowego do prostszej reguły: wielka litera tylko na
-- początku nazwy, reszta dokładnie tak, jak wpisał użytkownik. Poprzednia
-- reguła zabierała wielką literę nazwom własnym („Rafał Wiśniewski" →
-- „Rafał wiśniewski", „MBA Polska" → „MBA polska").
-- Trzy akronimy podniesione wcześniej ręcznie (CFO id=242, M&A id=300,
-- ESG id=314) zostają wielkimi literami — tak było przed zmianą zapisu.
-- Każdy UPDATE zabezpieczony obecną nazwą, żeby nie nadpisać ręcznej poprawki.

-- tag: Business mixer katowice 12/2025 → Business Mixer Katowice 12/2025
UPDATE crm_tags SET name='Business Mixer Katowice 12/2025' WHERE id=8 AND name='Business mixer katowice 12/2025';
-- tag: LI local katowice 12/25 → LI Local Katowice 12/25
UPDATE crm_tags SET name='LI Local Katowice 12/25' WHERE id=13 AND name='LI local katowice 12/25';
-- tag: MBA polska → MBA Polska
UPDATE crm_tags SET name='MBA Polska' WHERE id=16 AND name='MBA polska';
-- tag: Rafał wiśniewski → Rafał Wiśniewski
UPDATE crm_tags SET name='Rafał Wiśniewski' WHERE id=437 AND name='Rafał wiśniewski';
-- tag: Zaprosić na BNI → Zaprosić Na BNI
UPDATE crm_tags SET name='Zaprosić Na BNI' WHERE id=626 AND name='Zaprosić na BNI';
-- industry: Biura rachunkowe → Biura Rachunkowe
UPDATE crm_tags SET name='Biura Rachunkowe' WHERE id=496 AND name='Biura rachunkowe';
-- industry: Building cost estimation → Building Cost Estimation
UPDATE crm_tags SET name='Building Cost Estimation' WHERE id=30 AND name='Building cost estimation';
-- industry: Business consulting → Business Consulting
UPDATE crm_tags SET name='Business Consulting' WHERE id=31 AND name='Business consulting';
-- industry: Chłodnictwo i klimatyzacja → Chłodnictwo i Klimatyzacja
UPDATE crm_tags SET name='Chłodnictwo i Klimatyzacja' WHERE id=32 AND name='Chłodnictwo i klimatyzacja';
-- industry: Doradztwo biznesowe → Doradztwo Biznesowe
UPDATE crm_tags SET name='Doradztwo Biznesowe' WHERE id=249 AND name='Doradztwo biznesowe';
-- industry: Doradztwo inwestycyjne → Doradztwo Inwestycyjne
UPDATE crm_tags SET name='Doradztwo Inwestycyjne' WHERE id=333 AND name='Doradztwo inwestycyjne';
-- industry: Doradztwo/jakość → Doradztwo/Jakość
UPDATE crm_tags SET name='Doradztwo/Jakość' WHERE id=38 AND name='Doradztwo/jakość';
-- industry: Dystrybucja żywności → Dystrybucja Żywności
UPDATE crm_tags SET name='Dystrybucja Żywności' WHERE id=632 AND name='Dystrybucja żywności';
-- industry: E-commerce → E-Commerce
UPDATE crm_tags SET name='E-Commerce' WHERE id=3 AND name='E-commerce';
-- industry: Executive search → Executive Search
UPDATE crm_tags SET name='Executive Search' WHERE id=363 AND name='Executive search';
-- industry: Family office → Family Office
UPDATE crm_tags SET name='Family Office' WHERE id=625 AND name='Family office';
-- industry: Finanse/księgowość → Finanse/Księgowość
UPDATE crm_tags SET name='Finanse/Księgowość' WHERE id=45 AND name='Finanse/księgowość';
-- industry: Fundusze inwestycyjne → Fundusze Inwestycyjne
UPDATE crm_tags SET name='Fundusze Inwestycyjne' WHERE id=276 AND name='Fundusze inwestycyjne';
-- industry: IT/edukacja → IT/Edukacja
UPDATE crm_tags SET name='IT/Edukacja' WHERE id=51 AND name='IT/edukacja';
-- industry: IT/technologie → IT/Technologie
UPDATE crm_tags SET name='IT/Technologie' WHERE id=52 AND name='IT/technologie';
-- industry: Lean management → Lean Management
UPDATE crm_tags SET name='Lean Management' WHERE id=570 AND name='Lean management';
-- industry: Life sciences → Life Sciences
UPDATE crm_tags SET name='Life Sciences' WHERE id=579 AND name='Life sciences';
-- industry: Marketing / komunikacja PR → Marketing / Komunikacja PR
UPDATE crm_tags SET name='Marketing / Komunikacja PR' WHERE id=54 AND name='Marketing / komunikacja PR';
-- industry: Marketing / reklama → Marketing / Reklama
UPDATE crm_tags SET name='Marketing / Reklama' WHERE id=55 AND name='Marketing / reklama';
-- industry: Medycyna/zdrowie → Medycyna/Zdrowie
UPDATE crm_tags SET name='Medycyna/Zdrowie' WHERE id=57 AND name='Medycyna/zdrowie';
-- industry: Monitoring wizyjny → Monitoring Wizyjny
UPDATE crm_tags SET name='Monitoring Wizyjny' WHERE id=338 AND name='Monitoring wizyjny';
-- industry: Ochrona mienia → Ochrona Mienia
UPDATE crm_tags SET name='Ochrona Mienia' WHERE id=399 AND name='Ochrona mienia';
-- industry: Oświetlenie biurowe → Oświetlenie Biurowe
UPDATE crm_tags SET name='Oświetlenie Biurowe' WHERE id=512 AND name='Oświetlenie biurowe';
-- industry: Oświetlenie przemysłowe → Oświetlenie Przemysłowe
UPDATE crm_tags SET name='Oświetlenie Przemysłowe' WHERE id=346 AND name='Oświetlenie przemysłowe';
-- industry: Oświetlenie zewnętrzne → Oświetlenie Zewnętrzne
UPDATE crm_tags SET name='Oświetlenie Zewnętrzne' WHERE id=513 AND name='Oświetlenie zewnętrzne';
-- industry: Piekarnia - cukiernia → Piekarnia - Cukiernia
UPDATE crm_tags SET name='Piekarnia - Cukiernia' WHERE id=65 AND name='Piekarnia - cukiernia';
-- industry: Planowanie finansowe → Planowanie Finansowe
UPDATE crm_tags SET name='Planowanie Finansowe' WHERE id=624 AND name='Planowanie finansowe';
-- industry: Prawo / usługi prawnicze → Prawo / Usługi prawnicze
UPDATE crm_tags SET name='Prawo / Usługi prawnicze' WHERE id=67 AND name='Prawo / usługi prawnicze';
-- industry: Prawo/legal → Prawo/Legal
UPDATE crm_tags SET name='Prawo/Legal' WHERE id=69 AND name='Prawo/legal';
-- industry: Private equity → Private Equity
UPDATE crm_tags SET name='Private Equity' WHERE id=612 AND name='Private equity';
-- industry: Produkcja i handel → Produkcja i Handel
UPDATE crm_tags SET name='Produkcja i Handel' WHERE id=71 AND name='Produkcja i handel';
-- industry: Produkcja żywności → Produkcja Żywności
UPDATE crm_tags SET name='Produkcja Żywności' WHERE id=631 AND name='Produkcja żywności';
-- industry: Search fund → Search Fund
UPDATE crm_tags SET name='Search Fund' WHERE id=622 AND name='Search fund';
-- industry: SPA & wellness → SPA & Wellness
UPDATE crm_tags SET name='SPA & Wellness' WHERE id=532 AND name='SPA & wellness';
-- industry: Systemy alarmowe → Systemy Alarmowe
UPDATE crm_tags SET name='Systemy Alarmowe' WHERE id=593 AND name='Systemy alarmowe';
-- industry: Systemy bezpieczeństwa → Systemy Bezpieczeństwa
UPDATE crm_tags SET name='Systemy Bezpieczeństwa' WHERE id=398 AND name='Systemy bezpieczeństwa';
-- industry: Systemy zabezpieczeń → Systemy Zabezpieczeń
UPDATE crm_tags SET name='Systemy Zabezpieczeń' WHERE id=592 AND name='Systemy zabezpieczeń';
-- industry: Sztuczna inteligencja → Sztuczna Inteligencja
UPDATE crm_tags SET name='Sztuczna Inteligencja' WHERE id=230 AND name='Sztuczna inteligencja';
-- industry: Usługi dla firm → Usługi Dla Firm
UPDATE crm_tags SET name='Usługi Dla Firm' WHERE id=615 AND name='Usługi dla firm';
-- industry: Venture capital → Venture Capital
UPDATE crm_tags SET name='Venture Capital' WHERE id=638 AND name='Venture capital';
-- industry: Wprawadzają firmy irlandzkie do polski → Wprawadzają firmy irlandzkie do Polski
UPDATE crm_tags SET name='Wprawadzają firmy irlandzkie do Polski' WHERE id=146 AND name='Wprawadzają firmy irlandzkie do polski';
-- industry: Zarządzanie majątkiem → Zarządzanie Majątkiem
UPDATE crm_tags SET name='Zarządzanie Majątkiem' WHERE id=623 AND name='Zarządzanie majątkiem';
-- industry: Zarządzanie ryzykiem → Zarządzanie Ryzykiem
UPDATE crm_tags SET name='Zarządzanie Ryzykiem' WHERE id=313 AND name='Zarządzanie ryzykiem';

-- Sierota: wiersz z pustym kind (poza enumem), bez żadnych przypięć,
-- niewidoczny w żadnym słowniku.
DELETE FROM crm_tags WHERE id=444 AND kind='' AND name='komputer';
