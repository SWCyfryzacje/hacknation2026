"""Ekstrakcja z DOCX (python-docx) oraz DOC (konwersja do DOCX przez LibreOffice headless)."""

import io
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import docx
from docx.oxml.ns import qn

from app.errors import ConversionUnavailable, ExtractionFailed
from app.extraction.model import ExtractedDocument, Line
from app.extraction.text import clean, make_lines

_W_P, _W_TBL, _W_R, _W_T = qn("w:p"), qn("w:tbl"), qn("w:r"), qn("w:t")
_W_TAB, _W_BR, _W_SYM, _W_NUMPR = qn("w:tab"), qn("w:br"), qn("w:sym"), qn("w:numPr")
_W_TXBX = qn("w:txbxContent")
_LIST_STYLE_RE = re.compile(r"list|akapitzlist|wypunkt|numer", re.I)
_W14_CHECKBOX ="{http://schemas.microsoft.com/office/word/2010/wordml}checkbox"


def extract_docx(data: bytes) -> ExtractedDocument:
    try:
        document = docx.Document(io.BytesIO(data))
    except Exception as exc:  # python-docx rzuca różne wyjątki dla uszkodzonych plików
        raise ExtractionFailed(f"Nie udało się odczytać dokumentu DOCX: {exc}") from exc

    lines: list[Line] = []
    for child in document.element.body.iterchildren():
        if child.tag == _W_P:
            lines.extend(_paragraph_lines(child))
        elif child.tag == _W_TBL:
            lines.extend(_table_lines(child))
    return ExtractedDocument(lines=_dedupe_adjacent(lines), source_format="docx")


def extract_doc(data: bytes, *, soffice: str, timeout_s: int) -> ExtractedDocument:
    """Stary format Worda konwertujemy do DOCX w katalogu tymczasowym usuwanym po żądaniu."""
    binary = shutil.which(soffice)
    if binary is None:
        raise ConversionUnavailable("Konwersja plików .doc wymaga LibreOffice (brak programu soffice).")
    with tempfile.TemporaryDirectory(prefix="formularze-") as tmp:
        src = Path(tmp) / "input.doc"
        src.write_bytes(data)
        profile = Path(tmp, "profile").as_uri()  # osobny profil = brak konfliktów przy równoległych żądaniach
        try:
            subprocess.run(
                [binary, f"-env:UserInstallation={profile}", "--headless", "--norestore",
                 "--convert-to", "docx", "--outdir", tmp, str(src)],
                check=True, capture_output=True, timeout=timeout_s,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            raise ExtractionFailed("Konwersja pliku .doc nie powiodła się.") from exc
        out = Path(tmp) / "input.docx"
        if not out.exists():
            raise ExtractionFailed("Konwersja pliku .doc nie zwróciła wyniku.")
        result = extract_docx(out.read_bytes())
    result.source_format = "doc"
    return result


def _paragraph_lines(p) -> list[Line]:
    text = _run_text(p)
    props = p.pPr
    style = props.find(qn("w:pStyle")) if props is not None else None
    style_id = style.get(qn("w:val"), "") if style is not None else ""
    # Numeracja bezpośrednio w akapicie albo przez styl listy („List Number”, „Akapitzlist” w polskim Wordzie).
    numbered = (props is not None and props.find(_W_NUMPR) is not None) or bool(_LIST_STYLE_RE.search(style_id))
    lines: list[Line] = []
    for i, line in enumerate(make_lines(text)):
        if i == 0 and numbered:
            line.list_item = True
        lines.append(line)
    # Pola tekstowe (text boxy) — np. adres urzędu umieszczony w ramce obok nagłówka.
    for box in p.iter(_W_TXBX):
        for inner in box.iter(_W_P):
            lines.extend(make_lines(_run_text(inner)))
    return lines


def _run_text(p) -> str:
    """Tekst akapitu z zachowaniem tabulatorów, łamań linii i symboli pól wyboru."""
    parts: list[str] = []
    for run in p.iterchildren(_W_R, qn("w:hyperlink"), qn("w:ins"), qn("w:smartTag")):
        runs = [run] if run.tag == _W_R else run.iter(_W_R)
        for r in runs:
            for el in r.iterchildren():
                if el.tag == _W_T:
                    parts.append(el.text or "")
                elif el.tag == _W_TAB:
                    parts.append("\t")
                elif el.tag == _W_BR:
                    parts.append("\n")
                elif el.tag == _W_SYM:
                    parts.append(chr(int(el.get(qn("w:char"), "0"), 16)))
            if next(r.iter(_W14_CHECKBOX), None) is not None:
                parts.append("☐")
    return "".join(parts)


def _table_lines(tbl) -> list[Line]:
    lines: list[Line] = []
    for tr in tbl.iter(qn("w:tr")):
        cells: list[str] = []
        for tc in tr.iterchildren(qn("w:tc")):
            text = clean(" ".join(_run_text(p) for p in tc.iter(_W_P)))
            if not cells or cells[-1] != text:  # komórki scalone poziomo powtarzają treść
                cells.append(text)
        non_empty = [c for c in cells if c]
        if non_empty:
            lines.append(Line(text=" | ".join(non_empty), cells=cells))
    return lines


def _dedupe_adjacent(lines: list[Line]) -> list[Line]:
    """Text boxy występują w DOCX podwójnie (DrawingML + zapasowy VML)."""
    out: list[Line] = []
    for line in lines:
        if out and out[-1].text == line.text and not line.list_item:
            continue
        out.append(line)
    return out
