"""Serwer MCP (Model Context Protocol) — dodatkowy interfejs usługi dla asystentów AI.

    python -m app.mcp_server          # streamable HTTP na :8100, ścieżka /mcp

Idea: analizę formularza wykonuje **zewnętrzny asystent AI użytkownika** (np. Claude, ChatGPT — model opłaca
użytkownik, nie urząd), a nasz **deterministyczny generator** buduje z niej konfigurację eUsługi zgodną
ze standardami i eksportami z systemu docelowego. Urząd utrzymuje tylko darmowy generator i walidację.

Narzędzia:
  * `pobierz_standardy`   — zasady projektowania formularza, typy pól, walidatory, słowniki, dane inicjalne,
                            schemat opisu formularza i przykład (te same, których używa nasz model językowy),
  * `zbuduj_formularz`    — opis formularza (wynik analizy asystenta) → kompletny JSON + wynik kontroli reguł,
  * `sprawdz_formularz`   — kontrola dowolnej konfiguracji JSON regułami formularzy eUsług.

Ochrona danych: wejście każdego narzędzia jest sprawdzane pod kątem danych osobowych (PESEL, NIP, REGON
z sumami kontrolnymi, numer rachunku, seria i numer dowodu, e-mail, telefon). Po ich wykryciu narzędzie odmawia
i wskazuje rządową aplikację (MCP_SAFE_APP_URL), gdzie dokument przetwarza się na infrastrukturze urzędu.
Ograniczenie: serwer nie cofnie przesłania dokumentu do zewnętrznego modelu — odmowa zapobiega dalszemu
przetwarzaniu i wskazuje bezpieczną ścieżkę.

MCP jest interfejsem opcjonalnym: REST API działa w pełni bez niego (usługa nie zależy od MCP).
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from pydantic import ValidationError

from app.analysis.llm import (
    _INITIAL_DATA_VALUES,
    DICTIONARIES,
    EXAMPLE_OUTPUT,
    SYSTEM_PROMPT,
    VALIDATORS,
    _Answer,
    _to_analysis,
)
from app.config import get_settings
from app.generator.builder import BuildOptions, build_form
from app.generator.checks import check_form

INSTRUCTIONS = (
    "Serwer tworzy konfiguracje formularzy eUsług (JSON do importu w systemie docelowym) z analizy papierowego "
    "formularza wykonanej przez Ciebie. Najpierw wywołaj `pobierz_standardy`, przeanalizuj BLANKIET formularza "
    "według zasad i przekaż opis do `zbuduj_formularz`. Nie przekazuj danych osobowych (wypełnionych formularzy) — "
    "serwer odmówi i wskaże rządową aplikację."
)

# --------------------------------------------------------------------------- strażnik danych osobowych

_PESEL = re.compile(r"(?<!\d)\d{11}(?!\d)")
_NIP = re.compile(r"(?<!\d)\d{3}-?\d{3}-?\d{2}-?\d{2}(?!\d)")
_IBAN = re.compile(r"(?<![\dA-Z])(?:PL)?\s?\d{2}(?:\s?\d{4}){6}(?!\d)")
_ID_CARD = re.compile(r"(?<![A-Z])[A-Z]{3}\s?\d{6}(?!\d)")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE = re.compile(r"(?:\+48[\s-]?)?(?<!\d)\d{3}[\s-]\d{3}[\s-]\d{3}(?!\d)")


def _pesel_ok(d: str) -> bool:
    weights = [1, 3, 7, 9, 1, 3, 7, 9, 1, 3]
    return (10 - sum(w * int(c) for w, c in zip(weights, d, strict=False)) % 10) % 10 == int(d[10])


def _nip_ok(d: str) -> bool:
    d = re.sub(r"\D", "", d)
    weights = [6, 5, 7, 2, 3, 4, 5, 6, 7]
    check = sum(w * int(c) for w, c in zip(weights, d, strict=False)) % 11
    return check != 10 and check == int(d[9])


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for v in value.values() for s in _strings(v)]
    if isinstance(value, list):
        return [s for v in value for s in _strings(v)]
    return []


def find_personal_data(payload: Any) -> list[str]:
    """Rodzaje danych osobowych wykrytych w wejściu (bez ujawniania samych wartości)."""
    text = "\n".join(_strings(payload))
    found: list[str] = []
    if any(_pesel_ok(m) for m in _PESEL.findall(text)):
        found.append("numer PESEL")
    if any(_nip_ok(m) for m in _NIP.findall(text)):
        found.append("numer NIP")
    if _IBAN.search(text):
        found.append("numer rachunku bankowego")
    if _ID_CARD.search(text):
        found.append("seria i numer dokumentu tożsamości")
    if _EMAIL.search(text):
        found.append("adres e-mail")
    if _PHONE.search(text):
        found.append("numer telefonu")
    return found


def _refusal(found: list[str]) -> dict[str, Any]:
    url = get_settings().mcp_safe_app_url
    return {
        "odmowa": True,
        "powod": f"Wejście zawiera dane osobowe ({', '.join(found)}). Wygląda na wypełniony formularz, a nie blankiet.",
        "zalecenie": "Nie przetwarzaj tego dokumentu w zewnętrznym asystencie AI. Użyj rządowej aplikacji, "
                     "która przetwarza dokumenty na infrastrukturze urzędu.",
        "bezpiecznaAplikacja": url,
    }


# --------------------------------------------------------------------------- narzędzia (czyste funkcje)


def pobierz_standardy() -> dict[str, Any]:
    """Zasady projektowania formularza eUsługi i schemat opisu, który przyjmuje `zbuduj_formularz`."""
    return {
        "zasady": SYSTEM_PROMPT,
        "schematOpisu": _Answer.model_json_schema(),
        "przykladOpisu": EXAMPLE_OUTPUT,
        "typyPol": ["TEXT_FIELD", "TEXTAREA", "NUMBER", "DATEPICKER", "RADIO", "CHECKBOX", "SELECT",
                    "FILE_UPLOADER", "TEXT_BLOCK"],
        "walidatory": list(VALIDATORS),
        "slowniki": list(DICTIONARIES),
        "daneInicjalne": sorted(_INITIAL_DATA_VALUES),
        "sekcjePredefiniowane": [
            "Urząd / organ, do którego jest składany wniosek", "Podmiot wniosku", "Twoje dane (MLPZ)",
            "Adres zamieszkania (kraj + TERYT)", "Dane i adres innej osoby", "Dane i adres siedziby podmiotu",
            "Pełnomocnictwo", "Opłata skarbowa za pełnomocnictwo", "Dane do kontaktu", "Zgody i oświadczenia",
            "Podgląd (strona końcowa)"],
        "uwaga": "Sekcje predefiniowane dokłada generator — opis zawiera tylko część specyficzną dla wniosku.",
    }


def zbuduj_formularz(opis: dict[str, Any]) -> dict[str, Any]:
    """Opis formularza (wg `schematOpisu`) → kompletna konfiguracja eUsługi + wynik kontroli reguł."""
    found = find_personal_data(opis)
    if found:
        return _refusal(found)
    try:
        answer = _Answer.model_validate(opis)
    except ValidationError as exc:
        return {"blad": "Opis nie jest zgodny ze schematem z `pobierz_standardy`.",
                "szczegoly": exc.errors(include_url=False)[:20]}
    analysis = _to_analysis(answer)
    analysis.analyzer = "mcp"
    settings = get_settings()
    seed = hashlib.sha256(json.dumps(opis, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
    form = build_form(analysis, seed, BuildOptions(settings.finish_component, settings.validation_mode))
    return {"formularz": form, "problemy": check_form(form), "ostrzezenia": analysis.warnings,
            "proponowaneSlowniki": [d.__dict__ for d in analysis.proposed_dictionaries]}


def sprawdz_formularz(formularz: dict[str, Any]) -> dict[str, Any]:
    """Kontrola konfiguracji formularza regułami formularzy eUsług (pusta lista = brak problemów)."""
    found = find_personal_data(formularz)
    if found:
        return _refusal(found)
    if not isinstance(formularz.get("tabs"), list):
        return {"blad": "To nie jest konfiguracja formularza (brak tablicy `tabs`)."}
    return {"problemy": check_form(formularz)}


# --------------------------------------------------------------------------- serwer MCP + uwierzytelnianie


def create_server():  # noqa: ANN201 — typ z biblioteki mcp
    from mcp.server.mcpserver import MCPServer

    server = MCPServer(name="formularze-ai", title="Formularze AI — konfiguracje eUsług",
                       instructions=INSTRUCTIONS, version="0.1.0")
    server.tool(name="pobierz_standardy")(pobierz_standardy)
    server.tool(name="zbuduj_formularz")(zbuduj_formularz)
    server.tool(name="sprawdz_formularz")(sprawdz_formularz)
    return server


class BearerAuth:
    """Middleware ASGI: wymaga tokenu JWT (ten sam co REST API), gdy AUTH_ENABLED=true."""

    def __init__(self, app) -> None:  # noqa: ANN001
        self.app = app

    async def __call__(self, scope, receive, send) -> None:  # noqa: ANN001
        settings = get_settings()
        if scope["type"] == "http" and settings.auth_enabled:
            from app.errors import Unauthorized
            from app.security import decode_token

            header = dict(scope.get("headers") or []).get(b"authorization", b"").decode()
            try:
                if not header.lower().startswith("bearer "):
                    raise Unauthorized("Wymagany nagłówek Authorization: Bearer <token>.")
                decode_token(header[7:], settings)
            except Unauthorized as exc:
                body = json.dumps({"detail": exc.message}, ensure_ascii=False).encode()
                await send({"type": "http.response.start", "status": 401,
                            "headers": [(b"content-type", b"application/json"), (b"www-authenticate", b"Bearer")]})
                await send({"type": "http.response.body", "body": body})
                return
        await self.app(scope, receive, send)


def create_app():  # noqa: ANN201
    from mcp.server.transport_security import TransportSecuritySettings

    server = create_server()
    app = server.streamable_http_app(
        stateless_http=True, json_response=True, host="0.0.0.0",
        # Za proxy/na serwerze nagłówek Host jest różny od localhost — ochronę zapewnia token JWT.
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False))
    return BearerAuth(app)


def main() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(create_app(), host="0.0.0.0", port=settings.mcp_port, proxy_headers=True, server_header=False)


if __name__ == "__main__":
    main()
