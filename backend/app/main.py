"""Punkt wejścia aplikacji: `uvicorn app.main:app`."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api import router
from app.config import get_settings
from app.errors import AppError, app_error_handler

STATIC_DIR = Path(__file__).parent / "static"


def create_app() -> FastAPI:
    settings = get_settings()  # błędna konfiguracja zatrzymuje start, a nie pierwsze żądanie
    app = FastAPI(
        title="Formularze AI",
        version=__version__,
        description="Analiza formularzy urzędowych i generowanie konfiguracji eUsługi w formacie JSON.",
    )
    if settings.cors_origins:
        app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["GET", "POST"],
                           allow_headers=["Authorization", "Content-Type"],
                           expose_headers=["X-Analyzer", "X-Warnings"])
    app.add_exception_handler(AppError, app_error_handler)
    app.include_router(router)
    if settings.ui_enabled:
        # Zasoby strony WWW (biblioteka JSONata do podglądu formularza) — serwowane lokalnie, bez CDN.
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


app = create_app()
