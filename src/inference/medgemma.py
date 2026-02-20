"""MedGemma abstraction layer for prescription and lab result extraction.

Supports multiple backends:
- ModalBackend: Remote GPU inference via Modal A10G (recommended for development)
- TransformersBackend: Local GPU inference (for Kaggle notebooks or local GPU)
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Literal

from src.logger import get_logger, log_timing

from src.inference.constants import (
    MAX_NEW_TOKENS_DEFAULT,
    MAX_NEW_TOKENS_LABS,
    MAX_NEW_TOKENS_PRESCRIPTION,
    MODEL_ID,
)
from src.inference.utils import extract_json_from_response
from src.models import (
    LabResultExtraction,
    PrescriptionExtraction,
)
from src.prompts import (
    LAB_RESULTS_PROMPT,
    PRESCRIPTION_PROMPT,
    SYSTEM_INSTRUCTION,
)

logger = get_logger(__name__)

# --- Backend Abstraction ---


class MedGemmaBackend(ABC):
    """Abstract base class for MedGemma inference backends."""

    @abstractmethod
    def extract_raw(
        self,
        image_path: str | Path,
        prompt: str,
        max_new_tokens: int = MAX_NEW_TOKENS_DEFAULT,
    ) -> str:
        """Run raw extraction and return model response as string."""
        pass

    @abstractmethod
    def generate_text(
        self,
        prompt: str,
        max_new_tokens: int = MAX_NEW_TOKENS_DEFAULT,
    ) -> str:
        """Run text-only generation and return model response as string."""
        pass

    def extract_prescription(self, image_path: str | Path) -> PrescriptionExtraction:
        """Extract prescription data from an image."""
        logger.info("Extracting prescription from %s", image_path)
        raw = self.extract_raw(
            image_path, PRESCRIPTION_PROMPT, max_new_tokens=MAX_NEW_TOKENS_PRESCRIPTION
        )
        logger.debug("Raw response (first 200 chars): %s", raw[:200] if raw else "empty")
        extracted = extract_json_from_response(raw)
        result = PrescriptionExtraction.from_json(extracted)
        result.raw_response = raw
        logger.info(
            "Prescription extraction complete: %d medications, parse_success=%s",
            len(result.medicamentos),
            result.parse_success,
        )
        return result

    def extract_lab_results(self, image_path: str | Path) -> LabResultExtraction:
        """Extract lab results data from an image."""
        logger.info("Extracting lab results from %s", image_path)
        raw = self.extract_raw(
            image_path, LAB_RESULTS_PROMPT, max_new_tokens=MAX_NEW_TOKENS_LABS
        )
        logger.debug("Raw response (first 200 chars): %s", raw[:200] if raw else "empty")
        extracted = extract_json_from_response(raw)
        result = LabResultExtraction.from_json(extracted)
        result.raw_response = raw
        logger.info(
            "Lab results extraction complete: %d results, parse_success=%s",
            len(result.resultados),
            result.parse_success,
        )
        return result


class ModalBackend(MedGemmaBackend):
    """Backend that calls Modal function for remote GPU inference."""

    def extract_raw(
        self,
        image_path: str | Path,
        prompt: str,
        max_new_tokens: int = MAX_NEW_TOKENS_DEFAULT,
    ) -> str:
        """Call deployed Modal function to extract from image."""
        import modal

        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        width = height = None
        try:
            from PIL import Image

            with Image.open(image_path) as img:
                width, height = img.size
        except Exception as exc:
            logger.debug("Failed to read image dimensions: %s", exc)

        image_bytes = image_path.read_bytes()
        logger.debug("Image bytes size: %d", len(image_bytes))
        logger.info(
            "Submitting Modal request (bytes=%d, image=%sx%s, prompt_chars=%d, max_new_tokens=%d)",
            len(image_bytes),
            width if width is not None else "?",
            height if height is not None else "?",
            len(prompt),
            max_new_tokens,
        )
        from .modal_app import APP_NAME, CLS_NAME

        Model = modal.Cls.from_name(APP_NAME, CLS_NAME)
        model = Model()
        with log_timing(logger, "modal.extract_from_image.remote"):
            result = model.extract_from_image.remote(
                image_bytes, prompt, max_new_tokens=max_new_tokens
            )
        logger.info("Modal request finished")
        logger.debug("Modal call complete, response length: %d", len(result) if result else 0)
        return result

    def generate_text(
        self,
        prompt: str,
        max_new_tokens: int = MAX_NEW_TOKENS_DEFAULT,
    ) -> str:
        """Call deployed Modal function for text-only generation."""
        import modal

        from .modal_app import APP_NAME, CLS_NAME

        logger.info(
            "Submitting Modal text request (prompt_chars=%d, max_new_tokens=%d)",
            len(prompt),
            max_new_tokens,
        )
        Model = modal.Cls.from_name(APP_NAME, CLS_NAME)
        model = Model()
        with log_timing(logger, "modal.generate_from_text.remote"):
            result = model.generate_from_text.remote(prompt, max_new_tokens=max_new_tokens)
        logger.info("Modal text request finished")
        logger.debug("Modal text response length: %d", len(result) if result else 0)
        return result


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

        logger.info("Loading MedGemma model: %s", self.model_id)
        with log_timing(logger, "local.load_processor"):
            self._processor = AutoProcessor.from_pretrained(
                self.model_id, token=hf_token, use_fast=True
            )
        with log_timing(logger, "local.load_model"):
            self._model = AutoModelForImageTextToText.from_pretrained(
                self.model_id,
                token=hf_token,
                dtype=torch.bfloat16,  # Use dtype instead of deprecated torch_dtype
                device_map="auto",
            )
        logger.info("Model loaded successfully")

    def extract_raw(
        self,
        image_path: str | Path,
        prompt: str,
        max_new_tokens: int = MAX_NEW_TOKENS_DEFAULT,
    ) -> str:
        """Run local inference to extract from image."""
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

        return self._generate_with_messages(messages, max_new_tokens)

    def generate_text(
        self,
        prompt: str,
        max_new_tokens: int = MAX_NEW_TOKENS_DEFAULT,
    ) -> str:
        """Run local text-only generation."""
        self._load_model()
        messages = [
            {
                "role": "system",
                "content": [{"type": "text", "text": SYSTEM_INSTRUCTION}],
            },
            {
                "role": "user",
                "content": [{"type": "text", "text": prompt}],
            },
        ]
        return self._generate_with_messages(messages, max_new_tokens)

    def _generate_with_messages(
        self,
        messages: list[dict],
        max_new_tokens: int,
    ) -> str:
        """Generate model output from already-formatted chat messages."""
        import torch

        # Process input (cast to bfloat16 per official docs)
        inputs = self._processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        ).to(self._model.device, dtype=torch.bfloat16)

        # Generate response
        with torch.inference_mode():
            outputs = self._model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
            )

        input_len = inputs["input_ids"].shape[-1]
        response = self._processor.decode(
            outputs[0][input_len:], skip_special_tokens=True
        )
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
