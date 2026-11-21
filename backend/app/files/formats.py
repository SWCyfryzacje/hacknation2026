"""Obsługiwane formaty wejściowe."""

from enum import StrEnum


class Mime(StrEnum):
    PDF = "application/pdf"
    DOC = "application/msword"
    DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ODS = "application/vnd.oasis.opendocument.spreadsheet"
    XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    JPEG = "image/jpeg"
    PNG = "image/png"


EXTENSION_TO_MIME: dict[str, Mime] = {
    ".pdf": Mime.PDF,
    ".doc": Mime.DOC,
    ".docx": Mime.DOCX,
    ".ods": Mime.ODS,
    ".xlsx": Mime.XLSX,
    ".jpg": Mime.JPEG,
    ".jpeg": Mime.JPEG,
    ".png": Mime.PNG,
}

# Wymaganie traktuje „DOC (.doc .docx)” jako jeden format: plik .doc z zawartością DOCX (częste w BIP,
# także w materiałach wyzwania) jest poprawny — przetwarzamy go według faktycznej zawartości.
_WORD = frozenset({Mime.DOC, Mime.DOCX})
COMPATIBLE: dict[Mime, frozenset[Mime]] = {Mime.DOC: _WORD, Mime.DOCX: _WORD}

# Nagłówki Content-Type wysyłane przez klientów, które uznajemy za równoważne.
DECLARED_ALIASES: dict[Mime, frozenset[str]] = {
    Mime.JPEG: frozenset({"image/jpg", "image/pjpeg"}),
    Mime.PNG: frozenset({"image/x-png"}),
    Mime.PDF: frozenset({"application/x-pdf"}),
    Mime.DOC: frozenset({"application/doc", "application/vnd.ms-word"}),
}

# Typy, które nic nie mówią o zawartości (np. curl bez -F type=...).
GENERIC_DECLARED = frozenset({"", "application/octet-stream", "binary/octet-stream"})
