"""MedGemma inference module for prescription and lab result extraction."""

from .constants import MODEL_ID
from .medgemma import (
    MedGemmaBackend,
    ModalBackend,
    TransformersBackend,
    get_backend,
)

__all__ = [
    # Constants
    "MODEL_ID",
    # Backends
    "MedGemmaBackend",
    "ModalBackend",
    "TransformersBackend",
    "get_backend",
]
