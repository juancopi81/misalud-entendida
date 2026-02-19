# Evaluation Workspace

This folder contains the Day 1 decision-sprint setup for `SUBMISSION_DECISION_PLAN.md`.

## Files

- `SCORING.md`: fixed scoring protocol and metric formulas.
- `manifest.csv`: document inventory and labeling status tracker.
- `prescriptions_labels.jsonl`: ground-truth labels for prescription extraction.
- `lab_labels.jsonl`: ground-truth labels for lab extraction.

## Day 1 labeling workflow

1. Add all planned documents to `manifest.csv` (target: 20 prescriptions, 10 lab reports).
2. Set `label_status=todo` for new rows.
3. Fill matching JSONL entries with ground truth.
4. Set `label_status=labeled` when an entry is complete.
5. Set `label_status=reviewed` after a second pass.

## Day 2 measurement prerequisites

- At least one complete labeled subset exists for each doc type.
- All rows used for baseline have `label_status=reviewed`.
- Scoring rules in `SCORING.md` are not changed after baseline starts.

## OCRMac workflow for labeling (today's default)

This OCR step is **only for faster local labeling/review on macOS**.
It is **not** part of the production app runtime, CI requirements, or cross-platform setup.

Default loop for each batch:

1. Create or update manual labels in JSONL.
2. Run OCRMac comparison script (prescriptions or labs).
3. Inspect misses in compare report and patch labels if needed.
4. Mark as `reviewed` only after manual reviewer confirmation.

### Prescriptions

```bash
# Run with ephemeral dependency (does not modify pyproject.toml)
uv run --with ocrmac python scripts/compare_prescriptions_ocrmac.py
```

Useful variants:

```bash
# Faster OCR mode
uv run --with ocrmac python scripts/compare_prescriptions_ocrmac.py --recognition-level fast

# Alternate Apple LiveText backend
uv run --with ocrmac python scripts/compare_prescriptions_ocrmac.py --framework livetext
```

Generated outputs:

- `eval/ocrmac_prescriptions_raw.jsonl`: OCR text per prescription image.
- `eval/ocrmac_prescriptions_compare_report.json`: coverage summary + per-document misses.

### Labs

```bash
uv run --with ocrmac python scripts/compare_labs_ocrmac.py
```

Useful variants:

```bash
# Faster OCR mode
uv run --with ocrmac python scripts/compare_labs_ocrmac.py --recognition-level fast

# Include estado string checks (off by default)
uv run --with ocrmac python scripts/compare_labs_ocrmac.py --include-estado
```

Generated outputs:

- `eval/ocrmac_lab_raw.jsonl`: OCR text per lab report (all pages).
- `eval/ocrmac_lab_compare_report.json`: coverage summary + per-document misses.
