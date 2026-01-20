# MiSalud Entendida - Project ROADMAP

> **Deadline**: February 24, 2026
> **Team**: 2 people (~15-20 hrs/week each)
> **Competition**: MedGemma Impact Challenge (Kaggle)

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
| [ ] | Prescription extraction pipeline | Phase 1 complete |
| [ ] | Lab results interpretation pipeline | Phase 1 complete |
| [ ] | CUM integration (generic alternatives) | API stub |
| [ ] | SISMED integration (price lookup) | API stub |
| [ ] | Drug interaction checker | Hardcoded list from RESEARCH.md |
| [ ] | Spanish explanation generator | MedGemma prompts |

### Track B: UI/UX (Person 2)
| Status | Task | Depends On |
|--------|------|------------|
| [ ] | Gradio app skeleton | None |
| [ ] | Prescription tab (upload + display) | None |
| [ ] | Lab results tab (upload + display) | None |
| [ ] | Medication tracker tab | None |
| [ ] | Spanish labels and copy | None |
| [ ] | Disclaimers ("No es consejo médico") | None |
| [ ] | Mobile-friendly styling | None |

### Integration Point (End of Week 3)
- [ ] Connect UI to backend pipelines
- [ ] End-to-end test: photo → explanation + price
- [ ] Fix integration bugs

---

## Phase 3: Polish & Submit (Weeks 4-5: Feb 10-24)
**Goal**: Test, polish, and submit.

### Track A: Testing & Quality (Person 1)
| Status | Task | Notes |
|--------|------|-------|
| [ ] | Test 5+ real prescriptions | Document accuracy |
| [ ] | Test 3+ real lab results | Document accuracy |
| [ ] | Fix extraction edge cases | Based on test results |
| [ ] | Validate Spanish with native speaker | Quality check |
| [ ] | Performance optimization | If needed |

### Track B: Submission Materials (Person 2)
| Status | Task | Notes |
|--------|------|-------|
| [ ] | Script 3-min demo video | Use demo script from PROJECT_SPECS.md |
| [ ] | Record demo video | Screen recording + narration |
| [ ] | Write 3-page technical doc | Use template structure |
| [ ] | Create Kaggle notebook | Reproducible inference |
| [ ] | Choose competition track | Main vs special award |

### Final Submission Checklist
- [ ] Video uploaded (≤3 min)
- [ ] Write-up complete (≤3 pages)
- [ ] Code reproducible on Kaggle
- [ ] Submitted before Feb 24, 2026 11:59 PM UTC

---

## Quick Links
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
| Jan 20 | Use HF Inference API as primary | De-risks GPU availability on Kaggle |
| Jan 20 | SISMED prices are "reference only" | Data is from 2019, show date to users |
| Jan 20 | Link CUM→SISMED via expedientecum | Shared field enables price lookup for drugs |
| Jan 20 | Use Modal A10G for inference | Pay-per-use (~$0.36/hr), 24GB VRAM, local dev + remote inference |
| Jan 20 | Backend abstraction layer | Supports Modal (dev) and Transformers (Kaggle) backends |
| Jan 20 | Use MedGemma 1.5 4B IT | `google/medgemma-1.5-4b-it` - newer version with thinking support |

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
-

### Week 3
-

### Week 4
-

### Week 5
-
