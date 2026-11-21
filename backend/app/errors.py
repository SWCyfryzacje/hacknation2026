"""Błędy domenowe mapowane na odpowiedzi HTTP w formacie application/problem+json (RFC 9457)."""

from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    status_code: int = 400
    code: str = "bad_request"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidFileName(AppError):
    status_code = 422
    code = "invalid_file_name"


class UnsupportedFileType(AppError):
    status_code = 415
    code = "unsupported_file_type"


class FileTooLarge(AppError):
    status_code = 413
    code = "file_too_large"


class EmptyFile(AppError):
    status_code = 422
    code = "empty_file"


class ExtractionFailed(AppError):
    status_code = 422
    code = "extraction_failed"


class ConversionUnavailable(AppError):
    status_code = 503
    code = "conversion_unavailable"


class Unauthorized(AppError):
    status_code = 401
    code = "unauthorized"


async def app_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
    return JSONResponse(
        status_code=exc.status_code,
        content={"type": f"urn:formularze:{exc.code}", "title": exc.code, "status": exc.status_code,
                 "detail": exc.message},
        media_type="application/problem+json",
        headers=headers,
    )
