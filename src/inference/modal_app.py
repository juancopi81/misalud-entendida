"""Modal inference function for MedGemma on A10G GPU."""

from pathlib import Path
import modal
import os

APP_NAME = "misalud-medgemma"
APP_PATH = Path("/root/app")
MODEL_ID = "google/medgemma-1.5-4b-it"

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


@app.function(
    image=image,
    gpu="A10G",
    timeout=300,
    secrets=[modal.Secret.from_name("huggingface")],
)
def extract_from_image(image_bytes: bytes, prompt: str) -> str:
    """
    Extract information from a medical document image using MedGemma.

    Args:
        image_bytes: Raw bytes of the image file
        prompt: Extraction prompt (Spanish, requesting JSON output)

    Returns:
        Model response (expected to be JSON string)
    """
    import torch
    from transformers import AutoProcessor, AutoModelForImageTextToText
    from PIL import Image
    import io

    from src.prompts import SYSTEM_INSTRUCTION

    # Load model and processor
    hf_token = os.environ.get("HF_TOKEN")

    processor = AutoProcessor.from_pretrained(MODEL_ID, token=hf_token, use_fast=True)
    model = AutoModelForImageTextToText.from_pretrained(
        MODEL_ID,
        token=hf_token,
        dtype=torch.bfloat16,  # Use dtype instead of deprecated torch_dtype
        device_map="auto",
    )

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
    inputs = processor.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    ).to(model.device, dtype=torch.bfloat16)

    # Generate response (increased tokens to handle thinking mode output)
    with torch.inference_mode():
        outputs = model.generate(
            **inputs,
            max_new_tokens=2048,
            do_sample=False,
        )

    # Decode response (skip input tokens)
    input_len = inputs["input_ids"].shape[-1]
    response = processor.decode(outputs[0][input_len:], skip_special_tokens=True)

    # Handle MedGemma 1.5 thinking mode: extract response after <unused95> marker
    # Thinking format: <unused94>thought\n...thinking...<unused95>...actual response...
    if "<unused95>" in response:
        response = response.split("<unused95>", 1)[1].strip()

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
    result = extract_from_image.remote(image_bytes, PRESCRIPTION_PROMPT)

    print("\n--- Extraction Result ---")
    print(result)
    print("-------------------------")
