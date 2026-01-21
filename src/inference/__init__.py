"""MedGemma inference module for prescription and lab result extraction."""

from .medgemma import (
    MODEL_ID,
    MedGemmaBackend,
    ModalBackend,
    TransformersBackend,
    get_backend,
)

# Re-export models and prompts for backward compatibility
from src.models import (
    MedicationItem,
    PrescriptionExtraction,
    LabResultItem,
    LabResultExtraction,
)
from src.prompts import (
    SYSTEM_INSTRUCTION,
    PRESCRIPTION_PROMPT,
    LAB_RESULTS_PROMPT,
)

__all__ = [
    # Constants
    "MODEL_ID",
    # Prompts
    "SYSTEM_INSTRUCTION",
    "PRESCRIPTION_PROMPT",
    "LAB_RESULTS_PROMPT",
    # Models
    "MedicationItem",
    "PrescriptionExtraction",
    "LabResultItem",
    "LabResultExtraction",
    # Backends
    "MedGemmaBackend",
    "ModalBackend",
    "TransformersBackend",
    "get_backend",
]
