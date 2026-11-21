"""REST API."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from fastapi.concurrency import run_in_threadpool

from app import __version__
from app.config import Settings, get_settings
from app.files.formats import EXTENSION_TO_MIME
from app.files.validation import validate_upload
from app.security import require_auth
from app.service import convert

router = APIRouter()


@router.get("/health", tags=["system"], summary="Stan usługi")
def health(settings: Annotated[Settings, Depends(get_settings)]) -> dict[str, Any]:
    return {"status": "ok", "version": __version__, "llm": bool(settings.edenai_key and settings.llm_enabled)}


@router.get("/api/v1/formats", tags=["formularze"], summary="Obsługiwane formaty plików")
def formats(settings: Annotated[Settings, Depends(get_settings)]) -> dict[str, Any]:
    return {"formats": {ext: mime.value for ext, mime in EXTENSION_TO_MIME.items()},
            "maxFileSizeBytes": settings.max_file_size_bytes}


@router.post(
    "/api/v1/forms/convert",
    tags=["formularze"],
    summary="Konwersja blankietu formularza do konfiguracji eUsługi (JSON)",
    description=(
        "Przyjmuje pojedynczy plik (PDF, DOC, DOCX, ODS, XLSX, JPG, JPEG, PNG) jako `multipart/form-data` "
        "w polu `file`. Typ pliku jest weryfikowany na podstawie zawartości (MIME), a nie tylko rozszerzenia. "
        "Plik jest przetwarzany wyłącznie w pamięci / katalogu tymczasowym na czas żądania.\n\n"
        "Domyślnie odpowiedzią jest sama konfiguracja formularza gotowa do importu. "
        "Z `?report=true` odpowiedź ma postać `{\"form\": …, \"report\": …}` z informacjami o analizie."
    ),
    responses={401: {"description": "Brak lub nieprawidłowy token JWT"},
               413: {"description": "Plik za duży"},
               415: {"description": "Nieobsługiwany typ pliku / niezgodność MIME"},
               422: {"description": "Nieprawidłowa nazwa pliku lub nieczytelny dokument"}},
)
async def convert_form(
    response: Response,
    file: Annotated[UploadFile, File(description="Blankiet formularza")],
    settings: Annotated[Settings, Depends(get_settings)],
    _claims: Annotated[dict[str, Any] | None, Depends(require_auth)],
    report: Annotated[bool, Query(description="Dołącz raport z analizy")] = False,
) -> dict[str, Any]:
    data = await file.read(settings.max_file_size_bytes + 1)
    validated = validate_upload(file.filename, data, file.content_type, max_size=settings.max_file_size_bytes,
                                max_uncompressed=settings.max_uncompressed_bytes)
    result = await run_in_threadpool(convert, validated, settings)
    response.headers["X-Analyzer"] = result.report["analysis"]["analyzer"]
    response.headers["X-Warnings"] = str(len(result.report["warnings"]))
    return {"form": result.form, "report": result.report} if report else result.form
