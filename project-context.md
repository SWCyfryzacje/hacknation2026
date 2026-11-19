# MCPolska — Project Context

> Kontekst projektu dla HackNation 2026. Dokument źródłowy dla ludzi i asystentów AI
> pracujących nad repozytorium. Decyzje oznaczone jako *propozycja* nie są wiążące.

## 1. Czym jest MCPolska

Federacyjny gateway MCP (Model Context Protocol) — wspólna warstwa integracyjna, przez którą
asystenci AI rozmawiają z wieloma niezależnie rozwijanymi aplikacjami, bez konieczności
pisania osobnej integracji per asystent × aplikacja.

MCPolska to **infrastruktura**: nie chatbot, nie model, nie zamiennik aplikacji, które federuje.

Projekt powstaje jako PoC na HackNation, z naciskiem na realny potencjał wdrożeniowy
w infrastrukturze sektora publicznego.

## 2. Trzy cele główne

### A. Federacja MCP

Wiele niezależnych aplikacji, każda z własnym serwerem MCP, podłączonych przez jeden gateway.

Gateway odpowiada za:
- rejestr podłączonych serwerów MCP,
- agregację narzędzi (tools) z zarejestrowanych serwerów,
- jeden ujednolicony endpoint MCP dla klientów,
- routing wywołań narzędzi do właściwego serwera downstream.

Aplikacje zachowują własną logikę biznesową, bazy i infrastrukturę. Rejestracja serwerów jest
**świadoma i kontrolowana** — automatyczne wykrywanie dowolnych serwerów MCP nie jest w MVP.

### B. Uprawnienia i kontrola dostępu

Centralna warstwa uprawnień, sprawdzana przed wykonaniem narzędzia downstream:
- uprawnienia per użytkownik i per podłączona aplikacja,
- kontrola na poziomie pojedynczego narzędzia,
- rozdzielenie operacji read / write tam, gdzie ma to sens,
- jawne nadawanie i odbieranie uprawnień,
- egzekwowanie po stronie serwera, nigdy po stronie klienta,
- logowanie decyzji (allow / deny).

Dostęp do jednej aplikacji **nigdy** nie implikuje dostępu do pozostałych.

### C. Audytowalność

Zdarzenie audytowe zawiera (gdzie ma zastosowanie): tożsamość użytkownika, aplikację,
wywołane narzędzie MCP, timestamp, decyzję autoryzacyjną, wynik wykonania, correlation ID.

Wrażliwe payloady nie są przechowywane bez potrzeby.

## 3. Architektura federacji

```
MCP Client → MCPolska Gateway → Registered MCP Server → Application
```

| Gateway | Aplikacja downstream |
| --- | --- |
| uwierzytelnianie klientów | logika biznesowa |
| sprawdzanie uprawnień | własne dane |
| routing narzędzi | własna implementacja serwera MCP |
| rejestr serwerów | walidacja i wykonanie specyficzne dla domeny |
| audyt i zarządzanie federacją | |

**Kierunek przyszły (nie MVP):** federacja hierarchiczna — gateway krajowy federuje gatewaye
miejskie, a gminy zachowują autonomię nad swoimi usługami, infrastrukturą i uprawnieniami.

## 4. AI Handoff

Drugi filar funkcjonalny: przenoszenie kontekstu rozmowy, zadania i stanu między asystentami AI,
z MCP jako mechanizmem integracji.

```
Claude → MCPolska Handoff → ChatGPT
```

Przekazywany kontekst jest strukturalny, a **nie** całą historią rozmowy: podsumowanie, cel
użytkownika, podjęte decyzje, zebrane informacje, braki, sugerowany następny krok,
jawnie zatwierdzone dane.

Przepływ PoC:
1. asystent tworzy handoff,
2. kontekst trafia do serwisu handoff,
3. generowany jest identyfikator,
4. inny asystent pobiera i akceptuje handoff,
5. otrzymuje kontekst i kontynuuje zadanie,
6. handoff zostaje oznaczony jako completed / cancelled.

Wymagania: wygasające sesje, kontrola dostępu, zgoda użytkownika, jednorazowe lub kontrolowane
odczyty, śledzenie statusu. Asystent odbierający musi móc zwalidować kontekst i poprosić
użytkownika o potwierdzenie istotnych informacji.

Handoff jest **niezależny od dostawcy** — nie zakłada konkretnego modelu ani vendora. Dokładny
mechanizm interoperacyjności między klientami pozostaje otwarty; MCP daje warstwę integracji,
ale automatyczne przenoszenie rozmowy zależy od możliwości i współpracy klientów.

## 5. Aplikacje demonstracyjne

| # | Aplikacja | Rola w demie |
| --- | --- | --- |
| 1 | **Forms** | nowa aplikacja realizująca wymagania wyzwania HackNation; pokazuje integrację przez MCP i dostęp kontrolowany uprawnieniami |
| 2 | **Wotum** | istniejąca aplikacja z poprzedniego hackathonu; pokazuje, że działający produkt można sfederować **bez** przepisywania go do gatewaya |
| 3 | **Handoff** | niezależny serwer MCP demonstrujący przekazanie kontekstu AI↔AI; demonstrator pod przyszłe integracje z asystentami instytucjonalnymi |

Każda aplikacja pozostaje osobno wdrażalna i eksponuje własny serwer MCP.

## 6. Stack technologiczny

**Backend:** Python, FastAPI, oficjalne MCP Python SDK, Linux VPS z publicznym IP,
Docker / Docker Compose.

**Baza i auth:** Supabase (PostgreSQL + Supabase Auth gdzie ma zastosowanie).

Potencjalne encje: `users`, `mcp_servers`, `registered_applications`, `tools`, `permissions`,
`handoff_sessions`, `audit_events`.

> Uwierzytelnianie między zewnętrznymi klientami MCP a gatewayem wymaga projektu zgodnego
> z MCP i OAuth. Supabase Auth **nie** implementuje automatycznie całego flow autoryzacji MCP.

**Infrastruktura:** Cloudflare (DNS, ochrona brzegowa), Linux VPS dla trwałych usług MCP,
Vercel dla frontendu / dashboardów. Gateway MCP działa jako **usługa trwała** — model
serverless nie nadaje się do długo żyjących połączeń.

## 7. Domeny

Domena projektu: **oazai.pl** (już posiadana; decyzja z 2026-11-19 — rezygnacja z kupowania
`mcpolska.pl`).

Propozycja struktury:
- `oazai.pl` — landing page MCPolska,
- `mcp.oazai.pl` — endpoint gatewaya MCP,
- `api.oazai.pl` — backend API (jeśli wydzielone),
- `app.oazai.pl` — interfejs użytkownika,
- `admin.oazai.pl` — panel administracyjny.

## 8. Zakres MVP

Cel: działający PoC demonstrujący infrastrukturę — nie produkcyjna platforma krajowa.

### Federacja

- [ ] działający gateway MCP
- [ ] rejestracja niezależnych serwerów MCP
- [ ] połączenie z wieloma serwerami downstream
- [ ] agregacja narzędzi
- [ ] routing wywołań narzędzi
- [ ] centralne sprawdzanie uprawnień
- [ ] nadawanie i odbieranie uprawnień
- [ ] podstawowy audit log
- [ ] demo na min. dwóch niezależnych aplikacjach
- [ ] demo ograniczonego dostępu do narzędzia
- [ ] demo udanego, dozwolonego wywołania
- [ ] demo odmowy po odebraniu uprawnienia

### Handoff

- [ ] utworzenie handoffu
- [ ] zapis strukturalnego kontekstu rozmowy
- [ ] generowanie handoff ID
- [ ] pobranie handoffu z innego klienta
- [ ] akceptacja handoffu
- [ ] kontynuacja zadania na otrzymanym kontekście
- [ ] oznaczenie completed / cancelled

Handoff demonstrujemy niezależnie od federacji, korzystając z infrastruktury MCPolska tam,
gdzie to naturalne.

## 9. Zasady bezpieczeństwa

Least privilege · jawne nadawanie uprawnień · odbieranie uprawnień · uwierzytelnianie klientów ·
egzekwowanie po stronie serwera · brak sekretów serwisowych w kliencie · kontrolowany dostęp do
kontekstu handoffu · wygasające identyfikatory handoffu · audit log · minimalizacja przechowywania
wrażliwych danych rozmowy.

MVP nie pretenduje do statusu produkcyjnej infrastruktury krajowej.

## 10. Czym MCPolska nie jest

Nie jest: chatbotem · nowym modelem foundation · zamiennikiem pojedynczych aplikacji ·
publicznym API ogólnego przeznaczenia dla wszystkich aplikacji obywatelskich · systemem
nieograniczonego odkrywania serwerów MCP · gotową, produkcyjną platformą bezpieczeństwa
w skali kraju.

Jest infrastrukturą integracji, federacji, uprawnień i audytu — z AI handoff jako dodatkową
zdolnością funkcjonalną.

## 11. Pozycjonowanie

Poszczególne komponenty techniczne nie są same w sobie nowatorskie. Wartością jest **kombinacja**:
wspólna infrastruktura MCP + federacja niezależnych aplikacji + centralne uprawnienia +
audytowalność + handoff kontekstu AI + potencjał zastosowania w usługach publicznych.

Cel prototypu: pokazać, że ta architektura działa w praktyce i że niezależnie rozwijane
aplikacje mogą wejść do wspólnego ekosystemu MCP **bez przepisywania ich od zera**.

## 12. Priorytety rozwoju

1. Uruchomić gateway.
2. Rejestracja serwerów i federacja.
3. Routing narzędzi.
4. Uprawnienia.
5. Audit log.
6. Integracja Forms.
7. Integracja Wotum.
8. Handoff.
9. Demo end-to-end.

Nie przeinżynierowujemy architektury w skali krajowej na hackathonie. Działające, zrozumiałe
i demonstrowalne MVP przed spekulatywnymi funkcjami infrastrukturalnymi.

---

## Appendix A — stan przygotowań przed hackathonem

Hackathon jeszcze się nie zaczął. Faza przygotowawcza:

- [x] `project-context.md` (ten dokument)
- [ ] landing page MCPolska pod `oazai.pl`
- [ ] domena `oazai.pl` podłączona (DNS → hosting frontendu)
- [ ] projekt Supabase utworzony, klucze w `.env.local`
- [ ] autoryzacja użytkownika (Supabase Auth) działająca end-to-end
