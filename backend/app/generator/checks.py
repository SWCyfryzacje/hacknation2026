"""Kontrola wygenerowanej konfiguracji względem reguł formularzy eUsług.

Uruchamiana na każdym wyniku (problemy trafiają do raportu) i w testach — także na
referencyjnych eksportach, żeby reguły nie były surowsze niż prawdziwy system.
"""

import re
from itertools import pairwise
from typing import Any

SECTION_TYPES = {"SECTION", "REPEATING_SECTION"}
INPUT_TYPES = {"TEXT_FIELD", "TEXTAREA", "NUMBER", "DATEPICKER", "RADIO", "CHECKBOX", "SELECT", "FILE_UPLOADER",
               "CONSENT_SECTION"}
PRESENTATION_TYPES = {"TEXT_BLOCK", "INFO_SECTION"}
CHOICE_TYPES = {"RADIO", "CHECKBOX", "SELECT"}
INITIAL_DATA_RE = re.compile(r"^(PESEL|PESEL_ADDRESS|MLPZ)\.[A-Za-z]+$")
_TAB_REF_RE = re.compile(r"tabs\['([^']+)' in title\]")
_TECH_REF_RE = re.compile(r"\['([^']+)' in field\.?[Tt]ech[Nn]ame\]")


def check_form(form: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    title = form.get("title") or ""
    if not title.strip():
        issues.append("Brak tytułu formularza.")
    if len(title) > 255:
        issues.append("Tytuł formularza przekracza 255 znaków.")

    tabs = form.get("tabs") or []
    if len(tabs) < 2:
        issues.append("Formularz musi mieć co najmniej dwie strony.")
    if tabs and tabs[-1].get("type") != "FINISH":
        issues.append("Ostatnia strona musi mieć typ FINISH.")
    for t in tabs[:-1]:
        if t.get("type") != "MAIN":
            issues.append(f"Strona '{t.get('title')}' powinna mieć typ MAIN.")

    tab_titles = [t.get("title") for t in tabs]
    if len(set(tab_titles)) != len(tab_titles):
        issues.append("Tytuły stron muszą być unikalne (JSONata adresuje strony po tytule).")

    ids: list[str] = []
    tech_names: list[str] = []
    queries: list[tuple[str, str]] = []

    for tab in tabs:
        ids.append(tab.get("id", ""))
        questions = tab.get("questions") or []
        if not questions:
            issues.append(f"Strona '{tab.get('title')}' nie zawiera żadnego pola.")
        for qn in questions:
            section = qn["field"]
            ids.append(section["id"])
            tech_names.append(section["techName"])
            queries += [(section["techName"], s.get("query", "")) for s in section.get("states") or []]
            if section["type"] not in SECTION_TYPES:
                issues.append(f"Pole '{section['techName']}' musi być zagnieżdżone w sekcji.")
                continue
            children = section.get("repeatingSectionGrid") or []
            if not children:
                issues.append(f"Sekcja '{section['techName']}' jest pusta.")
            for child_q in children:
                child = child_q["field"]
                ids.append(child["id"])
                tech_names.append(child["techName"])
                queries += [(child["techName"], s.get("query", "")) for s in child.get("states") or []]
                issues += _check_field(child, tab)

    if len(set(ids)) != len(ids):
        issues.append("Identyfikatory (id) nie są unikalne.")
    duplicates = sorted({t for t in tech_names if tech_names.count(t) > 1})
    if duplicates:
        issues.append(f"Powtarzające się nazwy techniczne: {', '.join(duplicates)}.")

    known_tech, known_tabs = set(tech_names), set(tab_titles)
    for owner, query in queries:
        for ref in _TAB_REF_RE.findall(query):
            if ref not in known_tabs:
                issues.append(f"Warunek pola '{owner}' odwołuje się do nieistniejącej strony '{ref}'.")
        for ref in _TECH_REF_RE.findall(query):
            if ref not in known_tech:
                issues.append(f"Warunek pola '{owner}' odwołuje się do nieistniejącego pola '{ref}'.")

    links = (form.get("flow") or {}).get("links") or []
    tab_ids = [t.get("id") for t in tabs]
    expected = list(pairwise(tab_ids))
    actual = [(link.get("source"), link.get("target")) for link in links]
    if not set(expected) <= set(actual):
        issues.append("Przepływ (flow.links) nie łączy wszystkich kolejnych stron.")
    return issues


def _check_field(field: dict[str, Any], tab: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    t, name = field.get("type"), field.get("techName")
    if t in SECTION_TYPES:
        issues.append(f"Sekcja '{name}' nie może być zagnieżdżona w innej sekcji.")
    if tab.get("type") == "FINISH" and t in INPUT_TYPES:
        issues.append(f"Strona końcowa nie może zawierać pola do wprowadzania danych ('{name}').")
    if t in CHOICE_TYPES and not field.get("options") and not field.get("dictionaryName"):
        issues.append(f"Pole wyboru '{name}' nie ma opcji ani słownika.")
    for opt in field.get("options") or []:
        if not {"id", "name"} <= set(opt):  # techName bywa pominięty w eksportach z systemu
            issues.append(f"Opcja pola '{name}' musi mieć id i name.")
    if field.get("defaultValueType") == "EXTERNAL_SYSTEM" and not INITIAL_DATA_RE.match(str(field.get("defaultValue"))):
        issues.append(f"Pole '{name}': nieprawidłowe źródło danych inicjalnych '{field.get('defaultValue')}'.")
    if t == "CONSENT_SECTION" and not (field.get("consentSectionConfig") or {}).get("consents"):
        issues.append(f"Sekcja zgód '{name}' nie zawiera zgód.")
    return issues
