# MiSalud Entendida

Entiende recetas y examenes medicos en espanol colombiano usando MedGemma 1.5.

## What this project does

- Extracts medications from prescription images.
- Interprets lab result images in plain Spanish.
- Enriches medications with CUM generic alternatives.
- Adds SISMED reference prices when available.
- Tracks medications in-session and warns about common interactions.
- Adds a unified "Documento + Preguntas" flow (PDF/image -> report -> grounded follow-up chat).

## Current MVP architecture

- UI: Gradio (`src/app.py`)
- Inference backends: Modal (remote) and Transformers (local)
- Data providers: CUM + SISMED clients in `src/api/`
- Domain/pipelines: `src/models.py` and `src/pipelines/`
- Unified orchestrator: `src/io/document_ingestion.py` + `src/pipelines/document_orchestrator.py`

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

## Deploy the Modal backend

If using the Modal inference backend, deploy it before running the app:

```bash
uv run modal deploy src/inference/modal_app.py
```

Redeploy after any changes to `src/inference/modal_app.py` or when rotating the `huggingface` Modal secret.

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
- Scanned PDFs without selectable text are not yet supported in the unified flow (upload as image for now).

## Hybrid MedGemma evaluation note

This repo now includes a hybrid design where MedGemma is used as a verifier/reasoner layer (not only extraction).

- Baseline OCR labeling artifacts are available in:
  - `eval/ocrmac_prescriptions_compare_report.json`
  - `eval/ocrmac_lab_compare_report.json`
- Unified flow logic lives in:
  - `src/pipelines/document_orchestrator.py`
  - `src/pipelines/document_chat.py`

Three representative value-add examples for submission narrative:

1. Ambiguous route handling:
   - Heuristic routing can be uncertain; model fallback classifies document type before parsing.
2. Verification over raw evidence:
   - For noisy text evidence, MedGemma validates/corrects structured JSON before enrichment.
3. Grounded follow-up support:
   - The chat answers from extracted JSON + CUM/SISMED context and explicitly states uncertainty when missing.

## What comes next (app-ready fast path)

Target: keep the current architecture and make the app demo-ready with low operational risk.

1. Reliability gate for the new unified flow:
   - Evaluate at least 20 prescriptions and 10 labs with the orchestrated path.
   - Track route correctness, extraction parse success, and grounded-chat uncertainty behavior.
2. Failure-mode hardening:
   - Validate `pdf_no_text`, `unknown` route, CUM/SISMED outage, and chat-without-context paths in UI.
   - Ensure each path returns clear user-facing guidance (no silent failures).
3. Deployment readiness:
   - Deploy/update Modal backend and run `INFERENCE_BACKEND=auto` smoke tests.
   - Verify the four tabs: `Documento + Preguntas`, `Recetas`, `Exámenes de Laboratorio`, `Mis Medicamentos`.
4. Submission packaging:
   - Build final evidence section "Why MedGemma beyond OCR" with the three concrete failure-to-success examples.
   - Reuse this same evidence in the 3-minute demo and the write-up.

## Documentation hierarchy

- `SUBMISSION_DECISION_PLAN.md` - Source of truth for GO/NO-GO submission decision and pre-packaging sprint.
- `ROADMAP.md` - Current execution status and checklist tracking.
- `PROJECT_SPECS.md` - Product scope and success criteria.
- `RESEARCH.md` - Background research and references (supporting context).
- `docs/adr/0001-inference-runtime-strategy.md` - Runtime strategy decision record.
