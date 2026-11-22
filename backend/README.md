# Formularze AI

Usługa REST, która przyjmuje blankiet formularza urzędowego (PDF, DOC, DOCX, ODS, XLSX, JPG, JPEG, PNG),
analizuje go i zwraca **konfigurację eUsługi w formacie JSON**. Format jest zgodny z eksportami z systemu docelowego
(`title` → `tabs` → sekcje → pola, warunki `states` w JSONacie, przepływ `flow.links`).

Rozwiązanie wyzwania HackNation 2026 „Cyfryzacja formularzy” (Centralny Ośrodek Informatyki).
Szczegółowy opis architektury: [ARCHITEKTURA.md](ARCHITEKTURA.md).

## Jak to działa

```
plik ─► walidacja ─► ekstrakcja tekstu ─► analiza ─────────────► generator ─► kontrola reguł ─► JSON
        (nazwa,      DOCX: python-docx     model językowy          sekcje predefiniowane
         rozmiar,    DOC: LibreOffice      (Eden AI) albo reguły    ze „Standardów” +
         MIME z      XLSX/ODS: arkusze     ▼                        przedmiot wniosku
         zawartości) PDF: pypdfium2       opis formularza:
                     skany: OCR Eden AI    tytuł, adresat, kto składa,
                     lub Tesseract         strony/sekcje/pola, zależności,
                                           oświadczenia, opłaty, słowniki
```

**Podział pracy między AI a kod.** Model językowy rozpoznaje tylko to, co jest specyficzne dla danego wniosku:
pola przedmiotu wniosku (typy, opcje, walidatory, słowniki, dane inicjalne), zależności między polami, oświadczenia,
informacje o opłacie i to, kto może złożyć wniosek. Sekcje powtarzalne opisane w „Standardach i dobrych praktykach”
(urząd/organ, podmiot wniosku, Twoje dane z MLPZ, adres z krajem i TERYT, dane innej osoby, dane podmiotu,
pełnomocnictwo, opłata skarbowa za pełnomocnictwo, dane do kontaktu, zgody, podgląd) dokłada deterministyczny
generator. Dzięki temu wynik jest zgodny ze standardem niezależnie od jakości odpowiedzi modelu.

**Odporność.** Bez klucza Eden AI albo przy błędzie API usługa przechodzi na analizę regułową (wykropkowania,
podpisy pod polami, listy opcji, „☐ opcja”, „wynajem/użyczenie*”, listy załączników i oświadczeń) i lokalny OCR
Tesseract. Każda odpowiedź przechodzi kontrolę reguł (`app/generator/checks.py`), a problemy trafiają do raportu.

**Deterministyczne identyfikatory.** UUID są wyliczane (UUIDv5) z treści pliku, więc ten sam plik zawsze daje
ten sam JSON. To ułatwia porównywanie wyników i testy.

## Szybki start (Docker)

```bash
cd backend
cp .env.example .env          # uzupełnij JWT_SECRET, AUTH_PASSWORD (i opcjonalnie EDENAI_API_KEY)
docker build -t formularze-ai:0.1.0 .
docker run --rm -p 8000:8000 --env-file .env --read-only --tmpfs /tmp --tmpfs /home/app formularze-ai:0.1.0
```

albo `docker compose up --build`.

### Wybór modelu językowego (docker-compose.yml)

Model i OCR ustawia się w sekcji `environment` pliku `docker-compose.yml` (ma pierwszeństwo przed `.env`, więc
sekrety zostają w `.env`, a model zmienia się w jednym, widocznym miejscu):

```yaml
    environment:
      LLM_MODEL: "mistral/mistral-large-4-0@eu"     # np. mistral/mistral-medium-3.5@eu, google/gemma-4-31b-it
      LLM_FALLBACK_MODELS: '["mistral/mistral-medium-3.5@eu"]'
      LLM_ENABLED: "true"                           # "false" = analiza regułowa, zero wywołań Eden AI
      OCR_MODEL: "ocr/ocr/mistral"
```

Po zmianie: `docker compose up -d`. Aktywny model widać w `GET /health` (`llmModel`, `ocrModel`).
Lista modeli: katalog Eden AI (https://app.edenai.run/models) lub `curl -s https://api.edenai.run/v3/models`.

Bez LibreOffice (mniejszy obraz, bez obsługi `.doc`): `docker build --build-arg WITH_LIBREOFFICE=false …`.

Dokumentacja OpenAPI (Swagger UI): http://localhost:8000/docs. Frontend dla urzędnika: kontener `frontend` (http://localhost).

### Obraz Docker

- oficjalny obraz bazowy `python:3.14.9-alpine3.24`, wersja przypięta jawnie (bez `latest`),
- budowanie dwuetapowe: kompilatory zostają w etapie budowania,
- proces działa na dedykowanym użytkowniku `app` bez uprawnień,
- udostępniony tylko port `8000`,
- sekrety (`JWT_SECRET`, `EDENAI_API_KEY`) podaje się wyłącznie przy uruchomieniu (`--env-file` / `-e`),
  nie są zapisane w obrazie,
- działa z systemem plików tylko do odczytu (`--read-only` + `tmpfs` na `/tmp`).

## Uruchomienie lokalne (bez Dockera)

Wymagany Python 3.14+. Opcjonalnie `tesseract` z językiem polskim (skany bez Eden AI) i `soffice`
z LibreOffice (pliki `.doc`).

```bash
cd backend
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env                               # uzupełnij JWT_SECRET
uvicorn app.main:app --reload
pytest                                             # testy
```

Token do testów: `python -m app.token_cli --sub urzednik --hours 8`.

Przetwarzanie wsadowe całego katalogu (wyniki + raporty + słowniki, opcjonalny limit wywołań modelu):

```bash
python scripts/convert_dir.py formularze/ wyniki/ --max-llm-calls 15
python scripts/compare.py wyniki/wniosek.docx.json referencja.json   # porównanie z eksportem referencyjnym
```

## Frontend i logowanie

Interfejs dla urzędnika to osobny kontener `frontend` (React + nginx, port 80, katalog `web/` w repozytorium),
który korzysta wyłącznie z REST API opisanego niżej. Backend na porcie 8000 nie serwuje strony — udostępnia tylko
REST API i dokumentację OpenAPI (`/docs`).

Logowanie konfiguruje się zmiennymi `AUTH_USERNAME` i `AUTH_PASSWORD` (hasło podawane tylko przy uruchomieniu,
jak inne sekrety). Po zalogowaniu (`POST /api/v1/auth/token`) usługa wystawia token JWT ważny `JWT_TTL_MINUTES` minut.

## Serwer MCP dla asystentów AI (opcjonalny)

Dodatkowy interfejs [Model Context Protocol](https://modelcontextprotocol.io): kontener `mcp` (ten sam obraz,
`python -m app.mcp_server`, port **8100**, ścieżka `/mcp`, transport streamable HTTP, token JWT jak w REST API).

**Idea:** analizę formularza wykonuje zewnętrzny asystent AI użytkownika (Claude, ChatGPT, Copilot…) — **koszt
modelu ponosi użytkownik, nie urząd** — a nasz deterministyczny generator buduje z tej analizy konfigurację eUsługi
zgodną ze standardami (te same sekcje predefiniowane, kolejność kluczy, warunki JSONata i kontrola reguł co w REST API).
Odbiorcą są osoby projektujące formularze (urzędnicy cyfryzujący wnioski).

| Narzędzie | Działanie |
| --- | --- |
| `pobierz_standardy` | zasady projektowania (ten sam prompt co nasz model), schemat opisu formularza, przykład, typy pól, walidatory, słowniki, dane inicjalne |
| `zbuduj_formularz(opis)` | opis z analizy asystenta → kompletny JSON eUsługi + wynik kontroli reguł + zaproponowane słowniki |
| `sprawdz_formularz(formularz)` | kontrola dowolnej konfiguracji regułami formularzy eUsług |

**Ochrona danych:** każde wejście jest sprawdzane pod kątem danych osobowych (PESEL, NIP — z sumami kontrolnymi,
rachunek bankowy, seria i numer dowodu, e-mail, telefon). Po wykryciu narzędzie **odmawia** i wskazuje rządową
aplikację (`MCP_SAFE_APP_URL`), która przetwarza dokument na infrastrukturze urzędu. Ograniczenie: serwer nie cofnie
przesłania dokumentu do zewnętrznego modelu — odmowa zatrzymuje dalsze przetwarzanie i wskazuje bezpieczną ścieżkę.
Etykiety blankietu („Numer PESEL”, „Adres e-mail”) nie są danymi osobowymi i przechodzą bez przeszkód.

Podłączenie asystenta: adres `http://<serwer>:8100/mcp`, nagłówek `Authorization: Bearer <token>`
(token z `POST /api/v1/auth/token` lub `python -m app.token_cli`). Przykład dla Claude Desktop
(`claude_desktop_config.json`, przez most `mcp-remote` dla serwerów zdalnych):

```json
{
  "mcpServers": {
    "formularze-ai": {
      "command": "npx",
      "args": ["mcp-remote", "http://<serwer>:8100/mcp", "--header", "Authorization: Bearer <token>"]
    }
  }
}
```

Demonstracja całej ścieżki bez asystenta (standardy → budowa formularza → kontrola → odmowa przy danych osobowych):
`python scripts/mcp_demo.py --url http://<serwer>:8100/mcp --out wynik.json` — przykładowy wynik:
`wyniki/testy/mcp/przyklad_z_mcp.json`.

**Zgodność z wymaganiami wyzwania:** usługa **nie zależy** od MCP — REST API, frontend i analiza działają bez tego
kontenera (wersja bez MCP: gałąź `task-completed`). MCP jest dodatkowym interfejsem, który usługa udostępnia (biblioteka `mcp`, licencja MIT).

## REST API

### `POST /api/v1/forms/convert`

Konwertuje pojedynczy plik formularza. Wymaga nagłówka `Authorization: Bearer <JWT>`.

| Element | Opis |
| --- | --- |
| Body | `multipart/form-data`, pole `file` z jednym plikiem |
| `?report=true` | opcjonalnie: odpowiedź `{"form": …, "report": …}` z raportem z analizy |
| Odpowiedź 200 | konfiguracja formularza (JSON) gotowa do importu |
| Nagłówki odpowiedzi | `X-Analyzer: llm \| rules`, `X-Warnings: <liczba ostrzeżeń>` |

```bash
TOKEN=$(python -m app.token_cli)
curl -X POST http://localhost:8000/api/v1/forms/convert \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@Wniosek o wydanie zaświadczenia.pdf"
```

Raport (`?report=true`) zawiera: wykryty format, informację o OCR, użyty analizator i model, rozpoznany urząd
i warianty wnioskodawcy, statystyki (strony, sekcje, pola, pola warunkowe), **propozycje nowych słowników**,
ostrzeżenia i wynik kontroli reguł.

**Błędy** zwracane są jako `application/problem+json` (RFC 9457), np.
`{"type": "urn:formularze:unsupported_file_type", "title": "unsupported_file_type", "status": 415, "detail": "…"}`.

| Kod | Kiedy |
| --- | --- |
| 401 | brak tokenu, token wygasły, nieprawidłowy podpis, brak `exp` |
| 413 | plik większy niż `MAX_FILE_SIZE_MB` albo po rozpakowaniu większy niż `MAX_UNCOMPRESSED_MB` |
| 415 | nieobsługiwane rozszerzenie, zawartość niezgodna z rozszerzeniem lub zadeklarowanym typem |
| 422 | nieprawidłowa nazwa pliku, pusty albo nieczytelny dokument |
| 503 | brak silnika do konwersji (np. OCR, LibreOffice) |

### Walidacja pliku

- **Formaty:** `.pdf`, `.doc`, `.docx`, `.ods`, `.xlsx`, `.jpg`, `.jpeg`, `.png`.
- **Typ MIME jest wykrywany z zawartości**, a nie z rozszerzenia czy nagłówka klienta: sygnatury PDF/PNG/JPEG,
  kontener OLE2 ze strumieniem `WordDocument` (DOC), struktura ZIP (`word/document.xml` = DOCX,
  `xl/workbook.xml` = XLSX, `mimetype` = ODS). Wykryty typ musi zgadzać się z rozszerzeniem, a zadeklarowany
  `Content-Type` (jeśli inny niż `application/octet-stream`) z zawartością. Zgodnie z wymaganiem „DOC (.doc .docx)”
  oba rozszerzenia Worda tworzą jeden format: plik `.doc` z zawartością DOCX (spotykany w BIP i w materiałach
  wyzwania) jest przyjmowany i przetwarzany według faktycznej zawartości.
- **Nazwa pliku:** maks. 250 znaków, bez znaków `; : > < / \ | ' * % $` i znaków sterujących.
- **Rozmiar:** konfigurowalny (`MAX_FILE_SIZE_MB`) oraz ochrona przed „zip bomb” dla DOCX/XLSX/ODS.
- **Przechowywanie:** plik jest przetwarzany w pamięci; konwersja `.doc` używa katalogu tymczasowego usuwanego
  po żądaniu. Przy OCR przez Eden AI plik jest wgrywany do API organizatorów (retencja po stronie Eden AI).

### `POST /api/v1/auth/token`

Logowanie: body JSON `{"username": "…", "password": "…"}` → `{"access_token": "…", "token_type": "bearer",
"expires_in": 28800}`. Błędne dane → 401, brak konfiguracji `AUTH_USERNAME`/`AUTH_PASSWORD` → 503.

```bash
curl -X POST http://localhost:8000/api/v1/auth/token -H "Content-Type: application/json"   -d '{"username": "urzednik", "password": "…"}'
```

### Pozostałe endpointy

- `GET /` — strona WWW (bez uwierzytelniania; samo przetwarzanie wymaga tokenu),
- `GET /api/v1/auth/config` — czy wymagane jest logowanie (używane przez stronę WWW),
- `GET /health` — stan usługi i aktywne modele (`llmModel`, `ocrModel`; bez uwierzytelniania),
- `GET /api/v1/formats` — obsługiwane formaty i limit rozmiaru.

## Konfiguracja

Wszystkie parametry ustawia się zmiennymi środowiskowymi (lub w pliku `.env`); pełna lista w `.env.example`.

| Zmienna | Domyślnie | Opis |
| --- | --- | --- |
| `MAX_FILE_SIZE_MB` | `10` | maksymalny rozmiar pliku |
| `MAX_UNCOMPRESSED_MB` | `100` | limit po rozpakowaniu DOCX/XLSX/ODS |
| `MAX_PDF_PAGES` | `30` | maks. liczba analizowanych stron PDF |
| `AUTH_ENABLED` | `true` | wyłączenie JWT tylko do lokalnych testów |
| `JWT_SECRET` | – | klucz HMAC (wymagany, gdy brak `JWT_PUBLIC_KEY`) |
| `JWT_PUBLIC_KEY` | – | klucz publiczny PEM dla RS*/ES* |
| `JWT_ALGORITHMS` | `["HS256"]` | dozwolone algorytmy |
| `JWT_AUDIENCE`, `JWT_ISSUER` | – | opcjonalna weryfikacja `aud` / `iss` |
| `JWT_TTL_MINUTES` | `480` | ważność tokenów wystawianych przy logowaniu |
| `AUTH_USERNAME`, `AUTH_PASSWORD` | – | login i hasło urzędnika do strony WWW |
| `EDENAI_API_KEY` | – | klucz Eden AI; brak = analiza regułowa + Tesseract |
| `LLM_ENABLED` | `true` | analiza modelem językowym |
| `LLM_MODEL` | `mistral/mistral-large-4-0@eu` | model (otwarte wagi, przetwarzanie w UE) |
| `LLM_MAX_INPUT_CHARS` | `40000` | limit tekstu dokumentu wysyłanego do modelu |
| `LLM_MAX_OUTPUT_TOKENS` | `32000` | limit długości odpowiedzi modelu (duże formularze) |
| `OCR_ENABLED` | `true` | OCR skanów |
| `OCR_MODEL` | `ocr/ocr/mistral` | model OCR Eden AI |
| `OCR_LANGUAGE` | `pl` | język dokumentów dla OCR Eden AI |
| `OCR_LANGUAGES` | `pol` | języki zapasowego Tesseracta |
| `LLM_FALLBACK_MODELS` | `["mistral/mistral-medium-3.5@eu"]` | modele zapasowe (parametr `fallbacks` Eden AI) |
| `AI_TIMEOUT_S` | `300` | limit czasu wywołań Eden AI |
| `LIBREOFFICE_BINARY` | `soffice` | konwersja `.doc` |
| `FINISH_COMPONENT` | `TEXT_BLOCK` | komponent strony końcowej (`TEXT_BLOCK` jak w eksportach albo `INFO_SECTION`) |
| `VALIDATION_MODE` | `filled` | `filled` = walidatory w `validation` (np. `["REQUIRED","PESEL"]`), `empty` = puste tablice jak w eksportach |
| `CORS_ORIGINS` | `[]` | adresy frontendu |
| `MCP_PORT` | `8100` | port serwera MCP |
| `MCP_SAFE_APP_URL` | `http://localhost` | rządowa aplikacja, do której MCP odsyła przy danych osobowych |

## Decyzje projektowe

- **Źródłem prawdy są referencyjne eksporty z systemu** (wg mentorów COI). Kolejność kluczy, układ sekcji,
  `repeatingSectionGrid`, `states: []`, `TEXT_BLOCK` na stronie końcowej odwzorowują eksporty; „Reguły techniczne”
  traktujemy jako wskazówki. Test `test_reference_exports_pass_checker` pilnuje, żeby kontrola reguł nie była
  surowsza niż prawdziwy system.
- **Walidatory** (`REQUIRED`, `PESEL`, `NIP`, `REGON`, `ZIP_CODE`, `EMAIL`, …) są domyślnie wypełniane zgodnie z opisem
  pliku importu („tablica stringów przyjmująca nazwy predefiniowanych walidacji”); `VALIDATION_MODE=empty` daje
  puste tablice jak w eksportach.
- **Dane inicjalne:** „Twoje dane” z MLPZ (tylko do odczytu), adres i kontakt wstępnie uzupełniane z MLPZ
  (edytowalne, zgodnie ze „Standardami”); model może przypisać polom przedmiotu wniosku źródła `PESEL.*`,
  `PESEL_ADDRESS.*`, `MLPZ.*`.
- **Słowniki:** `Kraje` (domyślnie „Polska”), `TERYT_4G_DOWODOWY` dla adresu w Polsce; model może przypisać słowniki
  systemowe i zaproponować nowe (raport → `proposedDictionaries`).

## Licencje zależności

Wyłącznie licencje niecopyleftowe: FastAPI (MIT), Uvicorn (BSD-3), python-multipart (Apache-2.0), Pydantic (MIT),
PyJWT (MIT), mcp (MIT), python-docx (MIT), openpyxl (MIT), pypdfium2/PDFium (Apache-2.0/BSD-3), Pillow (MIT-CMU),
pytesseract (Apache-2.0), olefile (BSD-2), defusedxml (PSF-2.0), httpx (BSD-3). Programy zewnętrzne w obrazie:
Tesseract (Apache-2.0), LibreOffice (MPL-2.0, wywoływany jako osobny proces, bez linkowania).
