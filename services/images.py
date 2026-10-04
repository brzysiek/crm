"""Przetwarzanie obrazów: załączniki na Google Drive i zdjęcia użytkowników."""
import io

from PIL import Image

MAX_DIMENSION = 1600
JPEG_QUALITY = 90
AVATAR_SIZE = 256
AVATAR_QUALITY = 82


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


def build_avatar(content: bytes, size: int = AVATAR_SIZE) -> bytes:
    """Robi ze zdjęcia kwadratową miniaturę size×size w JPEG-u. Kadruje środek,
    bo ikonka użytkownika jest kołem — skalowanie bez kadru spłaszczałoby twarz,
    a dopasowanie „contain" dawałoby paski tła w kółku. Zapis zawsze do JPEG-a:
    jeden format zamiast przenoszenia PNG/HEIC/WEBP przez bazę, a przy 256 px
    wynik to kilkanaście kB, więc data URI w kolumnie jest bezpieczne.
    Zgłasza ValueError, gdy pliku nie da się otworzyć jako obrazu — to jedyny
    moment, w którym użytkownik może to naprawić (wybierając inny plik)."""
    try:
        img = Image.open(io.BytesIO(content))
        img.load()
    except Exception as exc:
        raise ValueError('Nie udało się odczytać pliku jako obrazu.') from exc

    # EXIF-owa orientacja ze zdjęć z telefonu: bez tego portret z iPhone'a
    # ląduje obrócony o 90°.
    try:
        from PIL import ImageOps
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass

    if img.mode != 'RGB':
        img = img.convert('RGB')

    width, height = img.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    square = img.crop((left, top, left + side, top + side))
    if side != size:
        square = square.resize((size, size), Image.LANCZOS)

    buf = io.BytesIO()
    square.save(buf, format='JPEG', quality=AVATAR_QUALITY, optimize=True)
    return buf.getvalue()
