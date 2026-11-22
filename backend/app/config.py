"""Konfiguracja aplikacji — wyłącznie przez zmienne środowiskowe (lub plik .env).

Sekrety (JWT_SECRET, AUTH_PASSWORD, EDENAI_API_KEY) podaje się dopiero przy uruchomieniu kontenera.
"""

from enum import StrEnum
from functools import lru_cache

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class FinishComponent(StrEnum):
    """Komponent informacyjny na stronie końcowej."""

    TEXT_BLOCK = "TEXT_BLOCK"  # jak w referencyjnych eksportach z systemu (domyślnie)
    INFO_SECTION = "INFO_SECTION"  # wariant z „Reguł technicznych”


class ValidationMode(StrEnum):
    """Czy wypełniać tablice `validation` nazwami walidatorów."""

    FILLED = "filled"  # np. ["REQUIRED", "PESEL"] — zgodnie z opisem pliku importu
    EMPTY = "empty"  # puste tablice, dokładnie jak w referencyjnych eksportach


class Settings(BaseSettings):
    # hide_input_in_errors: komunikat o błędnej konfiguracji nie może wypisać wartości (w tym sekretów).
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    # --- Pliki ---------------------------------------------------------------
    max_file_size_mb: float = Field(10, gt=0, description="Maksymalny rozmiar przesyłanego pliku (MB).")
    max_uncompressed_mb: float = Field(
        100, gt=0, description="Limit rozmiaru po rozpakowaniu DOCX/XLSX/ODS (ochrona przed zip bomb)."
    )
    max_pdf_pages: int = Field(30, gt=0, description="Maksymalna liczba analizowanych stron PDF.")

    # --- HTTP ------------------------------------------------------------------
    cors_origins: list[str] = Field(default_factory=list, description='Np. ["https://oazai.pl"] dla frontendu.')

    # --- Uwierzytelnianie JWT -------------------------------------------------
    auth_enabled: bool = Field(True, description="Wyłączenie tylko do lokalnego developmentu.")
    jwt_secret: SecretStr | None = Field(None, description="Klucz HMAC (HS256/384/512).")
    jwt_public_key: str | None = Field(None, description="Klucz publiczny PEM (RS*/ES*).")
    jwt_algorithms: list[str] = Field(default_factory=lambda: ["HS256"])
    jwt_audience: str | None = None
    jwt_issuer: str | None = None
    jwt_leeway_s: int = Field(30, ge=0)
    jwt_ttl_minutes: int = Field(480, gt=0, description="Ważność tokenów wystawianych przy logowaniu.")

    # --- Serwer MCP (opcjonalny interfejs dla asystentów AI) ---------------------
    mcp_port: int = Field(8100, gt=0, description="Port serwera MCP (python -m app.mcp_server).")
    mcp_safe_app_url: str = Field("http://localhost", description="Rządowa aplikacja, do której MCP odsyła przy "
                                                                    "wykryciu danych osobowych.")

    # --- Logowanie użytkownika frontendu (wydawanie tokenów JWT) --------------------
    auth_username: str | None = Field(None, description="Login urzędnika do frontendu.")
    auth_password: SecretStr | None = Field(None, description="Hasło urzędnika (sekret — tylko w środowisku).")

    # --- Eden AI (API organizatorów: model językowy + OCR) ----------------------
    edenai_api_key: SecretStr | None = Field(None, description="Klucz Eden AI. Brak = analiza regułami + Tesseract.")
    edenai_base_url: str = "https://api.edenai.run/v3"
    llm_enabled: bool = Field(True, description="Analiza modelem językowym (wymaga EDENAI_API_KEY).")
    llm_model: str = Field("mistral/mistral-large-4-0@eu", description="Model w formacie dostawca/model.")
    llm_fallback_models: list[str] = Field(
        default_factory=lambda: ["mistral/mistral-medium-3.5@eu"],
        description="Modele zapasowe, których Eden AI użyje, gdy główny zawiedzie (parametr `fallbacks`).")
    llm_max_input_chars: int = Field(40_000, gt=1000, description="Limit tekstu dokumentu wysyłanego do modelu.")
    llm_max_output_tokens: int = Field(32_000, gt=1000, description="Limit długości odpowiedzi modelu.")
    ocr_model: str = Field("ocr/ocr/mistral", description="Model OCR Eden AI (ocr/ocr/{dostawca}).")
    ocr_language: str = "pl"
    ai_timeout_s: float = Field(300, gt=0, description="Duże formularze potrafią zająć modelowi kilka minut.")

    # --- Ekstrakcja -----------------------------------------------------------
    ocr_enabled: bool = True
    ocr_languages: str = Field("pol", description="Języki zapasowego Tesseracta, np. 'pol' lub 'pol+eng'.")
    ocr_dpi: int = Field(300, ge=72, le=600)
    libreoffice_binary: str = Field("soffice", description="Ścieżka do LibreOffice (konwersja .doc).")
    conversion_timeout_s: int = Field(60, gt=0)

    # --- Generowanie ----------------------------------------------------------
    finish_component: FinishComponent = FinishComponent.TEXT_BLOCK
    validation_mode: ValidationMode = ValidationMode.FILLED

    @property
    def max_file_size_bytes(self) -> int:
        return int(self.max_file_size_mb * 1024 * 1024)

    @property
    def max_uncompressed_bytes(self) -> int:
        return int(self.max_uncompressed_mb * 1024 * 1024)

    @property
    def login_configured(self) -> bool:
        return bool(self.auth_username and self.auth_password and self.jwt_secret)

    @property
    def edenai_key(self) -> str | None:
        return self.edenai_api_key.get_secret_value() if self.edenai_api_key else None

    @model_validator(mode="after")
    def _check_auth(self) -> Settings:
        if self.auth_enabled and not (self.jwt_secret or self.jwt_public_key):
            raise ValueError("AUTH_ENABLED=true wymaga ustawienia JWT_SECRET albo JWT_PUBLIC_KEY.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
