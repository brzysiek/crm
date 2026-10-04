-- Jednolity zapis zdaniowy tagów, branż i tagów email: pierwsze słowo z
-- wielkiej litery, reszta z małej, akronimy (BNI, M&A, SaaS) bez zmian.
-- Wygenerowane ze stanu produkcji; każda zmiana po id, żeby nie ruszyć
-- niczego, czego nie było widać przy przeglądzie. Źródła (kind='source')
-- zostają przy zapisie tytułowym — tam wartością jest imię i nazwisko.
-- Trzy nazwy to akronimy wpisane małymi literami (m&a, cfo, esg) —
-- podnoszone do wersji wielkimi literami ręcznie, reguła tego nie odgadnie.

-- tag: Business Mixer Katowice 12/2025 → Business mixer katowice 12/2025
UPDATE crm_tags SET name='Business mixer katowice 12/2025' WHERE id=8 AND name='Business Mixer Katowice 12/2025';
-- tag: kuek → Kuek
UPDATE crm_tags SET name='Kuek' WHERE id=21 AND name='kuek';
-- tag: LI Local Katowice 12/25 → LI local katowice 12/25
UPDATE crm_tags SET name='LI local katowice 12/25' WHERE id=13 AND name='LI Local Katowice 12/25';
-- tag: MBA Polska → MBA polska
UPDATE crm_tags SET name='MBA polska' WHERE id=16 AND name='MBA Polska';
-- tag: poszukiwania nabywcy myTherapy → Poszukiwania nabywcy myTherapy
UPDATE crm_tags SET name='Poszukiwania nabywcy myTherapy' WHERE id=22 AND name='poszukiwania nabywcy myTherapy';
-- tag: Rafał Wiśniewski → Rafał wiśniewski
UPDATE crm_tags SET name='Rafał wiśniewski' WHERE id=437 AND name='Rafał Wiśniewski';
-- tag: Zaprosić Na BNI → Zaprosić na BNI
UPDATE crm_tags SET name='Zaprosić na BNI' WHERE id=626 AND name='Zaprosić Na BNI';
-- industry: adwokat → Adwokat
UPDATE crm_tags SET name='Adwokat' WHERE id=352 AND name='adwokat';
-- industry: agencja pracy → Agencja pracy
UPDATE crm_tags SET name='Agencja pracy' WHERE id=84 AND name='agencja pracy';
-- industry: analityka biznesowa → Analityka biznesowa
UPDATE crm_tags SET name='Analityka biznesowa' WHERE id=85 AND name='analityka biznesowa';
-- industry: architektura → Architektura
UPDATE crm_tags SET name='Architektura' WHERE id=432 AND name='architektura';
-- industry: audyt cyberbezpieczeństwa → Audyt cyberbezpieczeństwa
UPDATE crm_tags SET name='Audyt cyberbezpieczeństwa' WHERE id=502 AND name='audyt cyberbezpieczeństwa';
-- industry: audyty → Audyty
UPDATE crm_tags SET name='Audyty' WHERE id=281 AND name='audyty';
-- industry: automotive → Automotive
UPDATE crm_tags SET name='Automotive' WHERE id=354 AND name='automotive';
-- industry: big pharma → Big pharma
UPDATE crm_tags SET name='Big pharma' WHERE id=277 AND name='big pharma';
-- industry: Biura Rachunkowe → Biura rachunkowe
UPDATE crm_tags SET name='Biura rachunkowe' WHERE id=496 AND name='Biura Rachunkowe';
-- industry: biuro księgowe → Biuro księgowe
UPDATE crm_tags SET name='Biuro księgowe' WHERE id=280 AND name='biuro księgowe';
-- industry: bodyleasing → Bodyleasing
UPDATE crm_tags SET name='Bodyleasing' WHERE id=344 AND name='bodyleasing';
-- industry: bony → Bony
UPDATE crm_tags SET name='Bony' WHERE id=274 AND name='bony';
-- industry: budowlanka → Budowlanka
UPDATE crm_tags SET name='Budowlanka' WHERE id=89 AND name='budowlanka';
-- industry: Building Cost Estimation → Building cost estimation
UPDATE crm_tags SET name='Building cost estimation' WHERE id=30 AND name='Building Cost Estimation';
-- industry: Business Consulting → Business consulting
UPDATE crm_tags SET name='Business consulting' WHERE id=31 AND name='Business Consulting';
-- industry: celne → Celne
UPDATE crm_tags SET name='Celne' WHERE id=297 AND name='celne';
-- industry: centrum medyczne → Centrum medyczne
UPDATE crm_tags SET name='Centrum medyczne' WHERE id=257 AND name='centrum medyczne';
-- industry: cfo → CFO
UPDATE crm_tags SET name='CFO' WHERE id=242 AND name='cfo';
-- industry: chłodnictwo → Chłodnictwo
UPDATE crm_tags SET name='Chłodnictwo' WHERE id=286 AND name='chłodnictwo';
-- industry: Chłodnictwo i Klimatyzacja → Chłodnictwo i klimatyzacja
UPDATE crm_tags SET name='Chłodnictwo i klimatyzacja' WHERE id=32 AND name='Chłodnictwo i Klimatyzacja';
-- industry: ciuchy → Ciuchy
UPDATE crm_tags SET name='Ciuchy' WHERE id=307 AND name='ciuchy';
-- industry: coaching → Coaching
UPDATE crm_tags SET name='Coaching' WHERE id=288 AND name='coaching';
-- industry: coachng → Coachng
UPDATE crm_tags SET name='Coachng' WHERE id=290 AND name='coachng';
-- industry: cold calling → Cold calling
UPDATE crm_tags SET name='Cold calling' WHERE id=93 AND name='cold calling';
-- industry: cyberbezpieczeństwo → Cyberbezpieczeństwo
UPDATE crm_tags SET name='Cyberbezpieczeństwo' WHERE id=94 AND name='cyberbezpieczeństwo';
-- industry: cyfrowa transformacja → Cyfrowa transformacja
UPDATE crm_tags SET name='Cyfrowa transformacja' WHERE id=328 AND name='cyfrowa transformacja';
-- industry: doradztwo → Doradztwo
UPDATE crm_tags SET name='Doradztwo' WHERE id=298 AND name='doradztwo';
-- industry: Doradztwo Biznesowe → Doradztwo biznesowe
UPDATE crm_tags SET name='Doradztwo biznesowe' WHERE id=249 AND name='Doradztwo Biznesowe';
-- industry: Doradztwo Inwestycyjne → Doradztwo inwestycyjne
UPDATE crm_tags SET name='Doradztwo inwestycyjne' WHERE id=333 AND name='Doradztwo Inwestycyjne';
-- industry: doradztwo podatkowe → Doradztwo podatkowe
UPDATE crm_tags SET name='Doradztwo podatkowe' WHERE id=296 AND name='doradztwo podatkowe';
-- industry: doradztwo ubezpieczeniowe → Doradztwo ubezpieczeniowe
UPDATE crm_tags SET name='Doradztwo ubezpieczeniowe' WHERE id=262 AND name='doradztwo ubezpieczeniowe';
-- industry: Doradztwo/Jakość → Doradztwo/jakość
UPDATE crm_tags SET name='Doradztwo/jakość' WHERE id=38 AND name='Doradztwo/Jakość';
-- industry: drukarnia → Drukarnia
UPDATE crm_tags SET name='Drukarnia' WHERE id=305 AND name='drukarnia';
-- industry: due diligence → Due diligence
UPDATE crm_tags SET name='Due diligence' WHERE id=494 AND name='due diligence';
-- industry: duża → Duża
UPDATE crm_tags SET name='Duża' WHERE id=318 AND name='duża';
-- industry: Dystrybucja Żywności → Dystrybucja żywności
UPDATE crm_tags SET name='Dystrybucja żywności' WHERE id=632 AND name='Dystrybucja Żywności';
-- industry: E-Commerce → E-commerce
UPDATE crm_tags SET name='E-commerce' WHERE id=3 AND name='E-Commerce';
-- industry: elewacje domów → Elewacje domów
UPDATE crm_tags SET name='Elewacje domów' WHERE id=229 AND name='elewacje domów';
-- industry: esg → ESG
UPDATE crm_tags SET name='ESG' WHERE id=314 AND name='esg';
-- industry: Executive Search → Executive search
UPDATE crm_tags SET name='Executive search' WHERE id=363 AND name='Executive Search';
-- industry: Family Office → Family office
UPDATE crm_tags SET name='Family office' WHERE id=625 AND name='Family Office';
-- industry: finanse → Finanse
UPDATE crm_tags SET name='Finanse' WHERE id=102 AND name='finanse';
-- industry: Finanse/Księgowość → Finanse/księgowość
UPDATE crm_tags SET name='Finanse/księgowość' WHERE id=45 AND name='Finanse/Księgowość';
-- industry: firma budowlana → Firma budowlana
UPDATE crm_tags SET name='Firma budowlana' WHERE id=103 AND name='firma budowlana';
-- industry: firma konstrukcyjno-budowlana → Firma konstrukcyjno-budowlana
UPDATE crm_tags SET name='Firma konstrukcyjno-budowlana' WHERE id=317 AND name='firma konstrukcyjno-budowlana';
-- industry: firmy usługowe → Firmy usługowe
UPDATE crm_tags SET name='Firmy usługowe' WHERE id=582 AND name='firmy usługowe';
-- industry: fotowoltaika → Fotowoltaika
UPDATE crm_tags SET name='Fotowoltaika' WHERE id=319 AND name='fotowoltaika';
-- industry: Fundusze Inwestycyjne → Fundusze inwestycyjne
UPDATE crm_tags SET name='Fundusze inwestycyjne' WHERE id=276 AND name='Fundusze Inwestycyjne';
-- industry: fuzje i przejęcia → Fuzje i przejęcia
UPDATE crm_tags SET name='Fuzje i przejęcia' WHERE id=301 AND name='fuzje i przejęcia';
-- industry: handel międzynarodowy → Handel międzynarodowy
UPDATE crm_tags SET name='Handel międzynarodowy' WHERE id=506 AND name='handel międzynarodowy';
-- industry: hurtownia → Hurtownia
UPDATE crm_tags SET name='Hurtownia' WHERE id=253 AND name='hurtownia';
-- industry: hurtownie elektryczne → Hurtownie elektryczne
UPDATE crm_tags SET name='Hurtownie elektryczne' WHERE id=336 AND name='hurtownie elektryczne';
-- industry: internacjonalizacja → Internacjonalizacja
UPDATE crm_tags SET name='Internacjonalizacja' WHERE id=322 AND name='internacjonalizacja';
-- industry: inwestycje → Inwestycje
UPDATE crm_tags SET name='Inwestycje' WHERE id=389 AND name='inwestycje';
-- industry: IT/Edukacja → IT/edukacja
UPDATE crm_tags SET name='IT/edukacja' WHERE id=51 AND name='IT/Edukacja';
-- industry: IT/Technologie → IT/technologie
UPDATE crm_tags SET name='IT/technologie' WHERE id=52 AND name='IT/Technologie';
-- industry: jęzuk angielski → Jęzuk angielski
UPDATE crm_tags SET name='Jęzuk angielski' WHERE id=309 AND name='jęzuk angielski';
-- industry: język angielski → Język angielski
UPDATE crm_tags SET name='Język angielski' WHERE id=246 AND name='język angielski';
-- industry: kancelaria prawna → Kancelaria prawna
UPDATE crm_tags SET name='Kancelaria prawna' WHERE id=107 AND name='kancelaria prawna';
-- industry: karty dostępu → Karty dostępu
UPDATE crm_tags SET name='Karty dostępu' WHERE id=108 AND name='karty dostępu';
-- industry: komunikacja → Komunikacja
UPDATE crm_tags SET name='Komunikacja' WHERE id=248 AND name='komunikacja';
-- industry: konferencje → Konferencje
UPDATE crm_tags SET name='Konferencje' WHERE id=321 AND name='konferencje';
-- industry: kontroling finansowy → Kontroling finansowy
UPDATE crm_tags SET name='Kontroling finansowy' WHERE id=241 AND name='kontroling finansowy';
-- industry: koszulki → Koszulki
UPDATE crm_tags SET name='Koszulki' WHERE id=306 AND name='koszulki';
-- industry: księgowość → Księgowość
UPDATE crm_tags SET name='Księgowość' WHERE id=110 AND name='księgowość';
-- industry: leaderdship → Leaderdship
UPDATE crm_tags SET name='Leaderdship' WHERE id=289 AND name='leaderdship';
-- industry: Lean Management → Lean management
UPDATE crm_tags SET name='Lean management' WHERE id=570 AND name='Lean Management';
-- industry: Life Sciences → Life sciences
UPDATE crm_tags SET name='Life sciences' WHERE id=579 AND name='Life Sciences';
-- industry: lotnictwo → Lotnictwo
UPDATE crm_tags SET name='Lotnictwo' WHERE id=572 AND name='lotnictwo';
-- industry: m&a → M&A
UPDATE crm_tags SET name='M&A' WHERE id=300 AND name='m&a';
-- industry: Marketing / Komunikacja PR → Marketing / komunikacja PR
UPDATE crm_tags SET name='Marketing / komunikacja PR' WHERE id=54 AND name='Marketing / Komunikacja PR';
-- industry: Marketing / Reklama → Marketing / reklama
UPDATE crm_tags SET name='Marketing / reklama' WHERE id=55 AND name='Marketing / Reklama';
-- industry: markety → Markety
UPDATE crm_tags SET name='Markety' WHERE id=112 AND name='markety';
-- industry: medycyna → Medycyna
UPDATE crm_tags SET name='Medycyna' WHERE id=256 AND name='medycyna';
-- industry: Medycyna/Zdrowie → Medycyna/zdrowie
UPDATE crm_tags SET name='Medycyna/zdrowie' WHERE id=57 AND name='Medycyna/Zdrowie';
-- industry: Monitoring Wizyjny → Monitoring wizyjny
UPDATE crm_tags SET name='Monitoring wizyjny' WHERE id=338 AND name='Monitoring Wizyjny';
-- industry: nauka → Nauka
UPDATE crm_tags SET name='Nauka' WHERE id=342 AND name='nauka';
-- industry: nieruchomości komercyjne i mieszkaniowe → Nieruchomości komercyjne i mieszkaniowe
UPDATE crm_tags SET name='Nieruchomości komercyjne i mieszkaniowe' WHERE id=293 AND name='nieruchomości komercyjne i mieszkaniowe';
-- industry: obróbka szkła → Obróbka szkła
UPDATE crm_tags SET name='Obróbka szkła' WHERE id=335 AND name='obróbka szkła';
-- industry: obronność → Obronność
UPDATE crm_tags SET name='Obronność' WHERE id=573 AND name='obronność';
-- industry: Ochrona Mienia → Ochrona mienia
UPDATE crm_tags SET name='Ochrona mienia' WHERE id=399 AND name='Ochrona Mienia';
-- industry: odzież robocza → Odzież robocza
UPDATE crm_tags SET name='Odzież robocza' WHERE id=115 AND name='odzież robocza';
-- industry: ogrody zimowe → Ogrody zimowe
UPDATE crm_tags SET name='Ogrody zimowe' WHERE id=228 AND name='ogrody zimowe';
-- industry: opony → Opony
UPDATE crm_tags SET name='Opony' WHERE id=554 AND name='opony';
-- industry: oprogramowanie → Oprogramowanie
UPDATE crm_tags SET name='Oprogramowanie' WHERE id=221 AND name='oprogramowanie';
-- industry: organizator konferencji online → Organizator konferencji online
UPDATE crm_tags SET name='Organizator konferencji online' WHERE id=117 AND name='organizator konferencji online';
-- industry: Oświetlenie Biurowe → Oświetlenie biurowe
UPDATE crm_tags SET name='Oświetlenie biurowe' WHERE id=512 AND name='Oświetlenie Biurowe';
-- industry: Oświetlenie Przemysłowe → Oświetlenie przemysłowe
UPDATE crm_tags SET name='Oświetlenie przemysłowe' WHERE id=346 AND name='Oświetlenie Przemysłowe';
-- industry: Oświetlenie Zewnętrzne → Oświetlenie zewnętrzne
UPDATE crm_tags SET name='Oświetlenie zewnętrzne' WHERE id=513 AND name='Oświetlenie Zewnętrzne';
-- industry: patenty → Patenty
UPDATE crm_tags SET name='Patenty' WHERE id=350 AND name='patenty';
-- industry: payroll → Payroll
UPDATE crm_tags SET name='Payroll' WHERE id=282 AND name='payroll';
-- industry: Piekarnia - Cukiernia → Piekarnia - cukiernia
UPDATE crm_tags SET name='Piekarnia - cukiernia' WHERE id=65 AND name='Piekarnia - Cukiernia';
-- industry: pizzeria → Pizzeria
UPDATE crm_tags SET name='Pizzeria' WHERE id=347 AND name='pizzeria';
-- industry: Planowanie Finansowe → Planowanie finansowe
UPDATE crm_tags SET name='Planowanie finansowe' WHERE id=624 AND name='Planowanie Finansowe';
-- industry: plastik → Plastik
UPDATE crm_tags SET name='Plastik' WHERE id=358 AND name='plastik';
-- industry: podróże dla firm → Podróże dla firm
UPDATE crm_tags SET name='Podróże dla firm' WHERE id=387 AND name='podróże dla firm';
-- industry: pompy ciepła → Pompy ciepła
UPDATE crm_tags SET name='Pompy ciepła' WHERE id=287 AND name='pompy ciepła';
-- industry: pozycjonowanie stron → Pozycjonowanie stron
UPDATE crm_tags SET name='Pozycjonowanie stron' WHERE id=368 AND name='pozycjonowanie stron';
-- industry: Prawo / Usługi prawnicze → Prawo / usługi prawnicze
UPDATE crm_tags SET name='Prawo / usługi prawnicze' WHERE id=67 AND name='Prawo / Usługi prawnicze';
-- industry: Prawo/Legal → Prawo/legal
UPDATE crm_tags SET name='Prawo/legal' WHERE id=69 AND name='Prawo/Legal';
-- industry: Private Equity → Private equity
UPDATE crm_tags SET name='Private equity' WHERE id=612 AND name='Private Equity';
-- industry: producent → Producent
UPDATE crm_tags SET name='Producent' WHERE id=374 AND name='producent';
-- industry: produkcja hamulców → Produkcja hamulców
UPDATE crm_tags SET name='Produkcja hamulców' WHERE id=353 AND name='produkcja hamulców';
-- industry: Produkcja i Handel → Produkcja i handel
UPDATE crm_tags SET name='Produkcja i handel' WHERE id=71 AND name='Produkcja i Handel';
-- industry: produkcja materace → Produkcja materace
UPDATE crm_tags SET name='Produkcja materace' WHERE id=122 AND name='produkcja materace';
-- industry: produkcja opakowań → Produkcja opakowań
UPDATE crm_tags SET name='Produkcja opakowań' WHERE id=355 AND name='produkcja opakowań';
-- industry: produkcja oprogramowania → Produkcja oprogramowania
UPDATE crm_tags SET name='Produkcja oprogramowania' WHERE id=356 AND name='produkcja oprogramowania';
-- industry: produkcja urządzeń laboratoryjnych → Produkcja urządzeń laboratoryjnych
UPDATE crm_tags SET name='Produkcja urządzeń laboratoryjnych' WHERE id=125 AND name='produkcja urządzeń laboratoryjnych';
-- industry: Produkcja Żywności → Produkcja żywności
UPDATE crm_tags SET name='Produkcja żywności' WHERE id=631 AND name='Produkcja Żywności';
-- industry: przychodnia zdrowia → Przychodnia zdrowia
UPDATE crm_tags SET name='Przychodnia zdrowia' WHERE id=330 AND name='przychodnia zdrowia';
-- industry: przywództwo → Przywództwo
UPDATE crm_tags SET name='Przywództwo' WHERE id=376 AND name='przywództwo';
-- industry: psychiatria → Psychiatria
UPDATE crm_tags SET name='Psychiatria' WHERE id=255 AND name='psychiatria';
-- industry: psycholog → Psycholog
UPDATE crm_tags SET name='Psycholog' WHERE id=385 AND name='psycholog';
-- industry: psychoterapia → Psychoterapia
UPDATE crm_tags SET name='Psychoterapia' WHERE id=126 AND name='psychoterapia';
-- industry: psychoterapia dla dzieci → Psychoterapia dla dzieci
UPDATE crm_tags SET name='Psychoterapia dla dzieci' WHERE id=127 AND name='psychoterapia dla dzieci';
-- industry: python → Python
UPDATE crm_tags SET name='Python' WHERE id=345 AND name='python';
-- industry: płyty drewniane → Płyty drewniane
UPDATE crm_tags SET name='Płyty drewniane' WHERE id=304 AND name='płyty drewniane';
-- industry: restauracja → Restauracja
UPDATE crm_tags SET name='Restauracja' WHERE id=348 AND name='restauracja';
-- industry: rewitalizacja miejska → Rewitalizacja miejska
UPDATE crm_tags SET name='Rewitalizacja miejska' WHERE id=292 AND name='rewitalizacja miejska';
-- industry: rozwój technologiczny → Rozwój technologiczny
UPDATE crm_tags SET name='Rozwój technologiczny' WHERE id=505 AND name='rozwój technologiczny';
-- industry: sala → Sala
UPDATE crm_tags SET name='Sala' WHERE id=320 AND name='sala';
-- industry: Search Fund → Search fund
UPDATE crm_tags SET name='Search fund' WHERE id=622 AND name='Search Fund';
-- industry: serwis opon → Serwis opon
UPDATE crm_tags SET name='Serwis opon' WHERE id=555 AND name='serwis opon';
-- industry: skład budowlany → Skład budowlany
UPDATE crm_tags SET name='Skład budowlany' WHERE id=369 AND name='skład budowlany';
-- industry: software → Software
UPDATE crm_tags SET name='Software' WHERE id=357 AND name='software';
-- industry: software house → Software house
UPDATE crm_tags SET name='Software house' WHERE id=220 AND name='software house';
-- industry: SPA & Wellness → SPA & wellness
UPDATE crm_tags SET name='SPA & wellness' WHERE id=532 AND name='SPA & Wellness';
-- industry: sport → Sport
UPDATE crm_tags SET name='Sport' WHERE id=370 AND name='sport';
-- industry: sprzątanie → Sprzątanie
UPDATE crm_tags SET name='Sprzątanie' WHERE id=371 AND name='sprzątanie';
-- industry: startupy → Startupy
UPDATE crm_tags SET name='Startupy' WHERE id=134 AND name='startupy';
-- industry: stolarka aluminiowa → Stolarka aluminiowa
UPDATE crm_tags SET name='Stolarka aluminiowa' WHERE id=227 AND name='stolarka aluminiowa';
-- industry: stolarka alumioniowa → Stolarka alumioniowa
UPDATE crm_tags SET name='Stolarka alumioniowa' WHERE id=375 AND name='stolarka alumioniowa';
-- industry: strategie → Strategie
UPDATE crm_tags SET name='Strategie' WHERE id=299 AND name='strategie';
-- industry: system CRM → System CRM
UPDATE crm_tags SET name='System CRM' WHERE id=136 AND name='system CRM';
-- industry: Systemy Alarmowe → Systemy alarmowe
UPDATE crm_tags SET name='Systemy alarmowe' WHERE id=593 AND name='Systemy Alarmowe';
-- industry: Systemy Bezpieczeństwa → Systemy bezpieczeństwa
UPDATE crm_tags SET name='Systemy bezpieczeństwa' WHERE id=398 AND name='Systemy Bezpieczeństwa';
-- industry: Systemy Zabezpieczeń → Systemy zabezpieczeń
UPDATE crm_tags SET name='Systemy zabezpieczeń' WHERE id=592 AND name='Systemy Zabezpieczeń';
-- industry: Sztuczna Inteligencja → Sztuczna inteligencja
UPDATE crm_tags SET name='Sztuczna inteligencja' WHERE id=230 AND name='Sztuczna Inteligencja';
-- industry: technologie informatyczne → Technologie informatyczne
UPDATE crm_tags SET name='Technologie informatyczne' WHERE id=327 AND name='technologie informatyczne';
-- industry: technologie kosmiczne → Technologie kosmiczne
UPDATE crm_tags SET name='Technologie kosmiczne' WHERE id=574 AND name='technologie kosmiczne';
-- industry: testy osobowości → Testy osobowości
UPDATE crm_tags SET name='Testy osobowości' WHERE id=377 AND name='testy osobowości';
-- industry: trener → Trener
UPDATE crm_tags SET name='Trener' WHERE id=384 AND name='trener';
-- industry: turystyka → Turystyka
UPDATE crm_tags SET name='Turystyka' WHERE id=386 AND name='turystyka';
-- industry: tłumaczenia → Tłumaczenia
UPDATE crm_tags SET name='Tłumaczenia' WHERE id=388 AND name='tłumaczenia';
-- industry: usczelki → Usczelki
UPDATE crm_tags SET name='Usczelki' WHERE id=390 AND name='usczelki';
-- industry: Usługi Dla Firm → Usługi dla firm
UPDATE crm_tags SET name='Usługi dla firm' WHERE id=615 AND name='Usługi Dla Firm';
-- industry: usługi konsultingowe → Usługi konsultingowe
UPDATE crm_tags SET name='Usługi konsultingowe' WHERE id=326 AND name='usługi konsultingowe';
-- industry: usługi prawne → Usługi prawne
UPDATE crm_tags SET name='Usługi prawne' WHERE id=265 AND name='usługi prawne';
-- industry: Venture Capital → Venture capital
UPDATE crm_tags SET name='Venture capital' WHERE id=638 AND name='Venture Capital';
-- industry: weryfikacja podmiotów → Weryfikacja podmiotów
UPDATE crm_tags SET name='Weryfikacja podmiotów' WHERE id=145 AND name='weryfikacja podmiotów';
-- industry: wprawadzają firmy irlandzkie do Polski → Wprawadzają firmy irlandzkie do polski
UPDATE crm_tags SET name='Wprawadzają firmy irlandzkie do polski' WHERE id=146 AND name='wprawadzają firmy irlandzkie do Polski';
-- industry: wsparcie biznesu → Wsparcie biznesu
UPDATE crm_tags SET name='Wsparcie biznesu' WHERE id=504 AND name='wsparcie biznesu';
-- industry: wulkanizacja → Wulkanizacja
UPDATE crm_tags SET name='Wulkanizacja' WHERE id=556 AND name='wulkanizacja';
-- industry: wyjście na rynki skandynawskie → Wyjście na rynki skandynawskie
UPDATE crm_tags SET name='Wyjście na rynki skandynawskie' WHERE id=302 AND name='wyjście na rynki skandynawskie';
-- industry: wyjście na rynki zagraniczne → Wyjście na rynki zagraniczne
UPDATE crm_tags SET name='Wyjście na rynki zagraniczne' WHERE id=323 AND name='wyjście na rynki zagraniczne';
-- industry: zaopatrzenie biurowe → Zaopatrzenie biurowe
UPDATE crm_tags SET name='Zaopatrzenie biurowe' WHERE id=147 AND name='zaopatrzenie biurowe';
-- industry: Zarządzanie Majątkiem → Zarządzanie majątkiem
UPDATE crm_tags SET name='Zarządzanie majątkiem' WHERE id=623 AND name='Zarządzanie Majątkiem';
-- industry: Zarządzanie Ryzykiem → Zarządzanie ryzykiem
UPDATE crm_tags SET name='Zarządzanie ryzykiem' WHERE id=313 AND name='Zarządzanie Ryzykiem';
-- industry: zdrowie → Zdrowie
UPDATE crm_tags SET name='Zdrowie' WHERE id=331 AND name='zdrowie';
-- industry: zieleń → Zieleń
UPDATE crm_tags SET name='Zieleń' WHERE id=372 AND name='zieleń';
-- industry: znaki towarowe → Znaki towarowe
UPDATE crm_tags SET name='Znaki towarowe' WHERE id=351 AND name='znaki towarowe';
