"""Wspólna reprezentacja tekstu wyciągniętego z dowolnego formatu wejściowego."""

from dataclasses import dataclass, field


@dataclass(slots=True)
class Line:
    """Jedna logiczna linia dokumentu (akapit, wiersz tabeli, linia OCR)."""

    text: str
    list_item: bool = False  # element listy numerowanej/punktowanej albo pole wyboru ☐
    cells: list[str] | None = None  # komórki, gdy linia pochodzi z wiersza tabeli/arkusza
    page: int = 1


@dataclass(slots=True)
class ExtractedDocument:
    lines: list[Line]
    source_format: str
    used_ocr: bool = False
    warnings: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(line.text for line in self.lines)
