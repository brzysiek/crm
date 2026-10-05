"""Ostatni kontakt z firmą i z osobą.

Kontaktem jest ślad rozmowy, nie ślad edycji rekordu: notatka, zrobione zadanie
i wysłana kampania. Zmiany w `crm_history` celowo się nie liczą — poprawienie
NIP-u nie jest kontaktem, a gdyby się liczyło, filtr „bez kontaktu od 90 dni"
pokazywałby pustą listę po każdym porządkowaniu danych.

Wyrażenia są fragmentami SQL-a wstawianymi do zapytań list, żeby kolumna
i filtr liczyły dokładnie to samo. Brak kontaktu to data zerowa, a nie NULL —
dzięki temu „nigdy" wpada do „od 90 dni", bo to ten sam przypadek.
"""

# CAST, a nie goły literał: bez niego GREATEST zwraca napis zamiast daty
# i kolumna „ostatni kontakt" przychodzi z bazy jako string.
NEVER = "CAST('1000-01-01' AS DATETIME)"


def company_last_contact_sql(col: str = 'c.id') -> str:
    """Firmę kontaktuje się także przez jej ludzi, więc notatki, zadania
    i wysyłki przy kontaktach liczą się jako kontakt z firmą."""
    return f"""GREATEST(
        COALESCE((SELECT MAX(n.created_at) FROM crm_notes n
                  WHERE n.entity_type='company' AND n.entity_id={col}), {NEVER}),
        COALESCE((SELECT MAX(n.created_at) FROM crm_notes n
                  JOIN crm_contacts nc ON nc.id = n.entity_id
                  WHERE n.entity_type='contact' AND nc.company_id={col}), {NEVER}),
        COALESCE((SELECT MAX(COALESCE(t.completed_at, t.updated_at)) FROM tasks t
                  LEFT JOIN crm_contacts tc ON tc.id = t.crm_contact_id
                  WHERE t.status='done' AND t.deleted_at IS NULL
                    AND (t.crm_company_id={col} OR tc.company_id={col})), {NEVER}),
        COALESCE((SELECT MAX(r.sent_at) FROM email_campaign_recipients r
                  JOIN crm_contacts rc ON rc.id = r.contact_id
                  WHERE r.status='sent' AND rc.company_id={col}), {NEVER})
    )"""


def contact_last_contact_sql(col: str = 'ct.id') -> str:
    """Przy osobie liczą się tylko jej własne ślady. Notatka przy firmie nie
    jest kontaktem z każdym jej pracownikiem — inaczej cała lista ludzi
    z aktywnej firmy wyglądałaby na obdzwonioną."""
    return f"""GREATEST(
        COALESCE((SELECT MAX(n.created_at) FROM crm_notes n
                  WHERE n.entity_type='contact' AND n.entity_id={col}), {NEVER}),
        COALESCE((SELECT MAX(COALESCE(t.completed_at, t.updated_at)) FROM tasks t
                  WHERE t.status='done' AND t.deleted_at IS NULL
                    AND t.crm_contact_id={col}), {NEVER}),
        COALESCE((SELECT MAX(r.sent_at) FROM email_campaign_recipients r
                  WHERE r.status='sent' AND r.contact_id={col}), {NEVER})
    )"""


def stale_days(value) -> int | None:
    """Filtr przyjmuje tylko trzy progi — wyrażenie idzie do SQL-a jako liczba,
    więc wartość z adresu nie może trafić tam niesprawdzona."""
    try:
        days = int(value)
    except (TypeError, ValueError):
        return None
    return days if days in (30, 90, 180) else None
