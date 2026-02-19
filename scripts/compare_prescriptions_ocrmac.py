#!/usr/bin/env python3
"""Run ocrmac on prescription images and compare OCR text to labeled JSONL fields.

This script is for local labeling/evaluation support only (macOS OCR helper),
not for production runtime dependencies.

Usage:
    uv run --with ocrmac python scripts/compare_prescriptions_ocrmac.py
    uv run --with ocrmac python scripts/compare_prescriptions_ocrmac.py --recognition-level fast
    uv run --with ocrmac python scripts/compare_prescriptions_ocrmac.py --framework livetext
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_LABELS_PATH = Path("eval/prescriptions_labels.jsonl")
DEFAULT_REPORT_PATH = Path("eval/ocrmac_prescriptions_compare_report.json")
DEFAULT_RAW_PATH = Path("eval/ocrmac_prescriptions_raw.jsonl")
PRESCRIPTION_FIELDS = ("dosis", "frecuencia", "duracion", "instrucciones")


@dataclass
class MatchResult:
    matched: bool
    score: float
    method: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run OCR with ocrmac for each prescription in eval labels and compare "
            "against ground truth field values."
        )
    )
    parser.add_argument(
        "--labels-path",
        type=Path,
        default=DEFAULT_LABELS_PATH,
        help=f"Path to prescription labels JSONL (default: {DEFAULT_LABELS_PATH})",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help=f"Path to write JSON report (default: {DEFAULT_REPORT_PATH})",
    )
    parser.add_argument(
        "--raw-path",
        type=Path,
        default=DEFAULT_RAW_PATH,
        help=f"Path to write OCR raw output JSONL (default: {DEFAULT_RAW_PATH})",
    )
    parser.add_argument(
        "--framework",
        choices=("vision", "livetext"),
        default="vision",
        help="OCR backend framework supported by ocrmac.",
    )
    parser.add_argument(
        "--recognition-level",
        choices=("fast", "accurate"),
        default="accurate",
        help="Vision recognition level. Ignored when framework=livetext.",
    )
    parser.add_argument(
        "--languages",
        default="es-ES,en-US",
        help=(
            "Comma-separated language preference list for vision framework "
            "(default: es-ES,en-US)."
        ),
    )
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.0,
        help=(
            "Filter annotations below this confidence. "
            "Ignored for livetext where confidence is always 1."
        ),
    )
    parser.add_argument(
        "--min-token-recall",
        type=float,
        default=0.7,
        help=(
            "Token recall threshold used when exact substring does not match "
            "(default: 0.7)."
        ),
    )
    return parser.parse_args()


def normalize_text(text: str) -> str:
    if not text:
        return ""
    deaccented = "".join(
        ch
        for ch in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(ch)
    )
    normalized = deaccented.upper().replace(",", ".")
    normalized = re.sub(r"[^A-Z0-9.%/]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def token_set(normalized_text: str) -> set[str]:
    return {token for token in normalized_text.split() if len(token) >= 2}


def match_phrase(
    expected: str,
    normalized_ocr_text: str,
    normalized_ocr_tokens: set[str],
    min_token_recall: float,
) -> MatchResult:
    expected_normalized = normalize_text(expected)
    if not expected_normalized:
        return MatchResult(matched=True, score=1.0, method="empty")

    if expected_normalized in normalized_ocr_text:
        return MatchResult(matched=True, score=1.0, method="substring")

    expected_tokens = [token for token in expected_normalized.split() if len(token) >= 2]
    if not expected_tokens:
        return MatchResult(matched=False, score=0.0, method="no_tokens")

    matched_tokens = sum(1 for token in expected_tokens if token in normalized_ocr_tokens)
    recall = matched_tokens / len(expected_tokens)
    return MatchResult(
        matched=recall >= min_token_recall,
        score=recall,
        method="token_recall",
    )


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
    return rows


def extract_annotations(
    image_path: Path,
    framework: str,
    recognition_level: str,
    languages: list[str],
    confidence_threshold: float,
) -> list[dict[str, Any]]:
    try:
        from ocrmac import ocrmac
    except ImportError as exc:
        raise RuntimeError(
            "ocrmac is not installed. Install with:\n"
            "  uv pip install ocrmac\n"
            "or:\n"
            "  pip install ocrmac"
        ) from exc

    kwargs: dict[str, Any] = {"framework": framework}
    if framework == "vision":
        kwargs["recognition_level"] = recognition_level
        if languages:
            kwargs["language_preference"] = languages

    raw_annotations = ocrmac.OCR(str(image_path), **kwargs).recognize()

    parsed: list[dict[str, Any]] = []
    for item in raw_annotations:
        text = ""
        confidence = 1.0
        bbox = None

        if isinstance(item, (list, tuple)):
            if len(item) >= 1:
                text = str(item[0])
            if len(item) >= 2:
                try:
                    confidence = float(item[1])
                except (TypeError, ValueError):
                    confidence = 1.0
            if len(item) >= 3:
                bbox = item[2]
        elif isinstance(item, dict):
            text = str(item.get("text", ""))
            try:
                confidence = float(item.get("confidence", 1.0))
            except (TypeError, ValueError):
                confidence = 1.0
            bbox = item.get("bbox")
        else:
            text = str(item)

        if not text.strip():
            continue
        if framework == "vision" and confidence < confidence_threshold:
            continue

        parsed.append({"text": text, "confidence": confidence, "bbox": bbox})

    return parsed


def compare_doc(
    label_row: dict[str, Any],
    ocr_text: str,
    min_token_recall: float,
) -> dict[str, Any]:
    normalized_ocr_text = normalize_text(ocr_text)
    normalized_ocr_tokens = token_set(normalized_ocr_text)

    medications = label_row.get("medications", [])
    med_total = len(medications)
    med_hits = 0
    med_misses: list[dict[str, Any]] = []

    attrs_total = 0
    attrs_hits = 0
    attr_misses: list[dict[str, Any]] = []

    for med in medications:
        med_name = str(med.get("nombre_medicamento", "")).strip()
        name_match = match_phrase(
            med_name, normalized_ocr_text, normalized_ocr_tokens, min_token_recall
        )
        if name_match.matched:
            med_hits += 1
        else:
            med_misses.append(
                {
                    "medication": med_name,
                    "score": round(name_match.score, 3),
                    "method": name_match.method,
                }
            )

        for field in PRESCRIPTION_FIELDS:
            expected_value = str(med.get(field, "")).strip()
            if not expected_value:
                continue
            attrs_total += 1
            field_match = match_phrase(
                expected_value,
                normalized_ocr_text,
                normalized_ocr_tokens,
                min_token_recall,
            )
            if field_match.matched:
                attrs_hits += 1
            else:
                attr_misses.append(
                    {
                        "medication": med_name,
                        "field": field,
                        "expected": expected_value,
                        "score": round(field_match.score, 3),
                        "method": field_match.method,
                    }
                )

    med_cov = (med_hits / med_total) if med_total else 0.0
    attr_cov = (attrs_hits / attrs_total) if attrs_total else 0.0
    weighted_cov = 0.7 * med_cov + 0.3 * attr_cov

    return {
        "doc_id": label_row.get("doc_id"),
        "image_path": label_row.get("image_path"),
        "medications_total": med_total,
        "medication_name_hits": med_hits,
        "medication_name_coverage": round(med_cov, 4),
        "attributes_total_non_empty": attrs_total,
        "attribute_hits": attrs_hits,
        "attribute_coverage": round(attr_cov, 4),
        "weighted_coverage": round(weighted_cov, 4),
        "missing_medication_names": med_misses,
        "missing_attributes": attr_misses,
    }


def main() -> int:
    args = parse_args()

    if not args.labels_path.exists():
        print(f"Labels file not found: {args.labels_path}", file=sys.stderr)
        return 1

    labels = load_jsonl(args.labels_path)
    prescription_rows = [
        row for row in labels if str(row.get("doc_type", "")).lower() == "prescription"
    ]

    if not prescription_rows:
        print("No prescription rows found in labels JSONL.", file=sys.stderr)
        return 1

    languages = [lang.strip() for lang in args.languages.split(",") if lang.strip()]
    raw_rows: list[dict[str, Any]] = []
    comparison_rows: list[dict[str, Any]] = []

    for row in prescription_rows:
        doc_id = row.get("doc_id", "<unknown>")
        image_path = Path(str(row.get("image_path", "")))
        if not image_path.exists():
            print(f"[WARN] {doc_id}: image file not found: {image_path}")
            continue

        annotations = extract_annotations(
            image_path=image_path,
            framework=args.framework,
            recognition_level=args.recognition_level,
            languages=languages,
            confidence_threshold=args.confidence_threshold,
        )
        ocr_text = "\n".join(item["text"] for item in annotations)

        raw_rows.append(
            {
                "doc_id": doc_id,
                "image_path": str(image_path),
                "framework": args.framework,
                "recognition_level": args.recognition_level,
                "languages": languages,
                "annotations_count": len(annotations),
                "ocr_text": ocr_text,
            }
        )
        comparison_rows.append(compare_doc(row, ocr_text, args.min_token_recall))

    args.raw_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.parent.mkdir(parents=True, exist_ok=True)

    args.raw_path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in raw_rows) + "\n",
        encoding="utf-8",
    )

    med_total = sum(row["medications_total"] for row in comparison_rows)
    med_hits = sum(row["medication_name_hits"] for row in comparison_rows)
    attrs_total = sum(row["attributes_total_non_empty"] for row in comparison_rows)
    attrs_hits = sum(row["attribute_hits"] for row in comparison_rows)

    summary = {
        "docs_processed": len(comparison_rows),
        "framework": args.framework,
        "recognition_level": args.recognition_level,
        "languages": languages,
        "medication_name_coverage": round((med_hits / med_total), 4) if med_total else 0.0,
        "attribute_coverage": round((attrs_hits / attrs_total), 4) if attrs_total else 0.0,
        "medications_total": med_total,
        "medication_name_hits": med_hits,
        "attributes_total_non_empty": attrs_total,
        "attribute_hits": attrs_hits,
    }
    report = {"summary": summary, "documents": comparison_rows}
    args.report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print("OCR compare completed.")
    print(f"- Raw OCR output: {args.raw_path}")
    print(f"- Comparison report: {args.report_path}")
    print(
        "- Medication name coverage: "
        f"{summary['medication_name_hits']}/{summary['medications_total']} "
        f"({summary['medication_name_coverage']:.2%})"
    )
    print(
        "- Attribute coverage: "
        f"{summary['attribute_hits']}/{summary['attributes_total_non_empty']} "
        f"({summary['attribute_coverage']:.2%})"
    )

    for row in comparison_rows:
        print(
            f"- {row['doc_id']}: "
            f"name {row['medication_name_hits']}/{row['medications_total']}, "
            f"attr {row['attribute_hits']}/{row['attributes_total_non_empty']}, "
            f"weighted {row['weighted_coverage']:.2%}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
