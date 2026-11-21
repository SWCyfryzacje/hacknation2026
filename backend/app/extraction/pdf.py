"""Ekstrakcja z PDF (pypdfium2). Dokument bez warstwy tekstowej (skan) trafia do OCR."""

from collections.abc import Callable

import pypdfium2 as pdfium

from app.errors import ExtractionFailed
from app.extraction.model import ExtractedDocument, Line
from app.extraction.text import make_lines

_MIN_TEXT_CHARS_PER_PAGE = 25  # mniej znaków na stronie = najpewniej skan


def extract_pdf(data: bytes, *, max_pages: int, ocr: Callable[[bytes], list[Line]] | None) -> ExtractedDocument:
    try:
        pdf = pdfium.PdfDocument(data)
    except pdfium.PdfiumError as exc:
        raise ExtractionFailed(f"Nie udało się odczytać pliku PDF: {exc}") from exc

    lines: list[Line] = []
    warnings: list[str] = []
    try:
        pages = min(len(pdf), max_pages)
        if len(pdf) > max_pages:
            warnings.append(f"Przeanalizowano tylko pierwsze {max_pages} z {len(pdf)} stron.")
        chars = 0
        for index in range(pages):
            textpage = pdf[index].get_textpage()
            text = textpage.get_text_bounded()
            textpage.close()
            chars += len(text.strip())
            lines.extend(make_lines(text, page=index + 1))
    finally:
        pdf.close()

    if chars < _MIN_TEXT_CHARS_PER_PAGE * max(pages, 1):
        if ocr is None:
            warnings.append("PDF nie zawiera warstwy tekstowej, a OCR jest wyłączony.")
        else:
            return ExtractedDocument(lines=ocr(data), source_format="pdf", used_ocr=True, warnings=warnings)
    return ExtractedDocument(lines=lines, source_format="pdf", warnings=warnings)
