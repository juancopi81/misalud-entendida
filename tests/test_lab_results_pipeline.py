"""Unit tests for lab results pipeline helpers."""

from src.models import LabResultExtraction, LabResultItem
from src.pipelines.lab_results_pipeline import build_lab_results_output


def test_build_lab_results_output_normal_only():
    extraction = LabResultExtraction(
        resultados=[
            LabResultItem(
                nombre_prueba="Hemoglobina",
                valor="14.1",
                unidad="g/dL",
                rango_referencia="12.0 - 15.5",
                estado="normal",
            )
        ],
        parse_success=True,
    )

    output = build_lab_results_output(extraction)

    assert "Resultados de Laboratorio (1 pruebas)" in output
    assert "**Leyenda:**" in output
    assert "**Aviso:**" in output
    assert "Valores Fuera de Rango" not in output


def test_build_lab_results_output_with_abnormal_values():
    extraction = LabResultExtraction(
        resultados=[
            LabResultItem(
                nombre_prueba="Glucosa",
                valor="140",
                unidad="mg/dL",
                rango_referencia="70 - 110",
                estado="alto",
            ),
            LabResultItem(
                nombre_prueba="Sodio",
                valor="130",
                unidad="mmol/L",
                rango_referencia="135 - 145",
                estado="bajo",
            ),
        ],
        parse_success=True,
    )

    output = build_lab_results_output(extraction)

    assert "Valores Fuera de Rango" in output
    assert "por encima" in output
    assert "por debajo" in output
    assert "**Aviso:**" in output
