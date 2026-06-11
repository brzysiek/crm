# Prompt dla Claude Code — aplikacja finansowa RośliNarnia

Zbuduj wewnętrzną aplikację webową do zarządzania finansami centrum ogrodniczego **RośliNarnia**. Używaj Flask (Python) jako backend, Jinja2 + czysty HTML/CSS/vanilla JS jako frontend (bez frameworków JS). **MySQL** jako baza danych. Całość ma działać lokalnie.

---

## Stack i struktura projektu

```
roslinnarnia/
├── app.py                  # główna aplikacja Flask
├── config.py               # konfiguracja aplikacji (NIE commitować do gita)
├── config.example.py       # szablon konfiguracji do commitowania
├── database.py             # połączenie z MySQL, helper get_db()
├── setup_db.sql            # skrypt SQL tworzący bazę i tabele — uruchomić raz
├── seed_db.py              # wypełnienie bazy przykładowymi danymi (uruchomić po setup_db.sql)
├── models/
│   ├── expense.py          # funkcje CRUD dla wydatków
│   ├── invoice.py          # funkcje CRUD dla faktur Fakturowni
│   ├── user.py             # funkcje CRUD dla użytkowników
│   └── settings.py        # funkcje odczytu/zapisu ustawień
├── routes/
│   ├── expenses.py         # CRUD wydatków
│   ├── settings.py         # ustawienia + Fakturownia
│   ├── users.py            # zarządzanie użytkownikami
│   └── dashboard.py        # strona główna
├── services/
│   └── fakturownia.py      # klient API Fakturowni
├── templates/
│   ├── base.html           # layout z nawigacją
│   ├── dashboard.html
│   ├── expenses/
│   │   ├── list.html
│   │   └── form.html
│   └── settings/
│       ├── index.html
│       ├── fakturownia.html
│       └── users.html
├── static/
│   ├── style.css
│   └── app.js
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Konfiguracja (`config.py` i `config.example.py`)

Utwórz plik `config.example.py` jako szablon do commitowania (bez prawdziwych danych):

```python
# config.example.py — skopiuj do config.py i uzupełnij swoje dane

class Config:
    # Flask
    SECRET_KEY = "zmien-na-losowy-string"
    DEBUG = True

    # MySQL
    MYSQL_HOST = "localhost"
    MYSQL_PORT = 3306
    MYSQL_USER = "roslinnarnia_user"
    MYSQL_PASSWORD = "twoje_haslo"
    MYSQL_DB = "roslinnarnia_finance"
    MYSQL_CHARSET = "utf8mb4"

    # Aplikacja
    APP_NAME = "RośliNarnia Finanse"
    DEFAULT_CURRENCY = "PLN"
```

Plik `config.py` (faktyczny, z prawdziwymi danymi — dodany do `.gitignore`) ma identyczną strukturę z uzupełnionymi wartościami.

`database.py` czyta konfigurację z `config.py` i udostępnia `get_db()` — funkcję zwracającą połączenie MySQL z automatycznym zamknięciem po żądaniu (używaj `flask.g` i `teardown_appcontext`). Używaj `pymysql` z `DictCursor` — każdy wiersz jako słownik.

---

## Plik `setup_db.sql` — uruchomić raz przed startem aplikacji

```sql
-- Uruchomienie: mysql -u root -p < setup_db.sql

CREATE DATABASE IF NOT EXISTS roslinnarnia_finance
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'roslinnarnia_user'@'localhost'
    IDENTIFIED BY 'ZMIEN_NA_SWOJE_HASLO';

GRANT ALL PRIVILEGES ON roslinnarnia_finance.* 
    TO 'roslinnarnia_user'@'localhost';

FLUSH PRIVILEGES;

USE roslinnarnia_finance;

-- ── Użytkownicy ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    username    VARCHAR(64) NOT NULL UNIQUE,
    full_name   VARCHAR(128) NOT NULL,
    email       VARCHAR(128),
    password_hash VARCHAR(256) NOT NULL,
    role        ENUM('admin', 'owner', 'cashier') DEFAULT 'cashier',
    is_active   TINYINT(1) DEFAULT 1,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- ── Wydatki ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS expenses (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    date                DATE NOT NULL,
    responsible_person  VARCHAR(128) NOT NULL,
    description         TEXT NOT NULL,
    amount_gross        DECIMAL(12,2) NOT NULL,
    vat_rate            DECIMAL(5,2) NOT NULL,
    amount_net          DECIMAL(12,2) NOT NULL,
    payment_percent     DECIMAL(5,2) DEFAULT 0.00,
    invoice_status      ENUM('ksef','disk','none') DEFAULT 'none',
    invoice_ref         VARCHAR(256),
    paid_by             VARCHAR(128),
    payment_method      ENUM('transfer','card','cash') DEFAULT NULL,
    is_recurring        TINYINT(1) DEFAULT 0,
    category            VARCHAR(64),
    fakturownia_id      VARCHAR(64) UNIQUE,
    fakturownia_status  ENUM('manual','imported','pending_review') DEFAULT 'manual',
    notes               TEXT,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- ── Faktury z Fakturowni (bufor) ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fakturownia_invoices (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    fakturownia_id      VARCHAR(64) UNIQUE NOT NULL,
    invoice_number      VARCHAR(64) NOT NULL,
    vendor_name         VARCHAR(256),
    vendor_nip          VARCHAR(32),
    issue_date          DATE,
    amount_gross        DECIMAL(12,2),
    amount_net          DECIMAL(12,2),
    vat_amount          DECIMAL(12,2),
    ksef_number         VARCHAR(128),
    raw_json            LONGTEXT,
    status              ENUM('pending','assigned','rejected') DEFAULT 'pending',
    assigned_expense_id INT REFERENCES expenses(id),
    synced_at           DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ── Ustawienia aplikacji ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS settings (
    `key`       VARCHAR(128) PRIMARY KEY,
    value       TEXT,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

INSERT IGNORE INTO settings (`key`, value) VALUES
    ('fakturownia_subdomain', ''),
    ('fakturownia_api_key', ''),
    ('fakturownia_sync_schedule', 'manual'),
    ('fakturownia_last_sync', NULL),
    ('fakturownia_filter_category', 'all');

-- ── Log synchronizacji ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sync_log (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    synced_at           DATETIME DEFAULT CURRENT_TIMESTAMP,
    invoices_fetched    INT DEFAULT 0,
    invoices_new        INT DEFAULT 0,
    invoices_pending    INT DEFAULT 0,
    status              ENUM('ok','error') NOT NULL,
    message             TEXT
);
```

**Ważne:** hasło w `setup_db.sql` (`ZMIEN_NA_SWOJE_HASLO`) musi być identyczne z `MYSQL_PASSWORD` w `config.py`. Dodaj `setup_db.sql` do `.gitignore` lub usuń z niego hasło przed commitowaniem — zamiast tego commituj `setup_db.example.sql` z placeholderem.

---

## Tabela `users` — pełna implementacja

Użytkownicy są przechowywani w MySQL, **nie** w plikach ani sesji. Implementuj:

### `models/user.py`

```python
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db

def get_all_users() -> list[dict]: ...
def get_user_by_id(user_id: int) -> dict | None: ...
def get_user_by_username(username: str) -> dict | None: ...
def create_user(username, full_name, email, password, role='cashier') -> int: ...
def update_user(user_id, full_name, email, role, is_active) -> None: ...
def change_password(user_id, new_password) -> None: ...
def delete_user(user_id) -> None: ...
def verify_password(username, password) -> dict | None:
    """Sprawdza login i hasło, zwraca obiekt użytkownika lub None."""
```

Hasła hashuj przez `werkzeug.security.generate_password_hash` (domyślny algorytm `pbkdf2:sha256`).

### Zakładka Ustawienia → Użytkownicy (`/settings/users`)

Pełna strona (nie placeholder) z:

**Listą użytkowników** — tabela z kolumnami: imię i nazwisko, login, email, rola (badge), status aktywny/nieaktywny, akcje (edytuj, dezaktywuj/aktywuj, zmień hasło).

**Formularzem dodawania użytkownika** (poniżej listy lub modal):
- Login (unikalny)
- Imię i nazwisko
- Email (opcjonalny)
- Rola (select: administrator / właściciel / kasjer)
- Hasło + potwierdzenie hasła

**Formularzem edycji** (`/settings/users/<id>/edit`): zmiana imienia, emaila, roli, statusu. Hasło zmieniane osobno przez `/settings/users/<id>/password`.

**Seed danych** (`seed_db.py`) — stwórz jednego domyślnego admina:
- login: `admin`, hasło: `admin123`, rola: `admin`
- wydrukuj po seedzie: `"Domyślny admin: login=admin, hasło=admin123 — zmień po pierwszym logowaniu!"`

> **Uwaga:** autoryzacja/logowanie (sesje Flask) to poza zakresem tej wersji — użytkownicy są w bazie, ale aplikacja nie wymaga logowania. To zostanie dodane w kolejnym etapie.

---

## Połączenie z MySQL (`database.py`)

```python
import pymysql
import pymysql.cursors
from flask import g, current_app

def get_db():
    if 'db' not in g:
        from config import Config
        g.db = pymysql.connect(
            host=Config.MYSQL_HOST,
            port=Config.MYSQL_PORT,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB,
            charset=Config.MYSQL_CHARSET,
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False
        )
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_app(app):
    app.teardown_appcontext(close_db)
```

Wszystkie zapytania przez `get_db()`. Używaj parametryzowanych zapytań (`%s`) — nigdy f-stringów w SQL. Dla operacji zapisu: `db.commit()` po każdej transakcji, `db.rollback()` w bloku `except`.

---

## Widoki i funkcjonalności

### 1. Nawigacja (base.html)

Górny pasek z logo "RośliNarnia Finanse" i linkami:
- Dashboard
- Wydatki
- Przychody *(placeholder — pusta strona z komunikatem "wkrótce")*
- Przepływy *(placeholder)*
- Ustawienia — z badge liczby faktur `fakturownia_invoices` o statusie `pending`

### 2. Dashboard (`/`)

Cztery karty KPI pobierane z bazy:
- Łączne koszty brutto w bieżącym miesiącu
- Kwota opłacona (gdzie `payment_percent = 100`)
- Kwota oczekująca (gdzie `payment_percent < 100`)
- Liczba faktur z Fakturowni oczekujących na przegląd

Prosty wykres słupkowy (czysty Canvas API lub SVG, bez bibliotek) pokazujący koszty dzienne w bieżącym miesiącu.

---

### 3. Wydatki (`/expenses`)

#### Lista wydatków

Tabela z kolumnami (w tej kolejności):

| Kolumna | Typ | Uwagi |
|---|---|---|
| Data | DATE | format DD.MM.YYYY |
| Osoba | TEXT | |
| Opis | TEXT | skrócony, pełny w tooltip |
| Brutto | DECIMAL | format `X XXX,XX zł` |
| VAT | DECIMAL | jako `23%` |
| Netto | DECIMAL | format `X XXX,XX zł` |
| % opłacenia | DECIMAL | pasek postępu (zielony=100%, żółty=1-99%, czerwony=0%) |
| Faktura | TEXT | badge: `KSeF` (zielony) / `Dysk` (niebieski) / `Brak` (szary) |
| Kto zapłacił | TEXT | |
| Forma | TEXT | badge: `przelew` / `karta` / `gotówka` |
| Akcje | — | ikony: edytuj, usuń |

Filtry nad tabelą:
- Pole tekstowe (szukaj po opisie, osobie)
- Select: miesiąc/rok (domyślnie bieżący)
- Select: kategoria
- Select: status faktury (KSeF / dysk / brak)
- Select: % opłacenia (wszystkie / w pełni / częściowo / nieopłacone)

Przyciski w headerze strony:
- **Dodaj wydatek** — otwiera formularz
- **Import CSV** — placeholder (formularz upload pliku, backend parsuje ale nie przetwarza)

**Ważne**: żadnych linków ani wzmianek o Fakturowni na tej stronie.

#### Formularz wydatku (`/expenses/new`, `/expenses/<id>/edit`)

Pola:
- Data (date picker, domyślnie dziś)
- Osoba odpowiedzialna (select zasilany z tabeli `users.full_name` gdzie `is_active=1`, plus opcja "inna osoba" z free text)
- Opis / za co (textarea)
- Kwota brutto (number, 2 miejsca dziesiętne)
- Stawka VAT (select: 23%, 8%, 5%, 0%, zw.) — po wyborze automatycznie oblicza netto w JS
- Kwota netto (readonly, obliczana automatycznie)
- % opłacenia (slider 0-100 + pole numeryczne zsynchronizowane)
- Status faktury (radio: KSeF / Na dysku / Brak)
- Numer KSeF lub ścieżka pliku (pokazuje się warunkowo)
- Kto zapłacił (text input)
- Forma płatności (select: przelew / karta / gotówka)
- Rodzaj kosztu (radio: jednorazowy / stały/cykliczny)
- Kategoria (select z istniejących kategorii z bazy + opcja "nowa")
- Notatki (textarea, opcjonalne)

Walidacja po stronie serwera. Przekierowanie na listę po zapisie z flash message.

---

### 4. Ustawienia (`/settings`)

Layout z lewym sidebar zawierającym zakładki:
- Ogólne
- **Użytkownicy** ← pełna implementacja
- Import z banku *(placeholder)*
- **Fakturownia**

#### Zakładka Fakturownia (`/settings/fakturownia`)

Trzy sekcje na jednej stronie:

**A. Konfiguracja API**

Formularz z polami:
- Subdomena konta + suffix `.fakturownia.pl` widoczny obok
- Klucz API (input type=password z przyciskiem "pokaż/ukryj")
- Harmonogram synchronizacji (select: ręcznie / codziennie o 08:00 / co godzinę)
- Filtr kategorii (select: wszystkie faktury zakupowe / tylko z kategorią "koszty" / własna wartość)

Przyciski:
- **Zapisz konfigurację** — zapisuje do tabeli `settings`
- **Testuj połączenie** — `GET /api/fakturownia/test`
- **Synchronizuj teraz** — `POST /api/fakturownia/sync`

**B. Historia synchronizacji**

Tabela ostatnich 10 wpisów z `sync_log`: data/godzina, pobrano, nowych, do przeglądu, status, komunikat.

**C. Faktury do ręcznego przypisania**

Lista kart dla `fakturownia_invoices` gdzie `status = 'pending'`. Każda karta:
- Numer faktury + data wystawienia
- Nazwa i NIP kontrahenta
- Kwota brutto / VAT / netto
- Numer KSeF (jeśli jest)
- Przyczyna: "Brak dopasowania — przypisz ręcznie"
- Przyciski: **Utwórz wpis w rejestrze** (pre-fill formularza wydatku) / **Odrzuć** (confirm dialog)

---

## Serwis Fakturowni (`services/fakturownia.py`)

```python
class FakturowniaClient:
    BASE_URL = "https://{subdomain}.fakturownia.pl"

    def __init__(self, subdomain: str, api_token: str):
        self.base_url = self.BASE_URL.format(subdomain=subdomain)
        self.api_token = api_token

    def test_connection(self) -> dict:
        """GET /invoices.json?api_token=... — sprawdza autoryzację"""

    def fetch_purchase_invoices(self, period_start: str, period_end: str) -> list[dict]:
        """
        GET /invoices.json z parametrami:
        - api_token, kind=expense (lub purchase), date_from, date_to
        Zwraca listę słowników: id, number, buyer_name, buyer_tax_no,
        sell_date, gross_price, net_price, tax_price, ksef_number
        """

    def sync_to_db(self, db_conn, period_days: int = 30) -> dict:
        """
        1. Pobiera faktury z ostatnich period_days dni
        2. Dla każdej sprawdza czy fakturownia_id istnieje w DB
        3. Jeśli nie — INSERT z status='pending'
        4. Zapisuje wpis do sync_log
        5. Zwraca {fetched, new, pending, status}
        """
```

Dokumentacja API: https://github.com/fakturownia/api
**Obsługa błędów**: timeout 10s, retry 1x, błędy do sync_log.

---

## Endpointy API (JSON)

```
GET  /api/fakturownia/test          → {ok: bool, message: str}
POST /api/fakturownia/sync          → {fetched: int, new: int, pending: int, status: str}
POST /expenses/<id>/delete          → redirect
GET  /api/expenses/pending-count    → {count: int}
```

---

## Styl CSS

```css
:root {
  --lime: #B5E619;
  --lime-light: #C4EC5B;
  --bottle-green: #1C4B40;
  --bottle-dark: #0D2820;
  --slate: #484845;
  --slate-mid: #878782;
  --slate-light: #CDCDC8;
  --off-white: #F5F5F3;
}
```

Czcionka: **Work Sans** z Google Fonts. Styl płaski, minimalistyczny, bez cieni i gradientów. Nawigacja z `background: var(--bottle-green)`, tekst biały. Przyciski primary: `background: var(--bottle-green)`.

---

## requirements.txt

```
Flask>=3.0
pymysql>=1.1
cryptography>=41.0
requests>=2.31
python-dateutil>=2.8
werkzeug>=3.0
```

---

## .gitignore

```
config.py
setup_db.sql
*.pyc
__pycache__/
.env
*.sqlite
```

---

## Kolejność budowania

1. `setup_db.sql` + `config.example.py` + `config.py` (użytkownik uzupełnia ręcznie)
2. `database.py` — połączenie MySQL, `get_db()`
3. `models/` — wszystkie cztery moduły
4. `seed_db.py` — przykładowe dane (5-8 wydatków, 1 admin, 2-3 faktury pending)
5. `routes/` + `templates/` — dashboard, wydatki, ustawienia, użytkownicy
6. `services/fakturownia.py`
7. `static/style.css` + `static/app.js`
8. `README.md`

Upewniaj się że każdy etap jest działający przed przejściem do następnego.

---

## README.md — instrukcja uruchomienia

```markdown
## Wymagania
- Python 3.11+
- MySQL 8.0+ (lub MariaDB 10.6+)

## Instalacja

1. Sklonuj repozytorium i wejdź do katalogu
2. `pip install -r requirements.txt`
3. Skopiuj szablon konfiguracji: `cp config.example.py config.py`
4. Uzupełnij dane w `config.py` (host, user, hasło, nazwa bazy)
5. Uruchom skrypt SQL na serwerze MySQL jako root:
   `mysql -u root -p < setup_db.sql`
   (wcześniej ustaw hasło w setup_db.sql identyczne z config.py)
6. Wypełnij bazę danymi startowymi: `python seed_db.py`
7. Uruchom aplikację: `python app.py`
8. Otwórz http://localhost:5000

## Domyślny użytkownik
Login: admin | Hasło: admin123 — zmień po pierwszym uruchomieniu w Ustawienia → Użytkownicy.
```

---

## Co NIE wchodzi w zakres tej wersji

- Logowanie/sesje użytkowników (użytkownicy są w DB, ale auth zostanie dodana później)
- Automatyczne dopasowanie faktur do wydatków
- Import CSV z banku
- Moduł przychodów i przepływów
- Powiadomienia email
