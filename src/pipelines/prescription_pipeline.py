"""Prescription pipeline helpers.

Transforms MedGemma extraction output into Spanish markdown with
CUM generics and SISMED price references.
"""

from dataclasses import dataclass, field

from src.logger import get_logger
from src.models import MedicationItem, PrescriptionExtraction
from src.pipelines.prescription_enrichment import EnrichedMedication, enrich_medication

logger = get_logger(__name__)


@dataclass
class PrescriptionPipelineResult:
    """Output of the prescription enrichment pipeline."""

    medications_markdown: str
    generics_markdown: str
    prices_markdown: str
    enriched: list[EnrichedMedication] = field(default_factory=list)


def format_medication_card(med: MedicationItem, index: int) -> str:
    """Format a single medication as a markdown card."""
    return f"""
### {index}. {med.nombre_medicamento}

| Campo | Valor |
|-------|-------|
| **Dosis** | {med.dosis or "No especificada"} |
| **Frecuencia** | {med.frecuencia or "No especificada"} |
| **Duración** | {med.duracion or "No especificada"} |
| **Instrucciones** | {med.instrucciones or "Ninguna"} |
"""


def build_prescription_output(
    extraction: PrescriptionExtraction,
    limit: int = 5,
) -> PrescriptionPipelineResult:
    """Build Spanish markdown outputs from a prescription extraction.

    Args:
        extraction: Parsed MedGemma prescription result
        limit: Max number of CUM records to fetch during matching

    Returns:
        PrescriptionPipelineResult with markdown and enrichment details
    """
    if not extraction.medicamentos:
        return PrescriptionPipelineResult(
            medications_markdown=(
                "No se pudieron extraer medicamentos de esta imagen. "
                "Asegúrese de que la imagen sea clara y legible."
            ),
            generics_markdown="",
            prices_markdown="",
        )

    meds_md = f"## Medicamentos Encontrados ({len(extraction.medicamentos)})\n\n"
    enriched_results: list[EnrichedMedication] = []
    generics_sections: list[str] = []
    price_sections: list[str] = []

    for i, med in enumerate(extraction.medicamentos, 1):
        meds_md += format_medication_card(med, i)

        if not med.nombre_medicamento:
            continue

        enriched = enrich_medication(
            med.nombre_medicamento,
            dosage=med.dosis,
            limit=limit,
        )
        enriched_results.append(enriched)

        if enriched.match.record and enriched.generics:
            ingredient = enriched.match.record.principioactivo
            if ingredient:
                generics_md = f"**Alternativas para {ingredient}:**\n\n"
                for g in enriched.generics[:3]:
                    is_generic = "GENERICO" in g.descripcioncomercial.upper()
                    badge = " [GENÉRICO]" if is_generic else ""
                    generics_md += (
                        f"- {g.producto}{badge} "
                        f"({g.concentracion_valor}{g.unidadmedida})\n"
                    )
                generics_sections.append(f"### {med.nombre_medicamento}\n{generics_md}")

        if enriched.price_summary:
            summary = enriched.price_summary
            price_md = f"""**Precio referencia:**
- Mínimo: ${summary['min']:,.0f} COP
- Máximo: ${summary['max']:,.0f} COP
- Promedio: ${summary['avg']:,.0f} COP

*Datos de {summary['fecha_datos']} (referencia histórica)*
"""
            price_sections.append(f"### {med.nombre_medicamento}\n{price_md}")

    generics_output = (
        "\n\n".join(generics_sections)
        if generics_sections
        else "No se encontraron genéricos."
    )
    prices_output = (
        "\n\n".join(price_sections)
        if price_sections
        else "No se encontraron precios de referencia."
    )

    return PrescriptionPipelineResult(
        medications_markdown=meds_md,
        generics_markdown=generics_output,
        prices_markdown=prices_output,
        enriched=enriched_results,
    )
