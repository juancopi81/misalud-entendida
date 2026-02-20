"""Tests for unified document orchestrator."""

from src.io.document_ingestion import IngestedDocument
from src.models import (
    LabResultExtraction,
    LabResultItem,
    MedicationItem,
    PrescriptionExtraction,
    RouteDecision,
)
from src.pipelines.document_orchestrator import _VerificationResult, analyze_document
from src.pipelines.prescription_pipeline import PrescriptionPipelineResult


def test_prescription_happy_path(monkeypatch):
    monkeypatch.setattr(
        "src.pipelines.document_orchestrator.ingest_document",
        lambda _path: IngestedDocument(
            file_path="/tmp/doc.jpg",
            source="image",
            extracted_text="RECETA MEDICA",
            quality_score=0.8,
            media_path="/tmp/doc.jpg",
        ),
    )
    monkeypatch.setattr(
        "src.pipelines.document_orchestrator.route_document",
        lambda ingested, backend=None: RouteDecision(
            kind="prescription",
            confidence=0.9,
            method="heuristic",
            reasons=["receta"],
        ),
    )
    monkeypatch.setattr(
        "src.pipelines.document_orchestrator._verify_prescription",
        lambda ingested, route_hint, backend_order: _VerificationResult(
            extraction=PrescriptionExtraction(
                medicamentos=[MedicationItem(nombre_medicamento="METFORMINA")],
                parse_success=True,
            ),
            backend_name="modal",
        ),
    )
    monkeypatch.setattr(
        "src.pipelines.document_orchestrator.build_prescription_output",
        lambda extraction, limit=5: PrescriptionPipelineResult(
            medications_markdown="meds",
            generics_markdown="generics",
            prices_markdown="prices",
            explanations_markdown="explanations",
            enriched=[],
        ),
    )

    result = analyze_document("/tmp/doc.jpg")

    assert result.parse_success is True
    assert result.route.kind == "prescription"
    assert "meds" in result.report_markdown
    assert result.used_backend == "modal"


def test_lab_happy_path(monkeypatch):
    monkeypatch.setattr(
        "src.pipelines.document_orchestrator.ingest_document",
        lambda _path: IngestedDocument(
            file_path="/tmp/lab.jpg",
            source="image",
            extracted_text="RESULTADOS LABORATORIO",
            quality_score=0.8,
            media_path="/tmp/lab.jpg",
        ),
    )
    monkeypatch.setattr(
        "src.pipelines.document_orchestrator.route_document",
        lambda ingested, backend=None: RouteDecision(
            kind="lab",
            confidence=0.91,
            method="heuristic",
            reasons=["laboratorio"],
        ),
    )
    monkeypatch.setattr(
        "src.pipelines.document_orchestrator._verify_lab",
        lambda ingested, route_hint, backend_order: _VerificationResult(
            extraction=LabResultExtraction(
                resultados=[LabResultItem(nombre_prueba="GLUCOSA", valor="90")],
                parse_success=True,
            ),
            backend_name="transformers",
        ),
    )
    monkeypatch.setattr(
        "src.pipelines.document_orchestrator.build_lab_results_output",
        lambda extraction: "lab report",
    )

    result = analyze_document("/tmp/lab.jpg")

    assert result.parse_success is True
    assert result.route.kind == "lab"
    assert "lab report" in result.report_markdown
    assert result.used_backend == "transformers"


def test_unknown_partial_path(monkeypatch):
    monkeypatch.setattr(
        "src.pipelines.document_orchestrator.ingest_document",
        lambda _path: IngestedDocument(
            file_path="/tmp/doc.jpg",
            source="image",
            extracted_text="texto ambiguo",
            quality_score=0.5,
            media_path="/tmp/doc.jpg",
        ),
    )
    monkeypatch.setattr(
        "src.pipelines.document_orchestrator.route_document",
        lambda ingested, backend=None: RouteDecision(
            kind="unknown",
            confidence=0.2,
            method="heuristic",
            reasons=["ambiguous"],
        ),
    )
    monkeypatch.setattr(
        "src.pipelines.document_orchestrator._verify_prescription",
        lambda ingested, route_hint, backend_order: _VerificationResult(
            extraction=None,
            error="no parse",
        ),
    )
    monkeypatch.setattr(
        "src.pipelines.document_orchestrator._verify_lab",
        lambda ingested, route_hint, backend_order: _VerificationResult(
            extraction=None,
            error="no parse",
        ),
    )

    result = analyze_document("/tmp/doc.jpg")

    assert result.parse_success is False
    assert result.route.kind == "unknown"
    assert "No hay contenido estructurado para mostrar" in result.report_markdown
    assert result.warnings


def test_provider_outage_keeps_partial_output(monkeypatch):
    monkeypatch.setattr(
        "src.pipelines.document_orchestrator.ingest_document",
        lambda _path: IngestedDocument(
            file_path="/tmp/presc.jpg",
            source="image",
            extracted_text="RECETA",
            quality_score=0.8,
            media_path="/tmp/presc.jpg",
        ),
    )
    monkeypatch.setattr(
        "src.pipelines.document_orchestrator.route_document",
        lambda ingested, backend=None: RouteDecision(
            kind="prescription",
            confidence=0.9,
            method="heuristic",
            reasons=["receta"],
        ),
    )
    monkeypatch.setattr(
        "src.pipelines.document_orchestrator._verify_prescription",
        lambda ingested, route_hint, backend_order: _VerificationResult(
            extraction=PrescriptionExtraction(
                medicamentos=[MedicationItem(nombre_medicamento="LOSARTAN", dosis="50MG")],
                parse_success=True,
            ),
            backend_name="modal",
        ),
    )
    monkeypatch.setattr(
        "src.pipelines.document_orchestrator.build_prescription_output",
        lambda extraction, limit=5: (_ for _ in ()).throw(RuntimeError("CUM down")),
    )

    result = analyze_document("/tmp/presc.jpg")

    assert result.parse_success is True
    assert "sin enriquecimiento" in result.report_markdown
    assert any("enriquecimiento" in w.lower() for w in result.warnings)
