"""Unit tests for prescription enrichment helpers."""

from dataclasses import replace

from src.api.drug_matcher import DrugMatchResult
from src.models import PriceRecord
from src.pipelines.prescription_enrichment import enrich_medication


class TestEnrichMedication:
    def test_happy_path_filters_generics_by_form(self, monkeypatch, sample_cum_record):
        calls = {}

        match_result = DrugMatchResult(
            record=sample_cum_record,
            match_type="exact",
            confidence=0.9,
            query_normalized="METFORMINA",
        )

        record_tableta = sample_cum_record
        record_susp = replace(sample_cum_record, formafarmaceutica="SUSPENSION")

        def fake_match(name, dosage="", limit=20):
            calls["match"] = (name, dosage, limit)
            return match_result

        def fake_find(ingredient, concentration=None):
            calls["find"] = (ingredient, concentration)
            return [record_tableta, record_susp]

        price_records = [
            PriceRecord(
                expedientecum="20001234",
                descripcioncomercial="CAJA X 30 TABLETAS",
                formafarmaceutica="TABLETA",
                atc="A10BA02",
                descripcion_atc="METFORMINA",
                precio_minimo=1000.0,
                precio_maximo=2000.0,
                precio_promedio=1500.0,
                unidades=30.0,
                fechacorte="2020-01-01",
                tipo_reporte="VENTA",
                tipo_entidad="LABORATORIO",
            )
        ]

        def fake_prices(expedientecum, limit=10):
            calls["prices"] = (expedientecum, limit)
            return price_records

        def fake_range(prices):
            calls["range"] = prices
            return {"min": 1000.0, "max": 2000.0, "avg": 1500.0, "fecha_datos": "2020-01-01"}

        monkeypatch.setattr("src.pipelines.prescription_enrichment.match_drug_to_cum", fake_match)
        monkeypatch.setattr("src.pipelines.prescription_enrichment.find_generics", fake_find)
        monkeypatch.setattr("src.pipelines.prescription_enrichment.get_price_by_expediente", fake_prices)
        monkeypatch.setattr("src.pipelines.prescription_enrichment.get_price_range", fake_range)

        enriched = enrich_medication("METFORMINA 850MG")

        assert calls["match"] == ("METFORMINA 850MG", "", 20)
        assert calls["find"] == ("METFORMINA", "850")
        assert calls["prices"] == ("20001234", 10)
        assert enriched.match == match_result
        assert len(enriched.generics) == 1
        assert enriched.generics[0].formafarmaceutica == "TABLETA"
        assert enriched.price_summary["min"] == 1000.0
        assert enriched.warnings == []

    def test_no_match_skips_generics_and_prices(self, monkeypatch):
        def fake_match(name, dosage="", limit=20):
            return DrugMatchResult(match_type="none")

        def _fail(*_args, **_kwargs):
            raise AssertionError("Should not be called when there is no match")

        monkeypatch.setattr("src.pipelines.prescription_enrichment.match_drug_to_cum", fake_match)
        monkeypatch.setattr("src.pipelines.prescription_enrichment.find_generics", _fail)
        monkeypatch.setattr("src.pipelines.prescription_enrichment.get_price_by_expediente", _fail)

        enriched = enrich_medication("UNKNOWN_DRUG")

        assert enriched.match.match_type == "none"
        assert enriched.generics == []
        assert enriched.prices == []
        assert enriched.price_summary is None
        assert enriched.warnings == []

    def test_form_param_overrides_record_form(self, monkeypatch, sample_cum_record):
        match_result = DrugMatchResult(
            record=sample_cum_record,
            match_type="exact",
            confidence=0.9,
            query_normalized="METFORMINA",
        )

        record_tableta = sample_cum_record
        record_susp = replace(sample_cum_record, formafarmaceutica="SUSPENSION")

        def fake_match(name, dosage="", limit=20):
            return match_result

        def fake_find(_ingredient, concentration=None):
            return [record_tableta, record_susp]

        monkeypatch.setattr("src.pipelines.prescription_enrichment.match_drug_to_cum", fake_match)
        monkeypatch.setattr("src.pipelines.prescription_enrichment.find_generics", fake_find)
        monkeypatch.setattr(
            "src.pipelines.prescription_enrichment.get_price_by_expediente",
            lambda *_args, **_kwargs: [],
        )
        monkeypatch.setattr(
            "src.pipelines.prescription_enrichment.get_price_range",
            lambda *_args, **_kwargs: None,
        )

        enriched = enrich_medication("METFORMINA", form="SUSPENSION")

        assert len(enriched.generics) == 1
        assert enriched.generics[0].formafarmaceutica == "SUSPENSION"
        assert enriched.warnings == []

    def test_generics_failure_keeps_price_data(self, monkeypatch, sample_cum_record):
        match_result = DrugMatchResult(
            record=sample_cum_record,
            match_type="exact",
            confidence=0.9,
            query_normalized="METFORMINA",
        )

        def fake_match(name, dosage="", limit=20):
            return match_result

        def fail_generics(_ingredient, concentration=None):
            raise RuntimeError("CUM unavailable")

        price_records = [
            PriceRecord(
                expedientecum="20001234",
                descripcioncomercial="CAJA X 30 TABLETAS",
                formafarmaceutica="TABLETA",
                atc="A10BA02",
                descripcion_atc="METFORMINA",
                precio_minimo=1000.0,
                precio_maximo=2000.0,
                precio_promedio=1500.0,
                unidades=30.0,
                fechacorte="2020-01-01",
                tipo_reporte="VENTA",
                tipo_entidad="LABORATORIO",
            )
        ]

        monkeypatch.setattr("src.pipelines.prescription_enrichment.match_drug_to_cum", fake_match)
        monkeypatch.setattr("src.pipelines.prescription_enrichment.find_generics", fail_generics)
        monkeypatch.setattr(
            "src.pipelines.prescription_enrichment.get_price_by_expediente",
            lambda *_args, **_kwargs: price_records,
        )
        monkeypatch.setattr(
            "src.pipelines.prescription_enrichment.get_price_range",
            lambda *_args, **_kwargs: {"min": 1000.0, "max": 2000.0, "avg": 1500.0, "fecha_datos": "2020-01-01"},
        )

        enriched = enrich_medication("METFORMINA")

        assert enriched.generics == []
        assert enriched.price_summary is not None
        assert (
            "No se pudieron obtener alternativas genéricas en este momento."
            in enriched.warnings
        )

    def test_price_failure_keeps_generics_data(self, monkeypatch, sample_cum_record):
        match_result = DrugMatchResult(
            record=sample_cum_record,
            match_type="exact",
            confidence=0.9,
            query_normalized="METFORMINA",
        )

        def fake_match(name, dosage="", limit=20):
            return match_result

        def fail_prices(_expedientecum, limit=10):
            raise RuntimeError("SISMED unavailable")

        monkeypatch.setattr("src.pipelines.prescription_enrichment.match_drug_to_cum", fake_match)
        monkeypatch.setattr(
            "src.pipelines.prescription_enrichment.find_generics",
            lambda *_args, **_kwargs: [sample_cum_record],
        )
        monkeypatch.setattr(
            "src.pipelines.prescription_enrichment.get_price_by_expediente",
            fail_prices,
        )

        enriched = enrich_medication("METFORMINA")

        assert len(enriched.generics) == 1
        assert enriched.price_summary is None
        assert (
            "No se pudieron obtener precios de referencia en este momento."
            in enriched.warnings
        )

    def test_generics_and_price_failures_return_partial_output(
        self,
        monkeypatch,
        sample_cum_record,
    ):
        match_result = DrugMatchResult(
            record=sample_cum_record,
            match_type="exact",
            confidence=0.9,
            query_normalized="METFORMINA",
        )

        monkeypatch.setattr(
            "src.pipelines.prescription_enrichment.match_drug_to_cum",
            lambda *_args, **_kwargs: match_result,
        )
        monkeypatch.setattr(
            "src.pipelines.prescription_enrichment.find_generics",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("CUM down")),
        )
        monkeypatch.setattr(
            "src.pipelines.prescription_enrichment.get_price_by_expediente",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("SISMED down")),
        )

        enriched = enrich_medication("METFORMINA")

        assert enriched.generics == []
        assert enriched.prices == []
        assert enriched.price_summary is None
        assert len(enriched.warnings) == 2
