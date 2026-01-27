"""Template-based Spanish explanations for medications."""

from dataclasses import dataclass

from src.models import MedicationItem
from src.pipelines.prescription_enrichment import EnrichedMedication


DISCLAIMER_FULL = (
    "Esta herramienta es solo para ayudarle a entender sus documentos. "
    "No reemplaza el consejo de su médico."
)
DISCLAIMER_SHORT = "No es consejo médico."


@dataclass(frozen=True)
class ExplanationContext:
    """Structured context for rendering explanations."""

    medication_name: str
    active_ingredient: str
    dosage: str
    frequency: str
    duration: str
    instructions: str
    generics_count: int
    price_min: float | None
    price_max: float | None
    price_avg: float | None
    price_date: str


def build_explanation_context(
    med: MedicationItem,
    enriched: EnrichedMedication | None,
) -> ExplanationContext:
    active_ingredient = ""
    generics_count = 0
    price_min = None
    price_max = None
    price_avg = None
    price_date = ""

    if enriched and enriched.match.record:
        active_ingredient = enriched.match.record.principioactivo
        generics_count = len(enriched.generics)

        if enriched.price_summary:
            price_min = float(enriched.price_summary.get("min", 0) or 0)
            price_max = float(enriched.price_summary.get("max", 0) or 0)
            price_avg = float(enriched.price_summary.get("avg", 0) or 0)
            price_date = str(enriched.price_summary.get("fecha_datos", ""))

    return ExplanationContext(
        medication_name=med.nombre_medicamento,
        active_ingredient=active_ingredient,
        dosage=med.dosis,
        frequency=med.frecuencia,
        duration=med.duracion,
        instructions=med.instrucciones,
        generics_count=generics_count,
        price_min=price_min if price_min and price_min > 0 else None,
        price_max=price_max if price_max and price_max > 0 else None,
        price_avg=price_avg if price_avg and price_avg > 0 else None,
        price_date=price_date,
    )


def format_medication_explanation(
    med: MedicationItem,
    enriched: EnrichedMedication | None,
) -> str:
    """Generate a short, plain-Spanish explanation for a medication."""
    if not med.nombre_medicamento:
        return ""

    context = build_explanation_context(med, enriched)
    sentences: list[str] = []

    if context.active_ingredient:
        sentences.append(
            f"Este medicamento contiene {context.active_ingredient.lower()}."
        )
    else:
        sentences.append(
            "No se pudo validar este medicamento en el registro CUM."
        )

    if context.dosage:
        sentences.append(f"Dosis indicada: {context.dosage}.")
    if context.frequency:
        sentences.append(f"Frecuencia: {context.frequency}.")
    if context.duration:
        sentences.append(f"Duración: {context.duration}.")
    if context.instructions:
        sentences.append(f"Instrucciones: {context.instructions}.")

    if context.generics_count > 0:
        sentences.append(
            "Hay alternativas genéricas disponibles para este medicamento."
        )

    if context.price_min and context.price_max:
        price_text = (
            f"Precios de referencia: entre ${context.price_min:,.0f} y "
            f"${context.price_max:,.0f} COP."
        )
        if context.price_avg:
            price_text += f" Promedio ${context.price_avg:,.0f} COP."
        if context.price_date:
            price_text += f" (Datos de {context.price_date})."
        sentences.append(price_text)

    return " ".join(sentences)
