# Submission Decision Plan (Go/No-Go First)

> Last updated: 2026-02-18  
> Competition deadline: 2026-02-24 11:59 PM UTC

## Purpose

Decide whether to invest time in the final submission package (video + write-up) based on evidence, not intuition.

This document is the source of truth for:

1. The decision sprint before submission packaging.
2. The quantitative gate to decide `GO` or `NO-GO`.
3. The minimum evidence needed to stand out.

## Decision Rule

Do not start video/write-up work until the `GO/NO-GO` gate is evaluated.

Submit only if all gate thresholds are met.

## Scope Freeze (for the decision sprint)

Keep the current differentiators only:

1. MedGemma document understanding for prescriptions + lab reports.
2. Colombian enrichment via CUM/SISMED.
3. Spanish-first patient explanations.
4. Medication interaction warnings.

Avoid net-new features during this sprint unless they directly increase gate metrics.

## Decision Sprint (2026-02-18 to 2026-02-21)

### Day 1 - Scope + Evaluation Setup (2026-02-18)

1. Freeze feature scope.
2. Define labeled evaluation protocol.
3. Prepare sample sets:
   - 20 prescriptions (anonymized)
   - 10 lab reports (anonymized)
4. Define exact scoring fields for extraction accuracy.

### Day 2 - Baseline Measurement (2026-02-19)

1. Run full evaluation on the frozen baseline.
2. Record:
   - Prescription extraction accuracy
   - Lab extraction accuracy
   - End-to-end pipeline success rate
3. Log top failure modes by frequency.

### Day 3 - High-Impact Fixes (2026-02-20)

1. Fix only the top 2-3 failure modes.
2. Rerun the same full evaluation.
3. Capture before/after deltas with concrete examples.

### Day 4 - Judge-Style Readiness Review (2026-02-21)

1. Execute a reliability run (5 consecutive end-to-end demos).
2. Validate one local/offline inference path with measured latency.
3. Score against competition criteria using evidence from this sprint.
4. Apply `GO/NO-GO` gate.

## GO/NO-GO Gate (must all pass)

1. Prescription extraction accuracy `>= 85%` on the defined eval set.
2. Lab extraction accuracy `>= 75%` on the defined eval set.
3. End-to-end demo success `>= 90%`.
4. Reliability run passes (`5/5` stable runs).
5. At least one reproducible local/offline run documented.
6. At least 2 concrete standout proofs documented (examples below).

## Standout Proofs (minimum 2 required)

Examples that count:

1. Before/after extraction improvement on real Colombian documents.
2. Demonstrated price/generic enrichment utility (CUM/SISMED) on real cases.
3. Clear safety framing with stable failure handling and disclaimers.
4. Verified local/offline run in constrained setup.

Claims without evidence do not count.

## If GO: Packaging Window (2026-02-22 to 2026-02-24)

### 2026-02-22

1. Draft write-up directly from evaluation evidence.
2. Add figures/tables from measured results.

### 2026-02-23

1. Record final 3-minute demo from the stable flow.
2. Edit for clarity and rubric alignment.

### 2026-02-24

1. Final QA of package requirements.
2. Submit before 11:59 PM UTC.

## If NO-GO

Do not spend time on write-up/video for this cycle.  
Keep a short retrospective with the top blockers and next iteration plan.
