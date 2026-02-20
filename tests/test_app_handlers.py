"""Integration-style tests for app handlers and backend fallback behavior."""

import pytest

import src.app as app_module
from src.models import DocumentChatContext, MedicationItem, PrescriptionExtraction, UnifiedDocumentResult, RouteDecision
from src.pipelines.prescription_pipeline import PrescriptionPipelineResult


@pytest.fixture(autouse=True)
def _reset_app_backend_cache():
    app_module._backend_cache.clear()


def test_analyze_prescription_falls_back_to_transformers(monkeypatch):
    class ModalFailBackend:
        def __init__(self):
            self.calls = 0

        def extract_prescription(self, _image_path):
            self.calls += 1
            raise RuntimeError("modal backend unavailable")

    class TransformersSuccessBackend:
        def __init__(self):
            self.calls = 0

        def extract_prescription(self, _image_path):
            self.calls += 1
            return PrescriptionExtraction(
                medicamentos=[MedicationItem(nombre_medicamento="METFORMINA")],
                parse_success=True,
            )

    modal_backend = ModalFailBackend()
    transformers_backend = TransformersSuccessBackend()

    monkeypatch.setenv("INFERENCE_BACKEND", "auto")
    monkeypatch.setattr(
        app_module,
        "get_backend",
        lambda backend_name: {
            "modal": modal_backend,
            "transformers": transformers_backend,
        }[backend_name],
    )
    monkeypatch.setattr(
        app_module,
        "build_prescription_output",
        lambda *_args, **_kwargs: PrescriptionPipelineResult(
            medications_markdown="meds",
            generics_markdown="generics",
            prices_markdown="prices",
            explanations_markdown="explanations",
        ),
    )

    result = app_module.analyze_prescription("/tmp/fake-prescription.jpg")

    assert result == ("meds", "generics", "prices", "explanations")
    assert modal_backend.calls == 1
    assert transformers_backend.calls == 1


def test_analyze_lab_results_returns_stable_error_when_all_backends_fail(monkeypatch):
    class AlwaysFailBackend:
        def __init__(self):
            self.calls = 0

        def extract_lab_results(self, _image_path):
            self.calls += 1
            raise RuntimeError("backend unavailable")

    modal_backend = AlwaysFailBackend()
    transformers_backend = AlwaysFailBackend()

    monkeypatch.setenv("INFERENCE_BACKEND", "auto")
    monkeypatch.setattr(
        app_module,
        "get_backend",
        lambda backend_name: {
            "modal": modal_backend,
            "transformers": transformers_backend,
        }[backend_name],
    )
    monkeypatch.setattr(
        app_module,
        "build_lab_results_output",
        lambda _result: "should not be returned",
    )

    output = app_module.analyze_lab_results("/tmp/fake-lab.jpg")

    assert output.startswith("Error al analizar los resultados:")
    assert "No se logró extraer información con los backends configurados" in output
    assert modal_backend.calls == 1
    assert transformers_backend.calls == 1


def test_analyze_document_with_followups_success(monkeypatch):
    unified_result = UnifiedDocumentResult(
        file_path="/tmp/doc.pdf",
        evidence_source="text_pdf",
        evidence_quality=0.95,
        route=RouteDecision(kind="prescription", confidence=0.9, method="heuristic"),
        report_markdown="## Reporte Unificado",
        parse_success=True,
    )
    monkeypatch.setattr(
        app_module,
        "analyze_generic_document",
        lambda *_args, **_kwargs: unified_result,
    )

    report, context, history, cleared = app_module.analyze_document_with_followups(
        "/tmp/doc.pdf"
    )

    assert "Reporte Unificado" in report
    assert context is not None
    assert isinstance(context, DocumentChatContext)
    assert history == []
    assert cleared == ""


def test_analyze_document_with_followups_failure(monkeypatch):
    monkeypatch.setattr(
        app_module,
        "analyze_generic_document",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("bad doc")),
    )

    report, context, history, cleared = app_module.analyze_document_with_followups(
        "/tmp/doc.pdf"
    )

    assert report.startswith("Error al analizar el documento:")
    assert context is None
    assert history == []
    assert cleared == ""


def test_ask_document_followup_with_and_without_context(monkeypatch):
    monkeypatch.setattr(
        app_module,
        "answer_document_question",
        lambda question, context, backend_name="auto": "respuesta",
    )
    context = DocumentChatContext(
        document_kind="prescription",
        report_markdown="reporte",
        extracted_text="texto",
        extracted_json={},
        warnings=[],
        uncertainty_notes=[],
        route_confidence=0.8,
        evidence_source="image",
    )

    history, cleared = app_module.ask_document_followup(
        "¿Qué medicamento aparece?",
        [],
        context,
    )
    assert history == [("¿Qué medicamento aparece?", "respuesta")]
    assert cleared == ""

    history2, cleared2 = app_module.ask_document_followup("", history, None)
    assert history2 == history
    assert cleared2 == ""
