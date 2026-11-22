# Formularze AI — cyfryzacja formularzy urzędowych

Rozwiązanie wyzwania **HackNation 2026 „Cyfryzacja formularzy”** (Centralny Ośrodek Informatyki).

Usługa przyjmuje blankiet formularza urzędowego (**PDF, DOC, DOCX, ODS, XLSX, JPG, JPEG, PNG**), analizuje go z użyciem
AI i zwraca **konfigurację formularza eUsługi w formacie JSON**, gotową do importu w systemie docelowym — z podziałem na
strony tematyczne, sekcjami predefiniowanymi ze „Standardów”, walidacjami pól, słownikami, danymi inicjalnymi
i zależnościami między polami (warunki JSONata). Urzędnik korzysta z niej przez stronę WWW albo przez REST API.

```
 przeglądarka ──► frontend (nginx :80) ──/api/──► backend (FastAPI :8000) ──► Eden AI (model językowy, OCR)
                  React: wgrywanie plików,         walidacja pliku → ekstrakcja tekstu → analiza (LLM
                  podgląd formularza, JSON,         lub reguły) → generator JSON → kontrola reguł
                  raport, słowniki
```

Szczegóły techniczne: [backend/README.md](backend/README.md) (pełny opis usługi) i
[backend/ARCHITEKTURA.md](backend/ARCHITEKTURA.md) (architektura).

## Spis treści

1. [Wymagania](#wymagania)
2. [Budowanie obrazów Docker](#budowanie-obrazów-docker)
3. [Uruchomienie aplikacji](#uruchomienie-aplikacji)
4. [Konfiguracja](#konfiguracja)
5. [REST API](#rest-api)
6. [Bezpieczeństwo kontenerów](#bezpieczeństwo-kontenerów)
7. [Testy i dowód działania](#testy-i-dowód-działania)
8. [Struktura repozytorium](#struktura-repozytorium)
9. [Licencje](#licencje)
10. [Rozszerzenie: serwer MCP (branch `mcp`)](#rozszerzenie-serwer-mcp-branch-mcp)

## Wymagania

- Docker 24+ z Docker Compose v2 (`docker compose`).
- Klucz Eden AI (API udostępnione przez organizatorów) — **opcjonalnie**: bez klucza usługa działa w trybie
  regułowym z lokalnym OCR (Tesseract), w pełni na jednej maszynie.

## Budowanie obrazów Docker

Repozytorium zawiera dwa obrazy, budowane z jednego pliku `docker-compose.yml` w katalogu głównym:

| Usługa | Katalog | Obraz bazowy | Zawartość |
| --- | --- | --- | --- |
| `formularze` (backend) | [backend/](backend/) | `python:3.14.9-alpine3.24` | FastAPI, ekstrakcja (python-docx, openpyxl, pypdfium2), LibreOffice (pliki `.doc`), Tesseract z językiem polskim |
| `frontend` | [web/](web/) | `node:24.14.0-alpine` (budowanie) + `nginx` (serwowanie) | aplikacja React, proxy `/api/` → backend |

```bash
docker compose build              # oba obrazy
docker compose build formularze   # tylko backend (obraz formularze-ai)
docker compose build frontend     # tylko frontend
```

Sam backend bez Compose: `docker build -t formularze-ai:0.1.0 ./backend`
(bez LibreOffice, mniejszy obraz: `--build-arg WITH_LIBREOFFICE=false` — wtedy bez obsługi `.doc`).

## Uruchomienie aplikacji

1. Skopiuj plik konfiguracyjny i uzupełnij sekrety:
   ```bash
   cp backend/.env.example backend/.env
   ```
   W `backend/.env` ustaw co najmniej:
   - `JWT_SECRET` — losowy klucz podpisywania tokenów, np. `python -c "import secrets; print(secrets.token_urlsafe(48))"`,
   - `AUTH_USERNAME` i `AUTH_PASSWORD` — login i hasło urzędnika do strony WWW,
   - `EDENAI_API_KEY` — klucz Eden AI (opcjonalnie; bez niego tryb regułowy).
2. Uruchom:
   ```bash
   docker compose up -d --build
   ```
3. Otwórz:
   - **http://localhost** — strona WWW (logowanie → wgranie formularza → podgląd, JSON, raport),
   - **http://localhost:8000/docs** — interaktywna dokumentacja REST API (Swagger),
   - **http://localhost:8000/health** — stan usługi i aktywny model.

Zatrzymanie: `docker compose down`. Po zmianie `backend/.env` lub `docker-compose.yml`: `docker compose up -d`.

## Konfiguracja

Konfiguracja wyłącznie przez zmienne środowiskowe: **sekrety** w `backend/.env` (plik nie trafia do repozytorium ani
do obrazu — podawany przy uruchomieniu kontenera), **wybór modelu** w sekcji `environment` pliku `docker-compose.yml`
(ma pierwszeństwo przed `.env`). Pełna lista: [backend/.env.example](backend/.env.example).

| Zmienna | Domyślnie | Opis |
| --- | --- | --- |
| `MAX_FILE_SIZE_MB` | `10` | **maksymalny rozmiar przesyłanego pliku** |
| `MAX_UNCOMPRESSED_MB` | `100` | limit po rozpakowaniu DOCX/XLSX/ODS (ochrona przed „zip bomb”) |
| `MAX_PDF_PAGES` | `30` | maksymalna liczba analizowanych stron PDF |
| `AUTH_ENABLED` | `true` | **uwierzytelnianie JWT** (wyłączenie tylko do testów lokalnych) |
| `JWT_SECRET` | – | klucz HMAC do podpisywania tokenów (sekret) |
| `JWT_PUBLIC_KEY` | – | klucz publiczny PEM zamiast `JWT_SECRET` (RS256/ES256) |
| `JWT_ALGORITHMS` | `["HS256"]` | dozwolone algorytmy |
| `JWT_AUDIENCE`, `JWT_ISSUER` | – | opcjonalna weryfikacja `aud` / `iss` |
| `JWT_TTL_MINUTES` | `480` | ważność tokenu wystawianego przy logowaniu |
| `AUTH_USERNAME`, `AUTH_PASSWORD` | – | login i hasło do strony WWW (hasło = sekret) |
| `EDENAI_API_KEY` | – | **parametr integracyjny**: klucz Eden AI (sekret) |
| `LLM_MODEL` | `mistral/mistral-large-4-0@eu` | model językowy (w `docker-compose.yml`) |
| `LLM_FALLBACK_MODELS` | `["mistral/mistral-medium-3.5@eu"]` | modele zapasowe |
| `LLM_ENABLED` | `true` | `false` = tryb regułowy, zero wywołań Eden AI |
| `OCR_MODEL` | `ocr/ocr/mistral` | model OCR Eden AI dla skanów |
| `AI_TIMEOUT_S` | `300` | limit czasu wywołania modelu (duże formularze: kilka minut) |
| `OCR_LANGUAGES` | `pol` | języki zapasowego OCR Tesseract |
| `LIBREOFFICE_BINARY` | `soffice` | konwersja plików `.doc` |
| `VALIDATION_MODE` | `filled` | `filled` = walidatory w polach (`["REQUIRED","PESEL"]`), `empty` = puste jak w eksportach |
| `FINISH_COMPONENT` | `TEXT_BLOCK` | komponent strony końcowej (`TEXT_BLOCK` / `INFO_SECTION`) |
| `CORS_ORIGINS` | `[]` | dozwolone adresy frontendu przy dostępie bezpośrednim |

## REST API

Bazowy adres: `http://localhost:8000` (przez frontend: `http://localhost/api/…`). Format błędów: `application/problem+json`
(RFC 9457), np. `{"title": "unsupported_file_type", "status": 415, "detail": "…"}`.

| Metoda i ścieżka | Uwierzytelnianie | Opis |
| --- | --- | --- |
| `POST /api/v1/forms/convert` | Bearer JWT | **przesłanie pojedynczego pliku** (blankietu) → konfiguracja JSON |
| `POST /api/v1/auth/token` | – | logowanie `{"username", "password"}` → `{"access_token", "token_type", "expires_in"}` |
| `GET /api/v1/auth/config` | – | czy wymagane jest logowanie |
| `GET /api/v1/formats` | – | obsługiwane formaty i limit rozmiaru |
| `GET /health` | – | stan usługi, wersja, aktywny model (`llmModel`, `ocrModel`) |
| `GET /docs` | – | dokumentacja OpenAPI (Swagger UI) |

### `POST /api/v1/forms/convert`

- Body: `multipart/form-data`, pole **`file`** z jednym plikiem.
- Odpowiedź `200`: **dokument JSON z konfiguracją formularza** (`title`, `tabs` → sekcje → pola, `flow.links`).
- `?report=true`: odpowiedź `{"form": …, "report": …}` — raport z analizy (model, statystyki, ostrzeżenia, wynik
  kontroli reguł, zaproponowane nowe słowniki, zużycie tokenów, czas).
- Nagłówki odpowiedzi: `X-Analyzer` (`llm` / `rules`), `X-Warnings`.

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/token -H "Content-Type: application/json" \
  -d '{"username":"urzednik","password":"<hasło>"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
curl -X POST "http://localhost:8000/api/v1/forms/convert?report=true" \
  -H "Authorization: Bearer $TOKEN" -F "file=@wniosek.pdf"
```

### Walidacja przesyłanego pliku

| Reguła | Realizacja |
| --- | --- |
| **Typ pliku** | tylko `.pdf`, `.doc`, `.docx`, `.ods`, `.xlsx`, `.jpg`, `.jpeg`, `.png`; inaczej `415` |
| **MIME z zawartości** | typ wykrywany z treści pliku (sygnatury PDF/PNG/JPEG, kontener OLE2 dla DOC, struktura ZIP dla DOCX/XLSX/ODS) i porównywany z rozszerzeniem oraz nagłówkiem `Content-Type`; niezgodność → `415` (`.doc`/`.docx` = jeden format Worda, zgodnie z wymaganiem „DOC (.doc .docx)”) |
| **Nazwa pliku** | maks. **250 znaków**, bez znaków `; : > < / \ | ' * % $` → inaczej `422` |
| **Rozmiar** | konfigurowalny `MAX_FILE_SIZE_MB` → `413`; limit po rozpakowaniu formatów ZIP |
| **Przechowywanie** | plik przetwarzany **wyłącznie w pamięci** i w katalogu tymczasowym usuwanym po żądaniu (konwersja `.doc`); nic nie jest zapisywane trwale |

Kody błędów: `401` (brak / nieprawidłowy / wygasły token), `413`, `415`, `422`, `503` (brak silnika OCR / LibreOffice).

## Bezpieczeństwo kontenerów

| Wymaganie | Backend (`formularze`) |
| --- | --- |
| oficjalny obraz bazowy, lekka dystrybucja | `python:3.14.9-alpine3.24` |
| jawne wersjonowanie, bez `latest` | wersja Pythona i Alpine przypięta |
| dedykowany użytkownik bez uprawnień | proces działa jako `app` (uid 100) |
| tylko wymagane porty | `8000` |
| sekrety tylko w runtime | `env_file: ./backend/.env`, nic w obrazie (`.dockerignore`) |
| dodatkowo | system plików tylko do odczytu (`read_only` + `tmpfs`), `cap_drop: ALL`, `no-new-privileges`, healthcheck |

## Testy i dowód działania

- **Testy jednostkowe i integracyjne** (pytest, bez wywołań AI): `cd backend && pip install -e ".[dev]" && pytest`.
- **Testy REST API na wielu modelach i serwerach równolegle**:
  [backend/scripts/api_batch.py](backend/scripts/api_batch.py) — rejestr bez duplikatów (plik × model), pomiar czasu.
- **Nowe formularze spoza materiałów wyzwania**: [testy/formularze/](testy/formularze/) (8 wygenerowanych formularzy
  z kluczem odpowiedzi, każdy w 7 formatach, w tym skany) i [testy/bip/](testy/bip/) (prawdziwe formularze z BIP).
- **Wyniki**: [wyniki/](wyniki/) (konfiguracje JSON dla formularzy wyzwania) oraz
  [wyniki/testy/PORÓWNANIE.md](wyniki/testy/PORÓWNANIE.md) — 434 konwersje na 4 modelach otwartych
  (Mistral Large 4, Mistral Medium 3.5, Gemma 4 31B, gpt-oss-120b): skuteczność 96–100%, czasy 4–99 s,
  łączny koszt modeli ok. 3,3 USD.

## Struktura repozytorium

| Ścieżka | Zawartość |
| --- | --- |
| [backend/](backend/) | usługa REST (FastAPI), Dockerfile, testy, skrypty |
| [web/](web/) | frontend (React, Vite, nginx) |
| [docker-compose.yml](docker-compose.yml) | uruchomienie całości (backend + frontend) |
| [wyniki/](wyniki/) | wynikowe pliki JSON i wyniki testów |
| [testy/](testy/) | formularze testowe (wygenerowane i z BIP) |
| [form-examples/](form-examples/) | formularze z materiałów wyzwania |
| [task-context.md](task-context.md) | treść zadania |

## Licencje

Wyłącznie licencje niecopyleftowe — backend: FastAPI, Uvicorn, Pydantic, PyJWT, python-docx, openpyxl, httpx (MIT /
BSD / Apache-2.0), pypdfium2 (Apache-2.0 / BSD-3), Pillow (MIT-CMU), pytesseract (Apache-2.0), olefile (BSD-2),
defusedxml (PSF-2.0); programy w obrazie: Tesseract (Apache-2.0), LibreOffice (MPL-2.0, osobny proces). Szczegóły:
[backend/README.md](backend/README.md#licencje-zależności).

## Rozszerzenie: serwer MCP (branch `mcp`)

Drużyna na własną rękę rozbudowała ten projekt o **serwer MCP** (Model Context Protocol) **hostowany na Dockerze**,
który jest na branchu **`mcp`**. Serwer pozwala zewnętrznemu asystentowi AI (np. Claude, ChatGPT) przeanalizować
formularz własnym modelem — koszt modelu ponosi użytkownik asystenta, nie urząd — a nasz generator buduje z tej
analizy konfigurację JSON zgodną ze standardami. Wejścia z danymi osobowymi (PESEL, NIP, rachunek, dowód, e-mail,
telefon) są odrzucane z odesłaniem do rządowej aplikacji. Podstawowa usługa nie zależy od MCP.

Uruchomienie serwera MCP:

```bash
git checkout mcp
cp backend/.env.example backend/.env       # JWT_SECRET, AUTH_USERNAME, AUTH_PASSWORD
docker compose up -d --build               # backend :8000, frontend :80, serwer MCP :8100
```

- Adres serwera: `http://localhost:8100/mcp` (transport streamable HTTP), nagłówek `Authorization: Bearer <token>`
  (token z `POST /api/v1/auth/token`).
- Adres rządowej aplikacji, do której MCP odsyła przy danych osobowych: `MCP_SAFE_APP_URL` w `docker-compose.yml`.
- Demonstracja całej ścieżki: `cd backend && python scripts/mcp_demo.py --url http://localhost:8100/mcp`.
- Narzędzia: `pobierz_standardy`, `zbuduj_formularz`, `sprawdz_formularz` — opis w `backend/README.md` na branchu `mcp`.
