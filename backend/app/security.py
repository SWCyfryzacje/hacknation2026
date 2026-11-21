"""Uwierzytelnianie: wystawianie i weryfikacja tokenów JWT (nagłówek Authorization: Bearer)."""

import datetime as dt
import hmac
from typing import Annotated, Any

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, get_settings
from app.errors import AuthNotConfigured, Unauthorized

_bearer = HTTPBearer(auto_error=False, description="Token JWT podpisany kluczem z JWT_SECRET / JWT_PUBLIC_KEY.")


def issue_token(subject: str, settings: Settings, *, ttl_minutes: float | None = None) -> str:
    """Token HMAC podpisany JWT_SECRET (z `exp`, opcjonalnie `aud`/`iss` z konfiguracji)."""
    if not settings.jwt_secret:
        raise AuthNotConfigured("Wystawianie tokenów wymaga ustawienia JWT_SECRET.")
    now = dt.datetime.now(dt.UTC)
    claims: dict[str, Any] = {"sub": subject, "iat": now,
                              "exp": now + dt.timedelta(minutes=ttl_minutes or settings.jwt_ttl_minutes)}
    if settings.jwt_audience:
        claims["aud"] = settings.jwt_audience
    if settings.jwt_issuer:
        claims["iss"] = settings.jwt_issuer
    algorithm = next((a for a in settings.jwt_algorithms if a.startswith("HS")), "HS256")
    return jwt.encode(claims, settings.jwt_secret.get_secret_value(), algorithm=algorithm)


def check_credentials(username: str, password: str, settings: Settings) -> None:
    if not settings.login_configured:
        raise AuthNotConfigured("Logowanie nie jest skonfigurowane (AUTH_USERNAME, AUTH_PASSWORD, JWT_SECRET).")
    assert settings.auth_username and settings.auth_password
    # compare_digest dla obu pól — czas odpowiedzi nie zdradza, która część się nie zgadza.
    user_ok = hmac.compare_digest(username.encode(), settings.auth_username.encode())
    pass_ok = hmac.compare_digest(password.encode(), settings.auth_password.get_secret_value().encode())
    if not (user_ok and pass_ok):
        raise Unauthorized("Nieprawidłowy login lub hasło.")


def decode_token(token: str, settings: Settings) -> dict[str, Any]:
    key = settings.jwt_public_key or (settings.jwt_secret.get_secret_value() if settings.jwt_secret else "")
    try:
        return jwt.decode(
            token,
            key,
            algorithms=settings.jwt_algorithms,
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            leeway=settings.jwt_leeway_s,
            options={"require": ["exp"], "verify_aud": settings.jwt_audience is not None},
        )
    except jwt.ExpiredSignatureError:
        raise Unauthorized("Token wygasł.") from None
    except jwt.InvalidTokenError as exc:
        raise Unauthorized(f"Nieprawidłowy token: {exc}") from None


def require_auth(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, Any] | None:
    if not settings.auth_enabled:
        return None
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise Unauthorized("Wymagany nagłówek Authorization: Bearer <token>.")
    return decode_token(credentials.credentials, settings)
