import pytest
from fastapi.testclient import TestClient

from app.generator.checks import check_form

DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@pytest.fixture
def make_client(monkeypatch):
    """Klient z dodatkowymi zmiennymi środowiskowymi (ustawianymi przed odczytem konfiguracji)."""
    from app.config import get_settings
    from app.main import create_app

    clients = []

    def factory(**env: str) -> TestClient:
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        get_settings.cache_clear()
        client = TestClient(create_app())
        clients.append(client)
        return client

    yield factory
    for c in clients:
        c.close()
    get_settings.cache_clear()


def test_index_page_is_served(make_client):
    r = make_client().get("/")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert 'id="login-form"' in r.text and "/api/v1/forms/convert" in r.text
    assert "http://" not in r.text and "https://" not in r.text  # brak zasobów zewnętrznych


def test_index_page_can_be_disabled(make_client):
    assert make_client(UI_ENABLED="false").get("/").status_code == 404


def test_login_issues_token_that_works_for_convert(make_client, sample_docx):
    client = make_client(AUTH_USERNAME="urzednik", AUTH_PASSWORD="tajne-haslo")
    assert client.get("/api/v1/auth/config").json() == {"authEnabled": True, "loginConfigured": True}

    r = client.post("/api/v1/auth/token", json={"username": "urzednik", "password": "tajne-haslo"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["token_type"] == "bearer" and body["expires_in"] == 480 * 60

    r = client.post("/api/v1/forms/convert", headers={"Authorization": f"Bearer {body['access_token']}"},
                    files={"file": ("wniosek.docx", sample_docx, DOCX)})
    assert r.status_code == 200, r.text
    assert check_form(r.json()) == []


@pytest.mark.parametrize(("username", "password"), [("urzednik", "zle"), ("ktos", "tajne-haslo")])
def test_wrong_credentials_are_rejected(make_client, username, password):
    client = make_client(AUTH_USERNAME="urzednik", AUTH_PASSWORD="tajne-haslo")
    r = client.post("/api/v1/auth/token", json={"username": username, "password": password})
    assert r.status_code == 401
    assert r.json()["detail"] == "Nieprawidłowy login lub hasło."


def test_login_without_configuration(make_client, monkeypatch):
    monkeypatch.delenv("AUTH_USERNAME", raising=False)
    monkeypatch.delenv("AUTH_PASSWORD", raising=False)
    client = make_client(AUTH_USERNAME="", AUTH_PASSWORD="")
    assert client.get("/api/v1/auth/config").json()["loginConfigured"] is False
    r = client.post("/api/v1/auth/token", json={"username": "a", "password": "b"})
    assert r.status_code == 503


def test_preview_assets_are_served_locally(make_client):
    client = make_client()
    page = client.get("/").text
    assert 'src="/static/vendor/jsonata.min.js"' in page
    assert 'id="tab-preview"' in page and 'id="open-json"' in page and 'id="download-dicts"' in page
    lib = client.get("/static/vendor/jsonata.min.js")
    assert lib.status_code == 200 and "javascript" in lib.headers["content-type"]
    assert lib.text.startswith("/*! JSONata 2.2.2 | MIT License")


def test_static_files_disabled_with_ui(make_client):
    assert make_client(UI_ENABLED="false").get("/static/vendor/jsonata.min.js").status_code == 404


def test_health_reports_configured_models(make_client):
    client = make_client(EDENAI_API_KEY="klucz-testowy", LLM_MODEL="google/gemma-4-31b-it", OCR_MODEL="ocr/ocr/google")
    body = client.get("/health").json()
    assert body["llm"] is True and body["llmModel"] == "google/gemma-4-31b-it" and body["ocrModel"] == "ocr/ocr/google"
    assert "klucz" not in str(body)  # klucz nigdy nie trafia do odpowiedzi


def test_health_without_llm(make_client):
    body = make_client(EDENAI_API_KEY="klucz-testowy", LLM_ENABLED="false").get("/health").json()
    assert body["llm"] is False and body["llmModel"] is None
