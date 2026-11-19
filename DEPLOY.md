# Deploy landing page na Vercel + domena oazai.pl

Kolejność: najpierw repo na GitHubie, potem Vercel, na końcu DNS. Rób punkt po punkcie.

Repo git jest już zainicjalizowane lokalnie (branch `main`), pliki są w stage — brak commita.

---

## Krok 1 — pierwszy commit

```bash
cd c:/Users/jonso/hacknation2026
git commit -m "MCPolska: landing page + kontekst projektu"
```

## Krok 2 — repo na GitHubie

Jeśli masz `gh`:

```bash
gh repo create mcpolska --private --source . --remote origin --push
```

Bez `gh`: utwórz puste repo na github.com (bez README), potem:

```bash
git remote add origin https://github.com/<twoj-login>/mcpolska.git
git push -u origin main
```

## Krok 3 — projekt na Vercel

1. [vercel.com/new](https://vercel.com/new) → **Import Git Repository** → wybierz `mcpolska`.
2. **Root Directory**: ustaw na `web` ← kluczowe, aplikacja nie leży w korzeniu repo.
3. Framework Preset: `Next.js` (wykryje sam). Build command i output zostaw domyślne.
4. Environment Variables: żadnych na razie.
5. **Deploy**.

Po 1–2 min dostaniesz adres `*.vercel.app`. Sprawdź, czy strona wygląda poprawnie —
dopiero potem domena.

## Krok 4 — dodaj domenę w Vercel

W projekcie: **Settings → Domains → Add Existing**.

1. Wpisz `oazai.pl`. Vercel zaproponuje dorzucenie `www.oazai.pl` — przyjmij
   (`www` będzie przekierowywać na apex).
2. Vercel pokaże **konkretne wartości DNS dla tego projektu**. Nie przepisuj wartości
   z tutoriali z internetu — rekord CNAME jest dziś unikalny per projekt
   (coś w stylu `d1d4fc829fe7bc7c.vercel-dns-017.com`), a IP dla rekordu A też odczytaj
   z tego ekranu.

Zostaw tę kartę otwartą, potrzebujesz z niej wartości w kroku 5.

## Krok 5 — DNS u operatora domeny

Dwie drogi. **Opcja A** jest prostsza, **opcja B** bezpieczniejsza jeśli na `oazai.pl`
działa poczta albo coś jeszcze.

### Opcja A — nameservery Vercela (przejmujesz całą strefę DNS)

W panelu rejestratora `oazai.pl` ustaw nameservery na te pokazane przez Vercel
(zwykle `ns1.vercel-dns.com` i `ns2.vercel-dns.com`).

⚠️ Przed zmianą: **przepisz istniejące rekordy MX, SPF/DKIM i TXT weryfikacyjne** do
Vercel DNS. Po zmianie nameserwerów stara strefa przestaje obowiązywać i poczta
na tej domenie padnie.

### Opcja B — tylko rekordy, strefa zostaje u obecnego operatora

W panelu DNS dodaj / podmień:

| Typ | Nazwa | Wartość | Uwagi |
| --- | --- | --- | --- |
| `A` | `@` (apex) | IP pokazane przez Vercel | usuń inne rekordy `A`/`AAAA`/`CNAME` dla `@` |
| `CNAME` | `www` | wartość CNAME pokazana przez Vercel | nie `oazai.pl`, nie `vercel.app` |

Rekordy MX i reszta strefy zostają nietknięte. To zalecana droga, jeśli domena
„zbiera kurz” ale ma podpiętą pocztę.

### Jeśli DNS trzymasz na Cloudflare

- Dodaj te same rekordy co w opcji B, ale ustaw proxy na **DNS only** (szara chmurka).
  Pomarańczowa chmurka + Vercel = podwójne proxy i problemy z certyfikatem.
- SSL/TLS mode: **Full (strict)**.

## Krok 6 — weryfikacja

1. W **Settings → Domains** odczekaj, aż `oazai.pl` dostanie status `Valid Configuration`
   (certyfikat wystawia się automatycznie; propagacja DNS: minuty do kilku godzin).
2. Z terminala:

```bash
nslookup oazai.pl
nslookup www.oazai.pl
curl -I https://oazai.pl
```

3. Wejdź na `https://oazai.pl` — powinno być HTTPS bez ostrzeżeń, a `www` przekierowywać
   na apex.

Jeśli Vercel pokazuje `Invalid Configuration`: zwykle został stary, konfliktowy rekord
`A`/`CNAME` na `@` albo parkingowa strona rejestratora. Usuń konflikt i odśwież.

---

## Dalsze kroki (osobno, nie teraz)

Każde do zrobienia jako oddzielne zadanie, w tej kolejności:

1. `mcp.oazai.pl` → subdomena wskazująca na VPS z gatewayem MCP (rekord `A` na IP VPS-a,
   **nie** przez Vercel).
2. Projekt Supabase + `.env.local` w `web/`.
3. Autoryzacja użytkownika (Supabase Auth, `@supabase/ssr`) — logowanie i strona chroniona.
4. Szkielet gatewaya MCP (FastAPI + MCP Python SDK) na VPS-ie.

Kontekst i cele projektu: [project-context.md](project-context.md).
