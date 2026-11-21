"""OCR skanów (JPG/PNG) i PDF-ów bez warstwy tekstowej.

Silniki próbowane po kolei: Eden AI (jeśli skonfigurowano klucz), potem lokalny Tesseract.
"""

import io
import shutil
from dataclasses import dataclass, field
from typing import Protocol

from PIL import Image, ImageOps

from app.ai.edenai import AIError, EdenAIClient
from app.errors import ConversionUnavailable, ExtractionFailed
from app.extraction.model import Line
from app.extraction.text import make_lines
from app.files.formats import Mime

Image.MAX_IMAGE_PIXELS = 80_000_000  # ochrona przed "decompression bomb"
_MIN_WIDTH = 1600  # małe skany powiększamy — Tesseract radzi sobie lepiej przy ~300 DPI


class OcrEngine(Protocol):
    name: str

    def __call__(self, data: bytes, mime: Mime, filename: str) -> list[Line]: ...


@dataclass
class EdenAIOcr:
    client: EdenAIClient
    model: str
    language: str | None = "pl"
    name: str = "edenai"

    def __call__(self, data: bytes, mime: Mime, filename: str) -> list[Line]:
        file_id = self.client.upload(data, filename, mime.value)
        return make_lines(self.client.ocr(file_id, self.model, self.language))


@dataclass
class TesseractOcr:
    languages: str = "pol"
    dpi: int = 300
    max_pages: int = 30
    name: str = "tesseract"

    @staticmethod
    def available() -> bool:
        return shutil.which("tesseract") is not None

    def __call__(self, data: bytes, mime: Mime, filename: str) -> list[Line]:
        if not self.available():
            raise ConversionUnavailable("OCR wymaga programu Tesseract (brak w środowisku).")
        if mime is Mime.PDF:
            import pypdfium2 as pdfium

            pdf = pdfium.PdfDocument(data)
            try:
                lines: list[Line] = []
                for i in range(min(len(pdf), self.max_pages)):
                    lines += self._image(pdf[i].render(scale=self.dpi / 72).to_pil(), page=i + 1)
                return lines
            finally:
                pdf.close()
        try:
            image = Image.open(io.BytesIO(data))
            image.load()
        except Exception as exc:
            raise ExtractionFailed(f"Nie udało się odczytać obrazu: {exc}") from exc
        return self._image(image)

    def _image(self, image: Image.Image, page: int = 1) -> list[Line]:
        import pytesseract

        img = ImageOps.exif_transpose(image).convert("L")
        if img.width < _MIN_WIDTH:
            img = img.resize((_MIN_WIDTH, int(img.height * _MIN_WIDTH / img.width)), Image.Resampling.LANCZOS)
        # psm 4: pojedyncza kolumna tekstu o zmiennej wielkości — typowy układ formularza.
        return make_lines(pytesseract.image_to_string(img, lang=self.languages, config="--psm 4"), page=page)


@dataclass
class OcrChain:
    """Próbuje silników po kolei; zapamiętuje, który zadziałał, i dlaczego poprzednie nie."""

    engines: list[OcrEngine]
    used: str | None = None
    warnings: list[str] = field(default_factory=list)

    def __call__(self, data: bytes, mime: Mime, filename: str) -> list[Line]:
        errors: list[str] = []
        for engine in self.engines:
            try:
                lines = engine(data, mime, filename)
            except (AIError, ConversionUnavailable) as exc:
                errors.append(f"{engine.name}: {exc}")
                continue
            self.used = engine.name
            if errors:
                self.warnings.append("OCR: " + "; ".join(errors))
            return lines
        raise ConversionUnavailable("Brak działającego silnika OCR. " + "; ".join(errors))
