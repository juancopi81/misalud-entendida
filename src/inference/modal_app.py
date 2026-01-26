"""Modal inference function for MedGemma on A10G GPU."""

import os
from pathlib import Path

import modal

from src.inference.constants import (
    MAX_NEW_TOKENS_DEFAULT,
    MAX_NEW_TOKENS_PRESCRIPTION,
    MODEL_ID,
)
from src.logger import get_logger, log_timing

APP_NAME = "misalud-medgemma"
APP_PATH = Path("/root/app")

app = modal.App(APP_NAME)
logger = get_logger(__name__)

# Build image with uv for dependency management
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("uv")
    .workdir(APP_PATH)
    .add_local_file("pyproject.toml", str(APP_PATH / "pyproject.toml"), copy=True)
    .add_local_file("uv.lock", str(APP_PATH / "uv.lock"), copy=True)
    .add_local_dir("src", str(APP_PATH / "src"), copy=True)
    .env({"UV_PROJECT_ENVIRONMENT": "/usr/local"})
    .run_commands("uv sync --frozen --compile-bytecode --python-preference=only-system")
)


@app.cls(
    image=image,
    gpu="A10G",
    timeout=300,
    secrets=[modal.Secret.from_name("huggingface")],
    min_containers=1,
)
class MedGemmaModel:
    """Warm-started MedGemma container to avoid reloading on each call."""

    @modal.enter()
    def setup(self):
        import torch
        from transformers import AutoModelForImageTextToText, AutoProcessor

        hf_token = os.environ.get("HF_TOKEN")
        logger.info("Loading MedGemma model in Modal: %s", MODEL_ID)
        with log_timing(logger, "modal.setup.load_processor"):
            self.processor = AutoProcessor.from_pretrained(
                MODEL_ID, token=hf_token, use_fast=True
            )
        with log_timing(logger, "modal.setup.load_model"):
            self.model = AutoModelForImageTextToText.from_pretrained(
                MODEL_ID,
                token=hf_token,
                dtype=torch.bfloat16,  # Use dtype instead of deprecated torch_dtype
                device_map="auto",
            )
        logger.info("Modal model ready")

    @modal.method()
    def extract_from_image(
        self, image_bytes: bytes, prompt: str, max_new_tokens: int = MAX_NEW_TOKENS_DEFAULT
    ) -> str:
        """
        Extract information from a medical document image using MedGemma.

        Args:
            image_bytes: Raw bytes of the image file
            prompt: Extraction prompt (Spanish, requesting JSON output)
            max_new_tokens: Generation limit (task-specific)

        Returns:
            Model response (expected to be JSON string)
        """
        import io

        import torch
        from PIL import Image

        from src.prompts import SYSTEM_INSTRUCTION

        logger.info(
            "Modal extract_from_image start (bytes=%d, max_new_tokens=%d)",
            len(image_bytes),
            max_new_tokens,
        )

        # Load image from bytes
        with log_timing(logger, "modal.extract.decode_image"):
            pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        # Format conversation for MedGemma (following official docs structure)
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
        with log_timing(logger, "modal.extract.apply_chat_template"):
            inputs = self.processor.apply_chat_template(
                messages,
                add_generation_prompt=True,
                tokenize=True,
                return_dict=True,
                return_tensors="pt",
            ).to(self.model.device, dtype=torch.bfloat16)

        # Generate response
        with torch.inference_mode():
            with log_timing(logger, "modal.extract.generate"):
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    do_sample=False,
                )

        # Decode response (skip input tokens)
        input_len = inputs["input_ids"].shape[-1]
        output_tokens = outputs[0].shape[-1] - input_len
        logger.info(
            "Modal tokens (input=%d, output=%d)", input_len, max(output_tokens, 0)
        )
        with log_timing(logger, "modal.extract.decode_output"):
            response = self.processor.decode(
                outputs[0][input_len:], skip_special_tokens=True
            )
        logger.debug("Raw response (head): %s", response[:500])
        if len(response) > 500:
            logger.debug("Raw response (tail): %s", response[-300:])

        logger.info("Modal response size (raw=%d)", len(response))
        return response


@app.local_entrypoint()
def main():
    """Test the extraction function with a sample prescription image."""
    from src.prompts import PRESCRIPTION_PROMPT

    # Read sample image
    sample_path = Path(__file__).parent.parent.parent / "samples" / "prescriptions" / "receta_dermatologia_2025.jpeg"

    if not sample_path.exists():
        print(f"Sample image not found at: {sample_path}")
        return

    print(f"Reading image from: {sample_path}")
    image_bytes = sample_path.read_bytes()

    print("Calling Modal function (this may take a while on first run due to model download)...")
    model = MedGemmaModel()
    result = model.extract_from_image.remote(
        image_bytes,
        PRESCRIPTION_PROMPT,
        max_new_tokens=MAX_NEW_TOKENS_PRESCRIPTION,
    )

    print("\n--- Extraction Result ---")
    print(result)
    print("-------------------------")
