"""Zdalny serwer MCP (Model Context Protocol) do sterowania CRM z aplikacji Claude
(np. z telefonu, głosowo). Udostępnia operacje Create/Read/Update (bez Delete) na
firmach, kontaktach, notatkach i zadaniach oraz na deal'ach.

Serwer działa w tym samym procesie co aplikacja Flask (patrz passenger_wsgi.py) —
każde wywołanie narzędzia otwiera kontekst aplikacji Flask (app_context), żeby
modele mogły korzystać ze wspólnego database.get_db().

Autoryzacja: prosty token statyczny wpięty w sam adres URL, którym mocowany jest
ten serwer (patrz passenger_wsgi.py) — patrz Config.MCP_TOKEN i Config.MCP_USER_ID.
"""
from __future__ import annotations

import asyncio
import threading
from typing import Literal

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from app import app as flask_app
from config import Config
import models.crm_company as crm_company
import models.crm_contact as crm_contact
import models.crm_deal as crm_deal
import models.crm_notes as crm_notes
import models.task as task_model

mcp = FastMCP(
    "trustart-crm",
    stateless_http=True,
    json_response=True,
    streamable_http_path="/",
    # Domyślna ochrona przed DNS rebinding zakłada, że serwer stoi pod
    # 127.0.0.1/localhost — u nas stoi pod prawdziwą domeną za Passengerem,
    # a właściwą bramką dostępu i tak jest sekretny token w adresie URL
    # (patrz passenger_wsgi.py), więc wyłączamy tu tę dodatkową walidację
    # nagłówka Host, żeby uniknąć fałszywych 421 po wdrożeniu.
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)


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


# ── Montowanie pod Passengerem (WSGI) ───────────────────────────────────────

def get_wsgi_app():
    """Zwraca aplikację WSGI serwera MCP, gotową do zamontowania w passenger_wsgi.py.

    StreamableHTTPSessionManager (wewnętrzna grupa zadań MCP) inicjalizuje się
    dopiero w reakcji na zdarzenie ASGI ``lifespan.startup`` — Passenger, jako
    zwykły serwer WSGI, nigdy sam takiego zdarzenia nie wysyła. Dlatego
    uruchamiamy ten protokół ręcznie, raz, przy starcie procesu, na tej samej
    trwałej pętli zdarzeń, na której a2wsgi obsługuje potem każde żądanie.
    """
    from a2wsgi import ASGIMiddleware

    asgi_app = mcp.streamable_http_app()
    wsgi_app = ASGIMiddleware(asgi_app)

    started = threading.Event()
    failure: dict[str, str] = {}

    async def _drive_lifespan_startup():
        receive_queue: asyncio.Queue = asyncio.Queue()
        await receive_queue.put({"type": "lifespan.startup"})

        async def receive():
            return await receive_queue.get()

        async def send(message):
            if message["type"] == "lifespan.startup.complete":
                started.set()
            elif message["type"] == "lifespan.startup.failed":
                failure["message"] = message.get("message", "nieznany błąd")
                started.set()

        # Ten call nie wraca aż do lifespan.shutdown — zostaje jako zadanie w tle.
        await asgi_app({"type": "lifespan"}, receive, send)

    asyncio.run_coroutine_threadsafe(_drive_lifespan_startup(), wsgi_app.loop)
    if not started.wait(timeout=10):
        raise RuntimeError("Serwer MCP nie wystartował w ciągu 10s (brak lifespan.startup.complete).")
    if failure:
        raise RuntimeError(f"Serwer MCP nie wystartował: {failure['message']}")

    return wsgi_app
