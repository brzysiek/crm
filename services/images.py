"""Przetwarzanie obrazów przed wysłaniem na Google Drive."""
import io

from PIL import Image

MAX_DIMENSION = 1600
JPEG_QUALITY = 90


def resize_jpeg_if_needed(content: bytes) -> bytes:
    """Jeśli dłuższy bok obrazu JPG przekracza MAX_DIMENSION px, przeskalowuje
    proporcjonalnie i zapisuje z jakością JPEG_QUALITY. W przeciwnym razie zwraca
    oryginalną zawartość bez zmian (i bez utraty jakości)."""
    try:
        img = Image.open(io.BytesIO(content))
        width, height = img.size
        if max(width, height) <= MAX_DIMENSION:
            return content

        scale = MAX_DIMENSION / max(width, height)
        new_size = (round(width * scale), round(height * scale))
        if img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')
        resized = img.resize(new_size, Image.LANCZOS)

        buf = io.BytesIO()
        resized.save(buf, format='JPEG', quality=JPEG_QUALITY)
        return buf.getvalue()
    except Exception:
        # Uszkodzony/niepoprawny plik obrazu — wyślij oryginał, niech walidacja
        # po stronie Drive/przeglądarki zdecyduje, co z nim zrobić.
        return content
