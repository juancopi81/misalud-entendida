# MiSalud Entendida - Project ROADMAP

> **Deadline**: February 24, 2026, 11:59 PM UTC
> **Team**: 2 people (~15-20 hrs/week each)
> **Competition**: MedGemma Impact Challenge (Kaggle)
> **Decision gate first**: Follow `SUBMISSION_DECISION_PLAN.md` and complete GO/NO-GO before video/write-up packaging

---

## Phase 1: De-risk (Week 1: Jan 20-26)
**Goal**: Validate all technical unknowns before building. Both tracks must pass.

### Track A: APIs & Data (Person 1)
| Status | Task | Notes |
|--------|------|-------|
| [x] | Test CUM API query | `datos.gov.co/resource/i7cb-raxc.json` - works, ~35k+ products |
| [x] | Test SISMED API query | `datos.gov.co/resource/3he6-m866.json` - works, data from 2019 |
| [x] | Document API response formats | Documented in src/api/*.py docstrings |
| [x] | Create `src/api/cum.py` stub | `search_by_active_ingredient()`, `find_generics()` |
| [x] | Create `src/api/sismed.py` stub | `get_price_by_expediente()`, `get_price_range()` |

### Track B: MedGemma Inference (Person 2)
| Status | Task | Notes |
|--------|------|-------|
| [x] | Set up Modal inference backend | `src/inference/modal_app.py` - A10G GPU |
| [x] | Create `src/inference/medgemma.py` | Abstraction layer with ModalBackend + TransformersBackend |
| [x] | Create validation script | `scripts/validate_extraction.py` |
| [x] | Test on 1 prescription image | ✅ Extracted 2 medications correctly |
| [x] | Test on 1 clinical record image | ✅ Extracted diagnosis, symptoms, treatment |
| [x] | Evaluate extraction quality | GO - see results below |

### Phase 1 Checkpoint ✓
- [x] **GO/NO-GO**: CUM API returns drug data ✅ Confirmed
- [x] **GO/NO-GO**: SISMED API returns price data ✅ Confirmed (note: data from 2019)
- [x] **GO/NO-GO**: MedGemma extracts readable text from images ✅ Confirmed (prescription + clinical record)

---

## Phase 2: Core Build (Weeks 2-3: Jan 27 - Feb 9)
**Goal**: Build working app with all core features.

### Track A: Backend/Pipelines (Person 1)
| Status | Task | Depends On |
|--------|------|------------|
| [x] | Prescription extraction pipeline | MedGemma extraction → pipeline output wired in app |
| [x] | Lab results interpretation pipeline | Phase 1 complete |
| [x] | CUM integration (generic alternatives) | Pipeline uses match_drug_to_cum → find_generics |
| [x] | SISMED integration (price lookup) | Pipeline uses get_price_by_expediente + get_price_range |
| [x] | Drug interaction checker | src/interactions.py - 20+ common interactions |
| [~] | Spanish explanation generator | Template-based explanations in pipeline |

### Track B: UI/UX (Person 2)
| Status | Task | Depends On |
|--------|------|------------|
| [x] | Gradio app skeleton | None |
| [x] | Prescription tab (upload + display) | None |
| [x] | Lab results tab (upload + display) | None |
| [x] | Medication tracker tab | None |
| [x] | Spanish labels and copy | None |
| [x] | Disclaimers ("No es consejo médico") | None |
| [ ] | Mobile-friendly styling | None |

### Integration Point (End of Week 3)
- [x] Connect UI to backend pipelines
- [ ] End-to-end test: photo → explanation + price
- [ ] Fix integration bugs

---

## Phase 3: Polish & Submit (Weeks 4-5: Feb 10-24)
**Goal**: Run GO/NO-GO decision sprint first (`SUBMISSION_DECISION_PLAN.md`), then package and submit only if GO.

### Track A: Testing & Quality (Person 1)
| Status | Task | Notes |
|--------|------|-------|
| [ ] | Test 20 real prescriptions | GO gate target set in `SUBMISSION_DECISION_PLAN.md` |
| [ ] | Test 10 real lab results | GO gate target set in `SUBMISSION_DECISION_PLAN.md` |
| [ ] | Fix extraction edge cases | Based on test results |
| [ ] | Validate Spanish with native speaker | Quality check |
| [ ] | Performance optimization | If needed |

### Track B: Submission Materials (Person 2)
| Status | Task | Notes |
|--------|------|-------|
| [ ] | Evaluate GO/NO-GO gate | Must pass `SUBMISSION_DECISION_PLAN.md` thresholds before packaging |
| [ ] | Script 3-min demo video | Use demo script from PROJECT_SPECS.md |
| [ ] | Record demo video | Screen recording + narration |
| [ ] | Write 3-page technical doc | Use template structure |
| [ ] | Create Kaggle notebook | Reproducible inference |
| [ ] | Choose competition track | Main vs special award |

### Final Submission Checklist
- [ ] GO gate passed (`SUBMISSION_DECISION_PLAN.md`)
- [ ] Video uploaded (≤3 min)
- [ ] Write-up complete (≤3 pages)
- [ ] Code reproducible on Kaggle
- [ ] Submitted before Feb 24, 2026 11:59 PM UTC

---

## Quick Links
- [SUBMISSION_DECISION_PLAN.md](./SUBMISSION_DECISION_PLAN.md) - GO/NO-GO decision sprint and submission gate
- [PROJECT_SPECS.md](./PROJECT_SPECS.md) - Product specification
- [RESEARCH.md](./RESEARCH.md) - Technical research
- [Competition Page](https://www.kaggle.com/competitions/med-gemma-impact-challenge)
- [CUM API](https://www.datos.gov.co/resource/i7cb-raxc.json)
- [SISMED API](https://www.datos.gov.co/resource/3he6-m866.json)
- [MedGemma on HuggingFace](https://huggingface.co/google/medgemma-4b-it)

---

## Decision Log
| Date | Decision | Rationale |
|------|----------|-----------|
| Feb 10 | Runtime strategy: Modal-first with configurable Transformers fallback | Keeps current demo reliability while enabling local fallback via `INFERENCE_BACKEND` |
| Jan 20 | SISMED prices are "reference only" | Data is from 2019, show date to users |
| Jan 20 | Link CUM→SISMED via expedientecum | Shared field enables price lookup for drugs |
| Jan 20 | Use Modal A10G for inference | Pay-per-use (~$0.36/hr), 24GB VRAM, local dev + remote inference |
| Jan 20 | Backend abstraction layer | Supports Modal (dev) and Transformers (Kaggle) backends |
| Jan 20 | Use MedGemma 1.5 4B IT | `google/medgemma-1.5-4b-it` - newer version with thinking support |
| Jan 21 | Centralize prompts & models | Single source of truth: `src/prompts.py`, `src/models.py` |
| Jan 22 | Consolidate inference constants | Single source: `src/inference/constants.py` (MODEL_ID, token limits) |
| Jan 26 | Multi-strategy drug matching | Product name + active ingredient search + fuzzy scoring for robust CUM lookup |

---

## Progress Notes
_Update this section as you complete tasks._

### Week 1
- **Jan 20**: Completed Track A (APIs & Data)
  - Both CUM and SISMED APIs confirmed working
  - CUM: ~35k+ drug products, search by active ingredient works well
  - SISMED: Price data available but from 2019 (not real-time) - will show as "reference prices"
  - Created `src/api/cum.py` with `search_by_active_ingredient()`, `find_generics()`
  - Created `src/api/sismed.py` with `get_price_by_expediente()`, `get_price_range()`
  - Key finding: `expedientecum` field links both datasets
- **Jan 20**: Track B infrastructure ready
  - Created `src/inference/modal_app.py` - Modal A10G GPU function
  - Created `src/inference/medgemma.py` - abstraction layer with dataclasses
  - Created `scripts/validate_extraction.py` - validation script
- **Jan 20**: Track B validation complete ✅ **GO**
  - Prescription extraction: 2/2 medications extracted correctly (EXOMEGA, LUXONA)
  - Clinical record extraction: diagnosis (Apnea Obstructiva), symptoms, treatment extracted
  - Model: `google/medgemma-1.5-4b-it` with thinking mode handled
  - Fixed: thinking mode output parsing (`<unused95>` marker), dtype deprecation

### Week 2
- **Jan 21**: Code refactoring - centralized prompts & models
  - Created `src/prompts.py` - single source for SYSTEM_INSTRUCTION, PRESCRIPTION_PROMPT, LAB_RESULTS_PROMPT
  - Created `src/models.py` - all dataclasses (extraction models + API records)
  - Removed duplication: SYSTEM_INSTRUCTION was in medgemma.py and modal_app.py
  - Updated Modal image to include src/ directory for imports
  - Backward compatibility maintained via re-exports in `src/inference/__init__.py`
  - All smoke tests passing
- **Jan 21**: Inference stability + latency improvements
  - Modal warm-starts via `@app.cls` with `min_containers=1`
  - Task-specific `max_new_tokens` defaults for faster extraction
  - JSON extraction cleanup + schema checks for parse_success
  - SISMED `min()` guard for empty/zero price lists
- **Jan 22**: Pre-Phase 2 cleanup
  - Created `src/inference/constants.py` - single source for MODEL_ID and token limits
  - Removed duplicated constants from `modal_app.py` and `medgemma.py`
  - Removed unused re-exports from `src/inference/__init__.py`
  - Added `src/logger.py` - simple logging config with `LOG_LEVEL` env var support
  - Added logging to `medgemma.py`, `cum.py`, `sismed.py` for pipeline debugging

### Week 3
- **Jan 26**: Drug name matching for CUM lookup
  - Created `src/api/drug_matcher.py` - matches extracted medication names to CUM records
  - Multi-strategy matching: product name search → active ingredient search → fuzzy scoring
  - `DrugMatchResult` dataclass with match type, confidence, alternatives
  - Dosage extraction from medication names (e.g., "LOSARTAN 50MG" → "50", "MG")
  - Form word stripping (TABLETAS, CAPSULAS, etc.)
  - Verified with real drugs: METFORMINA, LOSARTAN, ACETAMINOFEN, LUXONA
- **Jan 26**: Testing infrastructure
  - Created `tests/` folder with pytest unit tests (34 tests, mocked API)
  - `tests/conftest.py` - fixtures with sample CUM records for offline testing
  - `tests/test_drug_matcher.py` - comprehensive unit tests for matching logic
  - `scripts/validate_drug_matcher.py` - integration tests against real CUM API
  - Added pytest config to `pyproject.toml`
  - Run: `uv run pytest` (unit) | `uv run python scripts/validate_drug_matcher.py --all` (integration)
- **Jan 26**: Gradio UI implementation complete
  - Created `src/app.py` - main Gradio app with 3 tabs
  - **Recetas tab**: Image upload → MedGemma extraction → CUM/SISMED lookup → display meds + generics + prices
  - **Exámenes tab**: Image upload → MedGemma extraction → formatted results table with status indicators
  - **Mis Medicamentos tab**: Session-based tracker with add/remove + interaction warnings
  - Created `src/interactions.py` - drug interaction checker with 20+ common dangerous combinations
  - Supports brand name → generic name normalization (Glucophage → Metformina, etc.)
  - All Spanish labels, required disclaimers included
  - Run with: `uv run python src/app.py` or `uv run python main.py`
- **Jan 27**: Prescription enrichment helper (CUM + SISMED)
  - Added `src/pipelines/prescription_enrichment.py` with `enrich_medication()`
  - Returns CUM match, form-filtered generics, and SISMED price summary
  - Added unit tests for happy path, no-match, and form override
- **Jan 27**: Prescription lookup uses enrichment helper
  - Wired `src/app.py` prescription flow to use `enrich_medication()`
  - Passes MedGemma-extracted dosage into matching for better scoring
- **Jan 27**: Prescription pipeline output (CUM + SISMED + Spanish)
  - Added `src/pipelines/prescription_pipeline.py` to build Spanish markdown output
  - Pipeline calls `match_drug_to_cum()` → `find_generics()` → SISMED prices
  - Gradio prescription flow now uses `build_prescription_output()`
- **Jan 27**: Template-based Spanish explanations
  - Added `src/pipelines/spanish_explanations.py` for plain-language summaries
  - Pipeline now outputs per-medication explanations with disclaimers
- **Jan 27**: Lab results pipeline output
  - Added `src/pipelines/lab_results_pipeline.py` to format lab results + explanations
  - Wired `src/app.py` lab flow to use `build_lab_results_output()`
  - Added unit tests for normal-only and abnormal lab results output
- **Jan 27**: Explanation heuristics refinement
  - Avoids labeling non-dosage text as "Dosis indicada"
  - Moves misclassified dosage text into instructions when needed

### Week 4
- **Feb 10**: Foundation hardening (Fix Now pass)
  - Added explicit backend selection via `INFERENCE_BACKEND` (`auto`, `modal`, `transformers`)
  - Implemented backend fallback in app handlers for prescriptions and lab results
  - Added graceful degradation in prescription enrichment for CUM/SISMED outages
  - Added CI workflow with `ruff` + `pytest`
  - Added integration tests for app handler fallback and API failure paths

### Week 5
-
