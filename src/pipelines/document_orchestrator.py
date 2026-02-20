"""Unified document analysis orchestrator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from src.inference.constants import (
    MAX_NEW_TOKENS_LABS,
    MAX_NEW_TOKENS_PRESCRIPTION,
)
from src.inference.medgemma import MedGemmaBackend, get_backend
from src.inference.utils import extract_json_from_response
from src.io.document_ingestion import IngestedDocument, ingest_document
from src.logger import get_logger
from src.models import (
    LabResultExtraction,
    PrescriptionExtraction,
    RouteDecision,
    UnifiedDocumentResult,
)
from src.pipelines.lab_results_pipeline import build_lab_results_output
from src.pipelines.prescription_pipeline import (
    PrescriptionPipelineResult,
    build_prescription_output,
)
from src.pipelines.document_router import route_document
from src.prompts import LAB_VERIFY_PROMPT, PRESCRIPTION_VERIFY_PROMPT

logger = get_logger(__name__)

SUPPORTED_BACKENDS = ("modal", "transformers")
_backend_cache: dict[str, MedGemmaBackend] = {}
MAX_EVIDENCE_IN_PROMPT = 3500


@dataclass
class _VerificationResult:
    extraction: PrescriptionExtraction | LabResultExtraction | None
    backend_name: str = ""
    error: str = ""


def _resolve_backend_order(backend_name: str) -> list[str]:
    configured = (backend_name or "auto").strip().lower()
    if configured == "auto":
        return ["modal", "transformers"]
    if configured in SUPPORTED_BACKENDS:
        return [configured]
    logger.warning(
        "Invalid backend_name=%r for unified flow. Falling back to auto.",
        configured,
    )
    return ["modal", "transformers"]


def _get_backend_instance(backend_name: str) -> MedGemmaBackend:
    backend = _backend_cache.get(backend_name)
    if backend is None:
        logger.info("Initializing backend for orchestrator: %s", backend_name)
        backend = get_backend(backend_name)  # type: ignore[arg-type]
        _backend_cache[backend_name] = backend
    return backend


def _run_with_backend_fallback(
    backend_order: list[str],
    task_label: str,
    runner: Callable[[MedGemmaBackend], object],
    validator: Callable[[object], bool] | None = None,
) -> tuple[object, str]:
    errors: list[str] = []
    for backend_name in backend_order:
        try:
            backend = _get_backend_instance(backend_name)
            result = runner(backend)
            if validator is None or validator(result):
                return result, backend_name
            errors.append(f"{backend_name}: resultado inválido")
        except Exception as exc:  # pragma: no cover - exercised via tests through handlers
            logger.warning("%s failed on backend=%s: %s", task_label, backend_name, exc)
            errors.append(f"{backend_name}: {exc}")
    raise RuntimeError(
        f"Falló {task_label} con backends {', '.join(backend_order)}. "
        f"Detalle: {' | '.join(errors) if errors else 'sin detalle'}"
    )


def _verify_prescription(
    ingested: IngestedDocument,
    route_hint: str,
    backend_order: list[str],
) -> _VerificationResult:
    evidence_text = (ingested.extracted_text or "").strip()[:MAX_EVIDENCE_IN_PROMPT]
    prompt = PRESCRIPTION_VERIFY_PROMPT.format(
        route_hint=route_hint,
        evidence_text=evidence_text or "(sin evidencia de texto)",
    )

    def _runner(backend: MedGemmaBackend) -> PrescriptionExtraction:
        if ingested.media_path:
            raw = backend.extract_raw(
                ingested.media_path,
                prompt,
                max_new_tokens=MAX_NEW_TOKENS_PRESCRIPTION,
            )
        else:
            raw = backend.generate_text(
                prompt,
                max_new_tokens=MAX_NEW_TOKENS_PRESCRIPTION,
            )
        extracted = extract_json_from_response(raw)
        result = PrescriptionExtraction.from_json(extracted)
        result.raw_response = raw
        return result

    try:
        result, backend_name = _run_with_backend_fallback(
            backend_order,
            task_label="verify_prescription",
            runner=_runner,
            validator=lambda r: isinstance(r, PrescriptionExtraction)
            and r.parse_success
            and bool(r.medicamentos),
        )
        return _VerificationResult(extraction=result, backend_name=backend_name)  # type: ignore[arg-type]
    except Exception as exc:
        return _VerificationResult(extraction=None, error=str(exc))


def _verify_lab(
    ingested: IngestedDocument,
    route_hint: str,
    backend_order: list[str],
) -> _VerificationResult:
    evidence_text = (ingested.extracted_text or "").strip()[:MAX_EVIDENCE_IN_PROMPT]
    prompt = LAB_VERIFY_PROMPT.format(
        route_hint=route_hint,
        evidence_text=evidence_text or "(sin evidencia de texto)",
    )

    def _runner(backend: MedGemmaBackend) -> LabResultExtraction:
        if ingested.media_path:
            raw = backend.extract_raw(
                ingested.media_path,
                prompt,
                max_new_tokens=MAX_NEW_TOKENS_LABS,
            )
        else:
            raw = backend.generate_text(
                prompt,
                max_new_tokens=MAX_NEW_TOKENS_LABS,
            )
        extracted = extract_json_from_response(raw)
        result = LabResultExtraction.from_json(extracted)
        result.raw_response = raw
        return result

    try:
        result, backend_name = _run_with_backend_fallback(
            backend_order,
            task_label="verify_lab",
            runner=_runner,
            validator=lambda r: isinstance(r, LabResultExtraction)
            and r.parse_success
            and bool(r.resultados),
        )
        return _VerificationResult(extraction=result, backend_name=backend_name)  # type: ignore[arg-type]
    except Exception as exc:
        return _VerificationResult(extraction=None, error=str(exc))


def _render_unified_header(
    route: RouteDecision,
    source: str,
    warnings: list[str],
    uncertainty_notes: list[str],
) -> str:
    lines = [
        "## Reporte Unificado del Documento",
        "",
        f"- **Tipo detectado:** `{route.kind}`",
        f"- **Confianza de ruteo:** {route.confidence:.2f}",
        f"- **Método de ruteo:** {route.method}",
        f"- **Fuente de evidencia:** `{source}`",
    ]
    if route.reasons:
        lines.append(f"- **Razonamiento de ruteo:** {' '.join(route.reasons)}")
    if warnings:
        lines.extend(["", "### Avisos", *[f"- {w}" for w in warnings]])
    if uncertainty_notes:
        lines.extend(["", "### Incertidumbres", *[f"- {n}" for n in uncertainty_notes]])
    lines.append("")
    return "\n".join(lines)


def analyze_document(file_path: str, backend_name: str = "auto") -> UnifiedDocumentResult:
    """Analyze generic document and route to prescription/lab pipeline."""
    ingested = ingest_document(file_path)
    warnings = list(ingested.warnings)
    uncertainty_notes: list[str] = []
    backend_order = _resolve_backend_order(backend_name)

    if ingested.source in ("unsupported", "pdf_no_text"):
        header = _render_unified_header(
            route=RouteDecision(kind="unknown", confidence=0.0, method="unavailable"),
            source=ingested.source,
            warnings=warnings,
            uncertainty_notes=uncertainty_notes,
        )
        return UnifiedDocumentResult(
            file_path=file_path,
            evidence_source=ingested.source,
            evidence_quality=ingested.quality_score,
            route=RouteDecision(kind="unknown", confidence=0.0, method="unavailable"),
            report_markdown=header
            + "No se pudo analizar este documento con la estrategia actual.",
            warnings=warnings,
            uncertainty_notes=uncertainty_notes,
            extracted_text=ingested.extracted_text,
            parse_success=False,
        )

    route_backend_name = ""
    route_errors: list[str] = []
    route = route_document(ingested, backend=None)
    if route.confidence < 0.62:
        for backend_candidate in backend_order:
            try:
                backend = _get_backend_instance(backend_candidate)
                candidate = route_document(ingested, backend=backend)
                route_backend_name = backend_candidate
                route = candidate
                if candidate.kind != "unknown":
                    break
            except Exception as exc:
                route_errors.append(f"{backend_candidate}: {exc}")
    if route_errors:
        warnings.append(
            "No se pudo clasificar con todos los backends de fallback: "
            + " | ".join(route_errors)
        )

    selected_kind = route.kind
    selected_backend = route_backend_name
    prescription_result: PrescriptionExtraction | None = None
    lab_result: LabResultExtraction | None = None
    prescription_report = ""
    lab_report = ""
    parse_success = False
    raw_verification_response = ""

    if selected_kind in ("prescription", "unknown"):
        pres_verification = _verify_prescription(ingested, selected_kind, backend_order)
        if isinstance(pres_verification.extraction, PrescriptionExtraction):
            prescription_result = pres_verification.extraction
            raw_verification_response = prescription_result.raw_response
            selected_backend = pres_verification.backend_name or selected_backend

    if selected_kind in ("lab", "unknown"):
        lab_verification = _verify_lab(ingested, selected_kind, backend_order)
        if isinstance(lab_verification.extraction, LabResultExtraction):
            # If route is unknown and both parsers worked, choose richer extraction.
            if prescription_result is not None and selected_kind == "unknown":
                if len(lab_verification.extraction.resultados) > len(
                    prescription_result.medicamentos
                ):
                    lab_result = lab_verification.extraction
                    prescription_result = None
                    selected_kind = "lab"
                else:
                    selected_kind = "prescription"
            else:
                lab_result = lab_verification.extraction
                selected_kind = "lab"
            raw_verification_response = lab_verification.extraction.raw_response
            selected_backend = lab_verification.backend_name or selected_backend
        elif prescription_result is not None and selected_kind == "unknown":
            selected_kind = "prescription"

    route.kind = selected_kind

    if prescription_result is not None:
        parse_success = prescription_result.parse_success and bool(
            prescription_result.medicamentos
        )
        if parse_success:
            try:
                pipeline_output: PrescriptionPipelineResult = build_prescription_output(
                    prescription_result,
                    limit=5,
                )
                prescription_report = (
                    "### Medicamentos\n\n"
                    f"{pipeline_output.medications_markdown}\n\n"
                    "### Alternativas Genéricas\n\n"
                    f"{pipeline_output.generics_markdown}\n\n"
                    "### Precios de Referencia\n\n"
                    f"{pipeline_output.prices_markdown}\n\n"
                    "### Explicación\n\n"
                    f"{pipeline_output.explanations_markdown}"
                )
            except Exception as exc:
                warnings.append(
                    "No se pudo completar el enriquecimiento CUM/SISMED; se muestran solo datos extraídos."
                )
                uncertainty_notes.append(f"Fallo de enriquecimiento: {exc}")
                prescription_report = (
                    "### Medicamentos (sin enriquecimiento)\n\n"
                    + "\n".join(
                        [
                            f"- {m.nombre_medicamento} | dosis: {m.dosis} | frecuencia: {m.frecuencia}"
                            for m in prescription_result.medicamentos
                        ]
                    )
                )
        else:
            uncertainty_notes.append(
                "La verificación de receta no logró extraer medicamentos confiables."
            )

    if lab_result is not None:
        parse_success = lab_result.parse_success and bool(lab_result.resultados)
        if parse_success:
            try:
                lab_report = build_lab_results_output(lab_result)
            except Exception as exc:
                warnings.append(
                    "No se pudo completar el formateo de laboratorio; se muestran datos mínimos."
                )
                uncertainty_notes.append(f"Fallo de formateo lab: {exc}")
                lab_report = "### Resultados (sin formateo)\n\n" + "\n".join(
                    [
                        f"- {r.nombre_prueba}: {r.valor} {r.unidad} ({r.rango_referencia})"
                        for r in lab_result.resultados
                    ]
                )
        else:
            uncertainty_notes.append(
                "La verificación de laboratorio no logró extraer resultados confiables."
            )

    if not parse_success:
        warnings.append(
            "No se logró una extracción estructurada confiable; revise la calidad del documento."
        )

    header = _render_unified_header(
        route=route,
        source=ingested.source,
        warnings=warnings,
        uncertainty_notes=uncertainty_notes,
    )
    body = prescription_report or lab_report or "No hay contenido estructurado para mostrar."

    return UnifiedDocumentResult(
        file_path=file_path,
        evidence_source=ingested.source,
        evidence_quality=ingested.quality_score,
        route=route,
        report_markdown=f"{header}\n{body}",
        warnings=warnings,
        uncertainty_notes=uncertainty_notes,
        extracted_text=ingested.extracted_text,
        parse_success=parse_success,
        raw_verification_response=raw_verification_response,
        used_backend=selected_backend,
        prescription=prescription_result,
        lab=lab_result,
        prescription_output=prescription_report,
        lab_output=lab_report,
    )
