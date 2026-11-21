"""Przetwarzanie wsadowe: konwertuje wszystkie obsługiwane pliki z katalogu i zapisuje wyniki.

    python scripts/convert_dir.py <katalog_wejściowy> <katalog_wyjściowy> [--max-llm-calls N]

Dla każdego pliku `<nazwa>.<ext>` powstają:
  * `<nazwa>.<ext>.json`         — konfiguracja formularza,
  * `<nazwa>.<ext>.report.json`  — raport z analizy,
  * `<nazwa>.<ext>.slowniki.json` — zaproponowane nowe słowniki (jeśli są).
`--max-llm-calls` przerywa przetwarzanie kolejnych plików po wykorzystaniu limitu wywołań modelu.
Konfiguracja (klucz Eden AI, model itd.) jest wczytywana z .env / zmiennych środowiskowych.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import Settings  # noqa: E402
from app.errors import AppError  # noqa: E402
from app.files.formats import EXTENSION_TO_MIME  # noqa: E402
from app.files.validation import validate_upload  # noqa: E402
from app.service import convert  # noqa: E402


def _write(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main(src: Path, dst: Path, *, max_llm_calls: int | None = None, settings: Settings | None = None) -> int:
    settings = settings or Settings(auth_enabled=False)
    dst.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in src.rglob("*") if p.suffix.lower() in EXTENSION_TO_MIME)
    failures = calls = done = 0
    for path in files:
        if max_llm_calls is not None and calls >= max_llm_calls:
            print(f"STOP  limit {max_llm_calls} wywołań modelu wykorzystany — pominięto pozostałe pliki.")
            break
        try:
            file = validate_upload(path.name, path.read_bytes(), None, max_size=settings.max_file_size_bytes,
                                   max_uncompressed=settings.max_uncompressed_bytes)
            result = convert(file, settings)
        except AppError as exc:
            failures += 1
            print(f"BŁĄD  {path.name}: {exc.message}")
            continue
        done += 1
        base = dst / f"{path.stem}{path.suffix.lower()}"
        _write(base.with_name(base.name + ".json"), result.form)
        _write(base.with_name(base.name + ".report.json"), result.report)
        dictionaries = result.report["proposedDictionaries"]
        if dictionaries:
            _write(base.with_name(base.name + ".slowniki.json"), {"dictionaries": dictionaries})
        r = result.report
        usage = r["analysis"]["llmUsage"] or {}
        calls += usage.get("calls", 0)
        tokens = (f", {usage.get('calls', 0)} wywoł., {usage.get('prompt_tokens', 0)}+"
                  f"{usage.get('completion_tokens', 0)} tokenów" if usage else "")
        print(f"OK    {path.name}: {r['analysis']['analyzer']}, {r['stats']['fields']} pól, "
              f"{len(dictionaries)} słown., {len(r['warnings'])} ostrzeżeń, {len(r['issues'])} problemów, "
              f"{r['durationMs']} ms{tokens}")
    print(f"\nPrzetworzono {done}/{len(files)} plików, wywołania modelu: {calls} → {dst}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # konsola Windows (cp1250) nie zna części znaków
    parser = argparse.ArgumentParser(description="Wsadowa konwersja formularzy do konfiguracji JSON.")
    parser.add_argument("src", type=Path, help="Katalog z plikami formularzy")
    parser.add_argument("dst", type=Path, help="Katalog na wyniki")
    parser.add_argument("--max-llm-calls", type=int, default=None, help="Limit wywołań modelu językowego")
    args = parser.parse_args()
    sys.exit(main(args.src, args.dst, max_llm_calls=args.max_llm_calls))
