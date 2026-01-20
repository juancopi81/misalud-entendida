# Research: MiSalud Entendida

## Concept

A healthcare literacy app for the MedGemma Impact Challenge (Google HAI-DEF on Kaggle) that uses MedGemma 1.5's document understanding capabilities to help Colombians understand prescriptions, lab results, and medication prices.

## Competition: Google HAI-DEF

### Overview

- **Name**: The MedGemma Impact Challenge (Google Health AI Developer Foundations / HAI-DEF)
- **Platform**: Kaggle
- **Deadline**: February 24, 2026
- **Prize pool**: $100,000
- **Focus**: Applications using MedGemma 1.5 open-weight medical AI model
- **Theme**: Privacy-focused healthcare AI that "can run anywhere"

### Judging Criteria

| Judging Pillar | Our Strategy |
|----------------|--------------|
| HAI-DEF model use | Use 4 core MedGemma 1.5 capabilities: document understanding, lab extraction, EHR QA, medical reasoning |
| Problem domain | Clear Colombian healthcare pain points with quantifiable impact |
| Impact potential | Cite WHO medication error statistics, Colombian health literacy data |
| Product feasibility | All components proven: MedGemma benchmarks, open SODA APIs, Gradio |
| Execution | Compelling 3-min demo showing real use cases |

### Deliverables Required

1. **Video demo** (max 3 minutes)
2. **Technical write-up** (max 3 pages)
3. **Code/notebook** (reproducible on Kaggle)
4. **Optional**: Hosted demo

## MedGemma 1.5 Technical Details

### Model Specifications

| Spec | Value |
|------|-------|
| Model name | MedGemma 1.5 |
| Parameters | 4B (we'll use this), 27B also available |
| Modality | Text + Image (multimodal) |
| License | Health AI Developer Foundations terms of use |
| Access | HuggingFace, Kaggle Models |

### Key Capabilities for Our Use Case

| Capability | Benchmark | Improvement over 1.0 |
|------------|-----------|---------------------|
| Medical document understanding (EHR Dataset 2, raw PDF → JSON) | 91.0 macro F1 | +13.0 (vs 78.0) |
| Medical document understanding (EHR Dataset 3, raw PDF → JSON) | 71.0 macro F1 | +21.0 (vs 50.0) |
| EHR question-answering (EHRQA) | 89.6 accuracy | +22.0 (vs 67.6) |
| Medical text QA (MedQA 4-op) | 69.1 | +4.7 (vs 64.4) |

### Why MedGemma 1.5 is Ideal

1. **Medical document understanding (PDF → JSON)**: Strong lab report parsing/extraction for structured fields (values, units)
2. **Multimodal**: Can process photos of documents directly
3. **Open weights**: Can run locally/offline, aligning with "privacy-focused" competition theme
4. **Validated**: Published benchmarks give confidence in extraction accuracy

### Hardware Requirements

| Setup | RAM | GPU VRAM | Notes |
|-------|-----|----------|-------|
| 4B model (CPU) | 16GB | - | Slow but works |
| 4B model (GPU) | 8GB | 8-12GB | Recommended |
| 27B model | 32GB+ | 24GB+ | Overkill for demo |

Note: The 16GB CPU row is for non-quantized / higher-precision runs; for edge use we target quantized GGUF (see table below).

**For competition**: Use Kaggle's free GPU (T4 16GB) or Colab Pro (A100)

## Edge Deployment for Vulnerable Populations

### Why Edge Matters

Our target users (estratos 1-3) face:
- **Inconsistent internet**: Rural areas, prepaid data plans
- **Older devices**: 4GB RAM laptops, budget Android phones
- **Privacy concerns**: Medical data should never leave the device

### Quantized Model Options

| Quantization | Size | RAM Needed | Speed (CPU) | Use Case |
|---|---|---|---|---|
| Q2_K | 1.73 GB | 2-4 GB | Slow | Extreme constraints |
| **Q4_K** | 2.49 GB | 4-8 GB | 30-60s | **Recommended** |
| Q5_K | 2.83 GB | 5-8 GB | 20-40s | Better devices |
| Q8_0 | 4.13 GB | 8-12 GB | 10-20s | Laptops with GPU |

### Deployment Tiers

**Tier 1 - Minimal (promotor de salud with old phone)**
- Hardware: Android phone 2GB+ RAM or old laptop 4GB RAM
- Model: MedGemma Q4 (2.5GB) via Ollama
- Workflow: Photo → local analysis → Spanish explanation
- Internet: Only for price lookup (optional)

**Tier 2 - Standard (rural clinic)**
- Hardware: Laptop 8GB RAM (no GPU needed)
- Model: MedGemma Q4 + Spanish ASR (TBD; MedASR is English-only today)
- Speed: 30-60 seconds per prescription
- Offline: Fully functional without internet

**Tier 3 - Connected (urban pharmacy)**
- Hardware: Any modern laptop/desktop
- Model: MedGemma Q8 for better accuracy
- Features: Real-time price lookup, generic suggestions

### MedASR for Low-Literacy Users

- 105M parameter speech-to-text model
- Note: MedASR is English-only today (Spanish ASR would be a separate component / future enhancement)
- When available: user speaks symptoms/questions → transcription fed to MedGemma
- Useful for users who struggle with typing

## Colombian Healthcare Context

### The Problem

**Medication errors are common and preventable:**
- WHO: More than half of medicines are prescribed/dispensed/sold inappropriately worldwide (high-level indicator)
- Many patients misunderstand dosage instructions (rates vary by setting; we will validate with local samples)
- Language barrier: Medical terms are confusing for low-literacy patients

**Price exploitation:**
- Same medication: $5,000 COP in one pharmacy, $20,000 COP in another
- Low-income patients don't know they're being overcharged
- Generic alternatives often 70-90% cheaper

**Lab anxiety:**
- Patients receive results but don't understand normal ranges
- Hours spent worrying about values that are actually fine
- Miss concerning values that need follow-up

### Target Population

**Primary: rough estimate 15M+ Colombians in estratos 1-3**

| Characteristic | Impact on Design |
|---|---|
| Low health literacy | Plain Spanish, no medical jargon |
| Limited data plans (prepaid) | Offline-first, model runs locally |
| Older devices (4GB RAM) | Q4 quantization (2.5GB model) |
| Can't afford brand medications | Generic alternatives prominent |
| Rely on community networks | Shareable explanations |
| Limited electricity (rural) | Fast inference, battery efficient |

**Why this matters for competition:**
- Demonstrates "can run anywhere" theme
- High social impact potential (judging criteria: 15%)
- Differentiates from cloud-only solutions

**Why Colombia specifically:**
- Familiar context (competition author's background)
- Open government health data (datos.gov.co)
- Significant need: health literacy lower than OECD average

## Data Sources

### CUM (Codigo Unico de Medicamentos)

**Purpose**: Official Colombian drug registry

**API Access**:
```
Base URL: https://www.datos.gov.co/resource/i7cb-raxc.json
Authentication: App token recommended (free registration)
```

**Key Fields**:
| Field | Description | Example |
|-------|-------------|---------|
| `principioactivo` | Active ingredient | METFORMINA |
| `concentracion` | Concentration | 850 MG |
| `formafarmaceutica` | Form | TABLETA |
| `nombreproducto` | Brand name | GLUCOPHAGE |
| `registrosanitario` | INVIMA registry | 2019M-0012345 |
| `titular` | Manufacturer | MERCK S.A. |

**Example Query** - Find generics for metformin:
```
GET https://www.datos.gov.co/resource/i7cb-raxc.json?principioactivo=METFORMINA
```

### SISMED (Sistema de Informacion de Precios de Medicamentos)

**Purpose**: Drug price reporting from pharmacies

**API Access**:
```
Base URL: https://www.datos.gov.co/resource/3he6-m866.json
```

**Key Fields**:
| Field | Description | Example |
|-------|-------------|---------|
| `medicamento` | Drug name | METFORMINA 850MG |
| `precio_minimo` | Min price reported | 2500 |
| `precio_maximo` | Max price reported | 8500 |
| `precio_promedio` | Average price | 4200 |
| `unidades_vendidas` | Units sold | 150000 |
| `periodo` | Report period | 202312 |

**Example Query** - Get price range for metformin:
```
GET https://www.datos.gov.co/resource/3he6-m866.json?$q=METFORMINA
```

### Data Limitations

1. **CUM**: ~35,000 products; some newer drugs may be missing
2. **SISMED**: Prices are reported averages, not real-time pharmacy prices
3. **Both**: Data updated monthly, may lag 2-3 months

**Mitigation**: Show "reference price range" with data date

## Technical Implementation

### Prescription Processing Pipeline

```python
# Implementation sketch (avoid committing to a specific framework too early)
#
# 1) Take photo of prescription / lab report
# 2) MedGemma: extract structured fields into JSON (drug name, dose, frequency, lab values, units)
# 3) Enrichment:
#    - CUM: validate drug registry + find bioequivalents/generics
#    - SISMED: fetch reference price ranges (+ period/date)
# 4) MedGemma: generate plain-language Spanish explanation + "what to ask / what is urgent"
#
# We will add a minimal "smoke test" notebook in Kaggle during Phase 1 validation.
def process_prescription(image_path: str) -> dict:
    """TBD (Phase 1 validation)."""
    ...
```

### Lab Results Processing

```python
def process_lab_results(image_path: str) -> dict:
    """TBD (Phase 1 validation)."""
    ...
```

### Drug Interaction Checking

```python
# Common dangerous combinations (hardcoded for demo)
KNOWN_INTERACTIONS = {
    ("warfarina", "aspirina"): {
        "severity": "alta",
        "warning": "Aumenta riesgo de sangrado. Consulte a su médico."
    },
    ("metformina", "alcohol"): {
        "severity": "media",
        "warning": "Evite alcohol excesivo. Riesgo de acidosis láctica."
    },
    ("losartan", "potasio"): {
        "severity": "media",
        "warning": "Puede aumentar potasio en sangre. Requiere monitoreo."
    },
    # ... more interactions
}

def check_interactions(medications: list[str]) -> list[dict]:
    """Check for known drug interactions."""
    warnings = []
    for i, med1 in enumerate(medications):
        for med2 in medications[i+1:]:
            key = tuple(sorted([med1.lower(), med2.lower()]))
            if key in KNOWN_INTERACTIONS:
                warnings.append({
                    "drugs": [med1, med2],
                    **KNOWN_INTERACTIONS[key]
                })
    return warnings
```

## Gradio Interface

```python
import gradio as gr

def prescription_tab():
    with gr.Column():
        gr.Markdown("## Entiende tu Receta")
        image_input = gr.Image(type="filepath", label="Foto de tu receta")
        submit_btn = gr.Button("Analizar", variant="primary")

        with gr.Row():
            extraction_output = gr.JSON(label="Extracción")
            explanation_output = gr.Textbox(label="Explicación", lines=10)

        with gr.Row():
            price_output = gr.Dataframe(label="Precios de Referencia")
            generics_output = gr.Dataframe(label="Alternativas Genéricas")

def lab_tab():
    with gr.Column():
        gr.Markdown("## Entiende tus Exámenes")
        image_input = gr.Image(type="filepath", label="Foto de resultados")
        submit_btn = gr.Button("Analizar", variant="primary")

        values_output = gr.Dataframe(label="Valores Extraídos")
        interpretation_output = gr.Textbox(label="Interpretación", lines=15)
        flags_output = gr.Textbox(label="Alertas", lines=3)

# Main app
with gr.Blocks(title="MiSalud Entendida") as demo:
    gr.Markdown("# MiSalud Entendida")
    gr.Markdown("*Entiende tus recetas y exámenes con IA médica*")

    with gr.Tab("Recetas"):
        prescription_tab()
    with gr.Tab("Exámenes"):
        lab_tab()
    with gr.Tab("Mis Medicamentos"):
        medication_tracker_tab()

    gr.Markdown("""
    ---
    **Aviso importante**: Esta herramienta es solo para fines educativos.
    No reemplaza el consejo de su médico. Siempre consulte a un profesional
    de la salud antes de tomar decisiones sobre sus medicamentos.
    """)
```

## Responsible AI Considerations

### Disclaimers Required

1. **Not medical advice**: "Esta herramienta es solo para ayudarle a entender sus documentos. No reemplaza el consejo de su médico."
2. **Verify with pharmacist**: "Siempre confirme los precios en su farmacia local."
3. **Seek care for urgency**: "Si tiene síntomas urgentes, busque atención médica inmediata."

### Privacy Protections

1. **No data storage**: Session-based only, no images saved
2. **Local inference**: Demonstrate model can run offline
3. **No PII collection**: No user accounts for demo

### Known Limitations to Disclose

1. Handwritten prescriptions may not work well
2. Prices are reference ranges, not exact
3. Not all medications in database
4. AI may make extraction errors - always verify

## Competitive Landscape

| Solution | Coverage | Limitations |
|----------|----------|-------------|
| Google Lens | OCR | No medical understanding |
| Farmapp (Colombia) | Prices | No prescription understanding |
| MedPal | Interactions | English only, no local prices |
| DrugBank | Drug info | No Spanish, no Colombian prices |

**Our differentiation**: Colombian context + MedGemma understanding + local pricing

## Implementation Timeline

### Phase 1: Validation (Days 1-3)
- [ ] Set up MedGemma 1.5 in Kaggle notebook
- [ ] Test on 5 sample Colombian prescriptions
- [ ] Test lab extraction on 3 sample reports
- [ ] Verify SODA API access works

### Phase 2: Core Build (Days 4-10)
- [ ] Build prescription extraction pipeline
- [ ] Build lab interpretation pipeline
- [ ] Integrate CUM and SISMED APIs
- [ ] Build Gradio interface
- [ ] Add medication tracking

### Phase 3: Polish (Days 11-14)
- [ ] Add interaction checking
- [ ] Add disclaimers and responsible AI messaging
- [ ] Test with diverse document samples
- [ ] Prepare reproducible Kaggle notebook

### Phase 4: Submission (Days 15-18)
- [ ] Record 3-minute video demo
- [ ] Write 3-page technical document
- [ ] Final testing and submission

## Success Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| Prescription extraction accuracy | >85% | Manual review of 20 samples |
| Lab value extraction accuracy | >75% | Manual review of 10 samples |
| CUM API success rate | >90% | Automated testing |
| SISMED API success rate | >90% | Automated testing |
| Demo runs end-to-end | 100% | Must work for video |

## References

- [MedGemma Technical Report (arXiv:2507.05201)](https://arxiv.org/abs/2507.05201)
- [MedGemma on HuggingFace](https://huggingface.co/google/medgemma-1.5-4b-it)
- [The MedGemma Impact Challenge (Kaggle)](https://www.kaggle.com/competitions/med-gemma-impact-challenge/overview)
- [datos.gov.co API Documentation](https://dev.socrata.com/foundry/www.datos.gov.co/)
- [CUM Dataset](https://www.datos.gov.co/Salud-y-Protecci-n-Social/C-digo-nico-de-Medicamentos/i7cb-raxc)
- [SISMED Dataset](https://www.datos.gov.co/Salud-y-Protecci-n-Social/SISMED/3he6-m866)
- [WHO Medication Errors Report](https://www.who.int/news-room/fact-sheets/detail/medication-errors)

**Edge Deployment Resources:**
- [MedGemma GGUF Quantizations](https://huggingface.co/bartowski/google_medgemma-4b-it-GGUF)
- [llama.cpp](https://github.com/ggerganov/llama.cpp)
- [Ollama](https://ollama.ai)
- [MedASR](https://medasr.org/)

## Qualitative Assessment

| Factor | Rating | Notes |
|--------|--------|-------|
| Competition fit | Excellent | Uses NEW MedGemma 1.5 features |
| Problem clarity | High | Specific, quantifiable pain points |
| Technical feasibility | High | All components proven |
| Differentiation | High | Colombian context unique |
| Learning value | Very High | MedGemma, medical AI, SODA APIs |
| Competition risk | Medium | Depends on other entries |

**Overall**: Strong competition entry that plays to MedGemma 1.5's new capabilities (lab extraction, document understanding) while addressing a real problem in a specific market. Main execution risk is ensuring extraction quality is demo-worthy.
