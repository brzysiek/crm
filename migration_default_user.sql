-- Migracja: domyślny użytkownik administratora
-- Uruchomić na istniejącej bazie (dla nowych instalacji użyj setup_db.sql)
-- Login: aadmin  |  Hasło: 12345678

INSERT IGNORE INTO users (username, full_name, role, password_hash) VALUES (
    'aadmin',
    'Administrator',
    'admin',
    'scrypt:32768:8:1$JxE8ts3xeIuIWpYR$b7dece926c2e8c733e0f3f1cfe51f0c6828ec8e1d1f3c8f5b71ad5be05c0207a94f3d3bc98bf08c6065f3c7aafba42f76deaf8f7ba8ada449994b556172f9185'
);
