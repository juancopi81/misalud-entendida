"""
Unit tests for drug name matching.

These tests use mocked API responses for fast, offline testing.
For integration tests with real API, use: scripts/validate_drug_matcher.py
"""

from src.api.drug_matcher import (
    DrugMatchResult,
    _calculate_match_score,
    _fuzzy_score,
    _normalize_drug_name,
    match_drug_to_cum,
)


class TestNormalizeDrugName:
    """Tests for _normalize_drug_name helper function."""

    def test_basic_name(self):
        name, dosage, unit = _normalize_drug_name("LOSARTAN")
        assert name == "LOSARTAN"
        assert dosage == ""
        assert unit == ""

    def test_with_dosage_mg(self):
        name, dosage, unit = _normalize_drug_name("LOSARTAN 50MG")
        assert name == "LOSARTAN"
        assert dosage == "50"
        assert unit == "MG"

    def test_with_dosage_and_space(self):
        name, dosage, unit = _normalize_drug_name("METFORMINA 850 MG")
        assert name == "METFORMINA"
        assert dosage == "850"
        assert unit == "MG"

    def test_lowercase_input(self):
        name, dosage, unit = _normalize_drug_name("losartan 50mg")
        assert name == "LOSARTAN"
        assert dosage == "50"
        assert unit == "MG"

    def test_with_form_words(self):
        name, dosage, unit = _normalize_drug_name("ACETAMINOFEN 500MG TABLETAS")
        assert name == "ACETAMINOFEN"
        assert dosage == "500"
        assert unit == "MG"

    def test_multiple_form_words(self):
        name, dosage, unit = _normalize_drug_name(
            "IBUPROFENO 400MG TABLETAS RECUBIERTAS"
        )
        assert name == "IBUPROFENO"
        assert dosage == "400"
        assert unit == "MG"

    def test_empty_input(self):
        name, dosage, unit = _normalize_drug_name("")
        assert name == ""
        assert dosage == ""
        assert unit == ""

    def test_whitespace_only(self):
        name, dosage, unit = _normalize_drug_name("   ")
        assert name == ""
        assert dosage == ""
        assert unit == ""

    def test_decimal_dosage(self):
        name, dosage, unit = _normalize_drug_name("LEVOTIROXINA 0.5MG")
        assert name == "LEVOTIROXINA"
        assert dosage == "0.5"
        assert unit == "MG"

    def test_comma_decimal(self):
        name, dosage, unit = _normalize_drug_name("LEVOTIROXINA 0,5MG")
        assert name == "LEVOTIROXINA"
        assert dosage == "0.5"  # Normalized to dot
        assert unit == "MG"

    def test_ml_unit(self):
        name, dosage, unit = _normalize_drug_name("AMOXICILINA 250ML SUSPENSION")
        assert name == "AMOXICILINA"
        assert dosage == "250"
        assert unit == "ML"

    def test_mcg_unit(self):
        name, dosage, unit = _normalize_drug_name("LEVOTIROXINA 50MCG")
        assert name == "LEVOTIROXINA"
        assert dosage == "50"
        assert unit == "MCG"


class TestFuzzyScore:
    """Tests for _fuzzy_score helper function."""

    def test_exact_match(self):
        score = _fuzzy_score("LOSARTAN", "LOSARTAN")
        assert score == 1.0

    def test_case_insensitive(self):
        score = _fuzzy_score("losartan", "LOSARTAN")
        assert score == 1.0

    def test_substring_match(self):
        score = _fuzzy_score("LOSARTAN", "LOSARTAN POTASICO")
        assert score >= 0.9

    def test_partial_match(self):
        score = _fuzzy_score("LOSAR", "LOSARTAN")
        assert 0.5 < score < 1.0

    def test_no_match(self):
        score = _fuzzy_score("METFORMINA", "LOSARTAN")
        assert score < 0.5

    def test_empty_query(self):
        score = _fuzzy_score("", "LOSARTAN")
        assert score == 0.0

    def test_empty_candidate(self):
        score = _fuzzy_score("LOSARTAN", "")
        assert score == 0.0


class TestCalculateMatchScore:
    """Tests for _calculate_match_score helper function."""

    def test_exact_product_match(self, sample_cum_record):
        score = _calculate_match_score("METFORMINA MK 850MG", sample_cum_record)
        assert score >= 0.9

    def test_ingredient_match(self, sample_cum_record):
        score = _calculate_match_score("METFORMINA", sample_cum_record)
        assert score >= 0.8

    def test_dosage_bonus(self, sample_cum_record):
        # Use a query that gives partial match (not substring, not exact)
        # "METFRMINA" is a typo that won't be a substring but will fuzzy match
        score_with_dosage = _calculate_match_score(
            "METFRMINA", sample_cum_record, "850", "MG"
        )
        score_without = _calculate_match_score("METFRMINA", sample_cum_record)
        # Dosage bonus should increase score (0.1 bonus for matching dosage)
        assert score_with_dosage > score_without

    def test_dosage_bonus_requires_unit_match(self, sample_cum_record):
        """Dosage bonus should NOT apply if units don't match (e.g., MG vs ML)."""
        # sample_cum_record has concentracion_valor="850", unidadmedida="mg"
        score_wrong_unit = _calculate_match_score(
            "METFRMINA", sample_cum_record, "850", "ML"
        )
        score_correct_unit = _calculate_match_score(
            "METFRMINA", sample_cum_record, "850", "MG"
        )
        # Wrong unit should NOT get the dosage bonus
        assert score_correct_unit > score_wrong_unit

    def test_no_match(self, sample_cum_record):
        score = _calculate_match_score("COMPLETELY_DIFFERENT", sample_cum_record)
        assert score < 0.5


class TestMatchDrugToCum:
    """Tests for match_drug_to_cum main function."""

    def test_active_ingredient_match(self, mock_cum_api):
        result = match_drug_to_cum("METFORMINA")

        assert result.record is not None
        assert "METFORMINA" in result.record.principioactivo
        # With mock data, product search finds match first (score >= 0.8 -> "exact")
        # In real API, this might be "active_ingredient" depending on results
        assert result.match_type in ("exact", "active_ingredient")
        assert result.confidence >= 0.85

    def test_product_with_dosage(self, mock_cum_api):
        result = match_drug_to_cum("LOSARTAN 50MG")

        assert result.record is not None
        assert "LOSARTAN" in result.record.principioactivo
        assert result.query_normalized == "LOSARTAN"

    def test_case_insensitive(self, mock_cum_api):
        result = match_drug_to_cum("losartan")

        assert result.record is not None
        assert "LOSARTAN" in result.record.principioactivo

    def test_with_form_words(self, mock_cum_api):
        result = match_drug_to_cum("ACETAMINOFEN 500MG TABLETAS")

        assert result.record is not None
        assert "ACETAMINOFEN" in result.record.principioactivo
        assert result.query_normalized == "ACETAMINOFEN"

    def test_nonexistent_drug(self, mock_cum_api):
        result = match_drug_to_cum("NONEXISTENT_DRUG_XYZ")

        assert result.record is None
        assert result.match_type == "none"

    def test_empty_input(self, mock_cum_api):
        result = match_drug_to_cum("")

        assert result.record is None
        assert result.match_type == "none"
        assert "empty_input" in result.debug_info.get("error", "")

    def test_whitespace_only(self, mock_cum_api):
        result = match_drug_to_cum("   ")

        assert result.record is None
        assert result.match_type == "none"

    def test_only_dosage_no_drug_name(self, monkeypatch):
        """Input like '500MG' should return no match and no API calls."""
        def _fail(*_args, **_kwargs):
            raise AssertionError("CUM API should not be called for empty normalized query")

        monkeypatch.setattr(
            "src.api.drug_matcher.search_by_product_name",
            _fail,
        )
        monkeypatch.setattr(
            "src.api.drug_matcher.search_by_active_ingredient",
            _fail,
        )
        result = match_drug_to_cum("500MG")

        assert result.record is None
        assert result.match_type == "none"
        assert result.other_matches == []
        assert result.debug_info.get("error") == "empty_normalized"

    def test_only_form_words_with_dosage(self, monkeypatch):
        """Input like 'TABLETAS 500MG' should return no match and no API calls."""
        def _fail(*_args, **_kwargs):
            raise AssertionError("CUM API should not be called for empty normalized query")

        monkeypatch.setattr(
            "src.api.drug_matcher.search_by_product_name",
            _fail,
        )
        monkeypatch.setattr(
            "src.api.drug_matcher.search_by_active_ingredient",
            _fail,
        )
        result = match_drug_to_cum("TABLETAS 500MG")

        assert result.record is None
        assert result.match_type == "none"
        assert result.other_matches == []
        assert result.debug_info.get("error") == "empty_normalized"

    def test_only_form_words(self, monkeypatch):
        """Input with only form words should return no match and no API calls."""
        def _fail(*_args, **_kwargs):
            raise AssertionError("CUM API should not be called for empty normalized query")

        monkeypatch.setattr(
            "src.api.drug_matcher.search_by_product_name",
            _fail,
        )
        monkeypatch.setattr(
            "src.api.drug_matcher.search_by_active_ingredient",
            _fail,
        )
        result = match_drug_to_cum("TABLETAS RECUBIERTAS")

        assert result.record is None
        assert result.match_type == "none"
        assert result.other_matches == []
        assert result.debug_info.get("error") == "empty_normalized"

    def test_other_matches_populated(self, mock_cum_api):
        result = match_drug_to_cum("METFORMINA")

        # Should have other_matches since we have multiple METFORMINA records
        assert result.record is not None
        assert len(result.other_matches) >= 1

    def test_debug_info_populated(self, mock_cum_api):
        result = match_drug_to_cum("LOSARTAN 50MG")

        assert "query_original" in result.debug_info
        assert "query_normalized" in result.debug_info
        assert "dosage_extracted" in result.debug_info
        assert result.debug_info["query_original"] == "LOSARTAN 50MG"
        assert result.debug_info["dosage_extracted"] == "50MG"

    def test_separate_dosage_parameter(self, mock_cum_api):
        """Test that dosage can be provided as a separate parameter."""
        result = match_drug_to_cum("LOSARTAN", dosage="50MG")

        assert result.record is not None
        assert "LOSARTAN" in result.record.principioactivo
        # Dosage should be extracted from the separate parameter
        assert result.debug_info["dosage_extracted"] == "50MG"

    def test_separate_dosage_not_override_inline(self, mock_cum_api):
        """Separate dosage param should not override dosage in medication name."""
        result = match_drug_to_cum("LOSARTAN 50MG", dosage="100MG")

        # Inline dosage (50MG) should take precedence
        assert result.debug_info["dosage_extracted"] == "50MG"


class TestDrugMatchResultDataclass:
    """Tests for DrugMatchResult dataclass."""

    def test_default_values(self):
        result = DrugMatchResult()

        assert result.record is None
        assert result.match_type == "none"
        assert result.confidence == 0.0
        assert result.other_matches == []
        assert result.query_normalized == ""
        assert result.debug_info == {}

    def test_with_record(self, sample_cum_record):
        result = DrugMatchResult(
            record=sample_cum_record,
            match_type="exact",
            confidence=0.95,
            query_normalized="METFORMINA",
        )

        assert result.record is not None
        assert result.record.producto == "METFORMINA MK 850MG"
        assert result.match_type == "exact"
        assert result.confidence == 0.95
