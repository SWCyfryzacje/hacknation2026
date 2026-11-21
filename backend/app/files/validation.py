"""Walidacja przesyłanego pliku: nazwa, rozmiar, rozszerzenie i zgodność typu MIME z zawartością."""

import io
import zipfile
from dataclasses import dataclass
from pathlib import PurePath

from app.errors import EmptyFile, FileTooLarge, InvalidFileName, UnsupportedFileType
from app.files.formats import (
    DECLARED_ALIASES,
    EXTENSION_TO_MIME,
    GENERIC_DECLARED,
    Mime,
)
from app.files.mime import detect_mime

MAX_FILENAME_LENGTH = 250
FORBIDDEN_FILENAME_CHARS = frozenset(";:></\\|'*%$")


@dataclass(frozen=True, slots=True)
class ValidatedFile:
    filename: str
    mime: Mime
    data: bytes


def validate_filename(filename: str | None) -> str:
    if not filename or not filename.strip():
        raise InvalidFileName("Brak nazwy pliku.")
    if len(filename) > MAX_FILENAME_LENGTH:
        raise InvalidFileName(f"Nazwa pliku nie może przekraczać {MAX_FILENAME_LENGTH} znaków.")
    found = sorted({c for c in filename if c in FORBIDDEN_FILENAME_CHARS})
    if found:
        raise InvalidFileName(f"Nazwa pliku zawiera niedozwolone znaki: {' '.join(found)}")
    if any(ord(c) < 32 for c in filename):
        raise InvalidFileName("Nazwa pliku zawiera znaki sterujące.")
    return filename


def mime_for_extension(filename: str) -> Mime:
    ext = PurePath(filename).suffix.lower()
    try:
        return EXTENSION_TO_MIME[ext]
    except KeyError:
        allowed = ", ".join(sorted(EXTENSION_TO_MIME))
        raise UnsupportedFileType(f"Nieobsługiwane rozszerzenie '{ext or '(brak)'}'. Dozwolone: {allowed}.") from None


def validate_upload(
    filename: str | None,
    data: bytes,
    declared_type: str | None,
    *,
    max_size: int,
    max_uncompressed: int,
) -> ValidatedFile:
    name = validate_filename(filename)
    expected = mime_for_extension(name)

    if not data:
        raise EmptyFile("Plik jest pusty.")
    if len(data) > max_size:
        raise FileTooLarge(f"Plik przekracza dopuszczalny rozmiar {max_size / 1024 / 1024:g} MB.")

    detected = detect_mime(data)
    if detected is None:
        raise UnsupportedFileType("Zawartość pliku nie odpowiada żadnemu z obsługiwanych formatów.")
    if detected != expected:
        raise UnsupportedFileType(
            f"Zawartość pliku ({detected.value}) nie pasuje do rozszerzenia (oczekiwano {expected.value})."
        )

    declared = (declared_type or "").split(";")[0].strip().lower()
    if declared not in GENERIC_DECLARED and declared != detected and declared not in DECLARED_ALIASES.get(detected, ()):
        raise UnsupportedFileType(
            f"Zadeklarowany typ '{declared}' nie zgadza się z zawartością pliku ({detected.value})."
        )

    if detected in (Mime.DOCX, Mime.XLSX, Mime.ODS):
        _check_zip_bomb(data, max_uncompressed)

    return ValidatedFile(filename=name, mime=detected, data=data)


def _check_zip_bomb(data: bytes, limit: int) -> None:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        total = sum(info.file_size for info in zf.infolist())
    if total > limit:
        raise FileTooLarge("Dokument po rozpakowaniu przekracza dopuszczalny rozmiar.")
