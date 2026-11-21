"""Ekstrakcja z arkuszy XLSX (openpyxl) i ODS (bezpośredni odczyt content.xml)."""

import io
import zipfile

import openpyxl
from defusedxml import ElementTree

from app.errors import ExtractionFailed
from app.extraction.model import ExtractedDocument, Line
from app.extraction.text import clean, make_lines

_MAX_REPEAT = 50  # ODS koduje puste wiersze/kolumny jako "powtórz N razy" — N bywa ogromne
_NS = {
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
}


def _row_to_lines(cells: list[str], page: int) -> list[Line]:
    while cells and not cells[-1]:
        cells.pop()
    non_empty = [c for c in cells if c]
    if not non_empty:
        return []
    if len(non_empty) == 1:  # pojedyncza komórka = zwykły akapit formularza
        return make_lines(non_empty[0], page=page)
    return [Line(text=" | ".join(non_empty), cells=cells, page=page)]


def extract_xlsx(data: bytes) -> ExtractedDocument:
    try:
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except Exception as exc:
        raise ExtractionFailed(f"Nie udało się odczytać pliku XLSX: {exc}") from exc
    lines: list[Line] = []
    try:
        for page, ws in enumerate(wb.worksheets, start=1):
            for row in ws.iter_rows(values_only=True):
                cells = [clean(str(v)) if v is not None else "" for v in row]
                lines.extend(_row_to_lines(cells, page))
    finally:
        wb.close()
    return ExtractedDocument(lines=lines, source_format="xlsx")


def extract_ods(data: bytes) -> ExtractedDocument:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            root = ElementTree.fromstring(zf.read("content.xml"))
    except Exception as exc:
        raise ExtractionFailed(f"Nie udało się odczytać pliku ODS: {exc}") from exc

    t = f"{{{_NS['table']}}}"
    lines: list[Line] = []
    for page, sheet in enumerate(root.iter(f"{t}table"), start=1):
        for row in sheet.iter(f"{t}table-row"):
            cells: list[str] = []
            for cell in row:
                if cell.tag not in (f"{t}table-cell", f"{t}covered-table-cell"):
                    continue
                text = clean("\n".join("".join(p.itertext()) for p in cell.iter(f"{{{_NS['text']}}}p")))
                repeat = min(int(cell.get(f"{t}number-columns-repeated", "1")), _MAX_REPEAT)
                cells.extend([text] * (repeat if text else min(repeat, 1)))
            row_lines = _row_to_lines(cells, page)
            repeat_rows = min(int(row.get(f"{t}number-rows-repeated", "1")), _MAX_REPEAT)
            lines.extend(row_lines * (repeat_rows if row_lines else 1))
    return ExtractedDocument(lines=lines, source_format="ods")
