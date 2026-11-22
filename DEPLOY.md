# Wdrożenie na serwerze i sprawdzenie działania

Instrukcja dla serwera Linux z Dockerem (np. Debian, serwer demonstracyjny `77.45.76.243`). Polecenia wykonuje się
na serwerze przez SSH, w katalogu repozytorium.

## 1. Pobranie kodu

```bash
cd ~/hacknation2026                 # katalog z repozytorium
git fetch origin
git checkout task-backend           # albo main / mcp — gałąź, którą wdrażamy
git pull
```

## 2. Konfiguracja (jednorazowo)

```bash
cp backend/.env.example backend/.env   # tylko jeśli pliku jeszcze nie ma
nano backend/.env
```

Ustaw: `JWT_SECRET` (losowy klucz), `AUTH_USERNAME`, `AUTH_PASSWORD` (silne hasło — serwer jest publiczny),
`EDENAI_API_KEY`, `AUTH_ENABLED=true`. Model językowy wybiera się w `docker-compose.yml` (`LLM_MODEL`).

## 3. Budowa i uruchomienie

```bash
docker compose up -d --build
```

Pierwsza budowa trwa kilka minut (LibreOffice i Tesseract w obrazie backendu, budowanie frontendu).

## 4. Sprawdzenie na serwerze

```bash
docker compose ps                         # wszystkie usługi: Up (healthy)
curl -s http://localhost:8000/health      # {"status":"ok", ..., "llm":true, "llmModel":"..."}
curl -sI http://localhost | head -1       # HTTP/1.1 200 OK  — frontend (nginx)
curl -s http://localhost/api/v1/formats   # backend przez proxy frontendu
docker compose exec formularze id         # uid=100(app) — backend bez uprawnień roota
docker compose exec frontend id           # uid=101(nginx) — frontend bez uprawnień roota
```

Logi: `docker compose logs -f formularze` (backend), `docker compose logs -f frontend`.

## 5. Sprawdzenie z zewnątrz (z własnego komputera)

- **http://77.45.76.243** — strona WWW: logowanie (`AUTH_USERNAME` / `AUTH_PASSWORD`) → wgranie formularza →
  podgląd, JSON, raport.
- **http://77.45.76.243:8000/docs** — dokumentacja REST API (Swagger).
- Test API z komputera (pyta o hasło, wynik zapisuje w repozytorium):
  ```bash
  cd backend
  python scripts/api_batch.py --target serwer=http://77.45.76.243:8000 \
      --input ../form-examples/3 --out ../wyniki/testy/serwer-sprawdzenie --workers 2
  ```

Jeśli strona nie odpowiada z zewnątrz, sprawdź zaporę serwera (porty `80` i `8000`, np. `sudo ufw allow 80,8000/tcp`).

## 6. Aktualizacja po zmianach w repozytorium

```bash
git pull
docker compose up -d --build              # przebudowuje i podmienia tylko zmienione usługi
```

## Serwer MCP (branch `mcp`)

Na gałęzi `mcp` ten sam `docker compose up -d --build` uruchamia dodatkowo serwer MCP na porcie `8100`
(`http://77.45.76.243:8100/mcp`, token jak w REST API). W `docker-compose.yml` ustaw `MCP_SAFE_APP_URL` na adres
strony (np. `http://77.45.76.243`) i otwórz port `8100` w zaporze. Sprawdzenie:

```bash
cd backend && python scripts/mcp_demo.py --url http://77.45.76.243:8100/mcp
```

## Konektor dla czatbota w przeglądarce — tunel Cloudflare (branch `cloudflare`)

Konektory claude.ai i ChatGPT wymagają adresu **https://** i nie wysyłają własnych nagłówków. Branch `cloudflare`
dodaje usługę `tunnel` (oficjalny obraz `cloudflare/cloudflared`), która wystawia serwer MCP pod publicznym adresem
https, oraz przyjmowanie tokenu w adresie (`…/mcp?token=…`).

### 1. Uruchomienie na serwerze

```bash
git fetch && git checkout cloudflare && git pull
nano docker-compose.yml        # w usłudze mcp: MCP_SAFE_APP_URL: "http://77.45.76.243"
docker compose down
docker compose up --build -d
```

### 2. Adres tunelu

```bash
docker compose logs tunnel | grep trycloudflare.com
```

Widać tam adres w rodzaju `https://losowe-slowa.trycloudflare.com`. Sprawdzenie: `curl -I <adres>/mcp` → `401`
(serwer działa, wymaga tokenu). Adres **zmienia się po każdym restarcie** usługi `tunnel` (tryb bez konta).

### 3. Token dla czatbota (na serwerze)

```bash
docker compose exec formularze python -m app.token_cli --sub czatbot --hours 24
```

Token trafia do adresu konektora, więc wystawiaj go **krótko ważnego** (np. 24 h) i wystaw nowy, gdy wygaśnie.

### 4. Link konektora

```
https://losowe-slowa.trycloudflare.com/mcp?token=<TOKEN>
```

- **claude.ai**: Ustawienia → Konektory → „Dodaj niestandardowy konektor” → wklej link (bez dodatkowego logowania).
- **ChatGPT**: Ustawienia → Konektory (tryb deweloperski) → utwórz konektor → wklej link, uwierzytelnianie „brak”.
- **Claude Code**: `claude mcp add --transport http formularze "<link>"`.

Potem w rozmowie: „Pobierz standardy z formularze i zbuduj konfigurację eUsługi dla tego wniosku” (z załączonym
blankietem formularza).

### Stały adres (opcjonalnie, konto Cloudflare)

W panelu Cloudflare: Zero Trust → Networks → Tunnels → Create tunnel → skopiuj token; w „Public hostname” wskaż
usługę `http://mcp:8100`. Następnie w `docker-compose.yml` zmień komendę usługi `tunnel` na
`["tunnel", "--no-autoupdate", "run"]` i dodaj zmienną `TUNNEL_TOKEN` (w `backend/.env` lub sekcji `environment`).
