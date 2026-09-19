"""Zdalny serwer MCP (Model Context Protocol) do sterowania CRM z aplikacji Claude
(np. z telefonu, głosowo). Udostępnia operacje Create/Read/Update (bez trwałego
Delete) na firmach, kontaktach, notatkach, zadaniach, deal'ach oraz ofertach M&A,
a także archiwizowanie/przywracanie zadań, projektów, deali i ofert M&A — wszystkie
cztery mają w bazie odwracalny soft-delete przez kolumnę deleted_at.

Moduł M&A ma też własne, osobne od CRM-owych firmy/kontakty/deale (long lista/
short lista) — mna_company/mna_contact/mna_deal, z takim samym archiwizowaniem/
przywracaniem (kolumna archived_at) oraz zarządzaniem pozycjami na long/short
liście danego deala M&A (mna_deal_targets). Firmy i kontakty M&A mają też własne
tagi (mna_tags) — osobna pula od tagów CRM, nie są ze sobą współdzielone.

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
import models.gtd_context as gtd_context
import models.mna_company as mna_company
import models.mna_contact as mna_contact
import models.mna_deal as mna_deal
import models.mna_tags as mna_tags
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


# ── Wzbogacanie danych firmy ze strony WWW ───────────────────────────────────

@mcp.tool()
def scrape_company_website(url: str) -> dict:
    """Wchodzi na podaną stronę WWW firmy (stronę główną i, jeśli ją znajdzie, stronę kontaktową),
    a następnie przez Gemini wyciąga z treści: opis działalności, do 3 branż, email, telefon, NIP
    i adres siedziby. Działa dla dowolnej firmy (CRM lub M&A) — zwraca tylko dane, nic nie zapisuje;
    do zapisania wyniku użyj update_company / update_mna_company z odpowiednimi polami.
    Wymaga skonfigurowanego klucza API Gemini w Ustawieniach ogólnych — jeśli go brak, zwraca błąd."""
    with flask_app.app_context():
        from models.settings import get_setting
        from services.company_profile import build_company_profile

        api_key = get_setting('gemini_api_key', '')
        model = get_setting('gemini_model', 'gemini-2.5-flash')
        return build_company_profile(url, api_key, model)


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
#
# Model danych GTD: projekt to zwykły wiersz tabeli tasks z is_project=1. Zadania projektu
# to wiersze z parent_id wskazującym na projekt (jeden poziom zagnieżdżenia — projekt nie ma
# rodzica). deal_id to osobne powiązanie z dealem CRM i nie służy do grupowania w projekty.

_STATUSES = ("inbox", "next", "waiting", "someday", "done")


def _compact_task(row: dict) -> dict:
    return {
        "id": row["id"], "title": row["title"], "status": row["status"],
        "parent_id": row["parent_id"], "is_project": bool(row["is_project"]),
        "context_name": row.get("context_name"),
    }


def _task_response(task_id: int, verbose: bool) -> dict:
    row = task_model.get_task(task_id)
    return row if verbose else _compact_task(row)


def _require_project(parent_id: int) -> None:
    parent = task_model.get_task(parent_id)
    if not parent or parent.get("deleted_at"):
        raise ValueError(f"Nie znaleziono projektu o id={parent_id}.")
    if not parent["is_project"]:
        raise ValueError(
            f"Zadanie id={parent_id} nie jest projektem (is_project=0) — nie można pod nie podpinać zadań."
        )


def _require_no_cycle(task_id: int, parent_id: int) -> None:
    """Sprawdza, że task_id nie jest przodkiem (ani samym) nowego rodzica."""
    seen: set[int] = set()
    current: int | None = parent_id
    while current and current not in seen:
        if current == task_id:
            raise ValueError(f"Zadanie id={task_id} nie może być własnym przodkiem (cykl w parent_id).")
        seen.add(current)
        row = task_model.get_task(current)
        current = row["parent_id"] if row else None


def _require_context(context_id: int) -> None:
    if not gtd_context.get_context(context_id):
        raise ValueError(f"Nie znaleziono kontekstu o id={context_id} (patrz list_contexts).")


def _validate_hierarchy(task: dict | None, parent_id: int | None, is_project: bool | None) -> None:
    """Walidacja parent_id/is_project dla create (task=None) i update (task=bieżący rekord).
    parent_id: None = bez zmian, 0 = odepnij, >0 = podepnij pod projekt."""
    currently_project = bool(task and task["is_project"])
    will_be_project = currently_project if is_project is None else is_project
    if parent_id is None:
        will_have_parent = bool(task and task["parent_id"])
    else:
        will_have_parent = parent_id > 0

    if will_be_project and will_have_parent:
        if parent_id:
            raise ValueError("Projekt (is_project=true) nie może mieć parent_id — projekty nie są zagnieżdżane.")
        raise ValueError(
            f"Zadanie id={task['id']} jest podpięte pod projekt id={task['parent_id']} — "
            "żeby zrobić z niego projekt, odepnij je w tym samym wywołaniu (parent_id=0)."
        )
    if parent_id:
        if task:
            _require_no_cycle(task["id"], parent_id)
        _require_project(parent_id)
    if task and currently_project and is_project is False:
        subtasks = task_model.get_project_subtasks(task["id"])
        if subtasks:
            raise ValueError(
                f"Projekt id={task['id']} ma {len(subtasks)} zadań — przepnij je lub odepnij "
                "(update_task z parent_id), zanim zmienisz go w zwykłe zadanie."
            )


@mcp.tool()
def find_tasks(
    search: str | None = None,
    company_id: int | None = None,
    contact_id: int | None = None,
    deal_id: int | None = None,
    include_done: bool = False,
    only_projects: bool = False,
    parent_id: int | None = None,
    context_id: int | None = None,
    status: Literal["inbox", "next", "waiting", "someday", "done"] | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """Szuka zadań i projektów. Model danych: projekt = zadanie z is_project=1; zadania projektu =
    zadania z parent_id wskazującym na projekt. deal_id to powiązanie z dealem CRM — nie służy
    do grupowania w projekty.

    - parent_id: zadania danego projektu (podstawowy sposób czytania kolejki projektu), w kolejności:
      aktywne, czekające, zrobione; w grupie wg terminu. Pełny stan projektu naraz: get_project.
    - only_projects=True: tylko projekty (np. znalezienie projektu po nazwie przez search).
    - status: filtr po statusie. Bez niego: przy parent_id/only_projects wszystkie statusy poza done,
      w pozostałych przypadkach tylko next actions; include_done=True dokłada done.
    - context_id: filtr po kontekście GTD (lista: list_contexts).
    - limit/offset: stronicowanie (max 500 na stronę)."""
    with flask_app.app_context():
        return task_model.find_tasks(
            search=search, company_id=company_id, contact_id=contact_id, deal_id=deal_id,
            parent_id=parent_id, context_id=context_id, status=status,
            only_projects=only_projects, include_done=include_done,
            limit=max(1, min(limit, 500)), offset=max(0, offset),
        )


@mcp.tool()
def get_project(project_id: int, include_done_tasks: bool = False, verbose: bool = False) -> dict:
    """Zwraca w jednym wywołaniu stan projektu GTD: dane projektu (zadanie z is_project=1), jego zadania
    (zadania z parent_id=project_id) pogrupowane po statusie oraz liczniki per status.
    Liczniki obejmują zawsze wszystkie zadania; lista „done” jest wypełniana tylko przy
    include_done_tasks=True. verbose=True zwraca pełne rekordy zadań zamiast skróconych."""
    with flask_app.app_context():
        project = task_model.get_task(project_id)
        if not project:
            raise ValueError(f"Nie znaleziono projektu o id={project_id}.")
        if not project["is_project"]:
            raise ValueError(f"Zadanie id={project_id} nie jest projektem (is_project=0).")
        subtasks = task_model.get_project_subtasks(project_id)
        counts = {s: 0 for s in _STATUSES}
        tasks: dict[str, list[dict]] = {s: [] for s in _STATUSES}
        for row in subtasks:
            counts[row["status"]] = counts.get(row["status"], 0) + 1
            if row["status"] == "done" and not include_done_tasks:
                continue
            tasks.setdefault(row["status"], []).append(row if verbose else {
                "id": row["id"], "title": row["title"], "due_date": row["due_date"],
                "scheduled_date": row["scheduled_date"], "waiting_on": row["waiting_on"],
                "is_important": bool(row["is_important"]), "context_name": row.get("context_name"),
            })
        counts["total"] = len(subtasks)
        return {"project": project, "counts": counts, "tasks": tasks}


@mcp.tool()
def list_contexts() -> list[dict]:
    """Zwraca listę kontekstów GTD (id, nazwa, czy domyślny) — do użycia jako context_id w zadaniach."""
    with flask_app.app_context():
        return [
            {"id": c["id"], "name": c["name"], "is_default": bool(c.get("is_default"))}
            for c in gtd_context.get_all_contexts()
        ]


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
    mna_offer_id: int | None = None,
    mna_deal_id: int | None = None,
    status: Literal["inbox", "next", "waiting", "someday"] = "inbox",
    parent_id: int | None = None,
    is_project: bool = False,
    context_id: int | None = None,
    is_important: bool = False,
    verbose: bool = False,
) -> dict:
    """Tworzy nowe zadanie lub projekt. Model danych: projekt = zadanie z is_project=1; zadania projektu =
    zadania z parent_id wskazującym na projekt. deal_id wiąże z dealem CRM i nie służy do grupowania
    w projekty; mna_deal_id to deal M&A (jeszcze inny obiekt).

    - parent_id: podpina zadanie pod projekt (musi istnieć i mieć is_project=1). Zadanie dziedziczy
      po projekcie kontekst i powiązania, o ile nie podano ich wprost.
    - is_project=True: tworzy projekt (nie może mieć parent_id; status inbox zamienia się na next).
    - context_id: kontekst GTD (lista: list_contexts); bez niego dziedziczy się z projektu/deala/
      firmy/kontaktu, a w ostateczności jest brany kontekst domyślny.
    - due_date w formacie RRRR-MM-DD.
    - Domyślnie zwraca skrót {id, title, status, parent_id, is_project, context_name};
      verbose=True zwraca pełny rekord."""
    with flask_app.app_context():
        _validate_hierarchy(None, parent_id, is_project)
        if context_id:
            _require_context(context_id)
        if is_project and status == "inbox":
            status = "next"
        task_id = task_model.create_task(
            title, _mcp_user_id(), is_project=is_project, status=status, due_date=due_date, notes=notes,
            parent_id=parent_id, context_id=context_id, is_important=is_important,
            crm_company_id=company_id, crm_contact_id=contact_id, crm_deal_id=deal_id,
            crm_mna_offer_id=mna_offer_id, crm_mna_deal_id=mna_deal_id,
        )
        return _task_response(task_id, verbose)


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
    mna_offer_id: int | None = None,
    mna_deal_id: int | None = None,
    parent_id: int | None = None,
    is_project: bool | None = None,
    context_id: int | None = None,
    is_important: bool | None = None,
    verbose: bool = False,
) -> dict:
    """Aktualizuje wybrane pola zadania. Podaj tylko te pola, które mają się zmienić.
    Model danych: projekt = zadanie z is_project=1; zadania projektu = zadania z parent_id wskazującym
    na projekt. deal_id wiąże z dealem CRM i nie służy do grupowania w projekty; mna_deal_id to deal M&A.

    - parent_id: przepina zadanie pod inny projekt; parent_id=0 odpina je od projektu. Kontekst
      i powiązania zadania nie zmieniają się przy przepięciu.
    - is_project=True: robi z zadania projekt (zadanie nie może mieć rodzica — odepnij je w tym samym
      wywołaniu przez parent_id=0). is_project=False: cofa projekt do zadania (tylko gdy nie ma zadań).
    - context_id: kontekst GTD (lista: list_contexts).
    - Domyślnie zwraca skrót {id, title, status, parent_id, is_project, context_name};
      verbose=True zwraca pełny rekord."""
    with flask_app.app_context():
        task = task_model.get_task(task_id)
        if not task:
            raise ValueError(f"Nie znaleziono zadania o id={task_id}.")
        _validate_hierarchy(task, parent_id, is_project)
        if context_id:
            _require_context(context_id)
        if is_project is False and task["is_project"]:
            task_model.flatten_project(task_id)
        data = {
            "title": title, "notes": notes, "status": status, "due_date": due_date,
            "scheduled_date": scheduled_date, "scheduled_time": scheduled_time,
            "crm_company_id": company_id, "crm_contact_id": contact_id, "crm_deal_id": deal_id,
            "crm_mna_offer_id": mna_offer_id, "crm_mna_deal_id": mna_deal_id,
            "parent_id": parent_id, "context_id": context_id, "is_important": is_important,
        }
        data = {k: v for k, v in data.items() if v is not None}
        task_model.update_task(task_id, data)
        if is_project and not task["is_project"]:
            task_model.convert_to_project(task_id)
        return _task_response(task_id, verbose)


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


# ── M&A: Firmy (long lista / short lista) ────────────────────────────────────

@mcp.tool()
def find_mna_company(query: str) -> list[dict]:
    """Szuka firm w module M&A (long lista/short lista) po nazwie, NIP-ie lub mieście.
    To osobne firmy od tych w CRM — cele M&A, nie partnerzy/leady/klienci."""
    with flask_app.app_context():
        return mna_company.search_mna_companies(query)


@mcp.tool()
def get_mna_company(company_id: int) -> dict:
    """Zwraca pełne dane firmy z modułu M&A po id."""
    with flask_app.app_context():
        row = mna_company.get_mna_company_by_id(company_id)
        if not row:
            raise ValueError(f"Nie znaleziono firmy M&A o id={company_id}.")
        return row


@mcp.tool()
def create_mna_company(
    name: str,
    short_name: str | None = None,
    city: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    website: str | None = None,
    nip: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
) -> dict:
    """Tworzy nową firmę w module M&A (cel long/short listy). Wymagana jest tylko nazwa.
    Tagi M&A to osobna pula od tagów CRM (nie są współdzielone)."""
    with flask_app.app_context():
        data = {
            "name": name, "short_name": short_name, "city": city, "phone": phone,
            "email": email, "website": website, "nip": nip, "description": description,
        }
        data = {k: v for k, v in data.items() if v is not None}
        company_id = mna_company.create_mna_company(data, _mcp_user_id(), tags=tags)
        return mna_company.get_mna_company_by_id(company_id)


@mcp.tool()
def update_mna_company(
    company_id: int,
    name: str | None = None,
    short_name: str | None = None,
    city: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    website: str | None = None,
    nip: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
) -> dict:
    """Aktualizuje wybrane pola firmy z modułu M&A. Podaj tylko te pola, które mają się zmienić.
    Podanie tags nadpisuje cały zestaw tagów firmy (nie dodaje pojedynczo)."""
    with flask_app.app_context():
        current = mna_company.get_mna_company_by_id(company_id)
        if not current:
            raise ValueError(f"Nie znaleziono firmy M&A o id={company_id}.")
        updates = {
            "name": name, "short_name": short_name, "city": city, "phone": phone,
            "email": email, "website": website, "nip": nip, "description": description,
        }
        data = {**current, **{k: v for k, v in updates.items() if v is not None}}
        mna_company.update_mna_company(company_id, data, _mcp_user_id(), tags=tags)
        return mna_company.get_mna_company_by_id(company_id)


@mcp.tool()
def archive_mna_company(company_id: int) -> dict:
    """Archiwizuje firmę z modułu M&A (soft-delete, odwracalne przez restore_mna_company)."""
    with flask_app.app_context():
        if not mna_company.get_mna_company_by_id(company_id):
            raise ValueError(f"Nie znaleziono firmy M&A o id={company_id}.")
        mna_company.delete_mna_company(company_id, _mcp_user_id())
        return {"id": company_id, "archived": True}


@mcp.tool()
def restore_mna_company(company_id: int) -> dict:
    """Przywraca wcześniej zarchiwizowaną firmę z modułu M&A."""
    with flask_app.app_context():
        if not mna_company.get_mna_company_by_id_any(company_id):
            raise ValueError(f"Nie znaleziono firmy M&A o id={company_id}.")
        mna_company.restore_mna_company(company_id, _mcp_user_id())
        return mna_company.get_mna_company_by_id(company_id)


@mcp.tool()
def get_mna_company_tags(company_id: int) -> list[str]:
    """Zwraca listę tagów przypisanych do firmy M&A. Tagi M&A to osobna pula od tagów CRM."""
    with flask_app.app_context():
        if not mna_company.get_mna_company_by_id(company_id):
            raise ValueError(f"Nie znaleziono firmy M&A o id={company_id}.")
        return mna_tags.get_company_tags(company_id)


@mcp.tool()
def set_mna_company_tags(company_id: int, tags: list[str]) -> list[str]:
    """Nadpisuje cały zestaw tagów firmy M&A podaną listą (tworzy nowe tagi, jeśli nie istnieją)."""
    with flask_app.app_context():
        if not mna_company.get_mna_company_by_id(company_id):
            raise ValueError(f"Nie znaleziono firmy M&A o id={company_id}.")
        mna_tags.set_company_tags(company_id, tags)
        return mna_tags.get_company_tags(company_id)


# ── M&A: Kontakty (long lista / short lista) ─────────────────────────────────

@mcp.tool()
def find_mna_contact(query: str, company_id: int | None = None) -> list[dict]:
    """Szuka kontaktów w module M&A po imieniu/nazwisku/emailu, opcjonalnie w obrębie jednej firmy M&A."""
    with flask_app.app_context():
        return mna_contact.search_mna_contacts(query)


@mcp.tool()
def get_mna_contact(contact_id: int) -> dict:
    """Zwraca pełne dane kontaktu z modułu M&A po id."""
    with flask_app.app_context():
        row = mna_contact.get_mna_contact_by_id(contact_id)
        if not row:
            raise ValueError(f"Nie znaleziono kontaktu M&A o id={contact_id}.")
        return row


@mcp.tool()
def create_mna_contact(
    first_name: str,
    last_name: str,
    company_id: int | None = None,
    position: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
) -> dict:
    """Tworzy nowy kontakt w module M&A. Wymagane są imię i nazwisko.
    Tagi M&A to osobna pula od tagów CRM (nie są współdzielone)."""
    with flask_app.app_context():
        data = {
            "first_name": first_name, "last_name": last_name, "company_id": company_id,
            "position": position, "email": email, "phone": phone, "description": description,
        }
        data = {k: v for k, v in data.items() if v is not None}
        contact_id = mna_contact.create_mna_contact(data, _mcp_user_id(), tags=tags)
        return mna_contact.get_mna_contact_by_id(contact_id)


@mcp.tool()
def update_mna_contact(
    contact_id: int,
    first_name: str | None = None,
    last_name: str | None = None,
    company_id: int | None = None,
    position: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
) -> dict:
    """Aktualizuje wybrane pola kontaktu z modułu M&A. Podaj tylko te pola, które mają się zmienić.
    Podanie tags nadpisuje cały zestaw tagów kontaktu (nie dodaje pojedynczo)."""
    with flask_app.app_context():
        current = mna_contact.get_mna_contact_by_id(contact_id)
        if not current:
            raise ValueError(f"Nie znaleziono kontaktu M&A o id={contact_id}.")
        updates = {
            "first_name": first_name, "last_name": last_name, "company_id": company_id,
            "position": position, "email": email, "phone": phone, "description": description,
        }
        data = {**current, **{k: v for k, v in updates.items() if v is not None}}
        mna_contact.update_mna_contact(contact_id, data, _mcp_user_id(), tags=tags)
        return mna_contact.get_mna_contact_by_id(contact_id)


@mcp.tool()
def archive_mna_contact(contact_id: int) -> dict:
    """Archiwizuje kontakt z modułu M&A (soft-delete, odwracalne przez restore_mna_contact)."""
    with flask_app.app_context():
        if not mna_contact.get_mna_contact_by_id(contact_id):
            raise ValueError(f"Nie znaleziono kontaktu M&A o id={contact_id}.")
        mna_contact.delete_mna_contact(contact_id, _mcp_user_id())
        return {"id": contact_id, "archived": True}


@mcp.tool()
def restore_mna_contact(contact_id: int) -> dict:
    """Przywraca wcześniej zarchiwizowany kontakt z modułu M&A."""
    with flask_app.app_context():
        if not mna_contact.get_mna_contact_by_id_any(contact_id):
            raise ValueError(f"Nie znaleziono kontaktu M&A o id={contact_id}.")
        mna_contact.restore_mna_contact(contact_id, _mcp_user_id())
        return mna_contact.get_mna_contact_by_id(contact_id)


@mcp.tool()
def get_mna_contact_tags(contact_id: int) -> list[str]:
    """Zwraca listę tagów przypisanych do kontaktu M&A. Tagi M&A to osobna pula od tagów CRM."""
    with flask_app.app_context():
        if not mna_contact.get_mna_contact_by_id(contact_id):
            raise ValueError(f"Nie znaleziono kontaktu M&A o id={contact_id}.")
        return mna_tags.get_contact_tags(contact_id)


@mcp.tool()
def set_mna_contact_tags(contact_id: int, tags: list[str]) -> list[str]:
    """Nadpisuje cały zestaw tagów kontaktu M&A podaną listą (tworzy nowe tagi, jeśli nie istnieją)."""
    with flask_app.app_context():
        if not mna_contact.get_mna_contact_by_id(contact_id):
            raise ValueError(f"Nie znaleziono kontaktu M&A o id={contact_id}.")
        mna_tags.set_contact_tags(contact_id, tags)
        return mna_tags.get_contact_tags(contact_id)


@mcp.tool()
def suggest_mna_tags(query: str = "") -> list[str]:
    """Podpowiada istniejące tagi M&A pasujące do wpisanego fragmentu (do autouzupełniania)."""
    with flask_app.app_context():
        return mna_tags.suggest_tags(query)


# ── M&A: Deale (long lista / short lista) ────────────────────────────────────

@mcp.tool()
def find_mna_deals(search: str | None = None, stage: str | None = None) -> list[dict]:
    """Szuka deali M&A, opcjonalnie po nazwie i/lub etapie.
    Etapy: long_list, short_list, kontakt_nawiazany, nda, ioi, due_diligence, loi, zamkniety, przegrany."""
    with flask_app.app_context():
        return mna_deal.get_all_mna_deals(search=search, stage=stage)


@mcp.tool()
def get_mna_deal(deal_id: int) -> dict:
    """Zwraca pełne dane deala M&A po id."""
    with flask_app.app_context():
        row = mna_deal.get_mna_deal_by_id(deal_id)
        if not row:
            raise ValueError(f"Nie znaleziono deala M&A o id={deal_id}.")
        return row


@mcp.tool()
def create_mna_deal(
    name: str,
    offer_id: int | None = None,
    stage: str | None = None,
    amount: float | None = None,
    description: str | None = None,
) -> dict:
    """Tworzy nowy deal M&A. Wymagana jest tylko nazwa. offer_id to opcjonalne
    powiązanie z istniejącą ofertą M&A (firma na sprzedaż/poszukiwana)."""
    with flask_app.app_context():
        data = {
            "name": name, "offer_id": offer_id, "stage": stage,
            "amount": amount, "description": description,
        }
        data = {k: v for k, v in data.items() if v is not None}
        deal_id = mna_deal.create_mna_deal(data, _mcp_user_id())
        return mna_deal.get_mna_deal_by_id(deal_id)


@mcp.tool()
def update_mna_deal(
    deal_id: int,
    name: str | None = None,
    offer_id: int | None = None,
    stage: str | None = None,
    amount: float | None = None,
    description: str | None = None,
) -> dict:
    """Aktualizuje wybrane pola deala M&A. Podaj tylko te pola, które mają się zmienić."""
    with flask_app.app_context():
        current = mna_deal.get_mna_deal_by_id(deal_id)
        if not current:
            raise ValueError(f"Nie znaleziono deala M&A o id={deal_id}.")
        updates = {
            "name": name, "offer_id": offer_id, "stage": stage,
            "amount": amount, "description": description,
        }
        data = {**current, **{k: v for k, v in updates.items() if v is not None}}
        mna_deal.update_mna_deal(deal_id, data, _mcp_user_id())
        return mna_deal.get_mna_deal_by_id(deal_id)


@mcp.tool()
def archive_mna_deal(deal_id: int) -> dict:
    """Archiwizuje deal M&A (soft-delete, odwracalne przez restore_mna_deal)."""
    with flask_app.app_context():
        if not mna_deal.get_mna_deal_by_id(deal_id):
            raise ValueError(f"Nie znaleziono deala M&A o id={deal_id}.")
        mna_deal.delete_mna_deal(deal_id, _mcp_user_id())
        return mna_deal.get_mna_deal_by_id(deal_id)


@mcp.tool()
def restore_mna_deal(deal_id: int) -> dict:
    """Przywraca wcześniej zarchiwizowany deal M&A."""
    with flask_app.app_context():
        if not mna_deal.get_mna_deal_by_id(deal_id):
            raise ValueError(f"Nie znaleziono deala M&A o id={deal_id}.")
        mna_deal.restore_mna_deal(deal_id, _mcp_user_id())
        return mna_deal.get_mna_deal_by_id(deal_id)


# ── M&A: pozycje long/short listy na dealu (mna_deal_targets) ────────────────

@mcp.tool()
def list_mna_deal_targets(deal_id: int, list_type: Literal["long_list", "short_list"] | None = None) -> list[dict]:
    """Zwraca pozycje long/short listy dla danego deala M&A (firmy i/lub kontakty),
    wraz ze statusem zainteresowania i oznaczeniem „wartościowy”."""
    with flask_app.app_context():
        return mna_deal.get_targets_for_deal(deal_id, list_type)


@mcp.tool()
def add_mna_deal_target(
    deal_id: int,
    list_type: Literal["long_list", "short_list"] = "long_list",
    company_id: int | None = None,
    contact_id: int | None = None,
) -> dict:
    """Dodaje firmę i/lub kontakt (z modułu M&A) na long/short listę deala.
    Podaj company_id i/lub contact_id — przynajmniej jedno z nich."""
    with flask_app.app_context():
        if not company_id and not contact_id:
            raise ValueError("Podaj company_id i/lub contact_id.")
        if not mna_deal.get_mna_deal_by_id(deal_id):
            raise ValueError(f"Nie znaleziono deala M&A o id={deal_id}.")
        target_id = mna_deal.add_target(deal_id, company_id, contact_id, list_type, _mcp_user_id())
        return mna_deal.get_target_by_id(target_id)


@mcp.tool()
def remove_mna_deal_target(target_id: int) -> dict:
    """Usuwa pozycję z long/short listy deala M&A (nie kasuje samej firmy/kontaktu)."""
    with flask_app.app_context():
        if not mna_deal.get_target_by_id(target_id):
            raise ValueError(f"Nie znaleziono pozycji listy o id={target_id}.")
        mna_deal.remove_target(target_id, _mcp_user_id())
        return {"id": target_id, "removed": True}


@mcp.tool()
def move_mna_deal_target(target_id: int, list_type: Literal["long_list", "short_list"]) -> dict:
    """Przenosi pozycję między long listą a short listą."""
    with flask_app.app_context():
        if not mna_deal.get_target_by_id(target_id):
            raise ValueError(f"Nie znaleziono pozycji listy o id={target_id}.")
        mna_deal.move_target_list(target_id, list_type, _mcp_user_id())
        return mna_deal.get_target_by_id(target_id)


@mcp.tool()
def set_mna_deal_target_interest(
    target_id: int,
    interest_status: Literal["unknown", "interested", "not_interested"],
) -> dict:
    """Ustawia status zainteresowania pozycji na long/short liście deala M&A."""
    with flask_app.app_context():
        if not mna_deal.get_target_by_id(target_id):
            raise ValueError(f"Nie znaleziono pozycji listy o id={target_id}.")
        mna_deal.set_target_interest(target_id, interest_status, _mcp_user_id())
        return mna_deal.get_target_by_id(target_id)


@mcp.tool()
def set_mna_deal_target_valuable(target_id: int, is_valuable: bool) -> dict:
    """Oznacza (lub odznacza) pozycję na long/short liście deala M&A jako wartościową."""
    with flask_app.app_context():
        if not mna_deal.get_target_by_id(target_id):
            raise ValueError(f"Nie znaleziono pozycji listy o id={target_id}.")
        mna_deal.set_target_valuable(target_id, is_valuable, _mcp_user_id())
        return mna_deal.get_target_by_id(target_id)


@mcp.tool()
def set_mna_deal_target_score(target_id: int, score: int | None) -> dict:
    """Ustawia scoring (1-100, do oceny celów na long liście) pozycji na long/short liście deala
    M&A. Podaj None (brak wartości), żeby wyczyścić scoring."""
    with flask_app.app_context():
        if not mna_deal.get_target_by_id(target_id):
            raise ValueError(f"Nie znaleziono pozycji listy o id={target_id}.")
        if score is not None and not (1 <= score <= 100):
            raise ValueError("Scoring musi być liczbą z zakresu 1-100 albo None.")
        mna_deal.set_target_score(target_id, score, _mcp_user_id())
        return mna_deal.get_target_by_id(target_id)


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
