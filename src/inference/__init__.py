"""MedGemma inference module for prescription and lab result extraction."""

from .medgemma import (
    MODEL_ID,
    SYSTEM_INSTRUCTION,
    PRESCRIPTION_PROMPT,
    LAB_RESULTS_PROMPT,
    MedicationItem,
    PrescriptionExtraction,
    LabResultItem,
    LabResultExtraction,
    MedGemmaBackend,
    ModalBackend,
    TransformersBackend,
    get_backend,
)

__all__ = [
    "MODEL_ID",
    "SYSTEM_INSTRUCTION",
    "PRESCRIPTION_PROMPT",
    "LAB_RESULTS_PROMPT",
    "MedicationItem",
    "PrescriptionExtraction",
    "LabResultItem",
    "LabResultExtraction",
    "MedGemmaBackend",
    "ModalBackend",
    "TransformersBackend",
    "get_backend",
]
