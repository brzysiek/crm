"""Wypełnia bazę danymi startowymi. Uruchomić raz po setup_db.sql."""
import sys
sys.path.insert(0, '.')

from flask import Flask
import database

app = Flask(__name__)
database.init_app(app)

with app.app_context():
    from models.user import create_user, get_user_by_username
    from models.expense import create_expense
    from models.invoice import upsert_invoice

    # ── Admin ────────────────────────────────────────────────────────────────
    if not get_user_by_username('admin'):
        create_user('admin', 'Administrator', 'admin@roslinarnia.pl', 'admin123', 'admin')
        print("Utworzono admina.")
    else:
        print("Admin już istnieje — pomijam.")
    print("Domyślny admin: login=admin, hasło=admin123 — zmień po pierwszym logowaniu!")

    # ── Przykładowi użytkownicy ───────────────────────────────────────────────
    for uname, fname, role in [
        ('magda',   'Magdalena Kowalska', 'owner'),
        ('tomek',   'Tomasz Nowak',       'cashier'),
    ]:
        if not get_user_by_username(uname):
            create_user(uname, fname, f'{uname}@roslinarnia.pl', 'haslo123', role)
            print(f"Użytkownik {uname} ({role}) utworzony.")

    # ── Przykładowe wydatki ───────────────────────────────────────────────────
    expenses = [
        {
            'date': '2025-06-02', 'responsible_person': 'Magdalena Kowalska',
            'description': 'Podłoże ogrodnicze 50L x 20 szt.',
            'amount_gross': 738.00, 'vat_rate': 8.00, 'amount_net': 683.33,
            'payment_percent': 100, 'invoice_status': 'ksef',
            'invoice_ref': 'KSeF/2025/06/001234',
            'paid_by': 'Magdalena Kowalska', 'payment_method': 'transfer',
            'category': 'Towar', 'is_recurring': 0,
        },
        {
            'date': '2025-06-05', 'responsible_person': 'Tomasz Nowak',
            'description': 'Nawozy mineralne — dostawa miesięczna',
            'amount_gross': 1230.00, 'vat_rate': 23.00, 'amount_net': 1000.00,
            'payment_percent': 50, 'invoice_status': 'disk',
            'invoice_ref': '/faktury/2025/06/nawoz.pdf',
            'paid_by': 'Tomasz Nowak', 'payment_method': 'card',
            'category': 'Materiały', 'is_recurring': 1,
        },
        {
            'date': '2025-06-08', 'responsible_person': 'Administrator',
            'description': 'Czynsz za lokal — czerwiec 2025',
            'amount_gross': 4920.00, 'vat_rate': 23.00, 'amount_net': 4000.00,
            'payment_percent': 100, 'invoice_status': 'ksef',
            'invoice_ref': 'KSeF/2025/06/005678',
            'paid_by': 'Administrator', 'payment_method': 'transfer',
            'category': 'Czynsz', 'is_recurring': 1,
        },
        {
            'date': '2025-06-10', 'responsible_person': 'Magdalena Kowalska',
            'description': 'Doniczki ceramiczne — uzupełnienie asortymentu',
            'amount_gross': 492.00, 'vat_rate': 23.00, 'amount_net': 400.00,
            'payment_percent': 0, 'invoice_status': 'none',
            'paid_by': None, 'payment_method': None,
            'category': 'Towar', 'is_recurring': 0,
        },
        {
            'date': '2025-06-12', 'responsible_person': 'Tomasz Nowak',
            'description': 'Paliwo — wyjazdy do dostawców',
            'amount_gross': 310.50, 'vat_rate': 23.00, 'amount_net': 252.44,
            'payment_percent': 100, 'invoice_status': 'disk',
            'paid_by': 'Tomasz Nowak', 'payment_method': 'card',
            'category': 'Transport', 'is_recurring': 0,
        },
        {
            'date': '2025-06-15', 'responsible_person': 'Administrator',
            'description': 'Hosting i domena — roczna opłata',
            'amount_gross': 369.00, 'vat_rate': 23.00, 'amount_net': 300.00,
            'payment_percent': 100, 'invoice_status': 'ksef',
            'paid_by': 'Administrator', 'payment_method': 'transfer',
            'category': 'IT', 'is_recurring': 1,
        },
        {
            'date': '2025-06-18', 'responsible_person': 'Magdalena Kowalska',
            'description': 'Materiały biurowe — papier, tonery',
            'amount_gross': 185.40, 'vat_rate': 23.00, 'amount_net': 150.73,
            'payment_percent': 0, 'invoice_status': 'none',
            'paid_by': None, 'payment_method': None,
            'category': 'Biuro', 'is_recurring': 0,
        },
    ]
    for e in expenses:
        create_expense(e)
    print(f"Dodano {len(expenses)} wydatków.")

    # ── Faktury pending z Fakturowni ──────────────────────────────────────────
    invoices = [
        {
            'fakturownia_id': 'fw_demo_001',
            'invoice_number': 'FV/2025/06/0042',
            'vendor_name': 'Agro-Mix Sp. z o.o.',
            'vendor_nip': '5213001234',
            'issue_date': '2025-06-03',
            'amount_gross': 2214.00,
            'amount_net': 1800.00,
            'vat_amount': 414.00,
            'ksef_number': '2025/06/KS/9988776',
        },
        {
            'fakturownia_id': 'fw_demo_002',
            'invoice_number': 'FV/2025/06/0078',
            'vendor_name': 'GreenPack Opakowania',
            'vendor_nip': '7811002345',
            'issue_date': '2025-06-11',
            'amount_gross': 615.00,
            'amount_net': 500.00,
            'vat_amount': 115.00,
            'ksef_number': None,
        },
        {
            'fakturownia_id': 'fw_demo_003',
            'invoice_number': 'FV/2025/06/0099',
            'vendor_name': 'FloriStar Dystrybutor',
            'vendor_nip': '9281003456',
            'issue_date': '2025-06-17',
            'amount_gross': 3690.00,
            'amount_net': 3000.00,
            'vat_amount': 690.00,
            'ksef_number': '2025/06/KS/1122334',
        },
    ]
    for inv in invoices:
        upsert_invoice(inv)
    print(f"Dodano {len(invoices)} faktur pending.")

    print("\nSeed zakończony pomyślnie.")
