"""MedGemma abstraction layer for prescription and lab result extraction.

Supports multiple backends:
- ModalBackend: Remote GPU inference via Modal A10G (recommended for development)
- TransformersBackend: Local GPU inference (for Kaggle notebooks or local GPU)
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Literal

from src.models import (
    LabResultExtraction,
    PrescriptionExtraction,
)
from src.prompts import (
    LAB_RESULTS_PROMPT,
    PRESCRIPTION_PROMPT,
    SYSTEM_INSTRUCTION,
)

# --- Constants ---

MODEL_ID = "google/medgemma-1.5-4b-it"


# --- Backend Abstraction ---


class MedGemmaBackend(ABC):
    """Abstract base class for MedGemma inference backends."""

    @abstractmethod
    def extract_raw(self, image_path: str | Path, prompt: str) -> str:
        """Run raw extraction and return model response as string."""
        pass

    def extract_prescription(self, image_path: str | Path) -> PrescriptionExtraction:
        """Extract prescription data from an image."""
        raw = self.extract_raw(image_path, PRESCRIPTION_PROMPT)
        return PrescriptionExtraction.from_json(raw)

    def extract_lab_results(self, image_path: str | Path) -> LabResultExtraction:
        """Extract lab results data from an image."""
        raw = self.extract_raw(image_path, LAB_RESULTS_PROMPT)
        return LabResultExtraction.from_json(raw)


class ModalBackend(MedGemmaBackend):
    """Backend that calls Modal function for remote GPU inference."""

    def extract_raw(self, image_path: str | Path, prompt: str) -> str:
        """Call Modal function to extract from image."""
        from .modal_app import extract_from_image

        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        image_bytes = image_path.read_bytes()
        return extract_from_image.remote(image_bytes, prompt)


class TransformersBackend(MedGemmaBackend):
    """Backend for direct local GPU inference using transformers.

    Use this for Kaggle notebooks or machines with local GPU access.
    Requires: CUDA-enabled GPU, HF_TOKEN environment variable.
    """

    def __init__(self, model_id: str = MODEL_ID):
        self.model_id = model_id
        self._model = None
        self._processor = None

    def _load_model(self):
        """Lazy load model and processor."""
        if self._model is not None:
            return

        import os

        import torch
        from transformers import AutoModelForImageTextToText, AutoProcessor

        hf_token = os.environ.get("HF_TOKEN")
        if not hf_token:
            raise ValueError(
                "HF_TOKEN environment variable required for MedGemma access"
            )

        self._processor = AutoProcessor.from_pretrained(
            self.model_id, token=hf_token, use_fast=True
        )
        self._model = AutoModelForImageTextToText.from_pretrained(
            self.model_id,
            token=hf_token,
            dtype=torch.bfloat16,  # Use dtype instead of deprecated torch_dtype
            device_map="auto",
        )

    def extract_raw(self, image_path: str | Path, prompt: str) -> str:
        """Run local inference to extract from image."""
        import torch
        from PIL import Image

        self._load_model()

        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        pil_image = Image.open(image_path).convert("RGB")

        # Format conversation following official docs (system + user with text before image)
        messages = [
            {
                "role": "system",
                "content": [{"type": "text", "text": SYSTEM_INSTRUCTION}],
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image", "image": pil_image},
                ],
            },
        ]

        # Process input (cast to bfloat16 per official docs)
        inputs = self._processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        ).to(self._model.device, dtype=torch.bfloat16)

        # Generate response (increased tokens to handle thinking mode output)
        with torch.inference_mode():
            outputs = self._model.generate(
                **inputs,
                max_new_tokens=2048,
                do_sample=False,
            )

        input_len = inputs["input_ids"].shape[-1]
        response = self._processor.decode(
            outputs[0][input_len:], skip_special_tokens=True
        )

        # Handle MedGemma 1.5 thinking mode: extract response after <unused95> marker
        # Thinking format: <unused94>thought\n...thinking...<unused95>...actual response...
        if "<unused95>" in response:
            response = response.split("<unused95>", 1)[1].strip()

        return response


# --- Factory ---

BackendType = Literal["modal", "transformers"]


def get_backend(backend_type: BackendType = "modal") -> MedGemmaBackend:
    """Factory function to get the appropriate backend.

    Args:
        backend_type: "modal" for remote GPU via Modal, "transformers" for local GPU

    Returns:
        MedGemmaBackend instance
    """
    if backend_type == "modal":
        return ModalBackend()
    elif backend_type == "transformers":
        return TransformersBackend()
    else:
        raise ValueError(f"Unknown backend type: {backend_type}")
