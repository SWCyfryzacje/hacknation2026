"""Demonstracja serwera MCP (dowód działania): standardy → budowa formularza z opisu → odmowa przy danych osobowych.

    python scripts/mcp_demo.py --url http://localhost:8100/mcp [--opis opis.json] [--out wynik.json]

Łączy się z serwerem MCP przez streamable HTTP (JSON-RPC), tak jak robi to asystent AI. Token JWT: zmienna
MCP_TOKEN albo wystawiony lokalnie z JWT_SECRET (`app.token_cli`). Bez `--opis` używa przykładowego opisu
z `pobierz_standardy`. Nie wywołuje żadnego modelu językowego — generator jest deterministyczny.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import httpx


class McpClient:
    def __init__(self, url: str, token: str | None) -> None:
        self.url = url
        self.headers = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
        self.next_id = 0

    def rpc(self, method: str, params: dict) -> dict:
        self.next_id += 1
        r = httpx.post(self.url, headers=self.headers, timeout=120,
                       json={"jsonrpc": "2.0", "id": self.next_id, "method": method, "params": params})
        r.raise_for_status()
        body = r.json()
        if "error" in body:
            raise RuntimeError(body["error"])
        return body["result"]

    def call(self, tool: str, **arguments) -> dict:
        result = self.rpc("tools/call", {"name": tool, "arguments": arguments})
        data = result.get("structuredContent") or json.loads(result["content"][0]["text"])
        return data.get("result", data)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Demonstracja serwera MCP Formularze AI.")
    ap.add_argument("--url", default="http://localhost:8100/mcp")
    ap.add_argument("--opis", type=Path, help="Plik JSON z opisem formularza (wynik analizy asystenta)")
    ap.add_argument("--out", type=Path, help="Gdzie zapisać zbudowaną konfigurację JSON")
    args = ap.parse_args()

    token = os.environ.get("MCP_TOKEN") or subprocess.run(
        [sys.executable, "-m", "app.token_cli", "--sub", "mcp-demo"], capture_output=True, text=True,
        cwd=Path(__file__).resolve().parents[1]).stdout.strip() or None
    mcp = McpClient(args.url, token)

    info = mcp.rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                  "clientInfo": {"name": "mcp-demo", "version": "1"}})
    print(f"1. Połączono z serwerem: {info['serverInfo']['title']} ({info['serverInfo']['version']})")
    tools = [t["name"] for t in mcp.rpc("tools/list", {})["tools"]]
    print(f"2. Narzędzia: {', '.join(tools)}")

    standards = mcp.call("pobierz_standardy")
    print(f"3. Standardy: {len(standards['typyPol'])} typów pól, {len(standards['walidatory'])} walidatorów, "
          f"{len(standards['sekcjePredefiniowane'])} sekcji predefiniowanych, schemat opisu z "
          f"{len(standards['schematOpisu']['properties'])} polami")

    opis = json.loads(args.opis.read_text(encoding="utf-8")) if args.opis else standards["przykladOpisu"]
    built = mcp.call("zbuduj_formularz", opis=opis)
    form = built["formularz"]
    fields = sum(len(q["field"]["repeatingSectionGrid"]) for t in form["tabs"] for q in t["questions"])
    print(f"4. Zbudowano: „{form['title']}” — strony: {[t['title'] for t in form['tabs']]}, pól: {fields}, "
          f"problemy z regułami: {built['problemy'] or 'brak'}")
    if args.out:
        args.out.write_text(json.dumps(form, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"   zapisano → {args.out}")

    check = mcp.call("sprawdz_formularz", formularz=form)
    print(f"5. Kontrola reguł zbudowanego formularza: {check['problemy'] or 'brak problemów'}")

    leaked = json.loads(json.dumps(opis))
    leaked["title"] = f"{leaked['title']} — Jan Kowalski, PESEL 44051401359, tel. 600 100 200"
    refusal = mcp.call("zbuduj_formularz", opis=leaked)
    print(f"6. Opis z danymi osobowymi → odmowa: {refusal.get('odmowa')} — {refusal.get('powod')}\n"
          f"   bezpieczna ścieżka: {refusal.get('bezpiecznaAplikacja')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
