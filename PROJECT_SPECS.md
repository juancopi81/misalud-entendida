# MiSalud Entendida

> One-line pitch: Entiende tus recetas y exámenes con IA médica abierta

## Goals

- [x] **Learning** — master MedGemma 1.5 multimodal medical AI
- [x] **Personal Brand** — Kaggle competition entry, showcase healthcare AI expertise
- [x] **Creative Expression** — build something impactful for Colombian healthcare

**Specific goals**:

- Win or place in the MedGemma Impact Challenge (Google HAI-DEF on Kaggle) (deadline: Feb 24, 2026)
- Demonstrate effective use of MedGemma 1.5's new capabilities
- Create a compelling 3-minute video demo

## Design Principles

1. **Spanish-first**: All UI, explanations, and prompts in Colombian Spanish. Medical terms translated to plain language (e.g., "hipertensión" → "presión alta")

2. **Offline-first**: Core functionality works without internet. Model runs locally on device. Only price lookups require connectivity (with graceful degradation)

3. **Low-resource devices**: Target 4GB RAM laptops and older Android phones. Use quantized models (Q4 = 2.5GB); text-only fallback if image processing exceeds device capacity

4. **Privacy by design**: No data leaves the device. No user accounts. Session-only storage

## Pain / Opportunity

Colombian patients struggle to understand their healthcare documents:

1. **Prescription confusion**: Nearly half of patients misunderstand medication instructions ([NIH study](https://pmc.ncbi.nlm.nih.gov/articles/PMC2607498/)), leading to errors
2. **Lab result anxiety**: Patients receive lab results but don't understand what values mean or when to worry
3. **Price opacity**: Brand medications can be many times more expensive than generics in developing countries ([WHO](https://www.emro.who.int/press-releases/2010/medicine-prices-vary-widely-both-between-and-within-countries.html)); low-income patients overpay
4. **Drug interactions**: Patients taking multiple medications don't know about dangerous combinations

**Why AI is the right solution:**
- MedGemma 1.5 improved medical document understanding for lab reports (raw PDF → JSON), e.g. 78.0 → 91.0 macro F1 (EHR Dataset 2),
  and improved EHR question-answering (EHRQA) from 67.6 → 89.6 accuracy
- Open-weight model aligns with competition's "privacy-focused, can run anywhere" theme
- Text + image multimodal capability matches real-world use (photos of documents)

## User

> **Core focus**: Colombians in estratos 1-3 (rough estimate: 15M+) with limited health literacy, connectivity, and device access

- **Primary**: Vulnerable populations in estratos 1-3 - patients and caregivers who:
  - Cannot afford brand-name medications and need generic alternatives
  - Have limited data plans or inconsistent internet access
  - Use older smartphones or shared family devices
  - Rely on community health workers for medical guidance
- **Secondary**: Promotores de salud (community health workers) serving rural and underserved areas
- **Tertiary**: Pharmacists in low-income neighborhoods validating prescriptions

## Inputs

- **Photo of prescription** (printed; handwritten support may be limited)
- **Photo of lab results** (blood tests, urinalysis, etc.)
- **Photo of medication box/label**
- **Text query** about medications or results

## Outputs

- **Plain-language explanation** in Colombian Spanish
- **Structured extraction**: drug name, dosage, frequency, duration
- **Lab value interpretation**: what each value means, normal ranges, flags
- **Price reference**: fair price range from SISMED data
- **Generic alternatives**: cheaper bioequivalent options from CUM
- **Interaction warnings**: if multiple medications tracked
- **Action items**: "Ask your doctor about X", "This is urgent", etc.

## MVP Scope (v0) - Competition Demo

### In Scope

- Photo → prescription extraction and explanation
- Photo → lab results interpretation
- Price lookup via SISMED data (datos.gov.co SODA)
- Generic alternatives via CUM data (datos.gov.co SODA)
- Basic medication tracking (session-based)
- Interaction warnings for common combinations
- Spanish-language UI
- Offline-capable inference (demonstrate model can run locally)

### Out of Scope (for now)

- User accounts / persistent history
- Handwritten prescription OCR (focus on printed for demo reliability)
- Integration with EPS/insurance systems
- Push notifications / reminders
- Multi-language support

## Tech Stack / Learning Goals

- **Stack**:
  - MedGemma 1.5 4B (via HuggingFace transformers)
  - Python pipeline modules (`src/`) + Gradio app runtime for MVP
  - FastAPI (deferred; not part of current MVP runtime)
  - SODA API for datos.gov.co (CUM drug registry, SISMED price data)
  - Google Colab / Kaggle Notebooks for reproducibility

- **Edge deployment**:
  - MedGemma 1.5 4B-IT with Q4 quantization (2.5GB)
  - llama.cpp or Ollama for CPU inference
  - Optional: Speech-to-text for voice input (Spanish ASR TBD; MedASR is English-only today)
  - Target: 30-60 second inference on old laptops without GPU

- **Skills to learn**:
  - MedGemma 1.5 multimodal inference
  - Medical document understanding prompting
  - Colombian health data APIs (SODA/Socrata)
  - Healthcare AI responsible deployment considerations

## Architecture

```
User Flow:
1. Take photo of document → 2. Upload to app → 3. Get explanation + prices → 4. Track medications

Offline-First Architecture:
┌─────────────────────────────────────────────────────────────┐
│                    USER'S DEVICE (offline)                   │
│  ┌──────────┐     ┌──────────────┐     ┌─────────────────┐  │
│  │  Gradio  │────▶│  MedGemma    │────▶│  Explanation    │  │
│  │   UI     │     │  4B Q4       │     │  in Spanish     │  │
│  │ (Spanish)│     │  (local)     │     │                 │  │
│  └──────────┘     └──────────────┘     └─────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                           │ (optional, when online)
                           ▼
              ┌────────────┴────────────┐
              ▼                         ▼
        ┌──────────┐              ┌──────────┐
        │   CUM    │              │  SISMED  │
        │ (Drugs)  │              │ (Prices) │
        └──────────┘              └──────────┘
```

### Document Processing Pipeline

```python
def process_prescription(image):
    # 1. Run MedGemma 1.5 for document understanding
    # 2. Extract: drug name, dosage, frequency, duration
    # 3. Validate against CUM database
    # 4. Fetch prices from SISMED
    # 5. Find generic alternatives
    # 6. Generate plain-language explanation
    # 7. Check for interactions with tracked meds
```

### Lab Results Pipeline

```python
def process_lab_results(image):
    # 1. Run MedGemma 1.5 lab extraction
    # 2. Parse values into structured JSON
    # 3. Compare against normal ranges
    # 4. Flag concerning values
    # 5. Generate plain-language interpretation
```

## Data Sources

| Dataset | URL | API | Use |
|---------|-----|-----|-----|
| CUM (Codigo Unico de Medicamentos) | datos.gov.co/i7cb-raxc | SODA | Drug validation, generics |
| SISMED (Precios) | datos.gov.co/3he6-m866 | SODA | Price references |
| INVIMA | app.invima.gov.co/cum | Web | Real-time validation |

## MedGemma 1.5 Capabilities Used

| Capability | Competition Feature | Benchmark |
|------------|---------------------|-----------|
| Medical document understanding | PDF → JSON (EHR Dataset 2) | 91.0 macro F1 (vs 78.0) |
| Medical document understanding | PDF → JSON (EHR Dataset 3) | 71.0 macro F1 (vs 50.0) |
| EHR question-answering | EHRQA | 89.6 accuracy (vs 67.6) |
| Medical text reasoning | MedQA (4-op) | 69.1 (vs 64.4) |

## Competition Alignment

| Judging Pillar | How We Address It |
|----------------|-------------------|
| **HAI-DEF use** | Uses 4 core MedGemma 1.5 capabilities; specifically targets NEW 1.5 features |
| **Problem domain** | Clear user personas, quantifiable pain, Colombian context |
| **Impact potential** | Cite WHO data on medication errors, Colombian health literacy stats |
| **Product feasibility** | All components proven: MedGemma benchmarks, open APIs, Gradio deployment |
| **Execution** | Compelling demo: 2 use cases (prescription + labs), visual before/after |

## Success Metrics

| Signal | Target | Notes |
|--------|--------|-------|
| Prescription extraction | >85% | Correct drug, dose, frequency |
| Lab value extraction | >75% | Correct values and units |
| Price lookup success | >90% | Match found in SISMED |
| Spanish explanation quality | Subjective | Review with native speakers |

## Risks & Unknowns

- **Risk**: Handwritten prescription OCR accuracy
  - *Mitigation*: Focus demo on printed prescriptions; acknowledge limitation

- **Risk**: Medical liability concerns ("this is not medical advice")
  - *Mitigation*: Clear disclaimers, frame as "understanding" not "diagnosis"

- **Risk**: SISMED data freshness/completeness
  - *Mitigation*: Show "reference price" not "exact price", cite data date

- **Unknown**: MedGemma performance on Colombian Spanish medical terms
  - *To validate*: Test with real Colombian prescription samples

## Demo Script (3 minutes)

```
0:00-0:30  Problem statement + user persona (María, 58, diabética)
0:30-1:15  Demo 1: Prescription photo → explanation + price + generic
1:15-2:00  Demo 2: Lab results photo → plain language + flags
2:00-2:30  Show: Medication tracker + interaction warning
2:30-3:00  Impact potential + why MedGemma 1.5 enables this
```

## Deliverables for Competition

1. **Video** (3 min): Demo with narration
2. **Write-up** (3 pages): Problem, solution, technical approach, impact
3. **Code**: Kaggle notebook with reproducible inference
4. **Optional**: Gradio hosted demo

## Progress Log

| Date | Event | Result |
|------|-------|--------|
| -    | -     | -      |

## Next Milestone

**Goal**: Phase 3 quality hardening and submission readiness

**Tasks**:

- [ ] Evaluate 5+ real prescriptions and document extraction accuracy
- [ ] Evaluate 3+ real lab reports and document extraction accuracy
- [ ] Resolve extraction edge cases found in evaluation
- [ ] Validate Spanish explanation quality with native reviewers
- [ ] Finalize competition assets (3-min video, 3-page write-up, Kaggle reproducibility)
