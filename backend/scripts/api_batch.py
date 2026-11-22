"""Automatyczne testy REST API na wielu serwerach równolegle — dowód działania (proof of work).

    python scripts/api_batch.py --target lokalny=http://localhost:8000 --target serwer=http://77.45.76.243:8000 \
        --input ../materials/formularze --out ../wyniki/testy/01-porownanie --workers 3

Co robi:
  * pyta każdy serwer o aktywny model (`GET /health` → `llmModel`),
  * każdy plik wysyła do każdego **różnego** modelu dokładnie raz — rejestr `wyniki/testy/rejestr.json`
    (klucz: SHA-256 pliku + model) pilnuje, żeby ta sama para plik × model nie była liczona dwa razy, także
    między uruchomieniami; gdy dwa serwery mają ten sam model, pliki są między nie dzielone,
  * mierzy dwa czasy: całkowity widziany przez klienta (wysyłka + przetwarzanie + sieć) i czas przetwarzania
    po stronie serwera (`report.durationMs`),
  * zapisuje wynik, raport i słowniki do `<out>/<serwer>/`, a podsumowanie do `<out>/podsumowanie.csv` i `.md`.

Logowanie: zmienne `API_USER_<NAZWA>` / `API_PASSWORD_<NAZWA>` (np. API_PASSWORD_SERWER), a gdy ich brak —
ukryte pytanie o hasło w terminalu. Token jest trzymany tylko w pamięci.
`--dry-run` pokazuje plan (co, gdzie, ile wywołań) bez wysyłania czegokolwiek.
"""

from __future__ import annotations

import argparse
import csv
import getpass
import hashlib
import json
import os
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import httpx

EXTENSIONS = {".pdf", ".doc", ".docx", ".ods", ".xlsx", ".jpg", ".jpeg", ".png"}
REGISTRY_DEFAULT = Path(__file__).resolve().parents[2] / "wyniki" / "testy" / "rejestr.json"
CREDIT_ERRORS = ("HTTP 401", "HTTP 402", "HTTP 403", "insufficient", "credit")


@dataclass
class Target:
    name: str
    url: str
    workers: int
    model: str = "?"
    token: str | None = None
    stopped: str | None = None  # powód zatrzymania (np. brak środków na koncie Eden AI)
    lock: threading.Lock = field(default_factory=threading.Lock)
    slots: threading.Semaphore | None = None


@dataclass(frozen=True)
class Job:
    path: Path
    sha: str
    target: Target

    @property
    def key(self) -> str:
        return f"{self.sha}:{self.target.model}"


# ------------------------------------------------------------------ rejestr bez duplikatów


class Registry:
    """Plik JSON: {"<sha256>:<model>": {...wpis...}}.

    Bezpieczny dla wielu wątków i wielu procesów naraz (np. osobne uruchomienia lokalne i na serwer):
    każdy zapis bierze blokadę plikową, wczytuje aktualny stan z dysku, dokłada wpis i zapisuje atomowo.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self.lock = threading.Lock()
        self.entries: dict[str, dict] = self._read()

    def _read(self) -> dict[str, dict]:
        return json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}

    def has(self, key: str) -> bool:
        entry = self.entries.get(key)
        # Za wykonane uznajemy tylko prawdziwe wyniki modelu; "fallback" (reguły) i błędy są powtarzane.
        return bool(entry and entry.get("status") == "ok")

    def put(self, key: str, entry: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock_file = self.path.with_suffix(".lock")
        with self.lock:
            for _ in range(600):  # do ~60 s czekania na inny proces
                try:
                    fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                    break
                except FileExistsError:
                    time.sleep(0.1)
            else:
                raise RuntimeError(f"Rejestr zablokowany: usuń {lock_file}, jeśli żaden test nie działa.")
            try:
                self.entries = self._read() | {key: entry}  # scalenie z wpisami innych procesów
                tmp = self.path.with_suffix(f".{os.getpid()}.tmp")
                tmp.write_text(json.dumps(self.entries, ensure_ascii=False, indent=2), encoding="utf-8")
                tmp.replace(self.path)
            finally:
                os.close(fd)
                lock_file.unlink(missing_ok=True)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plan_jobs(files: list[Path], targets: list[Target], registry: Registry) -> tuple[list[Job], int]:
    """Każdy plik × każdy różny model raz; serwery z tym samym modelem dzielą pliki po kolei."""
    by_model: dict[str, list[Target]] = {}
    for t in targets:
        by_model.setdefault(t.model, []).append(t)
    jobs, skipped = [], 0
    for i, path in enumerate(files):
        digest = sha256(path)
        for group in by_model.values():
            target = group[i % len(group)]
            job = Job(path, digest, target)
            if registry.has(job.key):
                skipped += 1
            else:
                jobs.append(job)
    return jobs, skipped


# ------------------------------------------------------------------ komunikacja z API


def credentials(target: Target) -> tuple[str, str]:
    env = target.name.upper().replace("-", "_")
    user = os.environ.get(f"API_USER_{env}") or os.environ.get("API_USER") or "urzednik"
    password = os.environ.get(f"API_PASSWORD_{env}") or os.environ.get("API_PASSWORD")
    if not password:
        password = getpass.getpass(f"Hasło aplikacji dla '{target.name}' ({target.url}, użytkownik {user}): ")
    return user, password


def probe(target: Target, client: httpx.Client) -> None:
    health = client.get(f"{target.url}/health", timeout=20).json()
    target.model = health.get("llmModel") or ("reguly" if not health.get("llm") else "?")
    auth = client.get(f"{target.url}/api/v1/auth/config", timeout=20).json()
    if auth.get("authEnabled"):
        login(target, client)


def login(target: Target, client: httpx.Client) -> None:
    user, password = credentials(target)
    r = client.post(f"{target.url}/api/v1/auth/token", json={"username": user, "password": password}, timeout=30)
    if r.status_code != 200:
        raise SystemExit(f"Logowanie do '{target.name}' nieudane (HTTP {r.status_code}): {r.text[:200]}")
    target.token = r.json()["access_token"]


def convert(job: Job, client: httpx.Client, timeout: float) -> tuple[int, dict | str, float]:
    t = job.target
    for attempt in (1, 2):
        headers = {"Authorization": f"Bearer {t.token}"} if t.token else {}
        started = time.perf_counter()
        with job.path.open("rb") as fh:
            r = client.post(f"{t.url}/api/v1/forms/convert", params={"report": "true"}, headers=headers,
                            files={"file": (job.path.name, fh)}, timeout=timeout)
        wall = time.perf_counter() - started
        if r.status_code == 401 and attempt == 1 and t.token:
            with t.lock:
                login(t, client)  # token wygasł — logujemy ponownie raz
            continue
        try:
            return r.status_code, r.json(), wall
        except ValueError:
            return r.status_code, r.text[:500], wall
    return 401, "Nie udało się uwierzytelnić.", 0.0


def run_job(job: Job, client: httpx.Client, out: Path, registry: Registry, timeout: float) -> dict:
    t = job.target
    assert t.slots is not None
    with t.slots:
        if t.stopped:
            return {"file": job.path.name, "target": t.name, "model": t.model, "status": "pominiety"}
        started_at = datetime.now(UTC).isoformat(timespec="seconds")
        code, body, wall = convert(job, client, timeout)

    entry = {"file": job.path.name, "sha256": job.sha, "model": t.model, "target": t.name, "url": t.url,
             "startedAt": started_at, "httpStatus": code, "clientSeconds": round(wall, 2)}
    if code == 200 and isinstance(body, dict):
        report, form = body["report"], body["form"]
        folder = out / t.name
        folder.mkdir(parents=True, exist_ok=True)
        base = folder / job.path.name
        base.with_name(base.name + ".json").write_text(json.dumps(form, ensure_ascii=False, indent=2), "utf-8")
        base.with_name(base.name + ".report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2),
                                                              "utf-8")
        if report.get("proposedDictionaries"):
            base.with_name(base.name + ".slowniki.json").write_text(
                json.dumps({"dictionaries": report["proposedDictionaries"]}, ensure_ascii=False, indent=2), "utf-8")
        usage = report["analysis"].get("llmUsage") or {}
        warnings = report.get("warnings") or []
        fallback = report["analysis"]["analyzer"] != "llm" and t.model not in ("reguly", "?")
        if fallback and any(any(m in w for m in CREDIT_ERRORS) for w in warnings):
            t.stopped = "Eden AI odrzuca wywołania (brak środków / klucz) — dalsze pliki pominięte"
        entry |= {
            "status": "fallback" if fallback else "ok",
            "serverSeconds": round(report["durationMs"] / 1000, 2),
            "analyzer": report["analysis"]["analyzer"], "title": form.get("title"),
            "pages": report["stats"]["pages"], "sections": report["stats"]["sections"],
            "fields": report["stats"]["fields"], "conditional": report["stats"]["conditional"],
            "issues": len(report.get("issues") or []), "warnings": len(warnings),
            "llmCalls": usage.get("calls", 0), "promptTokens": usage.get("prompt_tokens", 0),
            "completionTokens": usage.get("completion_tokens", 0),
            "ocr": report["extraction"].get("ocrEngine"), "result": str(base.with_name(base.name + ".json")),
        }
    else:
        detail = body.get("detail") if isinstance(body, dict) else body
        entry |= {"status": "error", "error": str(detail)[:300]}
    registry.put(job.key, entry)
    return entry


# ------------------------------------------------------------------ podsumowanie


def summarize(rows: list[dict], out: Path, label: str = "") -> str:
    out.mkdir(parents=True, exist_ok=True)
    suffix = f"-{label}" if label else ""  # osobne podsumowanie dla każdego uruchomienia (np. lokalne / serwer)
    cols = ["file", "target", "model", "status", "analyzer", "clientSeconds", "serverSeconds", "pages", "sections",
            "fields", "conditional", "issues", "warnings", "llmCalls", "promptTokens", "completionTokens", "ocr",
            "error"]
    with (out / f"podsumowanie{suffix}.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    lines = ["| Serwer | Model | OK / wszystkie | Czas klienta śr. / mediana / max [s] | Czas serwera śr. [s] "
             "| Pola śr. | Tokeny (we + wy) | Błędy |", "|---|---|---|---|---|---|---|---|"]
    for (target, model) in sorted({(r["target"], r["model"]) for r in rows}):
        group = [r for r in rows if r["target"] == target and r["model"] == model]
        ok = [r for r in group if r.get("status") == "ok"]
        wall = [r["clientSeconds"] for r in ok] or [0]
        server = [r["serverSeconds"] for r in ok] or [0]
        fields = [r["fields"] for r in ok] or [0]
        tok_in = sum(r.get("promptTokens", 0) for r in ok)
        tok_out = sum(r.get("completionTokens", 0) for r in ok)
        lines.append(f"| {target} | `{model}` | {len(ok)} / {len(group)} | {statistics.mean(wall):.1f} / "
                     f"{statistics.median(wall):.1f} / {max(wall):.1f} | {statistics.mean(server):.1f} | "
                     f"{statistics.mean(fields):.0f} | {tok_in} + {tok_out} | {len(group) - len(ok)} |")
    table = "\n".join(lines)
    (out / f"podsumowanie{suffix}.md").write_text(
        f"# Podsumowanie testów API\n\nWygenerowano: {datetime.now(UTC).isoformat(timespec='seconds')}\n\n{table}\n",
        encoding="utf-8")
    return table


# ------------------------------------------------------------------ uruchomienie


def collect(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        files += sorted(f for f in p.rglob("*") if f.suffix.lower() in EXTENSIONS) if p.is_dir() else [p]
    return files


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Równoległe testy REST API Formularze AI z rejestrem bez duplikatów.")
    ap.add_argument("--target", action="append", required=True, help="NAZWA=URL, np. serwer=http://1.2.3.4:8000")
    ap.add_argument("--input", action="append", required=True, type=Path, help="Plik lub katalog z formularzami")
    ap.add_argument("--out", required=True, type=Path, help="Katalog na wyniki (w repozytorium)")
    ap.add_argument("--workers", type=int, default=3, help="Równoległe konwersje na jeden serwer")
    ap.add_argument("--timeout", type=float, default=900, help="Limit czasu jednej konwersji [s]")
    ap.add_argument("--registry", type=Path, default=REGISTRY_DEFAULT)
    ap.add_argument("--dry-run", action="store_true", help="Tylko plan, bez wysyłania")
    args = ap.parse_args()

    targets = []
    for spec in args.target:
        name, _, url = spec.partition("=")
        targets.append(Target(name=name, url=url.rstrip("/"), workers=args.workers))
    files = collect(args.input)
    registry = Registry(args.registry)

    with httpx.Client() as client:
        reachable = []
        for t in targets:
            try:
                if args.dry_run:  # plan bez logowania
                    t.model = client.get(f"{t.url}/health", timeout=20).json().get("llmModel") or "reguly"
                else:
                    probe(t, client)
            except httpx.HTTPError as exc:
                print(f"✗ {t.name:10} {t.url:32} niedostępny ({type(exc).__name__}) — pomijam ten serwer")
                continue
            t.slots = threading.Semaphore(t.workers)
            reachable.append(t)
            print(f"• {t.name:10} {t.url:32} model: {t.model}")
        targets = reachable
        if not targets:
            print("Żaden serwer nie odpowiada — sprawdź adresy i czy kontenery działają (docker ps).")
            return 1
        jobs, skipped = plan_jobs(files, targets, registry)
        print(f"\nPliki: {len(files)}, do wysłania: {len(jobs)}, pominięte (już w rejestrze): {skipped}")
        for t in targets:
            print(f"  {t.name}: {sum(j.target is t for j in jobs)} konwersji")
        if args.dry_run or not jobs:
            return 0

        rows: list[dict] = []
        with ThreadPoolExecutor(max_workers=sum(t.workers for t in targets)) as pool:
            futures = [pool.submit(run_job, j, client, args.out, registry, args.timeout) for j in jobs]
            for done, future in enumerate(as_completed(futures), 1):
                r = future.result()
                rows.append(r)
                info = (f"{r.get('clientSeconds', 0):6.1f}s klient, {r.get('serverSeconds', 0):6.1f}s serwer, "
                        f"{r.get('fields', 0)} pól" if r["status"] in ("ok", "fallback") else r.get("error", ""))
                print(f"[{done}/{len(jobs)}] {r['status']:9} {r['target']:8} {r['file'][:50]:50} {info}")

    for t in targets:
        if t.stopped:
            print(f"\n⚠ {t.name}: {t.stopped}")
    print("\n" + summarize(rows, args.out, "-".join(t.name for t in targets)))
    return 0 if all(r["status"] == "ok" for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
