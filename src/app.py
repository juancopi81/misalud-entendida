"""Gradio UI for MiSalud Entendida.

A healthcare literacy app that helps Colombians understand prescriptions,
lab results, and medication prices using MedGemma's document understanding.

Usage:
    uv run python -m src.app
"""

import os
from typing import Any, Callable

import gradio as gr

from src.pipelines import (
    answer_question as answer_document_question,
    analyze_document as analyze_generic_document,
    build_lab_results_output,
    build_prescription_output,
)
from src.inference import get_backend
from src.interactions import Interaction, check_interactions
from src.logger import get_logger, log_timing
from src.models import DocumentChatContext, LabResultExtraction, PrescriptionExtraction

logger = get_logger("src.app")

# Backend configuration
BACKEND_ENV_VAR = "INFERENCE_BACKEND"
SUPPORTED_BACKENDS = ("modal", "transformers")
DEFAULT_BACKEND_MODE = "auto"

# Backends are initialized lazily and cached by name
_backend_cache: dict[str, Any] = {}


def _resolve_backend_order() -> list[str]:
    """Resolve backend order from INFERENCE_BACKEND env var."""
    configured = os.environ.get(BACKEND_ENV_VAR, DEFAULT_BACKEND_MODE).strip().lower()
    if configured == "auto":
        return ["modal", "transformers"]

    if configured in SUPPORTED_BACKENDS:
        return [configured]

    logger.warning(
        "Invalid %s=%r. Supported values: auto, modal, transformers. Falling back to auto.",
        BACKEND_ENV_VAR,
        configured,
    )
    return ["modal", "transformers"]


def _get_backend_instance(backend_name: str) -> Any:
    """Get backend instance by name, lazily initialized and cached."""
    backend = _backend_cache.get(backend_name)
    if backend is None:
        logger.info("Initializing inference backend: %s", backend_name)
        backend = get_backend(backend_name)
        _backend_cache[backend_name] = backend
    return backend


def _run_extraction_with_fallback(
    image_path: str,
    task_label: str,
    method_name: str,
    is_valid_result: Callable[[Any], bool],
) -> Any:
    """Run extraction using configured backend order with graceful fallback."""
    backend_order = _resolve_backend_order()
    errors: list[str] = []

    for backend_name in backend_order:
        try:
            backend = _get_backend_instance(backend_name)
            logger.info("Trying backend=%s for %s", backend_name, task_label)

            with log_timing(logger, f"{task_label}.extract.{backend_name}"):
                result = getattr(backend, method_name)(image_path)

            if is_valid_result(result):
                logger.info("%s extraction succeeded with backend=%s", task_label, backend_name)
                return result

            parse_success = getattr(result, "parse_success", False)
            logger.warning(
                "%s extraction returned invalid result with backend=%s (parse_success=%s)",
                task_label,
                backend_name,
                parse_success,
            )
            errors.append(f"{backend_name}: extracción inválida (parse_success={parse_success})")
        except Exception as exc:
            logger.exception(
                "%s extraction failed with backend=%s: %s", task_label, backend_name, exc
            )
            errors.append(f"{backend_name}: {exc}")

    attempted = ", ".join(backend_order)
    details = " | ".join(errors) if errors else "sin detalles"
    raise RuntimeError(
        f"No se logró extraer información con los backends configurados ({attempted}). "
        f"Detalle: {details}"
    )


# Required disclaimer per CLAUDE.md
DISCLAIMER = """
**Aviso importante**: Esta herramienta es solo para fines educativos.
No reemplaza el consejo de su médico. Siempre consulte a un profesional
de la salud antes de tomar decisiones sobre sus medicamentos.

*No es consejo médico.*
"""


# --- Prescription Tab Functions ---


def analyze_prescription(image_path: str | None) -> tuple[str, str, str, str]:
    """Analyze a prescription image and return formatted results.

    Args:
        image_path: Path to the prescription image

    Returns:
        Tuple of (medications_md, generics_md, prices_md, explanations_md)
    """
    logger.info("Analyze prescription button clicked")
    if not image_path:
        return "Por favor suba una imagen de su receta.", "", "", ""

    try:
        logger.info("Starting prescription analysis: %s", image_path)
        result: PrescriptionExtraction = _run_extraction_with_fallback(
            image_path=image_path,
            task_label="prescription",
            method_name="extract_prescription",
            is_valid_result=lambda r: r.parse_success and bool(r.medicamentos),
        )

        if not result.parse_success or not result.medicamentos:
            logger.warning(
                "Prescription extraction returned no medications (parse_success=%s)",
                result.parse_success,
            )
            return (
                "No se pudieron extraer medicamentos de esta imagen. "
                "Asegúrese de que la imagen sea clara y legible.",
                "",
                "",
                "",
            )

        logger.info("Building prescription pipeline output")
        with log_timing(logger, "prescription.build_output"):
            pipeline_output = build_prescription_output(result, limit=5)

        logger.info("Prescription analysis complete")
        return (
            pipeline_output.medications_markdown,
            pipeline_output.generics_markdown,
            pipeline_output.prices_markdown,
            pipeline_output.explanations_markdown,
        )

    except Exception as e:
        logger.exception("Prescription analysis failed: %s", e)
        return f"Error al analizar la receta: {str(e)}", "", "", ""


# --- Lab Results Tab Functions ---


def analyze_lab_results(image_path: str | None) -> str:
    """Analyze a lab results image and return formatted results.

    Args:
        image_path: Path to the lab results image

    Returns:
        Formatted markdown string with lab results
    """
    logger.info("Analyze lab results button clicked")
    if not image_path:
        return "Por favor suba una imagen de sus resultados de laboratorio."

    try:
        logger.info("Starting lab results analysis: %s", image_path)
        result: LabResultExtraction = _run_extraction_with_fallback(
            image_path=image_path,
            task_label="lab",
            method_name="extract_lab_results",
            is_valid_result=lambda r: r.parse_success and bool(r.resultados),
        )

        if not result.parse_success or not result.resultados:
            logger.warning(
                "Lab extraction returned no results (parse_success=%s)",
                result.parse_success,
            )
            return (
                "No se pudieron extraer resultados de esta imagen. "
                "Asegúrese de que la imagen sea clara y legible."
            )

        logger.info("Building lab results output")
        with log_timing(logger, "lab.build_output"):
            output = build_lab_results_output(result)
        logger.info("Lab results analysis complete")
        return output

    except Exception as e:
        logger.exception("Lab results analysis failed: %s", e)
        return f"Error al analizar los resultados: {str(e)}"


# --- Unified Document + Q&A Functions ---


def analyze_document_with_followups(
    file_path: str | None,
) -> tuple[str, DocumentChatContext | None, list[tuple[str, str]], str]:
    """Analyze a generic medical document and initialize follow-up chat context."""
    logger.info("Analyze unified document button clicked")
    if not file_path:
        return "Por favor suba un documento PDF o una imagen.", None, [], ""

    try:
        logger.info("Starting unified analysis: %s", file_path)
        result = analyze_generic_document(file_path, backend_name=os.environ.get(BACKEND_ENV_VAR, "auto"))
        context = result.to_chat_context()
        return result.report_markdown, context, [], ""
    except Exception as exc:
        logger.exception("Unified document analysis failed: %s", exc)
        return (
            f"Error al analizar el documento: {exc}",
            None,
            [],
            "",
        )


def ask_document_followup(
    question: str,
    history: list[tuple[str, str]] | None,
    context: DocumentChatContext | None,
) -> tuple[list[tuple[str, str]], str]:
    """Answer a follow-up question grounded on the analyzed document context."""
    history = history or []
    question_clean = (question or "").strip()
    if not question_clean:
        return history, ""

    answer = answer_document_question(
        question_clean,
        context,
        backend_name=os.environ.get(BACKEND_ENV_VAR, "auto"),
    )
    history.append((question_clean, answer))
    return history, ""


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
            # --- Unified Document Tab ---
            with gr.Tab("Documento + Preguntas"):
                gr.Markdown("## Analiza un Documento y Haz Preguntas")
                gr.Markdown(
                    "Sube una imagen o PDF con texto digital. "
                    "Después podrás hacer preguntas sobre el documento analizado."
                )

                document_file = gr.File(
                    type="filepath",
                    file_types=[".pdf", ".jpg", ".jpeg", ".png"],
                    label="Documento (PDF o imagen)",
                )
                analyze_document_btn = gr.Button(
                    "Analizar Documento",
                    variant="primary",
                    size="lg",
                )
                unified_report = gr.Markdown(
                    "El reporte unificado aparecerá aquí.",
                    label="Reporte Unificado",
                )

                document_context_state = gr.State(None)
                unified_chatbot = gr.Chatbot(
                    label="Preguntas sobre este documento",
                    height=320,
                )
                with gr.Row():
                    unified_chat_input = gr.Textbox(
                        label="Pregunta de seguimiento",
                        placeholder="Ej: ¿Qué valores están fuera de rango?",
                        scale=4,
                    )
                    unified_chat_send = gr.Button("Enviar", variant="secondary", scale=1)

                analyze_document_btn.click(
                    fn=analyze_document_with_followups,
                    inputs=[document_file],
                    outputs=[
                        unified_report,
                        document_context_state,
                        unified_chatbot,
                        unified_chat_input,
                    ],
                )

                unified_chat_send.click(
                    fn=ask_document_followup,
                    inputs=[unified_chat_input, unified_chatbot, document_context_state],
                    outputs=[unified_chatbot, unified_chat_input],
                )
                unified_chat_input.submit(
                    fn=ask_document_followup,
                    inputs=[unified_chat_input, unified_chatbot, document_context_state],
                    outputs=[unified_chatbot, unified_chat_input],
                )

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
                prescription_explanations = gr.Markdown(
                    "Las explicaciones aparecerán aquí.",
                    label="Explicación en español",
                )

                analyze_prescription_btn.click(
                    fn=analyze_prescription,
                    inputs=[prescription_image],
                    outputs=[
                        prescription_meds,
                        prescription_generics,
                        prescription_prices,
                        prescription_explanations,
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
