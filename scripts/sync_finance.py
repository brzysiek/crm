"""Synchronizacja Fakturowni → `fin_documents`, do crona.

Webhooki Fakturowni nie odpalają się dla faktur kosztowych, więc regularny
przebieg jest jedynym sposobem, żeby CRM wiedział o nowych kosztach.

    */30 * * * * cd /ścieżka/do/crm && venv/bin/python scripts/sync_finance.py

`--full` przechodzi wszystkie dokumenty, ignorując kursor.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import app
from services.fakturownia_api import FakturowniaError
from services.fin_sync import sync_documents


def main() -> int:
    full = '--full' in sys.argv
    with app.app_context():
        try:
            result = sync_documents(full=full)
        except FakturowniaError as e:
            print(f'Synchronizacja nieudana: {e}', file=sys.stderr)
            return 1
    print(f"{result['seen']} dokumentów, {result['new']} nowych, {result['updated']} zmienionych")
    for warning in result['warnings']:
        print(f'  uwaga: {warning}', file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
