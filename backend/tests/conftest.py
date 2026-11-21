import datetime as dt
import io
import json
import os
import zipfile
from pathlib import Path

import docx
import jwt
import openpyxl
import pytest
from fastapi.testclient import TestClient
from PIL import Image

SECRET = "test-secret-which-is-long-enough-for-hs256"

# Testy nie mogą zależeć od lokalnego .env ani prawdziwego klucza Eden AI.
os.environ.update({"AUTH_ENABLED": "true", "JWT_SECRET": SECRET, "EDENAI_API_KEY": "", "MAX_FILE_SIZE_MB": "2"})


@pytest.fixture
def client(monkeypatch):
    from app.config import get_settings

    get_settings.cache_clear()
    from app.main import create_app

    with TestClient(create_app()) as c:
        yield c
    get_settings.cache_clear()


@pytest.fixture
def token() -> str:
    now = dt.datetime.now(dt.UTC)
    return jwt.encode({"sub": "test", "exp": now + dt.timedelta(minutes=5)}, SECRET, algorithm="HS256")


@pytest.fixture
def auth(token) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ------------------------------------------------------------ przykładowe pliki budowane w pamięci


def make_docx(paragraphs: list[str], numbered: tuple[int, ...] = ()) -> bytes:
    document = docx.Document()
    for i, text in enumerate(paragraphs):
        document.add_paragraph(text, style="List Number" if i in numbered else None)
    buf = io.BytesIO()
    document.save(buf)
    return buf.getvalue()


def make_xlsx(rows: list[list[str]]) -> bytes:
    wb = openpyxl.Workbook()
    for row in rows:
        wb.active.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def make_ods(rows: list[list[str]]) -> bytes:
    cells = "".join(
        "<table:table-row>" + "".join(f"<table:table-cell><text:p>{c}</text:p></table:table-cell>" for c in r)
        + "</table:table-row>" for r in rows)
    content = (
        '<?xml version="1.0" encoding="UTF-8"?><office:document-content '
        'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
        'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" '
        'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"><office:body><office:spreadsheet>'
        f'<table:table table:name="A">{cells}</table:table></office:spreadsheet></office:body></office:document-content>')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("mimetype", "application/vnd.oasis.opendocument.spreadsheet", compress_type=zipfile.ZIP_STORED)
        zf.writestr("content.xml", content)
    return buf.getvalue()


def make_image(fmt: str) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (20, 20), "white").save(buf, format=fmt)
    return buf.getvalue()


PDF_BYTES = (b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj "
             b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF")

SAMPLE_FORM = [
    "Urząd Miasta i Gminy Młynary",
    "………………………………..",
    "/ imię i nazwisko /",
    "………………………………..",
    "/ PESEL /",
    "WNIOSEK O WYDANIE ZAŚWIADCZENIA",
    "Proszę o wydanie zaświadczenia o:*",
    "okresie posiadania gospodarstwa rolnego",
    "nieposiadaniu gospodarstwa rolnego",
    "inne………………………………………",
    "Przewidywana ilość egzemplarzy: ……………………",
    "Roboty będą realizowane w terminie od dnia …………… do dnia ……………",
    "………………………………………",
    "/podpis/",
    "Opłata za wydanie zaświadczenia wynosi 17 zł.",
]
SAMPLE_NUMBERED = (7, 8, 9)


@pytest.fixture
def sample_docx() -> bytes:
    return make_docx(SAMPLE_FORM, SAMPLE_NUMBERED)


def materials_dir() -> Path | None:
    """Katalog z materiałami konkursowymi (nie trafiają do repozytorium)."""
    path = Path(os.environ.get("FORMS_MATERIALS_DIR", Path(__file__).parents[2] / "materials"))
    return path if path.is_dir() else None


def reference_jsons() -> list[Path]:
    root = materials_dir()
    return sorted(root.rglob("konfiguracja_form_*.json")) if root else []


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))
