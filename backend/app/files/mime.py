"""Wykrywanie typu MIME na podstawie zawartości pliku (sygnatury, struktura kontenera).

Nie polegamy na rozszerzeniu ani nagłówku Content-Type od klienta — oba da się podrobić.
Własna detekcja zamiast libmagic: rozróżnia DOCX/XLSX/ODS (libmagic często zwraca
po prostu application/zip) i nie wymaga natywnej biblioteki.
"""

import io
import zipfile

import olefile

from app.files.formats import Mime

_PNG = b"\x89PNG\r\n\x1a\n"
_JPEG = b"\xff\xd8\xff"
_OLE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_ZIP = b"PK\x03\x04"
_ODS_MIMETYPE = b"application/vnd.oasis.opendocument.spreadsheet"


def detect_mime(data: bytes) -> Mime | None:
    """Zwraca wykryty typ albo None, jeśli zawartość nie jest żadnym z obsługiwanych formatów."""
    if data.startswith(_PNG):
        return Mime.PNG
    if data.startswith(_JPEG):
        return Mime.JPEG
    # Specyfikacja PDF dopuszcza śmieci przed nagłówkiem w pierwszych 1024 bajtach.
    if b"%PDF-" in data[:1024]:
        return Mime.PDF
    if data.startswith(_OLE):
        return _detect_ole(data)
    if data.startswith(_ZIP):
        return _detect_zip(data)
    return None


def _detect_ole(data: bytes) -> Mime | None:
    """Kontener OLE2 to też XLS/PPT/MSG — akceptujemy tylko dokumenty Worda."""
    try:
        with olefile.OleFileIO(io.BytesIO(data)) as ole:
            return Mime.DOC if ole.exists("WordDocument") else None
    except OSError:
        return None


def _detect_zip(data: bytes) -> Mime | None:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = set(zf.namelist())
            if "mimetype" in names:
                return Mime.ODS if zf.read("mimetype").strip() == _ODS_MIMETYPE else None
            if "[Content_Types].xml" in names:
                if "word/document.xml" in names:
                    return Mime.DOCX
                if "xl/workbook.xml" in names:
                    return Mime.XLSX
    except zipfile.BadZipFile:
        return None
    return None
