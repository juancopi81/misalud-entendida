"""
Centralized prompts for MedGemma medical document extraction.

All LLM prompts and system instructions are defined here for easy maintenance
and consistency across inference backends (Modal, Transformers).
"""

# --- System Instructions ---

SYSTEM_INSTRUCTION = (
    "Eres un asistente médico experto en interpretar documentos médicos "
    "colombianos como recetas, resultados de laboratorio e historias clínicas."
)
"""System instruction for MedGemma. Sets the role as a Colombian medical document expert."""


# --- Extraction Prompts ---

PRESCRIPTION_PROMPT = """Analiza esta imagen de una receta médica colombiana y extrae la información de cada medicamento.
Para cada medicamento, incluye: nombre_medicamento, dosis, frecuencia, duracion, instrucciones.
Responde SOLO con JSON válido en el siguiente formato:
{"medicamentos": [{"nombre_medicamento": "...", "dosis": "...", "frecuencia": "...", "duracion": "...", "instrucciones": "..."}]}"""
"""Prompt for extracting medication data from prescription images.

Expected output: JSON with list of medications containing:
- nombre_medicamento: Drug name
- dosis: Dosage (e.g., "500mg")
- frecuencia: Frequency (e.g., "cada 8 horas")
- duracion: Duration (e.g., "7 días")
- instrucciones: Special instructions
"""

LAB_RESULTS_PROMPT = """Analiza esta imagen de resultados de laboratorio y extrae cada prueba.
Para cada prueba, incluye: nombre_prueba, valor, unidad, rango_referencia, estado (normal/alto/bajo).
Responde SOLO con JSON válido en el siguiente formato:
{"resultados": [{"nombre_prueba": "...", "valor": "...", "unidad": "...", "rango_referencia": "...", "estado": "..."}]}"""
"""Prompt for extracting test results from lab result images.

Expected output: JSON with list of results containing:
- nombre_prueba: Test name
- valor: Measured value
- unidad: Unit of measurement
- rango_referencia: Normal reference range
- estado: Status ("normal", "alto", "bajo")
"""


# --- Validation-Only Prompts ---
# These prompts are used for testing/validation, not part of MVP pipelines.

CLINICAL_RECORD_PROMPT = """Analiza esta imagen de un documento médico colombiano y extrae la información relevante.
Incluye: diagnostico, sintomas, tratamiento, recomendaciones.
Responde SOLO con JSON válido."""
"""Prompt for clinical record extraction.

NOTE: This is used for VALIDATION ONLY (scripts/validate_extraction.py).
Clinical records are not part of MVP scope - no dedicated UI tab or extraction function.
Kept here for consistency and future reference.
"""
