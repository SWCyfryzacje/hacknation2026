"""Uwierzytelnianie żądań tokenem JWT (nagłówek Authorization: Bearer)."""

from typing import Annotated, Any

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, get_settings
from app.errors import Unauthorized

_bearer = HTTPBearer(auto_error=False, description="Token JWT podpisany kluczem z JWT_SECRET / JWT_PUBLIC_KEY.")


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
