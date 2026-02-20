"""Document routing helpers for unified ingestion flow."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
import unicodedata

from src.inference.constants import MAX_NEW_TOKENS_DEFAULT
from src.inference.medgemma import MedGemmaBackend
from src.io.document_ingestion import IngestedDocument
from src.logger import get_logger
from src.models import DocumentKind, RouteDecision
from src.prompts import DOC_TYPE_CLASSIFIER_PROMPT

logger = get_logger(__name__)

ROUTING_FALLBACK_THRESHOLD = 0.62
EVIDENCE_MAX_CHARS = 3000

PRESCRIPTION_HINTS = {
    "RECETA": 2.0,
    "FORMULA MEDICA": 2.0,
    "DOSIS": 1.0,
    "CADA": 1.0,
    "HORAS": 1.0,
    "TABLETA": 1.0,
    "CAPSULA": 1.0,
    "MEDICAMENTO": 1.0,
    "MG": 0.6,
    "ML": 0.6,
}

LAB_HINTS = {
    "LABORATORIO": 2.0,
    "RESULTADOS": 1.5,
    "RANGO": 1.0,
    "REFERENCIA": 1.0,
    "HEMOGLOBINA": 2.0,
    "HEMATOCRITO": 2.0,
    "GLUCOSA": 1.5,
    "LEUCOCITOS": 1.5,
    "NORMAL": 0.8,
    "ALTO": 0.8,
    "BAJO": 0.8,
}


@dataclass
class _HeuristicScore:
    kind: DocumentKind
    confidence: float
    reasons: list[str]


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    normalized = normalized.upper()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _score_hints(text: str, hints: dict[str, float]) -> tuple[float, list[str]]:
    score = 0.0
    hits: list[str] = []
    for token, weight in hints.items():
        if token in text:
            score += weight
            hits.append(token)
    return score, hits


def _heuristic_route(ingested: IngestedDocument) -> _HeuristicScore:
    if ingested.source in ("unsupported", "pdf_no_text"):
        return _HeuristicScore(
            kind="unknown",
            confidence=0.0,
            reasons=["No hay evidencia textual utilizable para ruteo heurístico."],
        )

    text = _normalize_text(ingested.extracted_text)
    if not text:
        return _HeuristicScore(
            kind="unknown",
            confidence=0.0,
            reasons=["Sin texto extraído; se requiere clasificación con modelo."],
        )

    prescription_score, prescription_hits = _score_hints(text, PRESCRIPTION_HINTS)
    lab_score, lab_hits = _score_hints(text, LAB_HINTS)

    total = prescription_score + lab_score
    if total <= 0:
        return _HeuristicScore(
            kind="unknown",
            confidence=0.0,
            reasons=["No se detectaron palabras clave fuertes para receta o laboratorio."],
        )

    if prescription_score == lab_score:
        return _HeuristicScore(
            kind="unknown",
            confidence=0.4,
            reasons=[
                f"Puntaje empatado receta={prescription_score:.2f}, lab={lab_score:.2f}."
            ],
        )

    kind: DocumentKind = "prescription" if prescription_score > lab_score else "lab"
    best = max(prescription_score, lab_score)
    margin = abs(prescription_score - lab_score) / total
    confidence = min(0.95, 0.45 + 0.55 * margin + 0.1 * min(best, 4.0) / 4.0)

    reasons = [
        f"Puntaje receta={prescription_score:.2f}; lab={lab_score:.2f}.",
        (
            f"Palabras receta: {', '.join(prescription_hits[:6]) or 'ninguna'}."
            if kind == "prescription"
            else f"Palabras lab: {', '.join(lab_hits[:6]) or 'ninguna'}."
        ),
    ]
    return _HeuristicScore(kind=kind, confidence=confidence, reasons=reasons)


def _extract_json_object(raw: str) -> dict:
    stripped = (raw or "").strip()
    if not stripped:
        return {}

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(stripped[start : end + 1])
        except json.JSONDecodeError:
            return {}
    return {}


def _classify_with_model(
    ingested: IngestedDocument,
    backend: MedGemmaBackend,
) -> RouteDecision:
    evidence_text = (ingested.extracted_text or "").strip()[:EVIDENCE_MAX_CHARS]
    prompt = DOC_TYPE_CLASSIFIER_PROMPT.format(
        evidence_text=evidence_text or "(sin texto extraído)"
    )

    raw = ""
    try:
        if ingested.media_path:
            raw = backend.extract_raw(
                ingested.media_path,
                prompt,
                max_new_tokens=min(1024, MAX_NEW_TOKENS_DEFAULT),
            )
        else:
            raw = backend.generate_text(
                prompt,
                max_new_tokens=min(1024, MAX_NEW_TOKENS_DEFAULT),
            )
    except Exception as exc:
        logger.warning("Model route classification failed: %s", exc)
        return RouteDecision(
            kind="unknown",
            confidence=0.0,
            method="model_fallback_error",
            reasons=[f"Error en clasificación con modelo: {exc}"],
            raw_response=raw,
        )

    parsed = _extract_json_object(raw)
    raw_kind = str(parsed.get("document_type", "")).strip().lower()
    if raw_kind not in {"prescription", "lab", "unknown"}:
        raw_kind = "unknown"

    try:
        confidence = float(parsed.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    reason = str(parsed.get("reason", "")).strip() or "Clasificación sin razón explícita."

    return RouteDecision(
        kind=raw_kind,  # type: ignore[arg-type]
        confidence=confidence,
        method="model_fallback",
        reasons=[reason],
        raw_response=raw,
    )


def route_document(
    ingested: IngestedDocument,
    backend: MedGemmaBackend | None = None,
) -> RouteDecision:
    """Route document to prescription or lab flow using heuristic-first strategy."""
    heuristic = _heuristic_route(ingested)
    decision = RouteDecision(
        kind=heuristic.kind,
        confidence=heuristic.confidence,
        method="heuristic",
        reasons=list(heuristic.reasons),
    )

    if heuristic.confidence >= ROUTING_FALLBACK_THRESHOLD:
        return decision

    if backend is None:
        decision.reasons.append("Sin backend disponible para fallback de clasificación.")
        return decision

    fallback = _classify_with_model(ingested, backend)
    if fallback.kind != "unknown":
        fallback.reasons.insert(
            0,
            (
                f"Fallback activado por baja confianza heurística "
                f"({heuristic.confidence:.2f} < {ROUTING_FALLBACK_THRESHOLD:.2f})."
            ),
        )
        return fallback

    decision.reasons.append(
        "Fallback de clasificación no logró una ruta confiable; se mantiene ruta desconocida."
    )
    if fallback.raw_response:
        decision.raw_response = fallback.raw_response
    return decision
