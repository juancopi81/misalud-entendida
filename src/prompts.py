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
TU RESPUESTA DEBE SER UN UNICO OBJETO JSON. Debe comenzar con "{" y terminar con "}".
No incluyas razonamiento, pasos, ni explicaciones. No uses markdown. No agregues texto extra.
Si no sigues el formato exacto, la respuesta es invalida.
Para cada prueba, incluye: nombre_prueba, valor, unidad, rango_referencia, estado (normal/alto/bajo).
Formato exacto:
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


# --- Unified Flow Prompts ---

DOC_TYPE_CLASSIFIER_PROMPT = """Clasifica el siguiente documento médico colombiano.
Debes responder SOLO con un objeto JSON válido y nada más.

Opciones de document_type:
- "prescription" (receta médica)
- "lab" (resultado/examen de laboratorio)
- "unknown" (no se puede determinar)

Incluye confidence como número entre 0 y 1 y una razón breve.
Formato exacto:
{{"document_type":"prescription|lab|unknown","confidence":0.0,"reason":"..."}}

Evidencia de texto detectada:
{evidence_text}
"""

PRESCRIPTION_VERIFY_PROMPT = """Analiza este documento y valida/corrige la extracción de receta.
Usa la imagen y también la evidencia de texto detectada para resolver ambigüedades.
Si un campo no es confiable, déjalo como cadena vacía.

Responde SOLO con un único JSON válido y nada más:
{{"medicamentos":[{{"nombre_medicamento":"...","dosis":"...","frecuencia":"...","duracion":"...","instrucciones":"..."}}]}}

Pistas de contexto:
- tipo_sugerido: {route_hint}
- evidencia_texto:
{evidence_text}
"""

LAB_VERIFY_PROMPT = """Analiza este documento y valida/corrige la extracción de laboratorio.
Usa la imagen y también la evidencia de texto detectada para resolver ambigüedades.
Si un campo no es confiable, déjalo como cadena vacía.

Responde SOLO con un único JSON válido y nada más:
{{"resultados":[{{"nombre_prueba":"...","valor":"...","unidad":"...","rango_referencia":"...","estado":"normal|alto|bajo|"}}]}}

Pistas de contexto:
- tipo_sugerido: {route_hint}
- evidencia_texto:
{evidence_text}
"""

FOLLOWUP_GROUNDED_QA_PROMPT = """Eres un asistente para explicar documentos médicos.
Reglas obligatorias:
1) Responde SOLO usando el CONTEXTO.
2) Si no está en el contexto, responde: "No se puede confirmar con la información disponible."
3) No inventes diagnósticos ni cambies tratamientos/dosis.
4) Si la pregunta pide diagnóstico o ajuste de tratamiento, rechaza y sugiere consultar al médico.
5) Responde en español claro y breve.
6) Cierra con: "Esta herramienta es educativa y no reemplaza el consejo médico."

CONTEXTO:
{context_payload}

PREGUNTA:
{question}
"""
