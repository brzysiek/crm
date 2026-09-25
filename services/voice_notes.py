"""Notatki głosowe — reguły wspólne dla nagrania z mikrofonu i wgranego pliku.

Jedno miejsce na format i rozmiar, bo notatkę głosową da się dodać z każdego
ekranu z notatkami oraz przez API. Rozmiar nie jest tu kosmetyczny: nagranie
trzymamy jako data URI w kolumnie MEDIUMTEXT (16 MB), a base64 puchnie o 1/3 —
limit musi zostawić zapas na nagłówek, inaczej INSERT po cichu utnie dane.
"""

import base64

# Rozszerzenie → MIME wysyłane do Gemini. Mapujemy po rozszerzeniu, nie po
# typie z przeglądarki, bo ten dla m4a bywa pusty albo egzotyczny (audio/x-m4a,
# audio/mp4) zależnie od systemu. Gemini i tak rozpoznaje kontener sam —
# sprawdzone na żywo: m4a przechodzi jako audio/mp4, audio/aac i audio/x-m4a.
AUDIO_MIME_BY_EXT = {
    'mp3':  'audio/mpeg',
    'm4a':  'audio/mp4',
    'mp4':  'audio/mp4',
    'aac':  'audio/aac',
    'wav':  'audio/wav',
    'ogg':  'audio/ogg',
    'oga':  'audio/ogg',
    'opus': 'audio/ogg',
    'webm': 'audio/webm',
    'flac': 'audio/flac',
    'aiff': 'audio/aiff',
    'aif':  'audio/aiff',
}

# 10 MB surowego audio → ~13,4 MB po base64, czyli mieści się w MEDIUMTEXT
# z zapasem. Przy 64 kbps mono to około 20 minut nagrania.
MAX_AUDIO_BYTES = 10 * 1024 * 1024

FORMATS_LABEL = 'MP3, M4A, WAV, OGG, OPUS, WEBM, FLAC, AAC'


class AudioNoteError(ValueError):
    """Nagranie odrzucone — komunikat jest przeznaczony dla użytkownika."""


def audio_mime(file_name: str, declared_mime: str = '') -> str:
    """Zwraca MIME nagrania na podstawie rozszerzenia pliku.

    `declared_mime` (typ podany przez przeglądarkę) jest awaryjny — używamy go
    tylko wtedy, gdy nazwa pliku nie ma rozszerzenia, co zdarza się przy blobach
    z MediaRecorder.
    """
    ext = file_name.rsplit('.', 1)[-1].lower() if '.' in (file_name or '') else ''
    if ext in AUDIO_MIME_BY_EXT:
        return AUDIO_MIME_BY_EXT[ext]

    base = (declared_mime or '').split(';', 1)[0].strip().lower()
    if base in set(AUDIO_MIME_BY_EXT.values()):
        return base

    raise AudioNoteError(f'Nieobsługiwany format nagrania. Obsługiwane: {FORMATS_LABEL}.')


def build_data_uri(audio_bytes: bytes, mime_type: str) -> str:
    """Pakuje nagranie w data URI zapisywane w crm_notes.audio_data."""
    if not audio_bytes:
        raise AudioNoteError('Puste nagranie.')
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise AudioNoteError(
            f'Nagranie jest za duże ({len(audio_bytes) / 1024 / 1024:.1f} MB). '
            f'Limit to {MAX_AUDIO_BYTES // 1024 // 1024} MB — podziel plik albo '
            'skompresuj do niższej jakości.'
        )
    encoded = base64.b64encode(audio_bytes).decode('ascii')
    return f'data:{mime_type};base64,{encoded}'


def split_data_uri(audio_data: str) -> tuple[bytes, str]:
    """Rozpakowuje data URI z bazy na (bajty, MIME)."""
    try:
        header, payload = audio_data.split(',', 1)
        mime_type = header.split(':', 1)[1].split(';', 1)[0]
        return base64.b64decode(payload), mime_type
    except Exception:
        raise AudioNoteError('Nieprawidłowe dane nagrania.')
