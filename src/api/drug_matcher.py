"""
Drug name matching for CUM database lookup.

Matches extracted medication names (from MedGemma) to CUM database records
using a multi-strategy approach:
1. Product name search (full-text)
2. Active ingredient search (exact)
3. Fuzzy matching with scoring

Example:
    >>> result = match_drug_to_cum("LOSARTAN 50MG")
    >>> if result.record:
    ...     print(f"Matched: {result.record.producto}")
    ...     print(f"Match type: {result.match_type} ({result.confidence:.0%})")
"""

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Optional

from src.api.cum import search_by_active_ingredient, search_by_product_name
from src.logger import get_logger
from src.models import CUMRecord

logger = get_logger(__name__)

# Confidence threshold for accepting a match
MIN_CONFIDENCE = 0.5

# Common pharmaceutical form words to strip from search queries
FORM_WORDS = frozenset({
    "TABLETA", "TABLETAS", "TAB", "TABS",
    "CAPSULA", "CAPSULAS", "CAP", "CAPS",
    "SOLUCION", "SOL",
    "JARABE", "JAR",
    "AMPOLLA", "AMP",
    "INYECTABLE", "INY",
    "CREMA", "GEL", "POMADA",
    "GOTAS", "SUSPENSION", "SUSP",
    "COMPRIMIDO", "COMPRIMIDOS", "COMP",
    "RECUBIERTA", "RECUBIERTAS",
    "LIBERACION", "PROLONGADA",
    "ORAL", "TOPICO", "TOPICA",
})

# Regex to extract dosage from medication name
DOSAGE_PATTERN = re.compile(r"(\d+(?:[.,]\d+)?)\s*(MG|ML|G|MCG|UI|%)", re.IGNORECASE)


@dataclass
class DrugMatchResult:
    """Result of matching a drug name to CUM database.

    Attributes:
        record: Best matching CUMRecord or None if no match found
        match_type: Type of match found ("exact", "active_ingredient", "fuzzy", "none")
        confidence: Match confidence score from 0.0 to 1.0
        other_matches: Other potential matches from fuzzy search (NOT generic alternatives)
        query_normalized: The cleaned/normalized query used for matching
        debug_info: Additional debug information (API calls, errors, etc.)

    Note:
        other_matches contains fuzzy search results, not true generic alternatives.
        For generic alternatives, use find_generics() with the matched principioactivo.
    """
    record: Optional[CUMRecord] = None
    match_type: str = "none"
    confidence: float = 0.0
    other_matches: list[CUMRecord] = field(default_factory=list)
    query_normalized: str = ""
    debug_info: dict[str, Any] = field(default_factory=dict)


def _normalize_drug_name(name: str) -> tuple[str, str, str]:
    """
    Normalize a drug name for matching.

    Args:
        name: Raw medication name (e.g., "LOSARTAN 50MG TABLETAS")

    Returns:
        Tuple of (normalized_name, dosage_value, dosage_unit)
        e.g., ("LOSARTAN", "50", "MG")
    """
    if not name:
        return ("", "", "")

    # Uppercase and strip
    normalized = name.upper().strip()

    # Extract dosage before removing it
    dosage_match = DOSAGE_PATTERN.search(normalized)
    dosage_value = ""
    dosage_unit = ""
    if dosage_match:
        dosage_value = dosage_match.group(1).replace(",", ".")
        dosage_unit = dosage_match.group(2).upper()
        # Remove dosage from name
        normalized = DOSAGE_PATTERN.sub("", normalized)

    # Remove form words
    words = normalized.split()
    filtered_words = [w for w in words if w not in FORM_WORDS]
    normalized = " ".join(filtered_words).strip()

    # Remove extra whitespace
    normalized = re.sub(r"\s+", " ", normalized)

    return (normalized, dosage_value, dosage_unit)


def _fuzzy_score(query: str, candidate: str) -> float:
    """
    Calculate fuzzy match score between query and candidate.

    Uses SequenceMatcher for similarity ratio.

    Args:
        query: Normalized query string
        candidate: Candidate string to compare

    Returns:
        Similarity score from 0.0 to 1.0
    """
    if not query or not candidate:
        return 0.0

    query = query.upper()
    candidate = candidate.upper()

    # Exact match
    if query == candidate:
        return 1.0

    # Check if query is contained in candidate
    if query in candidate:
        return 0.9 + (len(query) / len(candidate)) * 0.1

    # Use SequenceMatcher for fuzzy comparison
    return SequenceMatcher(None, query, candidate).ratio()


def _calculate_match_score(
    query: str,
    record: CUMRecord,
    dosage_value: str = "",
    dosage_unit: str = "",
) -> float:
    """
    Calculate overall match score for a CUM record.

    Considers:
    - Product name similarity
    - Active ingredient similarity
    - Dosage match (bonus if matches)

    Args:
        query: Normalized search query
        record: CUM record to score
        dosage_value: Extracted dosage value (e.g., "50")
        dosage_unit: Extracted dosage unit (e.g., "MG")

    Returns:
        Score from 0.0 to 1.0
    """
    # Score product name match
    product_score = _fuzzy_score(query, record.producto)

    # Score active ingredient match
    ingredient_score = _fuzzy_score(query, record.principioactivo)

    # Take the higher of product or ingredient score
    base_score = max(product_score, ingredient_score)

    # Bonus for dosage match (value AND unit must match)
    dosage_bonus = 0.0
    if dosage_value and dosage_unit and record.concentracion_valor and record.unidadmedida:
        # Normalize dosage values for comparison
        record_dosage = record.concentracion_valor.replace(",", ".")
        record_unit = record.unidadmedida.upper()
        if dosage_value == record_dosage and dosage_unit == record_unit:
            dosage_bonus = 0.1

    # Bonus for active registration status (case-insensitive)
    status_bonus = 0.05 if record.estadoregistro.upper() == "VIGENTE" else 0.0

    return min(1.0, base_score + dosage_bonus + status_bonus)


def match_drug_to_cum(
    medication_name: str,
    dosage: str = "",
    limit: int = 20,
) -> DrugMatchResult:
    """
    Match a medication name to CUM database records.

    Uses a multi-strategy approach:
    1. Product name search (full-text via API)
    2. Active ingredient search (exact match via API)
    3. Fuzzy scoring of results

    Args:
        medication_name: Medication name to search (e.g., "LOSARTAN 50MG")
        dosage: Optional separate dosage string (used if not in medication_name)
        limit: Maximum results to fetch from each API call

    Returns:
        DrugMatchResult with best match, other_matches, and match metadata

    Example:
        >>> result = match_drug_to_cum("METFORMINA 850MG")
        >>> if result.record:
        ...     print(f"Found: {result.record.producto}")
        ...     print(f"Active ingredient: {result.record.principioactivo}")
    """
    debug_info = {}

    # Handle empty input
    if not medication_name.strip():
        logger.debug("Empty medication name provided")
        return DrugMatchResult(
            match_type="none",
            debug_info={"error": "empty_input"},
        )

    # Normalize the drug name
    normalized, dosage_value, dosage_unit = _normalize_drug_name(medication_name)

    # If dosage provided separately, use it
    if dosage and not dosage_value:
        _, dosage_value, dosage_unit = _normalize_drug_name(dosage)

    logger.info(
        "Matching drug: '%s' -> normalized='%s', dosage=%s%s",
        medication_name, normalized, dosage_value, dosage_unit
    )
    debug_info["query_original"] = medication_name
    debug_info["query_normalized"] = normalized
    debug_info["dosage_extracted"] = f"{dosage_value}{dosage_unit}"

    # Guard: if normalized is empty after stripping dosage/form words, return early
    # This prevents API calls with empty queries returning unrelated results
    if not normalized:
        logger.debug("Normalized query is empty, skipping API calls")
        return DrugMatchResult(
            match_type="none",
            query_normalized=normalized,
            debug_info={**debug_info, "error": "empty_normalized"},
        )

    all_candidates: list[tuple[CUMRecord, float, str]] = []

    # Strategy 1: Product name search
    try:
        product_results = search_by_product_name(normalized, limit=limit)
        debug_info["product_search_count"] = len(product_results)
        logger.debug("Product search returned %d results", len(product_results))

        for record in product_results:
            score = _calculate_match_score(normalized, record, dosage_value, dosage_unit)
            # Higher scores for product name matches suggest "exact" type
            match_type = "exact" if score >= 0.8 else "fuzzy"
            all_candidates.append((record, score, match_type))

    except Exception as e:
        logger.warning("Product name search failed: %s", e)
        debug_info["product_search_error"] = str(e)

    # Strategy 2: Active ingredient search
    try:
        ingredient_results = search_by_active_ingredient(normalized, limit=limit)
        debug_info["ingredient_search_count"] = len(ingredient_results)
        logger.debug("Ingredient search returned %d results", len(ingredient_results))

        for record in ingredient_results:
            # Check if already in candidates (by expedientecum)
            if any(c[0].expedientecum == record.expedientecum for c in all_candidates):
                continue

            score = _calculate_match_score(normalized, record, dosage_value, dosage_unit)
            # If ingredient matches exactly, it's an ingredient match
            if record.principioactivo.upper() == normalized:
                all_candidates.append((record, max(score, 0.85), "active_ingredient"))
            else:
                all_candidates.append((record, score, "fuzzy"))

    except Exception as e:
        logger.warning("Active ingredient search failed: %s", e)
        debug_info["ingredient_search_error"] = str(e)

    # Sort candidates by score (descending)
    all_candidates.sort(key=lambda x: x[1], reverse=True)

    debug_info["total_candidates"] = len(all_candidates)

    # No matches found
    if not all_candidates:
        logger.info("No matches found for '%s'", medication_name)
        return DrugMatchResult(
            match_type="none",
            query_normalized=normalized,
            debug_info=debug_info,
        )

    # Get best match
    best_record, best_score, best_type = all_candidates[0]

    # Check if best match meets confidence threshold
    if best_score < MIN_CONFIDENCE:
        logger.info(
            "Best match for '%s' below threshold: %s (%.2f < %.2f)",
            medication_name, best_record.producto, best_score, MIN_CONFIDENCE
        )
        return DrugMatchResult(
            match_type="none",
            confidence=best_score,
            other_matches=[c[0] for c in all_candidates[:5]],
            query_normalized=normalized,
            debug_info=debug_info,
        )

    # Build other_matches list (excluding the best match)
    other_matches = [c[0] for c in all_candidates[1:6]]

    logger.info(
        "Matched '%s' -> %s (%s, confidence=%.2f)",
        medication_name, best_record.producto, best_type, best_score
    )

    return DrugMatchResult(
        record=best_record,
        match_type=best_type,
        confidence=best_score,
        other_matches=other_matches,
        query_normalized=normalized,
        debug_info=debug_info,
    )


def main():
    """
    Quick test of drug matching functionality.

    Run with:
        uv run python -m src.api.drug_matcher
    """
    print("=" * 60)
    print("Drug Matcher Test")
    print("=" * 60)

    test_cases = [
        "METFORMINA",
        "LOSARTAN 50MG",
        "losartan",
        "ACETAMINOFEN 500 MG TABLETAS",
        "NONEXISTENT_DRUG_XYZ",
    ]

    for drug in test_cases:
        print(f"\n[Test] Matching: '{drug}'")
        result = match_drug_to_cum(drug)

        if result.record:
            print(f"  Match type: {result.match_type}")
            print(f"  Confidence: {result.confidence:.0%}")
            print(f"  Product: {result.record.producto}")
            print(f"  Ingredient: {result.record.principioactivo}")
            print(f"  Concentration: {result.record.concentracion_valor}{result.record.unidadmedida}")
            if result.other_matches:
                print(f"  Other matches: {len(result.other_matches)}")
        else:
            print(f"  No match (type={result.match_type})")
            print(f"  Normalized query: {result.query_normalized}")

    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
