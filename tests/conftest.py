"""
Pytest fixtures for MiSalud Entendida tests.

Provides mocked API responses for fast, offline unit testing.
"""

import pytest
from pytest import MonkeyPatch

from src.models import CUMRecord


# Sample CUM records for testing
SAMPLE_CUM_RECORDS = {
    "METFORMINA": [
        CUMRecord(
            expedientecum="20001234",
            producto="METFORMINA MK 850MG",
            principioactivo="METFORMINA",
            concentracion_valor="850",
            unidadmedida="mg",
            formafarmaceutica="TABLETA",
            titular="TECNOQUIMICAS S.A.",
            registrosanitario="INVIMA 2020M-001234",
            estadoregistro="Vigente",
            cantidadcum="30",
            descripcioncomercial="CAJA X 30 TABLETAS",
        ),
        CUMRecord(
            expedientecum="20001235",
            producto="GLUCOPHAGE 850MG",
            principioactivo="METFORMINA",
            concentracion_valor="850",
            unidadmedida="mg",
            formafarmaceutica="TABLETA",
            titular="MERCK S.A.",
            registrosanitario="INVIMA 2020M-001235",
            estadoregistro="Vigente",
            cantidadcum="30",
            descripcioncomercial="CAJA X 30 TABLETAS - GENERICO",
        ),
    ],
    "LOSARTAN": [
        CUMRecord(
            expedientecum="20002001",
            producto="LOSARTAN",
            principioactivo="LOSARTAN POTASICO",
            concentracion_valor="50",
            unidadmedida="mg",
            formafarmaceutica="TABLETA",
            titular="GENFAR S.A.",
            registrosanitario="INVIMA 2021M-002001",
            estadoregistro="Vigente",
            cantidadcum="30",
            descripcioncomercial="CAJA X 30 TABLETAS",
        ),
        CUMRecord(
            expedientecum="20002002",
            producto="COZAAR 50MG",
            principioactivo="LOSARTAN POTASICO",
            concentracion_valor="50",
            unidadmedida="mg",
            formafarmaceutica="TABLETA",
            titular="MSD",
            registrosanitario="INVIMA 2021M-002002",
            estadoregistro="Vigente",
            cantidadcum="30",
            descripcioncomercial="CAJA X 30 TABLETAS",
        ),
    ],
    "ACETAMINOFEN": [
        CUMRecord(
            expedientecum="20003001",
            producto="ACETAMINOFEN MK 500MG",
            principioactivo="ACETAMINOFEN",
            concentracion_valor="500",
            unidadmedida="mg",
            formafarmaceutica="TABLETA",
            titular="TECNOQUIMICAS S.A.",
            registrosanitario="INVIMA 2019M-003001",
            estadoregistro="Vigente",
            cantidadcum="100",
            descripcioncomercial="CAJA X 100 TABLETAS - GENERICO",
        ),
    ],
}


@pytest.fixture
def mock_cum_api(monkeypatch: MonkeyPatch) -> dict[str, list[CUMRecord]]:
    """
    Mock CUM API calls for offline testing.

    Returns matching records based on search term.
    """
    def mock_search_by_product_name(
        product_name: str, limit: int = 50
    ) -> list[CUMRecord]:
        product_upper = product_name.upper()
        results: list[CUMRecord] = []
        for key, records in SAMPLE_CUM_RECORDS.items():
            for record in records:
                if product_upper in record.producto.upper() or product_upper in key:
                    results.append(record)
        return results[:limit]

    def mock_search_by_active_ingredient(
        ingredient: str, limit: int = 50, only_active: bool = True
    ) -> list[CUMRecord]:
        ingredient_upper = ingredient.upper()
        if ingredient_upper in SAMPLE_CUM_RECORDS:
            return SAMPLE_CUM_RECORDS[ingredient_upper][:limit]
        return []

    monkeypatch.setattr(
        "src.api.drug_matcher.search_by_product_name",
        mock_search_by_product_name
    )
    monkeypatch.setattr(
        "src.api.drug_matcher.search_by_active_ingredient",
        mock_search_by_active_ingredient
    )

    return SAMPLE_CUM_RECORDS


@pytest.fixture
def sample_cum_record() -> CUMRecord:
    """Return a single sample CUM record for basic tests."""
    return SAMPLE_CUM_RECORDS["METFORMINA"][0]
