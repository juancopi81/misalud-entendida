"""Prescription enrichment helpers.

Provides a focused, testable step that takes a medication name and returns
CUM match info, possible generics, and SISMED price references.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from src.api.cum import find_generics
from src.api.drug_matcher import DrugMatchResult, match_drug_to_cum
from src.api.sismed import get_price_by_expediente, get_price_range
from src.logger import get_logger
from src.models import CUMRecord, PriceRecord

logger = get_logger(__name__)


@dataclass
class EnrichedMedication:
    """Enriched medication details from CUM and SISMED lookups."""

    medication_name: str
    match: DrugMatchResult
    generics: list[CUMRecord] = field(default_factory=list)
    prices: list[PriceRecord] = field(default_factory=list)
    price_summary: Optional[dict[str, Any]] = None


def _filter_by_form(
    generics: list[CUMRecord],
    form: str,
) -> list[CUMRecord]:
    if not form:
        return generics

    form_upper = form.upper()
    return [g for g in generics if g.formafarmaceutica.upper() == form_upper]


def enrich_medication(
    medication_name: str,
    dosage: str = "",
    form: str = "",
    limit: int = 20,
) -> EnrichedMedication:
    """Enrich a medication name with CUM match, generics, and SISMED prices.

    Args:
        medication_name: Medication name to match (e.g., "LOSARTAN 50MG")
        dosage: Optional dosage string if not embedded in medication_name
        form: Optional pharmaceutical form to filter generics (e.g., "TABLETA")
        limit: Max number of CUM results to fetch during matching

    Returns:
        EnrichedMedication with match info, generics, and price references
    """
    logger.info("Enriching medication: %s", medication_name)

    match_result = match_drug_to_cum(
        medication_name,
        dosage=dosage,
        limit=limit,
    )

    if not match_result.record:
        return EnrichedMedication(
            medication_name=medication_name,
            match=match_result,
        )

    record = match_result.record

    generics = find_generics(
        record.principioactivo,
        concentration=record.concentracion_valor,
    )

    effective_form = form or record.formafarmaceutica
    generics = _filter_by_form(generics, effective_form)

    prices: list[PriceRecord] = []
    price_summary: Optional[dict[str, Any]] = None
    if record.expedientecum:
        prices = get_price_by_expediente(record.expedientecum, limit=10)
        price_summary = get_price_range(prices)

    return EnrichedMedication(
        medication_name=medication_name,
        match=match_result,
        generics=generics,
        prices=prices,
        price_summary=price_summary,
    )
