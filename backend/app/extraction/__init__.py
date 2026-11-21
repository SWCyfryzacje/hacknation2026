"""Wybór ekstraktora na podstawie zweryfikowanego typu MIME."""

from app.config import Settings
from app.extraction.model import ExtractedDocument, Line
from app.extraction.ocr import OcrEngine
from app.files.formats import Mime
from app.files.validation import ValidatedFile

__all__ = ["ExtractedDocument", "Line", "extract"]


def extract(file: ValidatedFile, settings: Settings, ocr: OcrEngine | None) -> ExtractedDocument:
    # Importy wewnątrz gałęzi: ciężkie biblioteki ładowane tylko, gdy są potrzebne.
    match file.mime:
        case Mime.DOCX:
            from app.extraction.word import extract_docx
            return extract_docx(file.data)
        case Mime.DOC:
            from app.extraction.word import extract_doc
            return extract_doc(file.data, soffice=settings.libreoffice_binary, timeout_s=settings.conversion_timeout_s)
        case Mime.PDF:
            from app.extraction.pdf import extract_pdf
            pdf_ocr = (lambda data: ocr(data, Mime.PDF, file.filename)) if ocr else None
            return extract_pdf(file.data, max_pages=settings.max_pdf_pages, ocr=pdf_ocr)
        case Mime.XLSX:
            from app.extraction.spreadsheet import extract_xlsx
            return extract_xlsx(file.data)
        case Mime.ODS:
            from app.extraction.spreadsheet import extract_ods
            return extract_ods(file.data)
        case Mime.JPEG | Mime.PNG:
            from app.errors import ConversionUnavailable
            if ocr is None:
                raise ConversionUnavailable("Skany wymagają OCR, który jest wyłączony (OCR_ENABLED=false).")
            return ExtractedDocument(lines=ocr(file.data, file.mime, file.filename),
                                     source_format=file.mime.name.lower(), used_ocr=True)
