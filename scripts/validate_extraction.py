#!/usr/bin/env python3
"""Validation script for MedGemma extraction.

Run from local machine, inference happens on Modal A10G GPU.

Usage:
    uv run python scripts/validate_extraction.py
    uv run python scripts/validate_extraction.py --only lab_results
    uv run python scripts/validate_extraction.py --lab-raw samples/raw/lab_results.txt
    uv run python scripts/validate_extraction.py --save-lab-raw samples/raw/lab_results.txt

Requirements:
    1. Modal token: `modal token new`
    2. HuggingFace secret: `modal secret create huggingface HF_TOKEN=<your_token>`
    3. HuggingFace access: Accept terms at https://huggingface.co/google/medgemma-1.5-4b-it
    4. Deployed Modal app: `uv run modal deploy src/inference/modal_app.py`
"""

import argparse
import sys
from pathlib import Path

import modal

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.inference.medgemma import get_backend
from src.inference.utils import extract_json_from_response
from src.logger import get_logger
from src.models import LabResultExtraction
from src.prompts import CLINICAL_RECORD_PROMPT

logger = get_logger(__name__)


def log_raw_response(raw_response: str, head: int = 500, tail: int = 300) -> None:
    """Log a safe excerpt of a raw model response."""
    logger.info("Raw response length: %d", len(raw_response))
    logger.info("--- Raw Response (head) ---")
    logger.info(
        raw_response[:head] + "..." if len(raw_response) > head else raw_response
    )
    if len(raw_response) > head:
        logger.info("--- Raw Response (tail) ---")
        logger.info("..." + raw_response[-tail:])


def validate_prescription(backend, image_path: Path) -> bool:
    """Validate prescription extraction."""
    logger.info("%s", "=" * 60)
    logger.info("Testing prescription extraction: %s", image_path.name)
    logger.info("%s", "=" * 60)

    result = backend.extract_prescription(image_path)

    logger.info("Parse success: %s", result.parse_success)
    logger.info("Medications found: %d", len(result.medicamentos))

    if result.medicamentos:
        for i, med in enumerate(result.medicamentos, 1):
            logger.info("  Medication %d:", i)
            logger.info("    Nombre: %s", med.nombre_medicamento)
            logger.info("    Dosis: %s", med.dosis)
            logger.info("    Frecuencia: %s", med.frecuencia)
            logger.info("    Duracion: %s", med.duracion)
            logger.info("    Instrucciones: %s", med.instrucciones)

    log_raw_response(result.raw_response)

    return result.parse_success and len(result.medicamentos) > 0


def validate_lab_results(
    backend, image_path: Path, save_raw_path: Path | None = None
) -> bool:
    """Validate lab results extraction."""
    logger.info("%s", "=" * 60)
    logger.info("Testing lab results extraction: %s", image_path.name)
    logger.info("%s", "=" * 60)

    result = backend.extract_lab_results(image_path)
    if save_raw_path is not None:
        save_raw_path.parent.mkdir(parents=True, exist_ok=True)
        save_raw_path.write_text(result.raw_response, encoding="utf-8")

    logger.info("Parse success: %s", result.parse_success)
    logger.info("Results found: %d", len(result.resultados))

    if result.resultados:
        for i, res in enumerate(result.resultados, 1):
            logger.info("  Result %d:", i)
            logger.info("    Prueba: %s", res.nombre_prueba)
            logger.info("    Valor: %s", res.valor)
            logger.info("    Unidad: %s", res.unidad)
            logger.info("    Rango: %s", res.rango_referencia)
            logger.info("    Estado: %s", res.estado)

    log_raw_response(result.raw_response)

    return result.parse_success


def validate_lab_results_from_raw(raw_response: str) -> bool:
    """Validate lab results extraction from a raw model response string."""
    logger.info("%s", "=" * 60)
    logger.info("Testing lab results extraction: raw response")
    logger.info("%s", "=" * 60)

    extracted = extract_json_from_response(raw_response)
    result = LabResultExtraction.from_json(extracted)
    result.raw_response = raw_response

    logger.info("Parse success: %s", result.parse_success)
    logger.info("Results found: %d", len(result.resultados))

    if result.resultados:
        for i, res in enumerate(result.resultados, 1):
            logger.info("  Result %d:", i)
            logger.info("    Prueba: %s", res.nombre_prueba)
            logger.info("    Valor: %s", res.valor)
            logger.info("    Unidad: %s", res.unidad)
            logger.info("    Rango: %s", res.rango_referencia)
            logger.info("    Estado: %s", res.estado)

    log_raw_response(raw_response)

    return result.parse_success


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate MedGemma extraction.")
    parser.add_argument(
        "--only",
        action="append",
        choices=["prescription", "lab_results", "clinical_record"],
        help="Run only specific validation(s). Can be provided multiple times.",
    )
    parser.add_argument(
        "--lab-raw",
        type=Path,
        help="Path to a raw lab-results response to parse locally (skips Modal).",
    )
    parser.add_argument(
        "--save-lab-raw",
        type=Path,
        help="Save raw lab-results response to this path when running inference.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    only = set(args.only or [])

    logger.info("MedGemma Extraction Validation")
    logger.info("Backend: Modal (A10G GPU)")
    logger.info("%s", "-" * 40)

    # Find sample images
    samples_dir = Path(__file__).parent.parent / "samples"
    prescription_path = samples_dir / "prescriptions" / "receta_dermatologia_2025.jpeg"
    clinical_record_path = (
        samples_dir / "clinical_records" / "historia_clinica_sueno_2025.jpeg"
    )
    lab_results_path = (
        samples_dir / "lab_results" / "resultados_laboratorio_2025_p1.jpeg"
    )

    results = {}

    def should_run(name: str) -> bool:
        return not only or name in only

    needs_backend = (
        (should_run("prescription"))
        or (should_run("clinical_record"))
        or (should_run("lab_results") and args.lab_raw is None)
    )

    if not needs_backend:
        if should_run("lab_results"):
            raw_response = args.lab_raw.read_text(encoding="utf-8")
            results["lab_results"] = validate_lab_results_from_raw(raw_response)
        else:
            logger.warning("No tests selected.")
            return 1
    else:
        with modal.enable_output():
            backend = get_backend("modal")

            # Test prescription extraction
            if should_run("prescription"):
                if prescription_path.exists():
                    results["prescription"] = validate_prescription(
                        backend, prescription_path
                    )
                else:
                    logger.warning(
                        f"WARNING: Prescription sample not found at {prescription_path}"
                    )
                    results["prescription"] = False

            # Test lab results extraction
            if should_run("lab_results"):
                if args.lab_raw is not None:
                    raw_response = args.lab_raw.read_text(encoding="utf-8")
                    results["lab_results"] = validate_lab_results_from_raw(
                        raw_response
                    )
                elif lab_results_path.exists():
                    results["lab_results"] = validate_lab_results(
                        backend, lab_results_path, save_raw_path=args.save_lab_raw
                    )
                else:
                    logger.warning(
                        f"WARNING: Lab results sample not found at {lab_results_path}"
                    )
                    results["lab_results"] = False

            # Test clinical record (using raw extraction - validation only, not MVP)
            if should_run("clinical_record"):
                if clinical_record_path.exists():
                    logger.info("%s", "=" * 60)
                    logger.info(
                        "Testing clinical record extraction: %s",
                        clinical_record_path.name,
                    )
                    logger.info("%s", "=" * 60)

                    # Use raw extraction with a general prompt for clinical records
                    raw_result = backend.extract_raw(
                        clinical_record_path,
                        CLINICAL_RECORD_PROMPT,
                    )
                    logger.info("--- Raw Response ---")
                    logger.info(
                        raw_result[:800] + "..."
                        if len(raw_result) > 800
                        else raw_result
                    )
                    results["clinical_record"] = len(raw_result) > 50
                else:
                    logger.warning(
                        f"WARNING: Clinical record sample not found at {clinical_record_path}"
                    )
                    results["clinical_record"] = False

    # Summary
    logger.info("%s", "=" * 60)
    logger.info("VALIDATION SUMMARY")
    logger.info("%s", "=" * 60)
    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        logger.info("  %s: %s", test_name, status)

    all_passed = all(results.values()) if results else False
    logger.info("Overall: %s", "GO" if all_passed else "NO-GO")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
