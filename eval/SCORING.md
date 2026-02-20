# Evaluation Scoring Protocol

Last updated: 2026-02-18
Owner: submission decision sprint

This protocol defines the exact scoring rules for the GO/NO-GO gate in `SUBMISSION_DECISION_PLAN.md`.

## Freeze rules

1. Do not change formulas after baseline measurement starts.
2. If a formula must change, reset baseline and note the change reason in this file.
3. Use the same labeled set for baseline and post-fix reruns.

## Normalization rules

Apply before any comparison:

1. Uppercase text.
2. Trim extra spaces.
3. Remove accents only for matching (`METFORMINA` equals `METFORMINA`).
4. Keep numeric separators normalized (`5,0` equals `5.0`).
5. Ignore punctuation-only differences.

## Prescription accuracy metric

Goal threshold: `>= 85%`

### Per-document prescription score

For each prescription document:

1. Match predicted medications to ground-truth medications by normalized medication name.
2. Compute `name_recall = matched_ground_truth_medications / total_ground_truth_medications`.
3. For matched medications, score fields:
   - `dosis`
   - `frecuencia`
   - `duracion`
   - `instrucciones`
4. Field score is binary (`1` if normalized exact match, else `0`).
5. Compute `attribute_accuracy = correct_attribute_fields / total_attribute_fields`.
6. Document score:

`prescription_doc_score = 0.70 * name_recall + 0.30 * attribute_accuracy`

### Dataset prescription accuracy

`prescription_accuracy = mean(prescription_doc_score across all prescription docs) * 100`

## Lab extraction accuracy metric

Goal threshold: `>= 75%`

### Per-document lab score

For each lab document:

1. Match predicted lab tests to ground-truth tests by normalized `nombre_prueba`.
2. Compute `test_recall = matched_ground_truth_tests / total_ground_truth_tests`.
3. For matched tests, score fields:
   - `valor` (`1` if equal after normalization or numeric difference <= 2%)
   - `unidad` (`1` if normalized exact match)
   - `rango_referencia` (`1` if normalized exact match when present in ground truth)
   - `estado` (`1` if normalized exact match)
4. Compute `lab_field_accuracy = correct_lab_fields / total_lab_fields`.
5. Document score:

`lab_doc_score = 0.60 * test_recall + 0.40 * lab_field_accuracy`

### Dataset lab accuracy

`lab_accuracy = mean(lab_doc_score across all lab docs) * 100`

## End-to-end pipeline success rate

Goal threshold: `>= 90%`

A run is `success=1` only if all are true:

1. No unhandled exception.
2. Structured parse succeeds (`parse_success=true` or equivalent).
3. At least one valid extracted item exists (medication or lab test).

Formula:

`pipeline_success_rate = successful_runs / total_runs * 100`

## Reliability run gate

Goal threshold: `5/5` stable runs.

For Day 4 reliability:

1. Execute 5 consecutive end-to-end demos.
2. All 5 must satisfy `success=1`.
3. No manual restart or code change between runs.

## Offline/local evidence gate

Goal threshold: at least one reproducible local/offline run documented.

Minimum evidence:

1. Backend mode used (`INFERENCE_BACKEND=transformers` or equivalent).
2. Command executed.
3. Hardware/environment note.
4. Measured latency for one full run.

## Standout proof gate

Goal threshold: at least 2 documented proofs.

A proof is valid only if it includes:

1. Example input reference (`doc_id` from `manifest.csv`).
2. Before/after or measured output evidence.
3. Short interpretation of why this is differentiation-relevant.
