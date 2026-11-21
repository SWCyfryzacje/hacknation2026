"""Normalizacja tekstu wspólna dla wszystkich ekstraktorów."""

import re

from app.extraction.model import Line

# Pola wyboru / punktory: znaki Unicode oraz prywatne kody czcionek Wingdings/Symbol
# (U+F000–U+F0FF), którymi Word i eksport do PDF rysują kratki i punktory.
CHECKBOX = "☐"
_BOX_CHARS = "☐☑☒□■▢❑❏◻◼○●◯"
_PRIVATE_RE = re.compile("[-]")
_BULLET_RE = re.compile(rf"^\s*[•·▪‣◦\-–—{_BOX_CHARS}]\s*")
_WS_RE = re.compile(r"[ \t   ]+")


def normalize_symbols(text: str) -> str:
    text = _PRIVATE_RE.sub(CHECKBOX, text)
    return re.sub(f"[{_BOX_CHARS}]", CHECKBOX, text)


def clean(text: str) -> str:
    text = normalize_symbols(text).replace("\r", "\n").replace("​", "")
    return _WS_RE.sub(" ", text).strip()


def make_lines(raw: str, *, page: int = 1) -> list[Line]:
    """Dzieli surowy tekst na linie, oznaczając wypunktowania i pola wyboru."""
    out: list[Line] = []
    for chunk in raw.splitlines():
        text = clean(chunk)
        if not text:
            continue
        bullet = _BULLET_RE.match(text)
        if bullet and len(text) > bullet.end():
            out.append(Line(text=text[bullet.end():].strip(), list_item=True, page=page))
        else:
            out.append(Line(text=text, page=page))
    return out
