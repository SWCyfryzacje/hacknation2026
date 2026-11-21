"""Przetwarzanie wsadowe: konwertuje wszystkie obsługiwane pliki z katalogu i zapisuje wyniki.

    python scripts/convert_dir.py <katalog_wejściowy> <katalog_wyjściowy>

Dla każdego pliku powstaje `<nazwa>.json` (konfiguracja formularza) i `<nazwa>.report.json` (raport).
Konfiguracja (klucz Eden AI, model itd.) jest wczytywana z .env / zmiennych środowiskowych.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import Settings  # noqa: E402
from app.errors import AppError  # noqa: E402
from app.files.formats import EXTENSION_TO_MIME  # noqa: E402
from app.files.validation import validate_upload  # noqa: E402
from app.service import convert  # noqa: E402


def main(src: Path, dst: Path) -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # konsola Windows (cp1250) nie zna części znaków
    settings = Settings(auth_enabled=False)
    dst.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in src.rglob("*") if p.suffix.lower() in EXTENSION_TO_MIME)
    failures = 0
    for path in files:
        try:
            file = validate_upload(path.name, path.read_bytes(), None, max_size=settings.max_file_size_bytes,
                                   max_uncompressed=settings.max_uncompressed_bytes)
            result = convert(file, settings)
        except AppError as exc:
            failures += 1
            print(f"BŁĄD  {path.name}: {exc.message}")
            continue
        (dst / f"{path.stem}{path.suffix.lower()}.json").write_text(
            json.dumps(result.form, ensure_ascii=False, indent=2), encoding="utf-8")
        (dst / f"{path.stem}{path.suffix.lower()}.report.json").write_text(
            json.dumps(result.report, ensure_ascii=False, indent=2), encoding="utf-8")
        r = result.report
        print(f"OK    {path.name}: {r['analysis']['analyzer']}, {r['stats']['fields']} pól, "
              f"{len(r['warnings'])} ostrzeżeń, {len(r['issues'])} problemów, {r['durationMs']} ms")
    print(f"\nPrzetworzono {len(files) - failures}/{len(files)} plików → {dst}")
    return 1 if failures else 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sys.exit(main(Path(sys.argv[1]), Path(sys.argv[2])))
