"""Potok przetwarzania: plik → tekst → analiza (model językowy lub reguły) → konfiguracja JSON → kontrola."""

import hashlib
import time
from dataclasses import asdict, dataclass
from typing import Any

from app.ai.edenai import AIError, EdenAIClient
from app.analysis.llm import analyze_with_llm
from app.analysis.model import FormAnalysis
from app.analysis.rules import analyze as analyze_with_rules
from app.config import Settings
from app.extraction import extract
from app.extraction.ocr import EdenAIOcr, OcrChain, TesseractOcr
from app.files.validation import ValidatedFile
from app.generator.builder import BuildOptions, build_form
from app.generator.checks import check_form


@dataclass
class ConversionResult:
    form: dict[str, Any]
    report: dict[str, Any]


def convert(file: ValidatedFile, settings: Settings) -> ConversionResult:
    started = time.perf_counter()
    client = (EdenAIClient(settings.edenai_key, settings.edenai_base_url, settings.ai_timeout_s)
              if settings.edenai_key else None)

    ocr = None
    if settings.ocr_enabled:
        engines = ([EdenAIOcr(client, settings.ocr_model, settings.ocr_language)] if client else [])
        engines.append(TesseractOcr(settings.ocr_languages, settings.ocr_dpi, settings.max_pdf_pages))
        ocr = OcrChain(engines)

    document = extract(file, settings, ocr)
    warnings: list[str] = list(ocr.warnings) if ocr else []

    analysis: FormAnalysis | None = None
    if client and settings.llm_enabled and document.lines:
        try:
            analysis = analyze_with_llm(document, client=client, model=settings.llm_model,
                                        max_chars=settings.llm_max_input_chars, filename=file.filename,
                                        fallbacks=settings.llm_fallback_models,
                                        max_tokens=settings.llm_max_output_tokens)
        except AIError as exc:
            warnings.append(f"Model językowy niedostępny — użyto analizy regułowej. ({exc})")
    if analysis is None:
        analysis = analyze_with_rules(document, fallback_title=file.filename)
    if analysis.field_count == 0 and analysis.analyzer == "llm":
        warnings.append("Model nie rozpoznał pól przedmiotu wniosku.")

    seed = hashlib.sha256(file.data).hexdigest()[:16]
    form = build_form(analysis, seed, BuildOptions(settings.finish_component, settings.validation_mode))
    issues = check_form(form)

    report = {
        "file": {"name": file.filename, "mime": file.mime.value, "sizeBytes": len(file.data)},
        "extraction": {"format": document.source_format, "lines": len(document.lines), "ocr": document.used_ocr,
                       "ocrEngine": ocr.used if ocr and document.used_ocr else None},
        "analysis": {"analyzer": analysis.analyzer, "model": settings.llm_model if analysis.analyzer == "llm" else None,
                     "authority": analysis.authority, "applicant": asdict(analysis.applicant),
                     "llmUsage": dict(client.usage) if client else None},
        "stats": _stats(form),
        "proposedDictionaries": [asdict(d) for d in analysis.proposed_dictionaries],
        "warnings": warnings + analysis.warnings,
        "issues": issues,
        "durationMs": round((time.perf_counter() - started) * 1000),
    }
    return ConversionResult(form=form, report=report)


def _stats(form: dict[str, Any]) -> dict[str, int]:
    sections = [q["field"] for tab in form["tabs"] for q in tab["questions"]]
    fields = [c["field"] for s in sections for c in s["repeatingSectionGrid"]]
    return {"pages": len(form["tabs"]), "sections": len(sections), "fields": len(fields),
            "conditional": sum(bool(f["states"]) for f in sections + fields)}
