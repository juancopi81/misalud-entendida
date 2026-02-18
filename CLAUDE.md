# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MiSalud Entendida is a healthcare literacy app for the MedGemma Impact Challenge (Kaggle, deadline Feb 24, 2026, 11:59 PM UTC). It uses MedGemma 1.5's document understanding capabilities to help Colombians understand prescriptions, lab results, and medication prices.

**One-line pitch**: Entiende tus recetas y exámenes con IA médica abierta

## Development Commands

This project uses `uv` for dependency management. **Always use `uv`, never `pip`**.

```bash
# Install dependencies
uv sync

# Add a new dependency
uv add <package>

# Add a dev dependency
uv add --dev <package>

# Run Python with project dependencies
uv run python <script.py>

# Run a module
uv run python -m <module>
```

Python version: 3.11+ (managed via `.python-version`)

## Architecture

**Offline-First Design** targeting low-resource devices (4GB RAM laptops, budget Android phones):

```
User Device (Offline)
├── Gradio UI (Spanish-first)
├── MedGemma 1.5 4B Q4 (local inference, 2.5GB quantized)
└── Session-only storage (no persistent data)

Optional Online Features:
├── CUM API (drug validation/generics) - datos.gov.co/resource/i7cb-raxc.json
└── SISMED API (price lookup) - datos.gov.co/resource/3he6-m866.json
```

**Core Pipelines**:
1. **Prescription**: Image → MedGemma extraction → CUM validation → SISMED price lookup → Spanish explanation + generic alternatives
2. **Lab Results**: Image → MedGemma extraction → JSON parsing → Normal range comparison → Plain-language interpretation
3. **Drug Interactions**: Hardcoded warnings for common dangerous combinations (warfarin+aspirin, metformin+alcohol, etc.)

## Key Technical Details

- **Model**: MedGemma 1.5 4B-IT with Q4 quantization (2.5GB GGUF) via llama.cpp or Ollama
- **Target inference**: 30-60 seconds on CPU for edge deployment
- **UI**: Gradio for rapid prototyping
- **APIs**: SODA/Socrata for Colombian government health data

## Design Principles

1. **Spanish-first**: All UI and explanations in Colombian Spanish. Medical terms translated to plain language.
2. **Offline-first**: Core functionality without internet. Only price lookups need connectivity.
3. **Privacy by design**: No data leaves device. No user accounts. Session-only storage.
4. **Low-resource**: Target 4GB RAM devices with quantized models.

## Required Disclaimers

All outputs must include: "No es consejo médico" / "Esta herramienta es solo para ayudarle a entender sus documentos. No reemplaza el consejo de su médico."

## Key Documentation

- `SUBMISSION_DECISION_PLAN.md` - Primary source of truth for GO/NO-GO submission gate and decision sprint (must pass before video/write-up)
- `ROADMAP.md` - Current status and checklist tracking
- `PROJECT_SPECS.md` - Product specification and scope
- `RESEARCH.md` - Background references and technical context

## Logging

Use `src/logger.py` for all operational logging. Never use `print()` for logs.

```python
from src.logger import get_logger, log_timing, timed

logger = get_logger(__name__)

# Standard logging
logger.info("Processing prescription...")
logger.debug("Raw response: %s", response[:100])
logger.warning("API returned empty results")
logger.error("Failed to parse JSON: %s", str(e))

# Timing a code block
with log_timing(logger, "load_model"):
    model = load_model()

# Timing a function (decorator)
@timed(logger, "extract_medications")
def extract_medications(image):
    ...
```

**When to use what:**
- `logger.*` → Operational logs (API calls, processing steps, errors) - goes to stderr
- `print()` → User-facing CLI output only (script results, progress) - goes to stdout

Set log level via environment: `LOG_LEVEL=DEBUG uv run python ...`

## Workflow

- **Update ROADMAP.md after changes are implemented** - Mark checkboxes complete, add progress notes, and log decisions as work is done
- **For submission work, use `SUBMISSION_DECISION_PLAN.md` as gate** - Do not start packaging assets until GO criteria pass
