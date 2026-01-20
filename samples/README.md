# Sample Medical Documents

Anonymized Colombian medical documents for testing MedGemma extraction pipelines.

**All personally identifiable information (PII) has been redacted.**

## Contents

### prescriptions/
- `receta_dermatologia_2025.jpeg` - Dermatology prescription with 2 medications

### clinical_records/
- `historia_clinica_sueno_2025.jpeg` - Sleep clinic record with diagnosis and treatment plan

## Usage

These samples are used for:
1. Smoke testing the MedGemma extraction pipeline
2. Validating Spanish medical document parsing
3. Demo/competition submission

```bash
# Test prescription extraction (once pipeline is built)
uv run python -m src.inference.medgemma samples/prescriptions/receta_dermatologia_2025.jpeg
```

## Privacy Notice

These documents have been manually reviewed and anonymized:
- Patient names: redacted
- Document/ID numbers: redacted
- Institution identifiers: redacted
- Healthcare provider names: redacted

Only clinical content (medications, diagnoses, instructions) remains visible.
