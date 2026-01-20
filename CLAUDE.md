# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MiSalud Entendida is a healthcare literacy app for the MedGemma Impact Challenge (Kaggle, deadline Feb 24, 2026). It uses MedGemma 1.5's document understanding capabilities to help Colombians understand prescriptions, lab results, and medication prices.

**One-line pitch**: Entiende tus recetas y exámenes con IA médica abierta

## Development Commands

The project is in early development. Current setup:

```bash
# Python version requirement
python --version  # Requires 3.11+

# No dependencies configured yet - will need:
# pip install transformers torch gradio requests pillow
```

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

- `PROJECT_SPECS.md` - Product specification, MVP scope, success metrics
- `RESEARCH.md` - Technical details, MedGemma benchmarks, Colombian healthcare context, API documentation
- `ROADMAP.md` - Project timeline with checkboxes for task tracking

## Workflow

- **Update ROADMAP.md after changes are implemented** - Mark checkboxes complete, add progress notes, and log decisions as work is done
