"""Pośredni opis formularza: co analiza rozpoznała w dokumencie, niezależnie od formatu JSON.

Analizator (reguły, w przyszłości model językowy) wypełnia ten model, a generator
zamienia go na konfigurację eUsługi, dokładając sekcje predefiniowane ze „Standardów”.
"""

from dataclasses import dataclass, field
from enum import StrEnum


class Kind(StrEnum):
    TEXT = "TEXT_FIELD"
    TEXTAREA = "TEXTAREA"
    NUMBER = "NUMBER"
    DATE = "DATEPICKER"
    RADIO = "RADIO"
    CHECKBOX = "CHECKBOX"
    SELECT = "SELECT"
    FILE = "FILE_UPLOADER"
    TEXT_BLOCK = "TEXT_BLOCK"


@dataclass(eq=False)
class Condition:
    """Pole/sekcja jest widoczne, gdy w polu `field` wybrano `value`."""

    field: FieldSpec
    value: str


@dataclass(eq=False)  # tożsamość obiektu identyfikuje pole w warunkach
class FieldSpec:
    label: str
    kind: Kind = Kind.TEXT
    options: list[str] = field(default_factory=list)
    required: bool = True
    validators: list[str] = field(default_factory=list)  # np. PESEL, NIP, ZIP_CODE, EMAIL
    dictionary: str | None = None
    description: str | None = None  # treść HTML budowana z tekstu
    show_if: Condition | None = None
    search: bool = False
    initial_data: str | None = None  # np. "PESEL.birthDate" — pole tylko do odczytu zasilane z rejestru


@dataclass
class ProposedDictionary:
    """Propozycja nowego słownika (rozszerzenie opcjonalne II)."""

    name: str
    description: str
    values: list[str]
    used_by: list[str] = field(default_factory=list)


@dataclass(eq=False)
class SectionSpec:
    title: str
    fields: list[FieldSpec] = field(default_factory=list)
    description: str | None = None
    show_if: Condition | None = None


@dataclass(eq=False)
class PageSpec:
    title: str
    sections: list[SectionSpec] = field(default_factory=list)


@dataclass
class Applicant:
    """Kto może złożyć wniosek — steruje sekcją „Podmiot wniosku” (Standardy, s. 9–10)."""

    person: bool = True
    company: bool = False


@dataclass
class FormAnalysis:
    title: str
    authority: str | None = None
    authority_is_organ: bool = False
    applicant: Applicant = field(default_factory=Applicant)
    pages: list[PageSpec] = field(default_factory=list)
    statements: list[str] = field(default_factory=list)  # oświadczenia → sekcja zgód
    fee_info: list[str] = field(default_factory=list)  # opłata za samą usługę (nie za pełnomocnictwo)
    proposed_dictionaries: list[ProposedDictionary] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    analyzer: str = "rules"

    @property
    def field_count(self) -> int:
        return sum(len(s.fields) for p in self.pages for s in p.sections)
