"""Wystawienie tokenu JWT do testów: `python -m app.token_cli --sub urzednik --hours 8`.

Używa JWT_SECRET z konfiguracji (zmienne środowiskowe / .env).
"""

import argparse
import datetime as dt

import jwt

from app.config import get_settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Wystaw token JWT dla API Formularze AI.")
    parser.add_argument("--sub", default="tester", help="Identyfikator użytkownika (claim 'sub').")
    parser.add_argument("--hours", type=float, default=8, help="Ważność tokenu w godzinach.")
    args = parser.parse_args()

    settings = get_settings()
    if not settings.jwt_secret:
        raise SystemExit("Ustaw JWT_SECRET, aby wystawić token HMAC.")
    now = dt.datetime.now(dt.UTC)
    claims = {"sub": args.sub, "iat": now, "exp": now + dt.timedelta(hours=args.hours)}
    if settings.jwt_audience:
        claims["aud"] = settings.jwt_audience
    if settings.jwt_issuer:
        claims["iss"] = settings.jwt_issuer
    print(jwt.encode(claims, settings.jwt_secret.get_secret_value(), algorithm=settings.jwt_algorithms[0]))


if __name__ == "__main__":
    main()
