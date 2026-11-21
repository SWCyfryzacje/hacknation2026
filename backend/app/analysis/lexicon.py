"""Słownik pojęć: rozpoznawanie typu pola, walidatorów i słowników na podstawie etykiety."""

import re
from dataclasses import dataclass

from app.analysis.model import Kind


@dataclass(frozen=True)
class FieldHint:
    kind: Kind | None = None
    validators: tuple[str, ...] = ()
    dictionary: str | None = None
    optional: bool = False
    description: str | None = None


def _rx(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE)


# Kolejność ma znaczenie — pierwsza pasująca reguła wygrywa.
_RULES: list[tuple[re.Pattern[str], FieldHint]] = [
    (_rx(r"\bpesel\b"), FieldHint(Kind.TEXT, ("PESEL",))),
    (_rx(r"\bnip\b"), FieldHint(Kind.TEXT, ("NIP",))),
    (_rx(r"\bregon\b"), FieldHint(Kind.TEXT, ("REGON",))),
    (_rx(r"kod(u)? pocztow"), FieldHint(Kind.TEXT, ("ZIP_CODE",))),
    (_rx(r"e-?mail|poczty elektronicznej"), FieldHint(Kind.TEXT, ("EMAIL",), optional=True)),
    (_rx(r"e-?doręcze"), FieldHint(Kind.TEXT, ("ADE",))),
    (_rx(r"\bepuap\b|skrytk"), FieldHint(Kind.TEXT, ("EPUAP",))),
    (_rx(r"seri[ai] i (nr|numer) dowodu|dowodu osobistego"), FieldHint(Kind.TEXT, ("SERIAL_NUMBER_ID_CARD",))),
    (_rx(r"telefon|\btel\b"), FieldHint(Kind.TEXT, optional=True)),
    (_rx(r"rachunk|nr konta|numer konta|iban"),
     FieldHint(Kind.TEXT, description="Numer rachunku bankowego (26 cyfr).")),
    (_rx(r"\bkraj\b|obywatelstw|państw[oa] urodzenia"), FieldHint(Kind.SELECT, dictionary="Kraje")),
    (_rx(r"\b(data|daty|dnia|termin\w*)\b"), FieldHint(Kind.DATE)),
    (_rx(r"\b(ilość|ilości|liczba|liczbę|kwot\w*|powierzchni\w*|długość|szerokość|wysokość|metraż|"
         r"m2|m²|zł|ha|hektar\w*|sztuk|osób|uczestników)\b"), FieldHint(Kind.NUMBER)),
    (_rx(r"uzasadnien|\bopis\w*|\bcel\b|uwagi|rodzaj robót|sposób|okoliczności|przyczyn"),
     FieldHint(Kind.TEXTAREA)),
]

_OPTIONAL_RE = _rx(r"jeżeli dotyczy|jeśli dotyczy|o ile|opcjonaln|nieobowiązkow|w przypadku|jeżeli|jeśli|\*\*")


def hint_for(label: str, context: str = "") -> FieldHint:
    text = f"{label} {context}"
    for pattern, hint in _RULES:
        if pattern.search(label):
            return hint
    for pattern, hint in _RULES:
        if hint.kind not in (Kind.TEXTAREA,) and pattern.search(text):
            return hint
    return FieldHint()


def is_optional(text: str) -> bool:
    return bool(_OPTIONAL_RE.search(text))
