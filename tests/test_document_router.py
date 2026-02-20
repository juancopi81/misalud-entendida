"""Tests for unified document routing helpers."""

from src.io.document_ingestion import IngestedDocument
from src.pipelines.document_router import route_document


def test_high_confidence_prescription_route_from_text():
    ingested = IngestedDocument(
        file_path="/tmp/presc.pdf",
        source="text_pdf",
        extracted_text=(
            "RECETA MEDICA\nMetformina 850 MG\nDosis: una tableta cada 12 horas"
        ),
        quality_score=0.95,
    )

    decision = route_document(ingested, backend=None)

    assert decision.kind == "prescription"
    assert decision.confidence >= 0.62
    assert decision.reasons


def test_high_confidence_lab_route_from_text():
    ingested = IngestedDocument(
        file_path="/tmp/lab.pdf",
        source="text_pdf",
        extracted_text=(
            "RESULTADOS DE LABORATORIO\nHEMOGLOBINA 14.2 g/dL\nRANGO REFERENCIA 12-16"
        ),
        quality_score=0.95,
    )

    decision = route_document(ingested, backend=None)

    assert decision.kind == "lab"
    assert decision.confidence >= 0.62
    assert decision.reasons


def test_low_confidence_triggers_model_fallback():
    class FakeBackend:
        def extract_raw(self, _image_path, _prompt, max_new_tokens=2048):
            raise AssertionError("Image path should not be used in this test")

        def generate_text(self, _prompt, max_new_tokens=2048):
            return (
                '{"document_type":"prescription","confidence":0.88,'
                '"reason":"Se observan dosis y frecuencia de receta."}'
            )

    ingested = IngestedDocument(
        file_path="/tmp/ambiguous.pdf",
        source="text_pdf",
        extracted_text="Documento médico con texto ambiguo",
        quality_score=0.8,
    )

    decision = route_document(ingested, backend=FakeBackend())

    assert decision.kind == "prescription"
    assert decision.method == "model_fallback"
    assert decision.confidence == 0.88
    assert decision.reasons


def test_route_reason_trace_for_unknown_without_backend():
    ingested = IngestedDocument(
        file_path="/tmp/ambiguous.pdf",
        source="text_pdf",
        extracted_text="Texto sin señales claras",
        quality_score=0.8,
    )

    decision = route_document(ingested, backend=None)

    assert decision.kind == "unknown"
    assert decision.reasons
