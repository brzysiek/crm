"""Zdalny serwer MCP (Model Context Protocol) do sterowania CRM z aplikacji Claude
(np. z telefonu, głosowo). Udostępnia operacje Create/Read/Update (bez trwałego
Delete) na firmach, kontaktach, notatkach, zadaniach, deal'ach oraz ofertach M&A,
a także archiwizowanie/przywracanie zadań, projektów, deali i ofert M&A — wszystkie
cztery mają w bazie odwracalny soft-delete przez kolumnę deleted_at.

Serwer działa w tym samym procesie co aplikacja Flask (patrz passenger_wsgi.py) —
każde wywołanie narzędzia otwiera kontekst aplikacji Flask (app_context), żeby
modele mogły korzystać ze wspólnego database.get_db().

Autoryzacja: prosty token statyczny wpięty w sam adres URL, którym mocowany jest
ten serwer (patrz passenger_wsgi.py) — patrz Config.MCP_TOKEN i Config.MCP_USER_ID.
"""
from __future__ import annotations

import asyncio
import json
from typing import Literal

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
import mcp.types as types

from app import app as flask_app
from config import Config
import models.crm_company as crm_company
import models.crm_contact as crm_contact
import models.crm_deal as crm_deal
import models.crm_mna_offer as crm_mna_offer
import models.crm_notes as crm_notes
import models.reconciliation as reconciliation
import models.task as task_model

# Używamy FastMCP wyłącznie jako rejestru narzędzi (dekorator @mcp.tool(),
# generowanie schematów, walidacja argumentów) — transport HTTP obsługujemy
# sami, niżej, jako zwykłą funkcję WSGI, więc opcje transportu ASGI
# (stateless_http, json_response, streamable_http_path, transport_security)
# tu nie mają zastosowania.
mcp = FastMCP("trustart-crm")


def _mcp_user_id() -> int:
    return getattr(Config, "MCP_USER_ID", 1)


# ── Firmy ──────────────────────────────────────────────────────────────────

@mcp.tool()
def find_company(query: str) -> list[dict]:
    """Szuka firm po nazwie, NIP-ie lub mieście. Zwraca listę pasujących firm."""
    with flask_app.app_context():
        return crm_company.search_companies(query)


@mcp.tool()
def get_company(company_id: int) -> dict:
    """Zwraca pełne dane firmy o podanym id."""
    with flask_app.app_context():
        row = crm_company.get_company_by_id(company_id)
        if not row:
            raise ValueError(f"Nie znaleziono firmy o id={company_id}.")
        return row


@mcp.tool()
def create_company(
    name: str,
    city: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    website: str | None = None,
    nip: str | None = None,
    description: str | None = None,
    relation_type: Literal["lead", "client", "partner", "inne", "dostawca"] | None = None,
) -> dict:
    """Tworzy nową firmę. Wymagana jest tylko nazwa."""
    with flask_app.app_context():
        data = {
            "name": name, "city": city, "phone": phone, "email": email,
            "website": website, "nip": nip, "description": description,
            "relation_type": relation_type,
        }
        data = {k: v for k, v in data.items() if v is not None}
        company_id = crm_company.create_company(data, _mcp_user_id())
        return crm_company.get_company_by_id(company_id)


@mcp.tool()
def update_company(
    company_id: int,
    name: str | None = None,
    city: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    website: str | None = None,
    nip: str | None = None,
    description: str | None = None,
    relation_type: Literal["lead", "client", "partner", "inne", "dostawca"] | None = None,
) -> dict:
    """Aktualizuje wybrane pola firmy. Podaj tylko te pola, które mają się zmienić."""
    with flask_app.app_context():
        current = crm_company.get_company_by_id(company_id)
        if not current:
            raise ValueError(f"Nie znaleziono firmy o id={company_id}.")
        updates = {
            "name": name, "city": city, "phone": phone, "email": email,
            "website": website, "nip": nip, "description": description,
            "relation_type": relation_type,
        }
        data = {**current, **{k: v for k, v in updates.items() if v is not None}}
        crm_company.update_company(company_id, data, _mcp_user_id())
        return crm_company.get_company_by_id(company_id)


# ── Kontakty ───────────────────────────────────────────────────────────────

@mcp.tool()
def find_contact(query: str, company_id: int | None = None) -> list[dict]:
    """Szuka kontaktów po imieniu/nazwisku/emailu, opcjonalnie w obrębie jednej firmy."""
    with flask_app.app_context():
        return crm_contact.search_contacts(query, company_id=company_id)


@mcp.tool()
def get_contact(contact_id: int) -> dict:
    """Zwraca pełne dane kontaktu (w tym telefon, email) po id."""
    with flask_app.app_context():
        row = crm_contact.get_contact_by_id(contact_id)
        if not row:
            raise ValueError(f"Nie znaleziono kontaktu o id={contact_id}.")
        return row


@mcp.tool()
def create_contact(
    first_name: str,
    last_name: str,
    company_id: int | None = None,
    position: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    description: str | None = None,
) -> dict:
    """Tworzy nowy kontakt. Wymagane są imię i nazwisko."""
    with flask_app.app_context():
        data = {
            "first_name": first_name, "last_name": last_name, "company_id": company_id,
            "position": position, "email": email, "phone": phone, "description": description,
        }
        data = {k: v for k, v in data.items() if v is not None}
        contact_id = crm_contact.create_contact(data, _mcp_user_id())
        return crm_contact.get_contact_by_id(contact_id)


@mcp.tool()
def update_contact(
    contact_id: int,
    first_name: str | None = None,
    last_name: str | None = None,
    company_id: int | None = None,
    position: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    description: str | None = None,
) -> dict:
    """Aktualizuje wybrane pola kontaktu. Podaj tylko te pola, które mają się zmienić."""
    with flask_app.app_context():
        current = crm_contact.get_contact_by_id(contact_id)
        if not current:
            raise ValueError(f"Nie znaleziono kontaktu o id={contact_id}.")
        updates = {
            "first_name": first_name, "last_name": last_name, "company_id": company_id,
            "position": position, "email": email, "phone": phone, "description": description,
        }
        data = {**current, **{k: v for k, v in updates.items() if v is not None}}
        crm_contact.update_contact(contact_id, data, _mcp_user_id())
        return crm_contact.get_contact_by_id(contact_id)


# ── Notatki (firmy/kontakty) ────────────────────────────────────────────────

@mcp.tool()
def add_note(
    entity_type: Literal["company", "contact"],
    entity_id: int,
    body: str,
    note_type: Literal["phone", "meeting", "task", "other"] = "other",
) -> dict:
    """Dodaje notatkę do firmy lub kontaktu."""
    with flask_app.app_context():
        note_id = crm_notes.add_note(entity_type, entity_id, _mcp_user_id(), body, note_type)
        return crm_notes.get_note_by_id(note_id)


@mcp.tool()
def list_notes(entity_type: Literal["company", "contact"], entity_id: int) -> list[dict]:
    """Zwraca listę notatek dla firmy lub kontaktu."""
    with flask_app.app_context():
        return crm_notes.get_notes(entity_type, entity_id)


@mcp.tool()
def update_note(note_id: int, body: str, note_type: Literal["phone", "meeting", "task", "other"] | None = None) -> dict:
    """Edytuje treść (i opcjonalnie typ) istniejącej notatki."""
    with flask_app.app_context():
        if not crm_notes.get_note_by_id(note_id):
            raise ValueError(f"Nie znaleziono notatki o id={note_id}.")
        crm_notes.update_note(note_id, body, note_type)
        return crm_notes.get_note_by_id(note_id)


# ── Zadania ────────────────────────────────────────────────────────────────

@mcp.tool()
def find_tasks(
    search: str | None = None,
    company_id: int | None = None,
    contact_id: int | None = None,
    deal_id: int | None = None,
    include_done: bool = False,
) -> list[dict]:
    """Szuka zadań (next actions), opcjonalnie po tytule i/lub powiązanej firmie/kontakcie/deal'u."""
    with flask_app.app_context():
        return task_model.get_next_actions(
            company_id=company_id, contact_id=contact_id, deal_id=deal_id,
            search=search, include_done=include_done,
        )


@mcp.tool()
def get_task(task_id: int) -> dict:
    """Zwraca pełne dane zadania po id."""
    with flask_app.app_context():
        row = task_model.get_task(task_id)
        if not row:
            raise ValueError(f"Nie znaleziono zadania o id={task_id}.")
        return row


@mcp.tool()
def create_task(
    title: str,
    due_date: str | None = None,
    notes: str | None = None,
    company_id: int | None = None,
    contact_id: int | None = None,
    deal_id: int | None = None,
    status: Literal["inbox", "next", "waiting", "someday"] = "inbox",
) -> dict:
    """Tworzy nowe zadanie, opcjonalnie powiązane z firmą/kontaktem/deal'em i z terminem.
    due_date w formacie RRRR-MM-DD."""
    with flask_app.app_context():
        task_id = task_model.create_task(
            title, _mcp_user_id(), status=status, due_date=due_date, notes=notes,
            crm_company_id=company_id, crm_contact_id=contact_id, crm_deal_id=deal_id,
        )
        return task_model.get_task(task_id)


@mcp.tool()
def update_task(
    task_id: int,
    title: str | None = None,
    notes: str | None = None,
    status: Literal["inbox", "next", "waiting", "someday", "done"] | None = None,
    due_date: str | None = None,
    scheduled_date: str | None = None,
    scheduled_time: str | None = None,
    company_id: int | None = None,
    contact_id: int | None = None,
    deal_id: int | None = None,
) -> dict:
    """Aktualizuje wybrane pola zadania. Podaj tylko te pola, które mają się zmienić."""
    with flask_app.app_context():
        if not task_model.get_task(task_id):
            raise ValueError(f"Nie znaleziono zadania o id={task_id}.")
        data = {
            "title": title, "notes": notes, "status": status, "due_date": due_date,
            "scheduled_date": scheduled_date, "scheduled_time": scheduled_time,
            "crm_company_id": company_id, "crm_contact_id": contact_id, "crm_deal_id": deal_id,
        }
        data = {k: v for k, v in data.items() if v is not None}
        task_model.update_task(task_id, data)
        return task_model.get_task(task_id)


@mcp.tool()
def archive_task(task_id: int) -> dict:
    """Archiwizuje zadanie lub projekt (soft-delete, odwracalne przez restore_task).
    Działa zarówno na pojedynczych zadaniach, jak i na projektach — to ten sam obiekt w bazie."""
    with flask_app.app_context():
        if not task_model.get_task(task_id):
            raise ValueError(f"Nie znaleziono zadania/projektu o id={task_id}.")
        task_model.delete_task(task_id)
        return task_model.get_task(task_id)


@mcp.tool()
def restore_task(task_id: int) -> dict:
    """Przywraca wcześniej zarchiwizowane zadanie lub projekt."""
    with flask_app.app_context():
        if not task_model.get_task(task_id):
            raise ValueError(f"Nie znaleziono zadania/projektu o id={task_id}.")
        task_model.restore_task(task_id)
        return task_model.get_task(task_id)


# ── Deale ──────────────────────────────────────────────────────────────────

@mcp.tool()
def find_deals(
    search: str | None = None,
    company_id: int | None = None,
    contact_id: int | None = None,
    stage: str | None = None,
) -> list[dict]:
    """Szuka deali (interesów), opcjonalnie po nazwie i/lub firmie/kontakcie/etapie.
    Etapy: new, in_progress, won, in_delivery, completed, someday, lost, unqualified."""
    with flask_app.app_context():
        return crm_deal.get_all_deals(search=search, company_id=company_id,
                                       contact_id=contact_id, stage=stage)


@mcp.tool()
def get_deal(deal_id: int) -> dict:
    """Zwraca pełne dane deala (interesu) po id."""
    with flask_app.app_context():
        row = crm_deal.get_deal_by_id(deal_id)
        if not row:
            raise ValueError(f"Nie znaleziono deala o id={deal_id}.")
        return row


@mcp.tool()
def create_deal(
    name: str,
    company_id: int | None = None,
    contact_id: int | None = None,
    amount: float | None = None,
    stage: str | None = None,
    deal_type: Literal["szkolenie", "ma", "warsztaty", "prowizja", "partnerstwo", "inne"] | None = None,
    description: str | None = None,
) -> dict:
    """Tworzy nowy deal (interes). Wymagana jest tylko nazwa."""
    with flask_app.app_context():
        data = {
            "name": name, "company_id": company_id, "contact_id": contact_id,
            "amount": amount, "stage": stage, "deal_type": deal_type, "description": description,
        }
        data = {k: v for k, v in data.items() if v is not None}
        deal_id = crm_deal.create_deal(data, _mcp_user_id())
        return crm_deal.get_deal_by_id(deal_id)


@mcp.tool()
def update_deal(
    deal_id: int,
    name: str | None = None,
    company_id: int | None = None,
    contact_id: int | None = None,
    amount: float | None = None,
    stage: str | None = None,
    deal_type: Literal["szkolenie", "ma", "warsztaty", "prowizja", "partnerstwo", "inne"] | None = None,
    description: str | None = None,
) -> dict:
    """Aktualizuje wybrane pola deala (interesu). Podaj tylko te pola, które mają się zmienić."""
    with flask_app.app_context():
        current = crm_deal.get_deal_by_id(deal_id)
        if not current:
            raise ValueError(f"Nie znaleziono deala o id={deal_id}.")
        updates = {
            "name": name, "company_id": company_id, "contact_id": contact_id,
            "amount": amount, "stage": stage, "deal_type": deal_type, "description": description,
        }
        data = {**current, **{k: v for k, v in updates.items() if v is not None}}
        crm_deal.update_deal(deal_id, data, _mcp_user_id())
        return crm_deal.get_deal_by_id(deal_id)


@mcp.tool()
def archive_deal(deal_id: int) -> dict:
    """Archiwizuje deal (soft-delete, odwracalne przez restore_deal)."""
    with flask_app.app_context():
        if not crm_deal.get_deal_by_id(deal_id):
            raise ValueError(f"Nie znaleziono deala o id={deal_id}.")
        crm_deal.delete_deal(deal_id, _mcp_user_id())
        return crm_deal.get_deal_by_id(deal_id)


@mcp.tool()
def restore_deal(deal_id: int) -> dict:
    """Przywraca wcześniej zarchiwizowany deal."""
    with flask_app.app_context():
        if not crm_deal.get_deal_by_id(deal_id):
            raise ValueError(f"Nie znaleziono deala o id={deal_id}.")
        crm_deal.restore_deal(deal_id, _mcp_user_id())
        return crm_deal.get_deal_by_id(deal_id)


# ── Oferty M&A ─────────────────────────────────────────────────────────────

@mcp.tool()
def find_mna_offers(
    offer_type: Literal["for_sale", "wanted"] | None = None,
    search: str | None = None,
) -> list[dict]:
    """Szuka ofert M&A (firmy na sprzedaż / firmy poszukiwane), opcjonalnie po
    typie oferty i/lub tekście (nazwa, opis, branża)."""
    with flask_app.app_context():
        return crm_mna_offer.get_all_mna_offers(offer_type=offer_type, search=search)


@mcp.tool()
def get_mna_offer(offer_id: int) -> dict:
    """Zwraca pełne dane oferty M&A po id."""
    with flask_app.app_context():
        row = crm_mna_offer.get_mna_offer_by_id(offer_id)
        if not row:
            raise ValueError(f"Nie znaleziono oferty M&A o id={offer_id}.")
        return row


@mcp.tool()
def create_mna_offer(
    name: str,
    offer_type: Literal["for_sale", "wanted"] = "for_sale",
    description: str | None = None,
    industry: str | None = None,
    revenue: float | None = None,
    ebitda: float | None = None,
    target_company_id: int | None = None,
    target_contact_id: int | None = None,
    source_company_id: int | None = None,
    source_contact_id: int | None = None,
) -> dict:
    """Tworzy nową ofertę M&A (firma na sprzedaż lub poszukiwana). Wymagana jest
    tylko nazwa. target_* to firma/kontakt, której dotyczy oferta; source_* to
    firma/kontakt będący źródłem oferty."""
    with flask_app.app_context():
        data = {
            "name": name, "offer_type": offer_type, "description": description,
            "industry": industry, "revenue": revenue, "ebitda": ebitda,
            "target_company_id": target_company_id, "target_contact_id": target_contact_id,
            "source_company_id": source_company_id, "source_contact_id": source_contact_id,
        }
        data = {k: v for k, v in data.items() if v is not None}
        offer_id = crm_mna_offer.create_mna_offer(data, _mcp_user_id())
        return crm_mna_offer.get_mna_offer_by_id(offer_id)


@mcp.tool()
def update_mna_offer(
    offer_id: int,
    name: str | None = None,
    offer_type: Literal["for_sale", "wanted"] | None = None,
    description: str | None = None,
    industry: str | None = None,
    revenue: float | None = None,
    ebitda: float | None = None,
    target_company_id: int | None = None,
    target_contact_id: int | None = None,
    source_company_id: int | None = None,
    source_contact_id: int | None = None,
) -> dict:
    """Aktualizuje wybrane pola oferty M&A. Podaj tylko te pola, które mają się zmienić."""
    with flask_app.app_context():
        current = crm_mna_offer.get_mna_offer_by_id(offer_id)
        if not current:
            raise ValueError(f"Nie znaleziono oferty M&A o id={offer_id}.")
        updates = {
            "name": name, "offer_type": offer_type, "description": description,
            "industry": industry, "revenue": revenue, "ebitda": ebitda,
            "target_company_id": target_company_id, "target_contact_id": target_contact_id,
            "source_company_id": source_company_id, "source_contact_id": source_contact_id,
        }
        data = {**current, **{k: v for k, v in updates.items() if v is not None}}
        crm_mna_offer.update_mna_offer(offer_id, data, _mcp_user_id())
        return crm_mna_offer.get_mna_offer_by_id(offer_id)


@mcp.tool()
def archive_mna_offer(offer_id: int) -> dict:
    """Archiwizuje ofertę M&A (soft-delete, odwracalne przez restore_mna_offer)."""
    with flask_app.app_context():
        if not crm_mna_offer.get_mna_offer_by_id(offer_id):
            raise ValueError(f"Nie znaleziono oferty M&A o id={offer_id}.")
        crm_mna_offer.delete_mna_offer(offer_id, _mcp_user_id())
        return crm_mna_offer.get_mna_offer_by_id(offer_id)


@mcp.tool()
def restore_mna_offer(offer_id: int) -> dict:
    """Przywraca wcześniej zarchiwizowaną ofertę M&A."""
    with flask_app.app_context():
        if not crm_mna_offer.get_mna_offer_by_id(offer_id):
            raise ValueError(f"Nie znaleziono oferty M&A o id={offer_id}.")
        crm_mna_offer.restore_mna_offer(offer_id, _mcp_user_id())
        return crm_mna_offer.get_mna_offer_by_id(offer_id)


# ── Uzgadnianie (finanse ↔ bank) ─────────────────────────────────────────────

@mcp.tool()
def reconciliation_summary() -> dict:
    """Zwraca liczby niepowiązanych pozycji po obu stronach uzgodnień:
    transakcje bankowe bez pary, wydatki/przychody bez pełnej płatności oraz
    dokumenty (Fakturownia/Dysk) czekające na przypisanie."""
    with flask_app.app_context():
        return reconciliation.summary()


@mcp.tool()
def list_unmatched_bank_transactions(kind: Literal["expense", "income"] | None = None) -> list[dict]:
    """Lista transakcji bankowych bez powiązania z wydatkiem/przychodem
    (status='pending'). kind='expense' — tylko wypływy (kwota ujemna),
    kind='income' — tylko wpływy (kwota dodatnia), brak — wszystkie."""
    with flask_app.app_context():
        return reconciliation.get_unmatched_bank_transactions(kind)


@mcp.tool()
def list_unmatched_records(record_type: Literal["expense", "income"]) -> list[dict]:
    """Lista wydatków lub przychodów bez pełnego pokrycia w transakcjach
    bankowych (wydatek: payment_percent < 100; przychód: payment_status != 'paid').
    Każdy rekord zawiera matched_amount — sumę już powiązanych kwot."""
    with flask_app.app_context():
        if record_type == "expense":
            return reconciliation.get_unmatched_expense_records()
        return reconciliation.get_unmatched_income_records()


@mcp.tool()
def list_pending_documents(kind: Literal["expense", "income"] | None = None) -> list[dict]:
    """Lista dokumentów (faktur z Fakturowni/Dysku Google) oczekujących na
    przypisanie do wydatku/przychodu (status='pending'). Wyłącznie do wglądu —
    do faktycznego przypisania służą istniejące narzędzia importu w aplikacji web."""
    with flask_app.app_context():
        return reconciliation.get_pending_documents(kind)


@mcp.tool()
def suggest_matches_for_document(source: Literal["fakturownia", "gdrive"], doc_id: int) -> list[dict]:
    """Sugeruje najlepiej pasujące niepowiązane transakcje bankowe dla danego
    oczekującego dokumentu (faktury). Zwraca listę {transaction, score}
    posortowaną wg trafności. Wyłącznie do wglądu."""
    with flask_app.app_context():
        return reconciliation.get_candidates_for_document(source, doc_id)


@mcp.tool()
def suggest_matches_for_transaction(bank_txn_id: int) -> list[dict]:
    """Sugeruje najlepiej pasujące niepokryte wydatki/przychody dla danej
    transakcji bankowej (dopasowanie po kwocie, numerze faktury, kontrahencie).
    Zwraca listę {record_type, record, score, remaining} posortowaną wg trafności."""
    with flask_app.app_context():
        return reconciliation.get_candidates_for_transaction(bank_txn_id)


@mcp.tool()
def suggest_matches_for_record(record_type: Literal["expense", "income"], record_id: int) -> list[dict]:
    """Sugeruje najlepiej pasujące niepowiązane transakcje bankowe dla danego
    wydatku/przychodu. Zwraca listę {transaction, score} posortowaną wg trafności."""
    with flask_app.app_context():
        return reconciliation.get_candidates_for_record(record_type, record_id)


@mcp.tool()
def link_transaction_to_record(record_type: Literal["expense", "income"], record_id: int, bank_txn_id: int) -> dict:
    """Łączy transakcję bankową z wydatkiem/przychodem. Dla wydatku przelicza
    automatycznie payment_percent; dla przychodu, jeśli suma powiązanych
    transakcji pokryje pełną kwotę brutto, oznacza go jako opłacony."""
    with flask_app.app_context():
        return reconciliation.link(record_type, record_id, bank_txn_id)


@mcp.tool()
def unlink_transaction_from_record(record_type: Literal["expense", "income"], record_id: int, bank_txn_id: int) -> dict:
    """Usuwa powiązanie transakcji bankowej z wydatkiem/przychodem (odwraca
    link_transaction_to_record)."""
    with flask_app.app_context():
        return reconciliation.unlink(record_type, record_id, bank_txn_id)


# ── Montowanie pod Passengerem (WSGI) ───────────────────────────────────────
#
# Passenger obsługuje wyłącznie WSGI (synchronicznie, proces/wątek na żądanie),
# więc zamiast montować pełny serwer ASGI biblioteki `mcp` (który wymaga
# zdarzenia lifespan.startup i własnej, trwałej pętli asyncio w tle —
# rozwiązanie kruche pod realnym modelem procesów/wątków Passengera i
# odpowiedzialne za wcześniejszą awarię produkcyjną), obsługujemy protokół
# Streamable HTTP MCP ręcznie, w pełni synchronicznie: każde żądanie parsuje
# JSON-RPC, woła narzędzie przez krótkotrwałą pętlę asyncio.run(...) (tworzoną
# i niszczoną w ramach jednego wywołania) i od razu zwraca odpowiedź WSGI.
# Brak wątków w tle, brak wspólnego stanu między żądaniami, brak czegokolwiek,
# co mogłoby zawiesić proces roboczy Passengera.

def _list_tools_sync() -> list[dict]:
    tools = asyncio.run(mcp.list_tools())
    return [t.model_dump(by_alias=True, exclude_none=True, mode="json") for t in tools]


def _call_tool_sync(name: str, arguments: dict) -> dict:
    try:
        result = asyncio.run(
            mcp._tool_manager.call_tool(name, arguments or {}, context=mcp.get_context(), convert_result=False)
        )
    except ToolError as e:
        return {"content": [{"type": "text", "text": str(e)}], "isError": True}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Błąd: {e}"}], "isError": True}
    text = json.dumps(result, ensure_ascii=False, default=str)
    return {"content": [{"type": "text", "text": text}]}


def _handle_jsonrpc(payload: dict) -> dict | None:
    """Obsługuje jedno żądanie/powiadomienie JSON-RPC 2.0. Zwraca None dla
    powiadomień (brak pola "id") — zgodnie z protokołem nie dostają odpowiedzi."""
    if not isinstance(payload, dict):
        return {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Nieprawidłowe żądanie"}}

    method = payload.get("method")
    has_id = "id" in payload
    msg_id = payload.get("id")

    def ok(result):
        return {"jsonrpc": "2.0", "id": msg_id, "result": result} if has_id else None

    def err(code, message):
        return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}} if has_id else None

    try:
        if method == "initialize":
            opts = mcp._mcp_server.create_initialization_options()
            return ok({
                "protocolVersion": types.LATEST_PROTOCOL_VERSION,
                "capabilities": opts.capabilities.model_dump(by_alias=True, exclude_none=True, mode="json"),
                "serverInfo": {"name": opts.server_name, "version": opts.server_version},
            })
        if method in ("notifications/initialized", "notifications/cancelled"):
            return None
        if method == "ping":
            return ok({})
        if method == "tools/list":
            return ok({"tools": _list_tools_sync()})
        if method == "tools/call":
            params = payload.get("params") or {}
            name = params.get("name")
            arguments = params.get("arguments") or {}
            with flask_app.app_context():
                return ok(_call_tool_sync(name, arguments))
        return err(-32601, f"Nieznana metoda: {method}")
    except Exception as e:
        return err(-32603, f"Błąd wewnętrzny: {e}")


def wsgi_app(environ, start_response):
    """Prosta, synchroniczna aplikacja WSGI obsługująca Streamable HTTP MCP
    (tylko tryb odpowiedzi JSON — bez SSE, zgodnie z json_response=True)."""
    from werkzeug.wrappers import Request, Response

    request = Request(environ)

    if request.method != "POST":
        response = Response(status=405)
        return response(environ, start_response)

    try:
        payload = json.loads(request.get_data() or b"{}")
    except ValueError:
        body = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Błąd parsowania JSON"}}
        response = Response(json.dumps(body), status=400, mimetype="application/json")
        return response(environ, start_response)

    if isinstance(payload, list):
        results = [r for r in (_handle_jsonrpc(item) for item in payload) if r is not None]
        response = Response(status=202) if not results else Response(
            json.dumps(results, ensure_ascii=False), mimetype="application/json"
        )
    else:
        result = _handle_jsonrpc(payload)
        response = Response(status=202) if result is None else Response(
            json.dumps(result, ensure_ascii=False), mimetype="application/json"
        )

    return response(environ, start_response)
