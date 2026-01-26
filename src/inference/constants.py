"""Shared constants for MedGemma inference.

Single source of truth for model configuration and token limits.
Imported by both medgemma.py (client-side) and modal_app.py (remote GPU).
"""

MODEL_ID = "google/medgemma-1.5-4b-it"

# Task-specific defaults (keep conservative for latency, adjust if truncation appears)
MAX_NEW_TOKENS_PRESCRIPTION = 2048
MAX_NEW_TOKENS_LABS = 6144
MAX_NEW_TOKENS_DEFAULT = 2048
