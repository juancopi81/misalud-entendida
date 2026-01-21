#!/usr/bin/env python3
"""Validation script for MedGemma extraction.

Run from local machine, inference happens on Modal A10G GPU.

Usage:
    uv run python scripts/validate_extraction.py

Requirements:
    1. Modal token: `modal token new`
    2. HuggingFace secret: `modal secret create huggingface HF_TOKEN=<your_token>`
    3. HuggingFace access: Accept terms at https://huggingface.co/google/medgemma-1.5-4b-it
"""

import sys
from pathlib import Path

import modal

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.inference.medgemma import get_backend
from src.inference.modal_app import app as modal_app
from src.prompts import CLINICAL_RECORD_PROMPT


def validate_prescription(backend, image_path: Path) -> bool:
    """Validate prescription extraction."""
    print(f"\n{'='*60}")
    print(f"Testing prescription extraction: {image_path.name}")
    print("=" * 60)

    result = backend.extract_prescription(image_path)

    print(f"\nParse success: {result.parse_success}")
    print(f"Medications found: {len(result.medicamentos)}")

    if result.medicamentos:
        for i, med in enumerate(result.medicamentos, 1):
            print(f"\n  Medication {i}:")
            print(f"    Nombre: {med.nombre_medicamento}")
            print(f"    Dosis: {med.dosis}")
            print(f"    Frecuencia: {med.frecuencia}")
            print(f"    Duracion: {med.duracion}")
            print(f"    Instrucciones: {med.instrucciones}")

    print("\n--- Raw Response ---")
    print(
        result.raw_response[:500] + "..."
        if len(result.raw_response) > 500
        else result.raw_response
    )

    return result.parse_success and len(result.medicamentos) > 0


def validate_lab_results(backend, image_path: Path) -> bool:
    """Validate lab results extraction."""
    print(f"\n{'='*60}")
    print(f"Testing lab results extraction: {image_path.name}")
    print("=" * 60)

    result = backend.extract_lab_results(image_path)

    print(f"\nParse success: {result.parse_success}")
    print(f"Results found: {len(result.resultados)}")

    if result.resultados:
        for i, res in enumerate(result.resultados, 1):
            print(f"\n  Result {i}:")
            print(f"    Prueba: {res.nombre_prueba}")
            print(f"    Valor: {res.valor}")
            print(f"    Unidad: {res.unidad}")
            print(f"    Rango: {res.rango_referencia}")
            print(f"    Estado: {res.estado}")

    print("\n--- Raw Response ---")
    print(
        result.raw_response[:500] + "..."
        if len(result.raw_response) > 500
        else result.raw_response
    )

    return result.parse_success


def main():
    print("MedGemma Extraction Validation")
    print("Backend: Modal (A10G GPU)")
    print("-" * 40)

    # Start Modal app context so functions can hydrate
    with modal.enable_output():
        with modal_app.run():
            # Get Modal backend
            backend = get_backend("modal")

            # Find sample images
            samples_dir = Path(__file__).parent.parent / "samples"
            prescription_path = (
                samples_dir / "prescriptions" / "receta_dermatologia_2025.jpeg"
            )
            clinical_record_path = (
                samples_dir / "clinical_records" / "historia_clinica_sueno_2025.jpeg"
            )

            results = {}

            # Test prescription extraction
            if prescription_path.exists():
                results["prescription"] = validate_prescription(
                    backend, prescription_path
                )
            else:
                print(f"WARNING: Prescription sample not found at {prescription_path}")
                results["prescription"] = False

            # Test clinical record (using lab results prompt as a general extraction test)
            if clinical_record_path.exists():
                print(f"\n{'='*60}")
                print(
                    f"Testing clinical record extraction: {clinical_record_path.name}"
                )
                print("=" * 60)

                # Use raw extraction with a general prompt for clinical records
                raw_result = backend.extract_raw(
                    clinical_record_path,
                    CLINICAL_RECORD_PROMPT,
                )
                print("\n--- Raw Response ---")
                print(raw_result[:800] + "..." if len(raw_result) > 800 else raw_result)
                results["clinical_record"] = len(raw_result) > 50
            else:
                print(
                    f"WARNING: Clinical record sample not found at {clinical_record_path}"
                )
                results["clinical_record"] = False

            # Summary
            print(f"\n{'='*60}")
            print("VALIDATION SUMMARY")
            print("=" * 60)
            for test_name, passed in results.items():
                status = "PASS" if passed else "FAIL"
                print(f"  {test_name}: {status}")

            all_passed = all(results.values())
            print(f"\nOverall: {'GO' if all_passed else 'NO-GO'}")

            return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
