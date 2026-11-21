"""Budowa węzłów JSON w dokładnie takiej postaci (i kolejności kluczy) jak w eksportach z systemu."""

import html
import re
import unicodedata
import uuid
from dataclasses import dataclass, field
from typing import Any

EMPTY_HTML = "<html><head></head><body></body></html>"
_NAMESPACE = uuid.UUID("6f1c2a8e-5b1d-4c39-9a51-0e3f1b7d2c44")


def to_html(text: str | None) -> str:
    if not text:
        return EMPTY_HTML
    paragraphs = "".join(f"<p>{html.escape(p)}</p>" for p in text.split("\n") if p.strip())
    return f"<html><head></head><body>{paragraphs}</body></html>"


def html_list(items: list[str]) -> str:
    li = "".join(f"<li>{html.escape(i)}</li>" for i in items)
    return f"<html><head></head><body><ul>{li}</ul></body></html>"


def slugify(text: str, max_len: int = 60) -> str:
    text = text.replace("ł", "l").replace("Ł", "L")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return (text[:max_len].rstrip("_") or "pole")


@dataclass
class IdFactory:
    """Deterministyczne UUID (v5): ten sam plik zawsze daje ten sam JSON — łatwe porównywanie wyników."""

    seed: str
    _tech: set[str] = field(default_factory=set)

    def uuid(self, *path: str) -> str:
        return str(uuid.uuid5(_NAMESPACE, ":".join((self.seed, *path))))

    def tech_name(self, label: str, prefix: str = "") -> str:
        base = slugify(f"{prefix} {label}" if prefix else label)
        name, n = base, 2
        while name in self._tech:
            name, n = f"{base}_{n}", n + 1
        self._tech.add(name)
        return name

    def reserve(self, name: str) -> str:
        if name in self._tech:
            return self.tech_name(name)
        self._tech.add(name)
        return name


def option(name: str) -> dict[str, str]:
    return {"id": name, "name": name, "techName": slugify(name)}


def node(
    *,
    id: str,
    type: str,
    tech_name: str,
    title: str = "",
    description: str | None = None,
    options: list[str] | None = None,
    validation: list[str] | None = None,
    read_only: bool = False,
    grid: list[dict[str, Any]] | None = None,
    states: list[dict[str, str]] | None = None,
    order: int = 0,
    tooltip: str = "",
    dictionary: str | None = None,
    multi_level_tree: bool | None = None,
    search_enabled: bool | None = None,
    default_value: Any = None,
    default_value_type: str | None = None,
    consent_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Pole formularza; kolejność kluczy odwzorowuje referencyjne eksporty."""
    out: dict[str, Any] = {"id": id, "type": type, "techName": tech_name, "title": title,
                           "description": description if description is not None else EMPTY_HTML}
    if dictionary is not None:
        out["dictionaryName"] = dictionary
    out["options"] = [option(o) for o in (options or [])]
    if multi_level_tree is not None:
        out["multiLevelTree"] = multi_level_tree
    out["validation"] = validation or []
    if search_enabled is not None:
        out["searchEnabled"] = search_enabled
    out["readOnly"] = read_only
    out["repeatingSectionGrid"] = grid or []
    if default_value is not None:
        out["defaultValue"] = default_value
    if default_value_type is not None:
        out["defaultValueType"] = default_value_type
    if consent_config is not None:
        out["consentSectionConfig"] = consent_config
    out["states"] = states or []
    out["questionOrder"] = order
    out["tooltipMessage"] = tooltip
    return out


def placed(field_node: dict[str, Any], y: int, rows: int = 1, **extra: Any) -> dict[str, Any]:
    """Umieszcza element w siatce: CSS grid-area = {y+1} / {x+1} / span {rows} / span {cols}."""
    return {"x": 0, "y": y, "rows": rows, "cols": 3, **extra, "field": field_node}
