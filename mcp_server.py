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

Kontakty mają też listy (crm_contact_lists) — nazwane grupy definiowane
w Ustawieniach CRM, do których jeden kontakt może należeć wielokrotnie; narzędzia
list_contact_lists / list_contacts_in_list / add_contacts_to_list /
remove_contacts_from_list pozwalają je czytać i zmieniać.

Moduł Finanse v2 (narzędzia z prefiksem fin_) czyta lustro faktur z Fakturowni
i pozwala zmieniać wyłącznie metadane analityczne CRM: kategorię, procent
odliczenia VAT i procent KUP oraz reguły, które je nadają automatycznie. Samych
faktur w Fakturowni te narzędzia nie tworzą ani nie modyfikują.

Serwer działa w tym samym procesie co aplikacja Flask (patrz passenger_wsgi.py) —
każde wywołanie narzędzia otwiera kontekst aplikacji Flask (app_context), żeby
modele mogły korzystać ze wspólnego database.get_db().

Autoryzacja: prosty token statyczny wpięty w sam adres URL, którym mocowany jest
ten serwer (patrz passenger_wsgi.py) — patrz Config.MCP_TOKEN i Config.MCP_USER_ID.
"""
from __future__ import annotations

import asyncio
import calendar
import json
import re
from datetime import date, timedelta
from decimal import Decimal
from typing import Literal

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
import mcp.types as types

from app import app as flask_app
from config import Config
import models.crm_company as crm_company
import models.crm_contact as crm_contact
import models.crm_contact_list as crm_contact_list
import models.crm_deal as crm_deal
import models.crm_mna_offer as crm_mna_offer
import models.crm_file as crm_file
import models.crm_notes as crm_notes
import models.gtd_context as gtd_context
import models.mna_company as mna_company
import models.mna_contact as mna_contact
import models.mna_deal as mna_deal
import models.mna_tags as mna_tags
import models.fin_category as fin_category
import models.fin_document as fin_document
import models.fin_tax as fin_tax_store
import models.reconciliation as reconciliation
import services.crm_files as crm_files_service
import services.fin_rules as fin_rules
import services.fin_sync as fin_sync_service
import services.fin_tax as fin_tax
import models.task as task_model
from routes.gtd import _add_months, _month_range, _try_gcal_delete, _week_range

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


# ── Listy kontaktów ─────────────────────────────────────────────────────────
#
# Lista to nazwana grupa kontaktów definiowana w Ustawieniach CRM (nazwa, opis,
# kolory). Kontakt może być na wielu listach naraz — inaczej niż kontekst GTD,
# którego kontakt ma najwyżej jeden. Każde dopisanie i wypisanie trafia do
# historii kontaktu, więc te operacje są odwracalne i widoczne w CRM.


def _require_contact_list(list_id: int) -> dict:
    row = crm_contact_list.get_list(list_id)
    if not row:
        raise ValueError(f"Nie znaleziono listy kontaktów o id={list_id}.")
    return row


@mcp.tool()
def list_contact_lists() -> list[dict]:
    """Zwraca listy kontaktów zdefiniowane w CRM wraz z liczbą kontaktów na każdej."""
    with flask_app.app_context():
        return [
            {"id": row["id"], "name": row["name"], "description": row["description"],
             "contacts": row.get("member_count", 0)}
            for row in crm_contact_list.get_all_lists(with_counts=True)
        ]


@mcp.tool()
def create_contact_list(name: str, description: str | None = None) -> dict:
    """Tworzy nową listę kontaktów. Nazwy są unikalne — jeśli lista już istnieje,
    zwraca tę istniejącą, żeby nie mnożyć duplikatów."""
    with flask_app.app_context():
        name = (name or "").strip()
        if not name:
            raise ValueError("Lista potrzebuje nazwy.")
        for row in crm_contact_list.get_all_lists():
            if row["name"].lower() == name.lower():
                return {"id": row["id"], "name": row["name"], "created": False}
        list_id = crm_contact_list.create_list(name, description=(description or "").strip() or None)
        return {"id": list_id, "name": name, "created": True}


@mcp.tool()
def list_contacts_in_list(list_id: int, search: str | None = None, limit: int = 100) -> dict:
    """Zwraca kontakty z danej listy — to samo zawężenie co widok listy w CRM.
    `search` filtruje po imieniu, nazwisku, emailu, telefonie i nazwie firmy."""
    with flask_app.app_context():
        contact_list = _require_contact_list(list_id)
        limit = max(1, min(int(limit), 500))
        rows = crm_contact.get_all_contacts(search=search or None, list_id=list_id, limit=limit)
        return {
            "list": {"id": contact_list["id"], "name": contact_list["name"]},
            "total": crm_contact.count_contacts(search=search or None, list_id=list_id),
            "returned": len(rows),
            "contacts": [
                {"id": r["id"], "first_name": r["first_name"], "last_name": r["last_name"],
                 "position": r["position"], "email": r["email"], "phone": r["phone"],
                 "company_id": r["company_id"], "company_name": r.get("company_name")}
                for r in rows
            ],
        }


@mcp.tool()
def get_contact_list_membership(contact_id: int) -> list[dict]:
    """Zwraca listy, na których jest dany kontakt."""
    with flask_app.app_context():
        if not crm_contact.get_contact_by_id(contact_id):
            raise ValueError(f"Nie znaleziono kontaktu o id={contact_id}.")
        return [{"id": row["id"], "name": row["name"]}
                for row in crm_contact_list.get_contact_lists(contact_id)]


@mcp.tool()
def add_contacts_to_list(list_id: int, contact_ids: list[int]) -> dict:
    """Dopisuje kontakty do listy. Kontakty już na liście są pomijane —
    `added` mówi, ile dopisań faktycznie nastąpiło."""
    with flask_app.app_context():
        contact_list = _require_contact_list(list_id)
        ids = [int(i) for i in contact_ids]
        if not ids:
            raise ValueError("Podaj co najmniej jeden contact_id.")
        added = crm_contact_list.add_contacts_to_list(list_id, ids, _mcp_user_id())
        return {"list": {"id": contact_list["id"], "name": contact_list["name"]},
                "requested": len(ids), "added": added,
                "already_on_list": len(ids) - added}


@mcp.tool()
def remove_contacts_from_list(list_id: int, contact_ids: list[int]) -> dict:
    """Usuwa kontakty z listy. Same kontakty zostają w CRM — znika tylko
    przynależność do tej listy."""
    with flask_app.app_context():
        contact_list = _require_contact_list(list_id)
        ids = [int(i) for i in contact_ids]
        if not ids:
            raise ValueError("Podaj co najmniej jeden contact_id.")
        removed = crm_contact_list.remove_contacts_from_list(list_id, ids, _mcp_user_id())
        return {"list": {"id": contact_list["id"], "name": contact_list["name"]},
                "requested": len(ids), "removed": removed,
                "not_on_list": len(ids) - removed}


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

_STATUSES = ("ideas", "next", "waiting", "someday", "done")


def _compact_task(row: dict) -> dict:
    compact = {
        "id": row["id"], "title": row["title"], "status": row["status"],
        "parent_id": row["parent_id"], "is_project": bool(row["is_project"]),
        "context_name": row.get("context_name"),
    }
    for key in ("planned_week", "planned_month"):
        if row.get(key):
            compact[key] = row[key]
    return compact


def _resolve_period(value: str, kind: Literal["week", "month"], allow_clear: bool = True) -> date | None:
    """Zamienia planned_week/planned_month z wejścia MCP na datę początku okresu
    (poniedziałek tygodnia / 1. dzień miesiąca). "clear" zwraca None (= wyczyść)."""
    v = value.strip().lower()
    if v == "clear" and allow_clear:
        return None
    today = date.today()
    current = _week_range(today)[0] if kind == "week" else _month_range(today)[0]
    if v == "this":
        return current
    if v == "next":
        return current + timedelta(weeks=1) if kind == "week" else _add_months(current, 1)
    if kind == "month" and len(v) == 7:
        v += "-01"
    try:
        d = date.fromisoformat(v)
    except ValueError:
        allowed = "RRRR-MM-DD" + (" lub RRRR-MM" if kind == "month" else "") + ", 'this', 'next'"
        if allow_clear:
            allowed += " lub 'clear'"
        raise ValueError(f"Nieprawidłowa wartość planned_{kind}={value!r} — oczekiwano {allowed}.")
    return _week_range(d)[0] if kind == "week" else _month_range(d)[0]


def _apply_planning(task: dict, week: date | None | str, month: date | None | str) -> None:
    """Przypisuje/czyści blok tygodniowy/miesięczny tak jak UI: przypisanie usuwa konkretną
    datę (i wydarzenie w Google Calendar) oraz drugi blok; "" = bez zmian, None = wyczyść."""
    for kind, value in (("week", week), ("month", month)):
        if value == "":
            continue
        if value is None:
            (task_model.clear_week if kind == "week" else task_model.clear_month)(task["id"])
            continue
        if task.get("gcal_event_id"):
            _try_gcal_delete(task)
        (task_model.assign_week if kind == "week" else task_model.assign_month)(task["id"], value)


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
    status: Literal["ideas", "next", "waiting", "someday", "done"] | None = None,
    planned_week: str | None = None,
    planned_month: str | None = None,
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
    - planned_week / planned_month: zadania przypisane do luźnego bloku tygodnia/miesiąca
      (data RRRR-MM-DD z danego tygodnia/miesiąca, RRRR-MM dla miesiąca, albo 'this'/'next').
      Uwaga: bez status/include_done dalej obowiązuje domyślny filtr statusu opisany wyżej.
    - limit/offset: stronicowanie (max 500 na stronę)."""
    week = _resolve_period(planned_week, "week", allow_clear=False) if planned_week else None
    month = _resolve_period(planned_month, "month", allow_clear=False) if planned_month else None
    with flask_app.app_context():
        return task_model.find_tasks(
            search=search, company_id=company_id, contact_id=contact_id, deal_id=deal_id,
            parent_id=parent_id, context_id=context_id, status=status,
            only_projects=only_projects, include_done=include_done,
            planned_week=week, planned_month=month,
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
                "scheduled_date": row["scheduled_date"], "planned_week": row["planned_week"],
                "planned_month": row["planned_month"], "waiting_on": row["waiting_on"],
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
    status: Literal["ideas", "next", "waiting", "someday"] = "ideas",
    parent_id: int | None = None,
    is_project: bool = False,
    context_id: int | None = None,
    is_important: bool = False,
    planned_week: str | None = None,
    planned_month: str | None = None,
    verbose: bool = False,
) -> dict:
    """Tworzy nowe zadanie lub projekt. Model danych: projekt = zadanie z is_project=1; zadania projektu =
    zadania z parent_id wskazującym na projekt. deal_id wiąże z dealem CRM i nie służy do grupowania
    w projekty; mna_deal_id to deal M&A (jeszcze inny obiekt).

    - parent_id: podpina zadanie pod projekt (musi istnieć i mieć is_project=1). Zadanie dziedziczy
      po projekcie kontekst i powiązania, o ile nie podano ich wprost.
    - is_project=True: tworzy projekt (nie może mieć parent_id; status ideas zamienia się na next).
    - context_id: kontekst GTD (lista: list_contexts); bez niego dziedziczy się z projektu/deala/
      firmy/kontaktu, a w ostateczności jest brany kontekst domyślny.
    - due_date (termin) w formacie RRRR-MM-DD.
    - planned_week / planned_month: przypisanie do luźnego bloku tygodnia/miesiąca bez konkretnego
      dnia (data RRRR-MM-DD z danego tygodnia/miesiąca, RRRR-MM dla miesiąca, albo 'this'/'next').
      Tydzień i miesiąc wykluczają się nawzajem. Zadanie z ideas przechodzi wtedy do next.
    - Domyślnie zwraca skrót {id, title, status, parent_id, is_project, context_name} (plus
      planned_week/planned_month, jeśli ustawione); verbose=True zwraca pełny rekord."""
    if planned_week and planned_month:
        raise ValueError("Podaj planned_week albo planned_month — zadanie może być w jednym bloku naraz.")
    week = _resolve_period(planned_week, "week", allow_clear=False) if planned_week else ""
    month = _resolve_period(planned_month, "month", allow_clear=False) if planned_month else ""
    with flask_app.app_context():
        _validate_hierarchy(None, parent_id, is_project)
        if context_id:
            _require_context(context_id)
        if is_project and status == "ideas":
            status = "next"
        task_id = task_model.create_task(
            title, _mcp_user_id(), is_project=is_project, status=status, due_date=due_date, notes=notes,
            parent_id=parent_id, context_id=context_id, is_important=is_important,
            crm_company_id=company_id, crm_contact_id=contact_id, crm_deal_id=deal_id,
            crm_mna_offer_id=mna_offer_id, crm_mna_deal_id=mna_deal_id,
        )
        _apply_planning({"id": task_id}, week, month)
        return _task_response(task_id, verbose)


@mcp.tool()
def update_task(
    task_id: int,
    title: str | None = None,
    notes: str | None = None,
    status: Literal["ideas", "next", "waiting", "someday", "done"] | None = None,
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
    planned_week: str | None = None,
    planned_month: str | None = None,
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
    - Planowanie — trzy wzajemnie wykluczające się formy, jak w UI:
      scheduled_date (konkretny dzień), planned_week (luźny blok tygodnia), planned_month (luźny
      blok miesiąca). planned_week/planned_month: data RRRR-MM-DD z danego okresu (RRRR-MM dla
      miesiąca), 'this', 'next' albo 'clear' (wyczyść). Przypisanie do tygodnia/miesiąca usuwa
      konkretny dzień/godzinę (i wydarzenie w Google Calendar) oraz drugi blok; ustawienie
      scheduled_date czyści bloki. W jednym wywołaniu można ustawić tylko jedną z tych form.
    - due_date to termin (deadline) — niezależny od planowania.
    - Domyślnie zwraca skrót {id, title, status, parent_id, is_project, context_name} (plus
      planned_week/planned_month, jeśli ustawione); verbose=True zwraca pełny rekord."""
    week = _resolve_period(planned_week, "week") if planned_week else ""
    month = _resolve_period(planned_month, "month") if planned_month else ""
    if sum(1 for v in (scheduled_date, week, month) if v) > 1:
        raise ValueError(
            "scheduled_date, planned_week i planned_month wykluczają się — ustaw tylko jedno z nich "
            "(pozostałe wyczyszczą się automatycznie)."
        )
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
        if scheduled_date:
            data.update(planned_week=None, planned_month=None)
        if data:
            task_model.update_task(task_id, data)
        _apply_planning(task, week, month)
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
    ref_number: str | None = None,
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
    firma/kontakt będący źródłem oferty. ref_number (numer oferty) nadaje się sam
    w formacie „Ref: <nr w roku>/<rok>” — podaj go tylko po to, by nadpisać."""
    with flask_app.app_context():
        data = {
            "name": name, "offer_type": offer_type, "ref_number": ref_number,
            "description": description,
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
    ref_number: str | None = None,
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
            "name": name, "offer_type": offer_type, "ref_number": ref_number,
            "description": description,
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


# ── M&A: pliki deala (Google Drive) ──────────────────────────────────────────
#
# Pliki deala M&A leżą na Drive w "Deale M&A/<firma z oferty>/pliki" i są widoczne w sekcji
# Pliki na stronie deala. Te narzędzia działają wyłącznie na plikach deali M&A — plików firm
# CRM celowo nie ruszają.

def _mna_deal_file(file_id: int) -> dict:
    rec = crm_file.get_file_by_id(file_id)
    if not rec:
        raise ValueError(f"Nie znaleziono pliku o id={file_id}.")
    if not rec.get("mna_deal_id"):
        raise ValueError(
            f"Plik id={file_id} nie należy do deala M&A (to plik firmy/kontaktu CRM) — "
            "tymi narzędziami zarządzasz tylko plikami deali M&A."
        )
    return rec


def _require_mna_deal(deal_id: int) -> dict:
    deal = mna_deal.get_mna_deal_by_id(deal_id)
    if not deal:
        raise ValueError(f"Nie znaleziono deala M&A o id={deal_id}.")
    return deal


@mcp.tool()
def list_mna_deal_files(deal_id: int) -> list[dict]:
    """Zwraca pliki przypięte do deala M&A (najnowsze pierwsze) wraz z nazwą folderu na Drive,
    w którym leżą ("Deale M&A/<firma z oferty>/pliki")."""
    with flask_app.app_context():
        deal = _require_mna_deal(deal_id)
        return [
            {
                "id": f["id"], "file_name": f["file_name"], "mime_type": f["mime_type"],
                "file_size": f["file_size"], "created_at": f["created_at"],
                "added_by": f.get("user_name"),
                "drive_folder": f"{crm_files_service.MNA_DEALS_FOLDER}/"
                                 f"{crm_files_service.mna_deal_folder_name(deal)}/"
                                 f"{crm_files_service.FILES_SUBFOLDER}",
            }
            for f in crm_file.get_files_for_mna_deal(deal_id)
        ]


@mcp.tool()
def upload_mna_deal_file(deal_id: int, file_name: str, content_base64: str) -> dict:
    """Dodaje plik do deala M&A: wrzuca go na Drive do "Deale M&A/<firma z oferty>/pliki",
    zapisuje w CRM i dopisuje wpis do historii deala.

    file_name musi mieć rozszerzenie z listy: PDF, DOCX, JPG, JPEG, PNG, HEIC, XML.
    content_base64 to zawartość pliku zakodowana base64 (nadaje się do małych plików —
    większe wygodniej wrzucić przez stronę deala)."""
    import base64
    import binascii

    crm_files_service.mime_for(file_name)
    try:
        content = base64.b64decode(content_base64, validate=True)
    except (binascii.Error, ValueError) as e:
        raise ValueError(f"content_base64 nie jest poprawnym base64: {e}")
    if not content:
        raise ValueError("Pusty plik — content_base64 nie zawiera danych.")
    with flask_app.app_context():
        deal = _require_mna_deal(deal_id)
        file_id = crm_files_service.upload_mna_deal_file(deal, file_name, content, _mcp_user_id())
        rec = crm_file.get_file_by_id(file_id)
        return {"id": rec["id"], "file_name": rec["file_name"], "mime_type": rec["mime_type"],
                "file_size": rec["file_size"], "mna_deal_id": rec["mna_deal_id"]}


@mcp.tool()
def rename_mna_deal_file(file_id: int, file_name: str) -> dict:
    """Zmienia nazwę pliku deala M&A — w CRM i na Google Drive. Rozszerzenie musi zostać
    to samo, żeby nie rozjechało się z typem pliku."""
    with flask_app.app_context():
        rec = _mna_deal_file(file_id)
        old_ext = crm_files_service.file_extension(rec["file_name"])
        new_ext = crm_files_service.file_extension(file_name)
        if new_ext != old_ext:
            raise ValueError(
                f"Nie zmieniaj rozszerzenia pliku (było .{old_ext}, podano .{new_ext or '—'})."
            )
        crm_files_service.rename_drive_file(rec["drive_file_id"], file_name)
        crm_file.rename_file(file_id, file_name)
        crm_notes.log_history("mna_deal", rec["mna_deal_id"], _mcp_user_id(), "file",
                               f"Zmieniono nazwę pliku: {rec['file_name']} → {file_name}",
                               file_id=file_id)
        return {"id": file_id, "file_name": file_name, "mna_deal_id": rec["mna_deal_id"]}


@mcp.tool()
def delete_mna_deal_file(file_id: int) -> dict:
    """Usuwa plik deala M&A z CRM i z Google Drive. Nieodwracalne — nie ma tu soft-delete."""
    with flask_app.app_context():
        rec = _mna_deal_file(file_id)
        drive_error = crm_files_service.delete_drive_file(rec["drive_file_id"])
        crm_file.delete_file(file_id)
        crm_notes.log_history("mna_deal", rec["mna_deal_id"], _mcp_user_id(), "file",
                               f"Usunięto plik: {rec['file_name']}")
        result = {"deleted": True, "id": file_id, "file_name": rec["file_name"],
                   "mna_deal_id": rec["mna_deal_id"]}
        if drive_error:
            result["drive_warning"] = f"Rekord usunięty z CRM, ale nie udało się usunąć pliku z Drive: {drive_error}"
        return result


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


# ── Finanse v2: faktury z Fakturowni ────────────────────────────────────────
#
# `fin_documents` to lustro Fakturowni — tu się dokumentów nie tworzy ani nie
# zmienia. Modyfikowalne są wyłącznie metadane analityczne CRM (kategoria,
# procent odliczenia VAT, procent KUP) i reguły, które je nadają automatycznie.
# Kwoty wracają jako łańcuchy znaków, bo to Decimal — nie float — i nie chcę
# gubić groszy w konwersji.

_FIN_DOC_FIELDS = ('fakturownia_id', 'number', 'kind', 'is_income', 'issue_date', 'sell_date',
                   'payment_to', 'paid_date', 'status', 'currency', 'net_pln', 'tax_pln',
                   'gross_pln', 'paid_amount', 'counterparty_name', 'counterparty_tax_no',
                   'description', 'gov_id', 'gov_status', 'category_id', 'category_name',
                   'vat_deduction_percent', 'tax_deductible_percent')


def _fin_doc(row: dict, extra: tuple = ()) -> dict:
    """Dokument w skrócie — bez raw_json, który ma kilka kilobajtów na sztukę."""
    out = {k: row.get(k) for k in _FIN_DOC_FIELDS if k in row}
    out['is_income'] = bool(row.get('is_income'))
    for k in extra:
        out[k] = row.get(k)
    return out


def _fin_category_id(category: str | int | None) -> int | None:
    """Kategoria podana jako id albo jako slug (agentowi łatwiej trafić slugiem)."""
    if category is None or category == '':
        return None
    if isinstance(category, int) or str(category).isdigit():
        found = fin_category.get_category(int(category))
        if not found:
            raise ValueError(f"Nie znaleziono kategorii o id={category}.")
        return found['id']
    found = fin_category.get_category_by_slug(str(category).strip())
    if not found:
        raise ValueError(f"Nie znaleziono kategorii o identyfikatorze „{category}”.")
    return found['id']


@mcp.tool()
def fin_list_documents(
    kind: Literal["cost", "income", "all"] = "cost",
    month: str | None = None,
    payment: Literal["paid", "unpaid", "overdue"] | None = None,
    category: str | None = None,
    uncategorized: bool = False,
    search: str | None = None,
    limit: int = 50,
) -> dict:
    """Lista faktur z lustra Fakturowni. `month` w formacie RRRR-MM (po dacie
    wystawienia), `category` to id albo identyfikator kategorii, `search` szuka
    w numerze, kontrahencie, NIP-ie, opisie i numerze KSeF. Proformy, wyceny
    i noty są pomijane — nie są zdarzeniem finansowym."""
    with flask_app.app_context():
        filters = {
            'kind': '' if kind == 'all' else kind,
            'month': (month or '').strip(),
            'payment': payment or '',
            'category_id': _fin_category_id(category),
            'uncategorized': bool(uncategorized),
            'search': (search or '').strip(),
            'financial_only': True,
        }
        limit = max(1, min(int(limit), 200))
        rows = fin_document.list_documents(filters, limit=limit)
        return {
            'total': fin_document.count_documents(filters),
            'returned': len(rows),
            'documents': [_fin_doc(r) for r in rows],
        }


@mcp.tool()
def fin_get_document(fakturownia_id: int) -> dict:
    """Pełne dane jednej faktury z lustra, razem z kategorią i procentami
    odliczeń. `fakturownia_id` to identyfikator dokumentu w Fakturowni."""
    with flask_app.app_context():
        row = fin_document.get_document(int(fakturownia_id))
        if not row:
            raise ValueError(f"Nie znam dokumentu o fakturownia_id={fakturownia_id} — "
                              "może nie został jeszcze zsynchronizowany.")
        return _fin_doc(row, extra=('department_id', 'exchange_rate', 'price_net', 'price_tax',
                                     'price_gross', 'accounting_kind', 'meta_note',
                                     'category_source', 'oid', 'synced_at'))


@mcp.tool()
def fin_unpaid(kind: Literal["cost", "income"] = "cost", limit: int = 100) -> dict:
    """Nieopłacone dokumenty w kubełkach terminów: overdue (po terminie),
    week (7 dni), month (30 dni), later, no_date. `amount_left` to brutto
    minus już wpłacone. kind='cost' — do zapłaty, kind='income' — należności."""
    with flask_app.app_context():
        rows = fin_document.open_items(is_income=(kind == 'income'), limit=max(1, min(int(limit), 300)))
        buckets: dict[str, list] = {}
        for row in rows:
            buckets.setdefault(row['bucket'], []).append(
                _fin_doc(row, extra=('amount_left', 'days_left', 'bucket')))
        return {
            'kind': kind,
            'total_amount_left': sum((r['amount_left'] for r in rows), Decimal('0')),
            'overdue_amount': sum((r['amount_left'] for r in rows if r['bucket'] == 'overdue'),
                                   Decimal('0')),
            'count': len(rows),
            'buckets': buckets,
        }


@mcp.tool()
def fin_summary(period: str | None = None) -> dict:
    """Podsumowanie okresu: sumy netto/VAT/brutto osobno dla kosztów i przychodów
    plus wynik. `period` to RRRR-MM albo RRRR; brak = bieżący miesiąc."""
    with flask_app.app_context():
        today = date.today()
        period = (period or today.strftime('%Y-%m')).strip()
        if len(period) == 4 and period.isdigit():
            date_from, date_to = f'{period}-01-01', f'{period}-12-31'
        else:
            try:
                year, month = int(period[:4]), int(period[5:7])
                last = calendar.monthrange(year, month)[1]
            except (ValueError, IndexError):
                raise ValueError("Okres podaj jako RRRR-MM albo RRRR.")
            date_from, date_to = f'{year}-{month:02d}-01', f'{year}-{month:02d}-{last}'
        totals = fin_document.period_totals(date_from, date_to)
        cost, income = totals['cost'], totals['income']
        return {
            'period': period, 'from': date_from, 'to': date_to,
            'cost': cost, 'income': income,
            'result_net': Decimal(str(income['net'])) - Decimal(str(cost['net'])),
            'uncategorized_documents': fin_document.count_uncategorized(),
        }


@mcp.tool()
def fin_categories() -> list[dict]:
    """Taksonomia kategorii finansowych CRM z domyślnymi procentami odliczenia
    VAT i kosztów podatkowych (KUP). Identyfikator (slug) można podawać wszędzie
    tam, gdzie narzędzia przyjmują kategorię."""
    with flask_app.app_context():
        return [{'id': c['id'], 'kind': c['kind'], 'name': c['name'], 'slug': c['slug'],
                 'vat_deduction_percent': c['default_vat_deduction'],
                 'tax_deductible_percent': c['default_tax_deductible'],
                 'is_fixed_cost': bool(c['is_fixed_cost'])}
                for c in fin_category.list_categories()]


@mcp.tool()
def fin_uncategorized(kind: Literal["cost", "income", "all"] = "all", limit: int = 50) -> dict:
    """Dokumenty bez kategorii — kolejka do rozdysponowania. Zwraca też łączną
    liczbę, żeby było wiadomo, ile zostało poza zwróconą stroną."""
    with flask_app.app_context():
        filters = {'kind': '' if kind == 'all' else kind, 'uncategorized': True,
                   'financial_only': True}
        rows = fin_document.list_documents(filters, limit=max(1, min(int(limit), 200)))
        return {'total': fin_document.count_documents(filters), 'returned': len(rows),
                'documents': [_fin_doc(r) for r in rows]}


@mcp.tool()
def fin_set_category(
    fakturownia_id: int,
    category: str | None,
    vat_deduction_percent: int | None = None,
    tax_deductible_percent: int | None = None,
    note: str | None = None,
) -> dict:
    """Przypisuje kategorię jednemu dokumentowi. `category` to id albo slug;
    None czyści przypisanie. Bez podanych procentów brane są domyślne
    z kategorii. Zmiana dotyczy metadanych CRM — faktura w Fakturowni
    zostaje nietknięta."""
    with flask_app.app_context():
        if not fin_document.get_document(int(fakturownia_id)):
            raise ValueError(f"Nie znam dokumentu o fakturownia_id={fakturownia_id}.")
        category_id = _fin_category_id(category)
        if category_id is None:
            fin_category.clear_document_category(int(fakturownia_id))
        else:
            fin_category.set_document_category(
                int(fakturownia_id), category_id, source='agent',
                vat_percent=vat_deduction_percent, kup_percent=tax_deductible_percent,
                note=note)
        return _fin_doc(fin_document.get_document(int(fakturownia_id)))


@mcp.tool()
def fin_bulk_categorize(fakturownia_ids: list[int], category: str) -> dict:
    """Przypisuje jedną kategorię wielu dokumentom naraz. Zwraca liczbę
    zmienionych wpisów."""
    with flask_app.app_context():
        category_id = _fin_category_id(category)
        if category_id is None:
            raise ValueError("Do masowego przypisania potrzebna jest kategoria.")
        ids = [int(i) for i in fakturownia_ids]
        if not ids:
            raise ValueError("Podaj co najmniej jeden fakturownia_id.")
        count = fin_category.bulk_set_category(ids, category_id, source='agent')
        return {'category_id': category_id, 'requested': len(ids), 'updated': count}


@mcp.tool()
def fin_add_rule(
    match_field: Literal["counterparty_tax_no_norm", "counterparty_name", "number",
                          "description", "accounting_kind"],
    match_type: Literal["equals", "contains", "starts_with", "regex"],
    match_value: str,
    category: str,
    priority: int = 100,
    apply_now: bool = True,
) -> dict:
    """Dodaje regułę auto-kategoryzacji („wszystko od tego kontrahenta idzie
    w tę kategorię”). Reguły działają przy każdej synchronizacji; `apply_now`
    przepuszcza przez nie także dokumenty już w bazie, ale bez kategorii."""
    with flask_app.app_context():
        category_id = _fin_category_id(category)
        rule_id = fin_rules.create_rule(match_field, match_type, (match_value or '').strip(),
                                         category_id, priority=int(priority))
        result = {'rule_id': rule_id, 'category_id': category_id}
        if apply_now:
            applied = fin_rules.apply_rules()
            result['checked'] = applied['checked']
            result['assigned'] = applied['assigned']
        return result


@mcp.tool()
def fin_sync(full: bool = False) -> dict:
    """Ściąga z Fakturowni faktury zmienione od ostatniego przebiegu (full=True —
    wszystkie od początku) i przepuszcza nowe przez reguły kategoryzacji."""
    with flask_app.app_context():
        result = fin_sync_service.sync_documents(full=bool(full))
        result['cursor'] = result['cursor'].isoformat() if result['cursor'] else None
        return result


@mcp.tool()
def fin_tax_estimate(period: str = "", include_documents: bool = False) -> dict:
    """Symulacja podatków za miesiąc (VAT, zaliczka PIT liniowy, ZUS społeczny i zdrowotna).

    `period` w formacie YYYY-MM; pusty = poprzedni miesiąc, czyli ten, który się właśnie
    płaci. Zwraca kwoty, terminy zapłaty, listę wyjątków (dokumenty, których silnik nie
    umie policzyć: odwrotne obciążenie, import usług, marża, OSS, zerowy VAT) oraz
    ostrzeżenia o niepotwierdzonych stawkach.

    To symulacja, nie deklaracja: nie nadaje się do wysłania do urzędu, a kwoty VAT nie
    uwzględniają nadwyżki przeniesionej z poprzednich okresów. Kategoryzacja kosztów
    wprost wpływa na wynik — dokument bez kategorii liczy się jak 100% odliczenia VAT
    i 100% kosztu podatkowego.
    """
    period = (period or "").strip()
    if not period:
        today = date.today()
        first = today.replace(day=1)
        previous = first - timedelta(days=1)
        period = previous.strftime("%Y-%m")
    if not re.fullmatch(r"\d{4}-\d{2}", period):
        raise ValueError("Okres podaj jako YYYY-MM, np. 2026-08.")

    with flask_app.app_context():
        missing = fin_tax_store.missing_rates(int(period[:4]))
        if missing:
            raise ValueError("Brak stawek podatkowych na "
                             f"{period[:4]}: {', '.join(missing)}. Uzupełnij je w CRM "
                             "(Finanse → Ustawienia) — bez nich nie policzę podatków.")
        overview = fin_tax.period_overview(period)
        rows = fin_tax.obligation_rows(overview)

    vat, pit, health, social = overview['vat'], overview['pit'], overview['health'], overview['social']
    result = {
        'period': period,
        'disclaimer': 'Symulacja, nie deklaracja. Sprawdź z księgową przed zapłatą.',
        'obligations': [{'kind': r['kind'], 'label': r['label'], 'amount': r['amount'],
                         'calculated': r['calculated'], 'declared': r['declared'],
                         'due_date': r['due_date'], 'paid_at': r['paid_at']} for r in rows],
        'vat': {'due': vat['due'], 'deductible': vat['deductible'], 'to_pay': vat['to_pay'],
                'carry_forward': vat['carry_forward'], 'due_date': vat['due_date'],
                'income_documents': vat['income_count'], 'cost_documents': vat['cost_count'],
                'uncategorized_documents': len(vat['uncategorized']),
                'uncategorized_tax': vat['uncategorized_tax'],
                'exceptions': [{'fakturownia_id': e['fakturownia_id'], 'number': e['number'],
                                'counterparty_name': e['counterparty_name'], 'net': e['net'],
                                'tax': e['tax'], 'is_income': e['is_income'],
                                'reason': e['reason'], 'reason_label': e['reason_label']}
                               for e in vat['exceptions']]},
        'pit': {'income_net_ytd': pit['income_net'], 'cost_net_ytd': pit['cost_net'],
                'social_deducted': pit['social_paid'], 'health_deducted': pit['health_deducted'],
                'taxable_ytd': pit['taxable'], 'rate': pit['rate'], 'tax_ytd': pit['tax_ytd'],
                'advances_paid': pit['advances_paid'], 'to_pay': pit['to_pay'],
                'overpaid': pit['overpaid'], 'due_date': pit['due_date'],
                'uncategorized_costs_ytd': overview['ytd']['cost_uncategorized']},
        'zus': {'social': social['amount'], 'health': health['amount'],
                'health_basis_month': health['basis_month'],
                'health_basis_income': health['basis_income'],
                'health_is_minimum': health['is_minimum'], 'due_date': social['due_date']},
        'rates_year': overview['rates_year'],
        'rates_warnings': overview['rates_warning'],
    }
    if include_documents:
        result['vat']['limited'] = vat['limited']
        result['vat']['uncategorized'] = vat['uncategorized']
    return result


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
