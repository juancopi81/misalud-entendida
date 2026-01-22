"""Modal inference function for MedGemma on A10G GPU."""

import os
from pathlib import Path

import modal

from src.inference.constants import (
    MAX_NEW_TOKENS_DEFAULT,
    MAX_NEW_TOKENS_PRESCRIPTION,
    MODEL_ID,
)

APP_NAME = "misalud-medgemma"
APP_PATH = Path("/root/app")

app = modal.App(APP_NAME)

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
        self.processor = AutoProcessor.from_pretrained(
            MODEL_ID, token=hf_token, use_fast=True
        )
        self.model = AutoModelForImageTextToText.from_pretrained(
            MODEL_ID,
            token=hf_token,
            dtype=torch.bfloat16,  # Use dtype instead of deprecated torch_dtype
            device_map="auto",
        )

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

        from src.inference.utils import extract_json_from_response
        from src.prompts import SYSTEM_INSTRUCTION

        # Load image from bytes
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
        inputs = self.processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        ).to(self.model.device, dtype=torch.bfloat16)

        # Generate response
        with torch.inference_mode():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
            )

        # Decode response (skip input tokens)
        input_len = inputs["input_ids"].shape[-1]
        response = self.processor.decode(outputs[0][input_len:], skip_special_tokens=True)

        # Extract JSON, handling thinking mode gracefully
        return extract_json_from_response(response)


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
