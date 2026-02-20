"""Grounded follow-up Q&A for unified document flow."""

from __future__ import annotations

from src.inference.constants import MAX_NEW_TOKENS_DEFAULT
from src.inference.medgemma import MedGemmaBackend, get_backend
from src.logger import get_logger
from src.models import DocumentChatContext
from src.prompts import FOLLOWUP_GROUNDED_QA_PROMPT

logger = get_logger(__name__)

SUPPORTED_BACKENDS = ("modal", "transformers")
_backend_cache: dict[str, MedGemmaBackend] = {}

UNKNOWN_RESPONSE = (
    "No se puede confirmar con la información disponible. "
    "Esta herramienta es educativa y no reemplaza el consejo médico."
)
NEEDS_CONTEXT_RESPONSE = (
    "Primero analice un documento para habilitar preguntas de seguimiento. "
    "Esta herramienta es educativa y no reemplaza el consejo médico."
)
REFUSAL_RESPONSE = (
    "No puedo diagnosticar ni indicar cambios de tratamiento o dosis. "
    "Consulte a su médico tratante. "
    "Esta herramienta es educativa y no reemplaza el consejo médico."
)


def _resolve_backend_order(backend_name: str) -> list[str]:
    configured = (backend_name or "auto").strip().lower()
    if configured == "auto":
        return ["modal", "transformers"]
    if configured in SUPPORTED_BACKENDS:
        return [configured]
    logger.warning("Invalid backend_name=%r for grounded chat. Falling back to auto.", configured)
    return ["modal", "transformers"]


def _get_backend_instance(backend_name: str) -> MedGemmaBackend:
    backend = _backend_cache.get(backend_name)
    if backend is None:
        backend = get_backend(backend_name)  # type: ignore[arg-type]
        _backend_cache[backend_name] = backend
    return backend


def _needs_medical_refusal(question: str) -> bool:
    question_lower = question.lower()
    blocked_phrases = (
        "diagnost",
        "diagnosis",
        "cambiar dosis",
        "subir dosis",
        "bajar dosis",
        "suspender",
        "reemplazar medicamento",
        "que tratamiento",
    )
    return any(token in question_lower for token in blocked_phrases)


def answer_question(
    question: str,
    context: DocumentChatContext | None,
    backend_name: str = "auto",
) -> str:
    """Answer follow-up questions using strict grounding against analyzed context."""
    if context is None:
        return NEEDS_CONTEXT_RESPONSE

    question_clean = (question or "").strip()
    if not question_clean:
        return UNKNOWN_RESPONSE

    if _needs_medical_refusal(question_clean):
        return REFUSAL_RESPONSE

    prompt = FOLLOWUP_GROUNDED_QA_PROMPT.format(
        context_payload=context.to_prompt_payload(),
        question=question_clean,
    )
    backend_order = _resolve_backend_order(backend_name)

    errors: list[str] = []
    for candidate in backend_order:
        try:
            backend = _get_backend_instance(candidate)
            raw = backend.generate_text(
                prompt,
                max_new_tokens=min(1024, MAX_NEW_TOKENS_DEFAULT),
            ).strip()
            if not raw:
                errors.append(f"{candidate}: respuesta vacía")
                continue
            if "no reemplaza el consejo médico" not in raw.lower():
                raw = (
                    f"{raw}\n\nEsta herramienta es educativa y no reemplaza el consejo médico."
                )
            return raw
        except Exception as exc:  # pragma: no cover - handled in integration tests
            logger.warning("Grounded chat failed on backend=%s: %s", candidate, exc)
            errors.append(f"{candidate}: {exc}")

    logger.warning("Grounded chat failed across backends: %s", " | ".join(errors))
    return UNKNOWN_RESPONSE
