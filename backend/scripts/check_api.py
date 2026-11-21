"""Skrypt do testowania komunikacji z REST API Formularze AI (lokalnym lub zdalnym).

Działa bez zewnętrznych zależności (używa wbudowanego urllib, a jeśli dostępny jest httpx, korzysta z niego).
Pobiera dane konfiguracyjne z backend/.env lub zmiennych środowiskowych, analogicznie do check_balance.py.

Wykonuje testy:
1. GET /health                - stan usługi, wersja, dostępność LLM
2. GET /api/v1/auth/config    - konfiguracja logowania
3. GET /api/v1/formats        - obsługiwane formaty i limit rozmiaru
4. POST /api/v1/auth/token    - logowanie i pobranie tokenu JWT (jeśli auth jest włączone)
5. POST /api/v1/forms/convert - opcjonalny test konwersji pliku formularza

Użycie:
    python scripts/check_api.py
    python scripts/check_api.py --url http://192.168.1.50:8000
    python scripts/check_api.py --url http://192.168.1.50:8000 --file "sciezka/do/formularza.docx"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

# Katalog backend jako root importów aplikacji
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

DEFAULT_API_URL = "http://localhost:8000"


def read_env_values() -> dict[str, str]:
    """Wczytuje zmienne z backend/.env lub app.config.Settings."""
    values: dict[str, str] = {}

    # 1. Próba przez app.config.Settings
    try:
        from app.config import Settings

        env_path = BACKEND_DIR / ".env"
        try:
            settings = Settings(auth_enabled=False, _env_file=str(env_path) if env_path.exists() else None)
        except TypeError:
            settings = Settings(auth_enabled=False)

        if settings.auth_username:
            values["AUTH_USERNAME"] = settings.auth_username
        if settings.auth_password:
            values["AUTH_PASSWORD"] = settings.auth_password
        if settings.jwt_secret:
            values["JWT_SECRET"] = settings.jwt_secret
    except Exception:
        pass

    # 2. Bezpośrednie wczytanie z backend/.env (gdy zależności Pydantic nie są zainstalowane)
    env_path = BACKEND_DIR / ".env"
    if env_path.is_file():
        try:
            with open(env_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        val = v.strip().strip("'\"")
                        if val and k not in values:
                            values[k] = val
        except Exception:
            pass

    # 3. Zmienne środowiskowe systemu
    for k in ("AUTH_USERNAME", "AUTH_PASSWORD", "JWT_SECRET", "API_URL"):
        val = os.environ.get(k)
        if val:
            values[k] = val

    return values


def create_token_from_secret(jwt_secret: str, username: str = "tester") -> str | None:
    """Tworzy token JWT lokalnie za pomocą klucza JWT_SECRET."""
    try:
        from app.config import Settings
        from app.security import issue_token

        settings = Settings(jwt_secret=jwt_secret)
        return issue_token(username, settings, ttl_minutes=480)
    except Exception:
        return None


class SimpleHttpClient:
    """Prosty klient HTTP używający urllib (brak zewnętrznych zależności)."""

    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def request(
        self,
        method: str,
        path: str,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        data: bytes | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> tuple[int, dict[str, str], Any]:
        url = f"{self.base_url}{path}"
        if params:
            url += f"?{urllib.parse.urlencode(params)}"

        hdrs = {
            "Accept": "application/json",
            "User-Agent": "Formularze-API-Check/1.0",
        }
        if headers:
            hdrs.update(headers)

        body_bytes = data
        if json_data is not None:
            hdrs["Content-Type"] = "application/json"
            body_bytes = json.dumps(json_data).encode("utf-8")

        req = urllib.request.Request(url, data=body_bytes, headers=hdrs, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                resp_headers = {k: v for k, v in resp.getheaders()}
                raw = resp.read().decode("utf-8", errors="replace")
                try:
                    payload = json.loads(raw)
                except Exception:
                    payload = raw
                return resp.status, resp_headers, payload
        except urllib.error.HTTPError as exc:
            resp_headers = {k: v for k, v in exc.headers.items()}
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw)
            except Exception:
                payload = raw
            return exc.code, resp_headers, payload
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Błąd połączenia z {url}: {exc.reason}") from exc


def run_checks(
    base_url: str,
    file_path: Path | None = None,
    username: str | None = None,
    password: str | None = None,
    token: str | None = None,
    output_path: Path | None = None,
    timeout: float = 60.0,
) -> int:
    client = SimpleHttpClient(base_url=base_url, timeout=timeout)
    print(f"=== Sprawdzanie API pod adresem: {base_url} ===")

    # 1. Test /health
    print("\n[1/4] Sprawdzanie GET /health ...")
    try:
        code, _, health_data = client.request("GET", "/health")
        if code != 200:
            print(f"  ✗ BŁĄD: /health zwrócił kod {code}: {health_data}", file=sys.stderr)
            return 1
        status = health_data.get("status") if isinstance(health_data, dict) else health_data
        version = health_data.get("version", "nieznana") if isinstance(health_data, dict) else "nieznana"
        llm_active = health_data.get("llm", False) if isinstance(health_data, dict) else False

        print(f"  ✓ Status: {status} (wersja: {version})")
        print(f"  ✓ Obsługa LLM (Eden AI): {'WŁĄCZONA' if llm_active else 'WYŁĄCZONA (tryb regułowy)'}")
    except Exception as exc:
        print(f"  ✗ BŁĄD połączenia z /health: {exc}", file=sys.stderr)
        return 1

    # 2. Test /api/v1/auth/config
    print("\n[2/4] Sprawdzanie GET /api/v1/auth/config ...")
    auth_enabled = True
    try:
        code, _, auth_data = client.request("GET", "/api/v1/auth/config")
        if code == 200 and isinstance(auth_data, dict):
            auth_enabled = auth_data.get("authEnabled", True)
            login_configured = auth_data.get("loginConfigured", False)
            print(f"  ✓ Uwierzytelnianie aktywne: {auth_enabled}")
            print(f"  ✓ Logowanie hasłem skonfigurowane: {login_configured}")
        else:
            print(f"  ⚠ Kod {code}: {auth_data}")
    except Exception as exc:
        print(f"  ⚠ Nie udało się pobrać konfiguracji auth ({exc}) — zakładam auth_enabled=True")

    # 3. Test /api/v1/formats
    print("\n[3/4] Sprawdzanie GET /api/v1/formats ...")
    try:
        code, _, formats_data = client.request("GET", "/api/v1/formats")
        if code != 200 or not isinstance(formats_data, dict):
            print(f"  ✗ BŁĄD pobierania formatów (kod {code}): {formats_data}", file=sys.stderr)
            return 1
        fmts = list(formats_data.get("formats", {}).keys())
        max_mb = formats_data.get("maxFileSizeBytes", 0) / (1024 * 1024)
        print(f"  ✓ Obsługiwane formaty ({len(fmts)}): {', '.join(fmts)}")
        print(f"  ✓ Maksymalny rozmiar pliku: {max_mb:.1f} MB")
    except Exception as exc:
        print(f"  ✗ BŁĄD pobierania formatów: {exc}", file=sys.stderr)
        return 1

    # 4. Uwierzytelnienie (JWT)
    jwt_token = token
    if auth_enabled and not jwt_token:
        print("\n[4/4] Uzyskiwanie tokenu JWT ...")
        if username and password:
            try:
                code, _, token_data = client.request(
                    "POST", "/api/v1/auth/token", json_data={"username": username, "password": password}
                )
                if code == 200 and isinstance(token_data, dict):
                    jwt_token = token_data.get("access_token")
                    expires = token_data.get("expires_in", 0)
                    print(f"  ✓ Zalogowano jako '{username}' (token ważny przez {expires}s)")
                else:
                    print(f"  ✗ Błąd logowania (HTTP {code}): {token_data}")
            except Exception as exc:
                print(f"  ✗ Błąd zapytania logowania: {exc}")

        # Jeśli logowanie przez HTTP nie powiodło się, próba lokalnego wygenerowania z JWT_SECRET
        if not jwt_token:
            env_vars = read_env_values()
            secret = env_vars.get("JWT_SECRET")
            if secret:
                jwt_token = create_token_from_secret(secret, username=username or "tester")
                if jwt_token:
                    print("  ✓ Wygenerowano token JWT lokalnie na podstawie JWT_SECRET")

        if not jwt_token:
            print("  ⚠ Brak tokenu JWT. Jeśli endpointy wymagają autoryzacji, kolejne żądania mogą zwrócić 401.")
    else:
        print("\n[4/4] Autoryzacja:")
        if jwt_token:
            print("  ✓ Użyto przekazanego tokenu Bearer")
        else:
            print("  ✓ Uwierzytelnianie jest wyłączone na serwerze")

    # 5. Opcjonalny test konwersji pliku
    if file_path:
        print(f"\n[TEST KONWERSJI] POST /api/v1/forms/convert ...")
        if not file_path.is_file():
            print(f"  ✗ BŁĄD: Plik '{file_path}' nie istnieje!", file=sys.stderr)
            return 1

        print(f"  Wysyłanie pliku: {file_path.name} ({file_path.stat().st_size / 1024:.1f} KB)")
        try:
            with open(file_path, "rb") as f:
                file_bytes = f.read()

            boundary = f"----FormBoundary{int(time.time() * 1000)}"
            delimiter = f"--{boundary}\r\n".encode("utf-8")
            end_boundary = f"\r\n--{boundary}--\r\n".encode("utf-8")

            part_header = (
                f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"\r\n'
                f"Content-Type: application/octet-stream\r\n\r\n"
            ).encode("utf-8")

            multipart_body = delimiter + part_header + file_bytes + end_boundary

            headers = {
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            }
            if jwt_token:
                headers["Authorization"] = f"Bearer {jwt_token}"

            t0 = time.perf_counter()
            code, resp_headers, result = client.request(
                "POST",
                "/api/v1/forms/convert",
                params={"report": "true"},
                headers=headers,
                data=multipart_body,
            )
            duration = time.perf_counter() - t0

            if code == 200 and isinstance(result, dict):
                # Dopasowanie wielkości liter w nagłówkach
                analyzer = resp_headers.get("x-analyzer") or resp_headers.get("X-Analyzer", "nieznany")
                warnings_hdr = resp_headers.get("x-warnings") or resp_headers.get("X-Warnings", "0")

                form_data = result.get("form", {})
                report_data = result.get("report", {})
                tabs = form_data.get("tabs", [])
                total_sections = sum(len(t.get("sections", [])) for t in tabs)

                print(f"  ✓ Sukces! Czas odpowiedzi: {duration:.2f} s (HTTP 200)")
                print(f"  ✓ Analizator: {analyzer}")
                print(f"  ✓ Ostrzeżeń: {warnings_hdr}")
                print(f"  ✓ Tytuł eUsługi: '{form_data.get('title', 'brak')}'")
                print(f"  ✓ Struktura: {len(tabs)} stron/kroków, {total_sections} sekcji")

                dicts = report_data.get("proposedDictionaries", [])
                if dicts:
                    names = [d.get("name", "") for d in dicts]
                    print(f"  ✓ Zaproponowane nowe słowniki ({len(dicts)}): {', '.join(names)}")

                if output_path:
                    with open(output_path, "w", encoding="utf-8") as out:
                        json.dump(result, out, indent=2, ensure_ascii=False)
                    print(f"  ✓ Zapisano wynik w: {output_path}")

            else:
                print(f"  ✗ Błąd konwersji (HTTP {code}) w {duration:.2f} s:")
                if isinstance(result, (dict, list)):
                    print(json.dumps(result, indent=2, ensure_ascii=False))
                else:
                    print(result)
                return 1

        except Exception as exc:
            print(f"  ✗ Błąd żądania konwersji: {exc}", file=sys.stderr)
            return 1

    print("\n===========================================")
    print("Wszystkie wykonane testy zakończone sukcesem!")
    print("===========================================")
    return 0


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    env_vars = read_env_values()

    parser = argparse.ArgumentParser(description="Testuje działanie REST API Formularze AI.")
    parser.add_argument(
        "--url",
        default=env_vars.get("API_URL", DEFAULT_API_URL),
        help=f"Bazowy adres URL API (domyślnie: {DEFAULT_API_URL} lub z API_URL)",
    )
    parser.add_argument(
        "--file",
        "-f",
        type=Path,
        default=None,
        help="Opcjonalna ścieżka do pliku formularza (PDF, DOCX, XLSX itp.) do przetestowania /api/v1/forms/convert",
    )
    parser.add_argument(
        "--user",
        "-u",
        default=env_vars.get("AUTH_USERNAME"),
        help="Nazwa użytkownika do logowania (domyślnie z .env: AUTH_USERNAME)",
    )
    parser.add_argument(
        "--password",
        "-p",
        default=env_vars.get("AUTH_PASSWORD"),
        help="Hasło do logowania (domyślnie z .env: AUTH_PASSWORD)",
    )
    parser.add_argument(
        "--token",
        "-t",
        default=None,
        help="Opcjonalny gotowy token JWT Bearer (omija logowanie)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Ścieżka do zapisu wyniku JSON (używana z --file)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Maksymalny czas oczekiwania na odpowiedź w sekundach (domyślnie 30.0)",
    )

    args = parser.parse_args()

    return run_checks(
        base_url=args.url,
        file_path=args.file,
        username=args.user,
        password=args.password,
        token=args.token,
        output_path=args.output,
        timeout=args.timeout,
    )


if __name__ == "__main__":
    sys.exit(main())
