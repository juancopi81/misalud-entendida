"""Gradio UI for MiSalud Entendida.

A healthcare literacy app that helps Colombians understand prescriptions,
lab results, and medication prices using MedGemma's document understanding.

Usage:
    uv run python -m src.app
"""

import gradio as gr

from src.api.cum import find_generics, search_by_product_name
from src.api.sismed import get_price_by_expediente, get_price_range
from src.inference import get_backend
from src.inference.modal_app import app as modal_app
from src.interactions import Interaction, check_interactions
from src.logger import get_logger
from src.models import LabResultExtraction, MedicationItem, PrescriptionExtraction

logger = get_logger(__name__)

# Backend is initialized lazily within Modal context
_backend = None


def get_modal_backend():
    """Get the Modal backend, initializing if needed."""
    global _backend
    if _backend is None:
        _backend = get_backend("modal")
    return _backend


# Required disclaimer per CLAUDE.md
DISCLAIMER = """
**Aviso importante**: Esta herramienta es solo para fines educativos.
No reemplaza el consejo de su médico. Siempre consulte a un profesional
de la salud antes de tomar decisiones sobre sus medicamentos.

*No es consejo médico.*
"""


# --- Prescription Tab Functions ---


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


def lookup_drug_info(med_name: str) -> tuple[str, str]:
    """Look up CUM and SISMED info for a medication.

    Returns:
        Tuple of (generics_markdown, price_markdown)
    """
    generics_md = ""
    price_md = ""

    try:
        # Search CUM by product name
        cum_results = search_by_product_name(med_name, limit=5)

        if cum_results:
            # Get the active ingredient from first result
            ingredient = cum_results[0].principioactivo
            if ingredient:
                # Find generics
                generics = find_generics(ingredient, limit=5)
                if generics:
                    generics_md = f"**Alternativas para {ingredient}:**\n\n"
                    for g in generics[:3]:
                        is_generic = "GENERICO" in g.descripcioncomercial.upper()
                        badge = " [GENÉRICO]" if is_generic else ""
                        generics_md += f"- {g.producto}{badge} ({g.concentracion_valor}{g.unidadmedida})\n"

                # Get price for first result
                if cum_results[0].expedientecum:
                    prices = get_price_by_expediente(
                        cum_results[0].expedientecum, limit=10
                    )
                    price_summary = get_price_range(prices)
                    if price_summary:
                        price_md = f"""**Precio referencia:**
- Mínimo: ${price_summary['min']:,.0f} COP
- Máximo: ${price_summary['max']:,.0f} COP
- Promedio: ${price_summary['avg']:,.0f} COP

*Datos de {price_summary['fecha_datos']} (referencia histórica)*
"""
    except Exception as e:
        logger.warning("Error looking up drug info for %s: %s", med_name, e)

    return generics_md, price_md


def analyze_prescription(image_path: str | None) -> tuple[str, str, str]:
    """Analyze a prescription image and return formatted results.

    Args:
        image_path: Path to the prescription image

    Returns:
        Tuple of (medications_md, generics_md, prices_md)
    """
    if not image_path:
        return "Por favor suba una imagen de su receta.", "", ""

    try:
        logger.info("Analyzing prescription: %s", image_path)

        # Extract prescription data using MedGemma (within Modal context)
        with modal_app.run():
            backend = get_modal_backend()
            result: PrescriptionExtraction = backend.extract_prescription(image_path)

        if not result.parse_success or not result.medicamentos:
            return (
                "No se pudieron extraer medicamentos de esta imagen. "
                "Asegúrese de que la imagen sea clara y legible.",
                "",
                "",
            )

        # Format medications
        meds_md = f"## Medicamentos Encontrados ({len(result.medicamentos)})\n\n"
        all_generics = []
        all_prices = []

        for i, med in enumerate(result.medicamentos, 1):
            meds_md += format_medication_card(med, i)

            # Look up additional info
            if med.nombre_medicamento:
                generics_md, price_md = lookup_drug_info(med.nombre_medicamento)
                if generics_md:
                    all_generics.append(f"### {med.nombre_medicamento}\n{generics_md}")
                if price_md:
                    all_prices.append(f"### {med.nombre_medicamento}\n{price_md}")

        generics_output = (
            "\n\n".join(all_generics)
            if all_generics
            else "No se encontraron genéricos."
        )
        prices_output = (
            "\n\n".join(all_prices)
            if all_prices
            else "No se encontraron precios de referencia."
        )

        return meds_md, generics_output, prices_output

    except Exception as e:
        logger.error("Error analyzing prescription: %s", e)
        return f"Error al analizar la receta: {str(e)}", "", ""


# --- Lab Results Tab Functions ---


STATUS_EMOJI = {
    "normal": "🟢",
    "alto": "🔴",
    "bajo": "🟡",
}


def get_status_emoji(estado: str) -> str:
    """Get emoji for lab result status."""
    return STATUS_EMOJI.get(estado.lower(), "⚪")


def format_lab_results_table(results: list) -> str:
    """Format lab results as a markdown table with status indicators."""
    if not results:
        return "No se encontraron resultados."

    md = "| Estado | Prueba | Valor | Unidad | Rango Referencia |\n"
    md += "|:------:|--------|-------|--------|------------------|\n"

    for r in results:
        emoji = get_status_emoji(r.estado)
        md += f"| {emoji} | {r.nombre_prueba} | {r.valor} | {r.unidad} | {r.rango_referencia} |\n"

    # Add legend
    md += "\n\n**Leyenda:** 🟢 Normal | 🔴 Alto | 🟡 Bajo"

    return md


def analyze_lab_results(image_path: str | None) -> str:
    """Analyze a lab results image and return formatted results.

    Args:
        image_path: Path to the lab results image

    Returns:
        Formatted markdown string with lab results
    """
    if not image_path:
        return "Por favor suba una imagen de sus resultados de laboratorio."

    try:
        logger.info("Analyzing lab results: %s", image_path)

        # Extract lab results using MedGemma (within Modal context)
        with modal_app.run():
            backend = get_modal_backend()
            result: LabResultExtraction = backend.extract_lab_results(image_path)

        if not result.parse_success or not result.resultados:
            return (
                "No se pudieron extraer resultados de esta imagen. "
                "Asegúrese de que la imagen sea clara y legible."
            )

        # Format results
        md = f"## Resultados de Laboratorio ({len(result.resultados)} pruebas)\n\n"
        md += format_lab_results_table(result.resultados)

        # Add interpretation hints for abnormal values
        abnormal = [
            r for r in result.resultados if r.estado.lower() in ("alto", "bajo")
        ]
        if abnormal:
            md += "\n\n### Valores Fuera de Rango\n\n"
            for r in abnormal:
                status = "por encima" if r.estado.lower() == "alto" else "por debajo"
                md += f"- **{r.nombre_prueba}**: Su valor ({r.valor} {r.unidad}) está {status} del rango normal ({r.rango_referencia}). Consulte con su médico.\n"

        return md

    except Exception as e:
        logger.error("Error analyzing lab results: %s", e)
        return f"Error al analizar los resultados: {str(e)}"


# --- Medication Tracker Functions ---


def get_tracker_displays(medications: list[str]) -> tuple[str, str]:
    """Compute the medication list and interaction displays."""
    meds_display = format_tracked_medications(medications)
    interactions = check_interactions(medications)
    interactions_display = format_interactions(interactions)
    return meds_display, interactions_display


def format_tracked_medications(medications: list[str]) -> str:
    """Format the list of tracked medications."""
    if not medications:
        return "No hay medicamentos registrados. Agregue medicamentos usando el campo de arriba."

    md = "## Mis Medicamentos\n\n"
    for i, med in enumerate(medications, 1):
        md += f"{i}. {med}\n"
    return md


def format_interactions(interactions: list[Interaction]) -> str:
    """Format interaction warnings as markdown."""
    if not interactions:
        return "✅ No se detectaron interacciones conocidas entre sus medicamentos."

    md = "## ⚠️ Interacciones Detectadas\n\n"

    for interaction in interactions:
        severity_badge = {
            "alta": "🔴 **ALTA**",
            "media": "🟡 **MEDIA**",
            "baja": "🟢 **BAJA**",
        }.get(interaction.severity, "⚪")

        md += f"""### {interaction.drugs[0]} + {interaction.drugs[1]}

**Severidad:** {severity_badge}

{interaction.warning}

---
"""

    return md


def add_medication(
    new_med: str, current_meds: list[str]
) -> tuple[list[str], str, str, str]:
    """Add a medication to the tracker.

    Returns:
        Tuple of (updated_meds, meds_display, interactions_display, input_cleared)
    """
    if not new_med or not new_med.strip():
        meds_display, interactions_display = get_tracker_displays(current_meds)
        return current_meds, meds_display, interactions_display, ""

    new_med = new_med.strip()

    # Avoid duplicates (case-insensitive)
    if new_med.lower() in [m.lower() for m in current_meds]:
        meds_display, interactions_display = get_tracker_displays(current_meds)
        return current_meds, meds_display, interactions_display, ""

    updated_meds = current_meds + [new_med]
    meds_display, interactions_display = get_tracker_displays(updated_meds)
    return updated_meds, meds_display, interactions_display, ""


def remove_medication(
    med_to_remove: str, current_meds: list[str]
) -> tuple[list[str], str, str]:
    """Remove a medication from the tracker.

    Returns:
        Tuple of (updated_meds, meds_display, interactions_display)
    """
    if not med_to_remove:
        meds_display, interactions_display = get_tracker_displays(current_meds)
        return current_meds, meds_display, interactions_display

    updated_meds = [m for m in current_meds if m != med_to_remove]
    meds_display, interactions_display = get_tracker_displays(updated_meds)
    return updated_meds, meds_display, interactions_display


def clear_medications() -> tuple[list[str], str, str, gr.Dropdown]:
    """Clear all medications from the tracker.

    Returns:
        Tuple of (empty_meds, meds_display, interactions_display, updated_dropdown)
    """
    meds_display, interactions_display = get_tracker_displays([])
    return [], meds_display, interactions_display, gr.Dropdown(choices=[], value=None)


def update_remove_dropdown(medications: list[str]) -> gr.Dropdown:
    """Update the remove dropdown with current medications."""
    return gr.Dropdown(choices=medications, value=None)


# --- Build Gradio Interface ---


def create_app() -> gr.Blocks:
    """Create and return the Gradio app."""

    with gr.Blocks(title="MiSalud Entendida") as app:
        # Header
        gr.Markdown(
            """
# MiSalud Entendida

### Entiende tus recetas y exámenes con IA médica abierta
"""
        )

        # Disclaimer
        gr.Markdown(DISCLAIMER)

        # Tabs
        with gr.Tabs():
            # --- Recetas Tab ---
            with gr.Tab("Recetas"):
                gr.Markdown("## Analiza tu Receta Médica")
                gr.Markdown(
                    "Sube una foto de tu receta para extraer los medicamentos, "
                    "encontrar alternativas genéricas y ver precios de referencia."
                )

                with gr.Row():
                    prescription_image = gr.Image(
                        type="filepath",
                        label="Foto de tu receta",
                        height=300,
                    )

                analyze_prescription_btn = gr.Button(
                    "Analizar Receta", variant="primary", size="lg"
                )

                with gr.Row():
                    with gr.Column():
                        prescription_meds = gr.Markdown(
                            "Los medicamentos extraídos aparecerán aquí.",
                            label="Medicamentos",
                        )
                    with gr.Column():
                        prescription_generics = gr.Markdown(
                            "Las alternativas genéricas aparecerán aquí.",
                            label="Alternativas Genéricas",
                        )

                prescription_prices = gr.Markdown(
                    "Los precios de referencia aparecerán aquí.",
                    label="Precios de Referencia",
                )

                analyze_prescription_btn.click(
                    fn=analyze_prescription,
                    inputs=[prescription_image],
                    outputs=[
                        prescription_meds,
                        prescription_generics,
                        prescription_prices,
                    ],
                )

            # --- Lab Results Tab ---
            with gr.Tab("Exámenes de Laboratorio"):
                gr.Markdown("## Analiza tus Resultados de Laboratorio")
                gr.Markdown(
                    "Sube una foto de tus resultados para entender qué significa cada valor "
                    "y si están dentro del rango normal."
                )

                with gr.Row():
                    lab_image = gr.Image(
                        type="filepath",
                        label="Foto de tus resultados",
                        height=300,
                    )

                analyze_lab_btn = gr.Button(
                    "Analizar Examen", variant="primary", size="lg"
                )

                lab_results_output = gr.Markdown(
                    "Los resultados analizados aparecerán aquí.",
                    label="Resultados",
                )

                analyze_lab_btn.click(
                    fn=analyze_lab_results,
                    inputs=[lab_image],
                    outputs=[lab_results_output],
                )

            # --- Medication Tracker Tab ---
            with gr.Tab("Mis Medicamentos"):
                gr.Markdown("## Seguimiento de Medicamentos")
                gr.Markdown(
                    "Registra los medicamentos que tomas actualmente para detectar "
                    "posibles interacciones peligrosas."
                )

                # Session state for medications
                tracked_meds = gr.State([])

                with gr.Row():
                    with gr.Column(scale=2):
                        new_med_input = gr.Textbox(
                            label="Agregar medicamento",
                            placeholder="Ej: Metformina, Losartan, Aspirina...",
                        )
                        add_med_btn = gr.Button("Agregar", variant="primary")

                    with gr.Column(scale=2):
                        remove_med_dropdown = gr.Dropdown(
                            label="Eliminar medicamento",
                            choices=[],
                            interactive=True,
                        )
                        remove_med_btn = gr.Button("Eliminar", variant="secondary")

                    with gr.Column(scale=1):
                        clear_all_btn = gr.Button("Limpiar Todo", variant="stop")

                with gr.Row():
                    with gr.Column():
                        meds_display = gr.Markdown(
                            format_tracked_medications([]),
                            label="Medicamentos Registrados",
                        )
                    with gr.Column():
                        interactions_display = gr.Markdown(
                            format_interactions([]),
                            label="Interacciones",
                        )

                # Wire up medication tracker events
                add_med_btn.click(
                    fn=add_medication,
                    inputs=[new_med_input, tracked_meds],
                    outputs=[
                        tracked_meds,
                        meds_display,
                        interactions_display,
                        new_med_input,
                    ],
                ).then(
                    fn=update_remove_dropdown,
                    inputs=[tracked_meds],
                    outputs=[remove_med_dropdown],
                )

                # Also trigger on Enter key
                new_med_input.submit(
                    fn=add_medication,
                    inputs=[new_med_input, tracked_meds],
                    outputs=[
                        tracked_meds,
                        meds_display,
                        interactions_display,
                        new_med_input,
                    ],
                ).then(
                    fn=update_remove_dropdown,
                    inputs=[tracked_meds],
                    outputs=[remove_med_dropdown],
                )

                remove_med_btn.click(
                    fn=remove_medication,
                    inputs=[remove_med_dropdown, tracked_meds],
                    outputs=[tracked_meds, meds_display, interactions_display],
                ).then(
                    fn=update_remove_dropdown,
                    inputs=[tracked_meds],
                    outputs=[remove_med_dropdown],
                )

                clear_all_btn.click(
                    fn=clear_medications,
                    inputs=[],
                    outputs=[
                        tracked_meds,
                        meds_display,
                        interactions_display,
                        remove_med_dropdown,
                    ],
                )

        # Footer
        gr.Markdown(
            """
---
**MiSalud Entendida** - Desarrollado para el MedGemma Impact Challenge

Usando [MedGemma 1.5](https://huggingface.co/google/medgemma-1.5-4b-it) para análisis de documentos médicos.
Datos de medicamentos: [CUM](https://www.datos.gov.co/Salud-y-Protecci-n-Social/C-digo-nico-de-Medicamentos/i7cb-raxc) |
[SISMED](https://www.datos.gov.co/Salud-y-Protecci-n-Social/SISMED/3he6-m866)
"""
        )

    return app


# Entry point
if __name__ == "__main__":
    app = create_app()
    app.launch()
