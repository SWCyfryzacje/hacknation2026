import datetime as dt

import jwt

from app.generator.checks import check_form
from tests.conftest import SECRET, make_image, make_ods, make_xlsx

DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def test_health_is_public(client):
    assert client.get("/health").json()["status"] == "ok"


def test_convert_requires_token(client, sample_docx):
    r = client.post("/api/v1/forms/convert", files={"file": ("w.docx", sample_docx, DOCX)})
    assert r.status_code == 401
    assert r.headers["content-type"].startswith("application/problem+json")


def test_rejects_expired_and_forged_tokens(client, sample_docx):
    past = dt.datetime.now(dt.UTC) - dt.timedelta(hours=1)
    for token in (jwt.encode({"sub": "x", "exp": past}, SECRET, algorithm="HS256"),
                  jwt.encode({"sub": "x", "exp": past + dt.timedelta(hours=2)}, "inny-klucz-" * 4, algorithm="HS256"),
                  jwt.encode({"sub": "x"}, SECRET, algorithm="HS256")):  # brak exp
        r = client.post("/api/v1/forms/convert", headers={"Authorization": f"Bearer {token}"},
                        files={"file": ("w.docx", sample_docx, DOCX)})
        assert r.status_code == 401


def test_convert_docx_returns_valid_form(client, auth, sample_docx):
    r = client.post("/api/v1/forms/convert", headers=auth, files={"file": ("wniosek.docx", sample_docx, DOCX)})
    assert r.status_code == 200, r.text
    form = r.json()
    assert form["title"] == "Wniosek o wydanie zaświadczenia"
    assert [t["type"] for t in form["tabs"]][-1] == "FINISH"
    assert check_form(form) == []
    assert r.headers["X-Analyzer"] == "rules"


def test_convert_with_report(client, auth, sample_docx):
    r = client.post("/api/v1/forms/convert?report=true", headers=auth,
                    files={"file": ("wniosek.docx", sample_docx, DOCX)})
    body = r.json()
    assert set(body) == {"form", "report"}
    assert body["report"]["issues"] == []
    assert body["report"]["analysis"]["authority"] == "Urząd Miasta i Gminy Młynary"


def test_spreadsheets_are_converted(client, auth):
    rows = [["WNIOSEK O WYNAJEM SALI"], ["Liczba uczestników:", "……………………"]]
    for name, data in (("a.xlsx", make_xlsx(rows)), ("a.ods", make_ods(rows))):
        r = client.post("/api/v1/forms/convert", headers=auth, files={"file": (name, data)})
        assert r.status_code == 200, r.text
        assert check_form(r.json()) == []


def test_upload_errors(client, auth):
    cases = [
        (("a.gif", b"GIF89a", "image/gif"), 415),
        (("a.pdf", make_image("PNG"), "application/pdf"), 415),
        (("zły;plik.pdf", b"%PDF-1.4", "application/pdf"), 422),
        (("duzy.pdf", b"%PDF-1.4" + b"0" * (3 * 1024 * 1024), "application/pdf"), 413),
    ]
    for file, status in cases:
        r = client.post("/api/v1/forms/convert", headers=auth, files={"file": file})
        assert r.status_code == status, (file[0], r.text)
        assert r.json()["detail"]


def test_scan_without_ocr_engine_is_reported(client, auth, monkeypatch):
    monkeypatch.setattr("app.extraction.ocr.TesseractOcr.available", staticmethod(lambda: False))
    r = client.post("/api/v1/forms/convert", headers=auth, files={"file": ("skan.png", make_image("PNG"), "image/png")})
    assert r.status_code == 503
