"""Zbiorcze porównanie modeli z rejestru testów → wyniki/testy/PORÓWNANIE.md.

    python scripts/summary_tests.py

Czyta `wyniki/testy/rejestr.json` (wszystkie biegi api_batch.py) i ceny modeli z publicznego katalogu Eden AI
(`GET https://api.edenai.run/v3/models`, bez klucza), liczy dla każdego modelu i zestawu plików: skuteczność,
czasy (klient / serwer), liczbę pól, tokeny i szacowany koszt.
"""

import json
import statistics
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "wyniki" / "testy" / "rejestr.json"
OUT = ROOT / "wyniki" / "testy" / "PORÓWNANIE.md"


def prices() -> dict[str, tuple[float, float]]:
    try:
        data = httpx.get("https://api.edenai.run/v3/models", timeout=30).json()["data"]
    except (httpx.HTTPError, KeyError, ValueError):
        return {}
    return {m["id"]: ((m.get("pricing") or {}).get("input_cost_per_token") or 0.0,
                      (m.get("pricing") or {}).get("output_cost_per_token") or 0.0) for m in data}


def file_set(name: str) -> str:
    if name.startswith("T") and name[1:2].isdigit():
        return "wygenerowane (T1–T8)"
    if name.startswith("B") and name[1:2].isdigit():
        return "BIP (B1–B3)"
    return "materiały wyzwania"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    entries = list(json.loads(REGISTRY.read_text(encoding="utf-8")).values())
    entries = [e for e in entries if e.get("target") != "wyniki-final"]  # import wcześniejszego biegu, bez czasów
    cost_table = prices()
    rows = ["| Model | Zestaw | OK / wszystkie | Skuteczność | Czas klienta śr. / mediana [s] | Czas serwera śr. [s] "
            "| Pola śr. | Tokeny we + wy | Koszt szac. |", "|---|---|---|---|---|---|---|---|---|"]
    total_cost = 0.0
    for model in sorted({e["model"] for e in entries}):
        for group in sorted({file_set(e["file"]) for e in entries if e["model"] == model}):
            sel = [e for e in entries if e["model"] == model and file_set(e["file"]) == group]
            ok = [e for e in sel if e.get("status") == "ok"]
            wall = [e["clientSeconds"] for e in ok if e.get("clientSeconds")] or [0]
            server = [e["serverSeconds"] for e in ok if e.get("serverSeconds")] or [0]
            fields = [e["fields"] for e in ok if e.get("fields")] or [0]
            tin = sum(e.get("promptTokens", 0) for e in ok)
            tout = sum(e.get("completionTokens", 0) for e in ok)
            pin, pout = cost_table.get(model, (0.0, 0.0))
            cost = tin * pin + tout * pout
            total_cost += cost
            rows.append(f"| `{model}` | {group} | {len(ok)} / {len(sel)} | {len(ok) / len(sel):.0%} | "
                        f"{statistics.mean(wall):.1f} / {statistics.median(wall):.1f} | "
                        f"{statistics.mean(server):.1f} | "
                        f"{statistics.mean(fields):.0f} | {tin:,} + {tout:,} | ${cost:.2f} |".replace(",", " "))
    fallback = sum(e.get("status") == "fallback" for e in entries)
    errors = sum(e.get("status") == "error" for e in entries)
    text = (f"# Porównanie modeli — testy REST API\n\nWygenerowano: {datetime.now(UTC).isoformat(timespec='seconds')} "
            f"z `wyniki/testy/rejestr.json` (`backend/scripts/summary_tests.py`).\n\n"
            "Każda para plik × model przetworzona raz (rejestr bez duplikatów). „OK” = wynik modelu językowego; "
            "pozostałe to analiza regułowa po błędzie modelu (`fallback`) lub błąd żądania. Koszt = tokeny × ceny "
            "z publicznego katalogu Eden AI (bez OCR).\n\n" + "\n".join(rows) +
            f"\n\nRazem: {len(entries)} konwersji, fallback: {fallback}, błędy: {errors}, "
            f"szacowany koszt modeli: ${total_cost:.2f}.\n")
    OUT.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
