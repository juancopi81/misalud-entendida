"""Unit tests for Spanish medication explanations."""

from src.api.drug_matcher import DrugMatchResult
from src.models import MedicationItem
from src.pipelines.prescription_enrichment import EnrichedMedication
from src.pipelines.spanish_explanations import (
    DISCLAIMER_FULL,
    DISCLAIMER_SHORT,
    format_medication_explanation,
)


class TestSpanishExplanations:
    def test_explanation_includes_core_fields(self, sample_cum_record):
        med = MedicationItem(
            nombre_medicamento="METFORMINA",
            dosis="850MG",
            frecuencia="Cada 12 horas",
            duracion="30 días",
            instrucciones="Con comida",
        )

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
            price_summary={
                "min": 1000.0,
                "max": 2000.0,
                "avg": 1500.0,
                "fecha_datos": "2020-01-01",
            },
        )

        explanation = format_medication_explanation(med, enriched)

        assert "contiene metformina" in explanation.lower()
        assert "Dosis indicada: 850MG" in explanation
        assert "Frecuencia: Cada 12 horas" in explanation
        assert "Duración: 30 días" in explanation
        assert "Instrucciones: Con comida" in explanation
        assert "alternativas genéricas" in explanation.lower()
        assert "Precios de referencia" in explanation

    def test_disclaimer_constants(self):
        assert "No reemplaza el consejo de su médico" in DISCLAIMER_FULL
        assert "No es consejo médico" in DISCLAIMER_SHORT
