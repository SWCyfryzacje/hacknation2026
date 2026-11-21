"""Wystawienie tokenu JWT do testów: `python -m app.token_cli --sub urzednik --hours 8`.

Używa JWT_SECRET z konfiguracji (zmienne środowiskowe / .env).
"""

import argparse

from app.config import get_settings
from app.errors import AuthNotConfigured
from app.security import issue_token


def main() -> None:
    parser = argparse.ArgumentParser(description="Wystaw token JWT dla API Formularze AI.")
    parser.add_argument("--sub", default="tester", help="Identyfikator użytkownika (claim 'sub').")
    parser.add_argument("--hours", type=float, default=8, help="Ważność tokenu w godzinach.")
    args = parser.parse_args()
    try:
        print(issue_token(args.sub, get_settings(), ttl_minutes=args.hours * 60))
    except AuthNotConfigured as exc:
        raise SystemExit(exc.message) from None


if __name__ == "__main__":
    main()
