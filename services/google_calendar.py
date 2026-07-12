"""Google Calendar API client — service account JWT (patrz services/google_auth.py).

Dwa kierunki użycia:
- odczyt kalendarza głównego ('primary') jako kontekst "zajęte" w widoku dnia (read-only)
- jednokierunkowy zapis zablokowanych czasowo zadań do osobnego, dedykowanego
  kalendarza ("Zadania"), współdzielonego z kontem usługi — GTD nigdy nie
  czyta z powrotem tego kalendarza, więc nie ma ryzyka konfliktu źródeł prawdy.
"""
import json
from datetime import date, datetime, timedelta

import requests

from services.google_auth import get_service_account_token

TIMEOUT = 20
CALENDAR_SCOPE = 'https://www.googleapis.com/auth/calendar'
CALENDAR_API = 'https://www.googleapis.com/calendar/v3'


def _raise_for_status(resp: requests.Response) -> None:
    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        raise requests.HTTPError(f'{e} — treść odpowiedzi: {resp.text[:500]}', response=resp) from None


class GoogleCalendarClient:
    def __init__(self, api_token: str):
        token_str = api_token.strip()
        if not token_str.startswith('{'):
            raise ValueError(
                'Integracja z Google Calendar wymaga konta usługi (service account JSON).'
            )
        self._sa_json = json.loads(token_str)

    def _auth_headers(self) -> dict:
        token = get_service_account_token(self._sa_json, CALENDAR_SCOPE)
        return {'Authorization': f'Bearer {token}'}

    def get_busy_events(self, calendar_id: str, day: date) -> list[dict]:
        """Read-only: zwraca wydarzenia z danego kalendarza (np. 'primary') na dany dzień."""
        start = datetime.combine(day, datetime.min.time())
        end = start + timedelta(days=1)
        resp = requests.get(
            f'{CALENDAR_API}/calendars/{calendar_id}/events',
            headers=self._auth_headers(),
            params={
                'timeMin': start.isoformat() + 'Z',
                'timeMax': end.isoformat() + 'Z',
                'singleEvents': 'true',
                'orderBy': 'startTime',
            },
            timeout=TIMEOUT,
        )
        _raise_for_status(resp)
        return resp.json().get('items', [])

    def upsert_task_event(self, calendar_id: str, event_id: str | None, title: str,
                           day: date, time_str: str, duration_min: int, notes: str = '') -> dict:
        """Tworzy albo aktualizuje wydarzenie odpowiadające zablokowanemu czasowi zadania."""
        start_dt = datetime.combine(day, datetime.strptime(time_str, '%H:%M').time())
        end_dt = start_dt + timedelta(minutes=duration_min)
        body = {
            'summary': title,
            'description': notes,
            'start': {'dateTime': start_dt.isoformat(), 'timeZone': 'Europe/Warsaw'},
            'end': {'dateTime': end_dt.isoformat(), 'timeZone': 'Europe/Warsaw'},
        }
        if event_id:
            resp = requests.put(
                f'{CALENDAR_API}/calendars/{calendar_id}/events/{event_id}',
                headers={**self._auth_headers(), 'Content-Type': 'application/json'},
                json=body,
                timeout=TIMEOUT,
            )
        else:
            resp = requests.post(
                f'{CALENDAR_API}/calendars/{calendar_id}/events',
                headers={**self._auth_headers(), 'Content-Type': 'application/json'},
                json=body,
                timeout=TIMEOUT,
            )
        _raise_for_status(resp)
        return resp.json()

    def delete_task_event(self, calendar_id: str, event_id: str) -> None:
        resp = requests.delete(
            f'{CALENDAR_API}/calendars/{calendar_id}/events/{event_id}',
            headers=self._auth_headers(),
            timeout=TIMEOUT,
        )
        if resp.status_code not in (200, 204, 404, 410):
            _raise_for_status(resp)
