"""Tests for grounded follow-up Q&A helpers."""

from src.models import DocumentChatContext
from src.pipelines.document_chat import (
    NEEDS_CONTEXT_RESPONSE,
    REFUSAL_RESPONSE,
    UNKNOWN_RESPONSE,
    answer_question,
)


def _sample_context() -> DocumentChatContext:
    return DocumentChatContext(
        document_kind="prescription",
        report_markdown="Reporte",
        extracted_text="Metformina 850 mg cada 12 horas",
        extracted_json={"medicamentos": [{"nombre_medicamento": "METFORMINA"}]},
        warnings=[],
        uncertainty_notes=[],
        route_confidence=0.9,
        evidence_source="image",
    )


def test_grounded_answer_when_data_exists(monkeypatch):
    class FakeBackend:
        def generate_text(self, prompt, max_new_tokens=2048):
            return (
                "El documento muestra metformina como medicamento principal. "
                "Esta herramienta es educativa y no reemplaza el consejo médico."
            )

    monkeypatch.setattr(
        "src.pipelines.document_chat._get_backend_instance",
        lambda _backend_name: FakeBackend(),
    )

    response = answer_question("¿Qué medicamento aparece?", _sample_context())

    assert "metformina" in response.lower()
    assert "no reemplaza el consejo médico" in response.lower()


def test_unknown_when_question_exceeds_context(monkeypatch):
    class FakeBackend:
        def generate_text(self, prompt, max_new_tokens=2048):
            return "No se puede confirmar con la información disponible."

    monkeypatch.setattr(
        "src.pipelines.document_chat._get_backend_instance",
        lambda _backend_name: FakeBackend(),
    )

    response = answer_question("¿Cuál es mi diagnóstico exacto según TAC?", _sample_context())

    assert "no se puede confirmar" in response.lower() or response == REFUSAL_RESPONSE


def test_refusal_for_diagnosis_or_treatment_changes():
    response = answer_question("¿Debo cambiar dosis y suspender el medicamento?", _sample_context())
    assert response == REFUSAL_RESPONSE


def test_missing_context_handling():
    response = answer_question("¿Qué dice el documento?", None)
    assert response == NEEDS_CONTEXT_RESPONSE


def test_empty_question_returns_unknown():
    response = answer_question("   ", _sample_context())
    assert response == UNKNOWN_RESPONSE
