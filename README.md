# MiSalud Entendida

Entiende recetas y examenes medicos en espanol colombiano usando MedGemma 1.5.

## What this project does

- Extracts medications from prescription images.
- Interprets lab result images in plain Spanish.
- Enriches medications with CUM generic alternatives.
- Adds SISMED reference prices when available.
- Tracks medications in-session and warns about common interactions.

## Current MVP architecture

- UI: Gradio (`src/app.py`)
- Inference backends: Modal (remote) and Transformers (local)
- Data providers: CUM + SISMED clients in `src/api/`
- Domain/pipelines: `src/models.py` and `src/pipelines/`

FastAPI is currently deferred for MVP. The active runtime is Gradio + pipeline modules.

## Requirements

- Python 3.11+
- `uv`
- Optional for Modal backend:
  - Modal auth configured (`modal token new`)
  - Modal secret `huggingface` with `HF_TOKEN`
- Optional for local Transformers backend:
  - `HF_TOKEN` environment variable
  - Local hardware capable of loading MedGemma

## Setup

```bash
uv sync --all-groups
```

## Deploy Modal backend

Required once, and after any changes to `src/inference/modal_app.py`:

```bash
uv run modal deploy src/inference/modal_app.py
```

> **Note**: Adding or rotating the `huggingface` secret in Modal also requires a redeploy for running containers to pick it up.

## Run the app

```bash
uv run python main.py
```

or

```bash
uv run python -m src.app
```

## Inference backend configuration

Use `INFERENCE_BACKEND` to control backend selection.

- `auto` (default): tries `modal`, then falls back to `transformers`
- `modal`: uses only Modal backend
- `transformers`: uses only local Transformers backend

Examples:

```bash
INFERENCE_BACKEND=auto uv run python main.py
INFERENCE_BACKEND=modal uv run python main.py
INFERENCE_BACKEND=transformers uv run python main.py
```

## Validation and quality checks

```bash
uv run ruff check .
uv run pytest
```

## Testing scripts

```bash
uv run python scripts/validate_extraction.py
uv run python scripts/validate_drug_matcher.py --all
```

## Important limitations

- This is not medical advice.
- Handwritten prescriptions are less reliable.
- SISMED prices are historical reference data, not real-time pharmacy prices.
- CUM/SISMED availability can vary; the app now degrades gracefully when one provider is unavailable.

## Key docs

- `SUBMISSION_DECISION_PLAN.md` - Source of truth for GO/NO-GO submission decision and pre-packaging sprint
- `PROJECT_SPECS.md`
- `ROADMAP.md`
- `RESEARCH.md`
- `docs/adr/0001-inference-runtime-strategy.md`
