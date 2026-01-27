"""Unit tests for prescription pipeline output."""

from src.models import MedicationItem, PrescriptionExtraction
from src.pipelines.prescription_enrichment import EnrichedMedication
from src.pipelines.prescription_pipeline import build_prescription_output
from src.api.drug_matcher import DrugMatchResult


class TestPrescriptionPipeline:
    def test_empty_extraction_returns_message(self):
        extraction = PrescriptionExtraction(medicamentos=[], parse_success=True)
        result = build_prescription_output(extraction)

        assert "No se pudieron extraer medicamentos" in result.medications_markdown
        assert result.generics_markdown == ""
        assert result.prices_markdown == ""
        assert result.explanations_markdown == ""

    def test_pipeline_formats_generics_and_prices(self, monkeypatch, sample_cum_record):
        med = MedicationItem(
            nombre_medicamento="METFORMINA",
            dosis="850MG",
            frecuencia="Cada 12 horas",
            duracion="30 días",
            instrucciones="Con comida",
        )
        extraction = PrescriptionExtraction(medicamentos=[med], parse_success=True)

        match = DrugMatchResult(
            record=sample_cum_record,
            match_type="exact",
            confidence=0.9,
            query_normalized="METFORMINA",
        )

        enriched = EnrichedMedication(
            medication_name="METFORMINA",
            match=match,
            generics=[sample_cum_record],
            prices=[],
            price_summary={"min": 1000.0, "max": 2000.0, "avg": 1500.0, "fecha_datos": "2020-01-01"},
        )

        def fake_enrich(name, dosage="", limit=5):
            assert name == "METFORMINA"
            assert dosage == "850MG"
            assert limit == 5
            return enriched

        monkeypatch.setattr("src.pipelines.prescription_pipeline.enrich_medication", fake_enrich)

        result = build_prescription_output(extraction, limit=5)

        assert "Medicamentos Encontrados" in result.medications_markdown
        assert "Alternativas para" in result.generics_markdown
        assert "Precio referencia" in result.prices_markdown
        assert "Aviso" in result.explanations_markdown
