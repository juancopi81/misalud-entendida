"""Lab results pipeline helpers.

Transforms MedGemma lab extraction output into Spanish markdown with
simple explanations for abnormal values.
"""

from src.models import LabResultExtraction, LabResultItem
from src.pipelines.spanish_explanations import DISCLAIMER_FULL, DISCLAIMER_SHORT

STATUS_EMOJI = {
    "normal": "🟢",
    "alto": "🔴",
    "bajo": "🟡",
}


def get_status_emoji(estado: str) -> str:
    """Get emoji for lab result status."""
    return STATUS_EMOJI.get(estado.lower(), "⚪")


def format_lab_results_table(results: list[LabResultItem]) -> str:
    """Format lab results as a markdown table with status indicators."""
    if not results:
        return "No se encontraron resultados."

    md = "| Estado | Prueba | Valor | Unidad | Rango Referencia |\n"
    md += "|:------:|--------|-------|--------|------------------|\n"

    for r in results:
        emoji = get_status_emoji(r.estado)
        md += f"| {emoji} | {r.nombre_prueba} | {r.valor} | {r.unidad} | {r.rango_referencia} |\n"

    md += "\n\n**Leyenda:** 🟢 Normal | 🔴 Alto | 🟡 Bajo"

    return md


def build_lab_results_output(extraction: LabResultExtraction) -> str:
    """Build Spanish markdown output from a lab results extraction."""
    if not extraction.resultados:
        return "No se encontraron resultados."

    md = f"## Resultados de Laboratorio ({len(extraction.resultados)} pruebas)\n\n"
    md += format_lab_results_table(extraction.resultados)

    abnormal = [
        r for r in extraction.resultados if r.estado.lower() in ("alto", "bajo")
    ]
    if abnormal:
        md += "\n\n### Valores Fuera de Rango\n\n"
        for r in abnormal:
            status = "por encima" if r.estado.lower() == "alto" else "por debajo"
            md += (
                f"- **{r.nombre_prueba}**: Su valor ({r.valor} {r.unidad}) "
                f"está {status} del rango normal ({r.rango_referencia}). "
                "Consulte con su médico.\n"
            )

    md += f"\n\n**Aviso:** {DISCLAIMER_FULL} {DISCLAIMER_SHORT}"

    return md
