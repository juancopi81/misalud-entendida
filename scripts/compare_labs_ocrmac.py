#!/usr/bin/env python3
"""Run ocrmac on lab report images and compare OCR text to labeled JSONL fields.

This script is for local labeling/evaluation support only (macOS OCR helper),
not for production runtime dependencies.

Usage:
    uv run --with ocrmac python scripts/compare_labs_ocrmac.py
    uv run --with ocrmac python scripts/compare_labs_ocrmac.py --recognition-level fast
    uv run --with ocrmac python scripts/compare_labs_ocrmac.py --framework livetext
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


DEFAULT_LABELS_PATH = Path("eval/lab_labels.jsonl")
DEFAULT_REPORT_PATH = Path("eval/ocrmac_lab_compare_report.json")
DEFAULT_RAW_PATH = Path("eval/ocrmac_lab_raw.jsonl")
LAB_FIELDS = ("valor", "unidad", "rango_referencia")


@dataclass
class MatchResult:
    matched: bool
    score: float
    method: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run OCR with ocrmac for each lab report in eval labels and compare "
            "against ground-truth field values."
        )
    )
    parser.add_argument(
        "--labels-path",
        type=Path,
        default=DEFAULT_LABELS_PATH,
        help=f"Path to lab labels JSONL (default: {DEFAULT_LABELS_PATH})",
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
    parser.add_argument(
        "--include-estado",
        action="store_true",
        help=(
            "Also compare `estado` against OCR text. Disabled by default because "
            "estado is often derived from reference ranges rather than printed verbatim."
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
    normalized = re.sub(r"[^A-Z0-9.%/:-]+", " ", normalized)
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
            "ocrmac is not installed. Run with:\n"
            "  uv run --with ocrmac python scripts/compare_labs_ocrmac.py"
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
    combined_ocr_text: str,
    min_token_recall: float,
    include_estado: bool,
) -> dict[str, Any]:
    normalized_ocr_text = normalize_text(combined_ocr_text)
    normalized_ocr_tokens = token_set(normalized_ocr_text)

    results = label_row.get("results", [])
    tests_total = len(results)
    test_hits = 0
    test_misses: list[dict[str, Any]] = []

    fields_total = 0
    field_hits = 0
    field_misses: list[dict[str, Any]] = []

    fields = list(LAB_FIELDS)
    if include_estado:
        fields.append("estado")

    for lab in results:
        test_name = str(lab.get("nombre_prueba", "")).strip()
        test_match = match_phrase(
            test_name, normalized_ocr_text, normalized_ocr_tokens, min_token_recall
        )
        if test_match.matched:
            test_hits += 1
        else:
            test_misses.append(
                {
                    "nombre_prueba": test_name,
                    "score": round(test_match.score, 3),
                    "method": test_match.method,
                }
            )

        for field in fields:
            expected_value = str(lab.get(field, "")).strip()
            if not expected_value:
                continue
            fields_total += 1
            value_match = match_phrase(
                expected_value, normalized_ocr_text, normalized_ocr_tokens, min_token_recall
            )
            if value_match.matched:
                field_hits += 1
            else:
                field_misses.append(
                    {
                        "nombre_prueba": test_name,
                        "field": field,
                        "expected": expected_value,
                        "score": round(value_match.score, 3),
                        "method": value_match.method,
                    }
                )

    test_cov = (test_hits / tests_total) if tests_total else 0.0
    field_cov = (field_hits / fields_total) if fields_total else 0.0
    weighted_cov = 0.6 * test_cov + 0.4 * field_cov

    return {
        "doc_id": label_row.get("doc_id"),
        "image_paths": label_row.get("image_paths", []),
        "tests_total": tests_total,
        "test_name_hits": test_hits,
        "test_name_coverage": round(test_cov, 4),
        "fields_total_non_empty": fields_total,
        "field_hits": field_hits,
        "field_coverage": round(field_cov, 4),
        "weighted_coverage": round(weighted_cov, 4),
        "missing_tests": test_misses,
        "missing_fields": field_misses,
    }


def main() -> int:
    args = parse_args()

    if not args.labels_path.exists():
        print(f"Labels file not found: {args.labels_path}", file=sys.stderr)
        return 1

    labels = load_jsonl(args.labels_path)
    lab_rows = [row for row in labels if str(row.get("doc_type", "")).lower() == "lab"]
    if not lab_rows:
        print("No lab rows found in labels JSONL.", file=sys.stderr)
        return 1

    languages = [lang.strip() for lang in args.languages.split(",") if lang.strip()]

    raw_rows: list[dict[str, Any]] = []
    comparison_rows: list[dict[str, Any]] = []

    for row in lab_rows:
        doc_id = row.get("doc_id", "<unknown>")
        image_paths = [Path(str(p)) for p in row.get("image_paths", [])]
        missing_paths = [str(p) for p in image_paths if not p.exists()]
        if missing_paths:
            print(f"[WARN] {doc_id}: missing image paths: {missing_paths}")
            continue

        page_entries: list[dict[str, Any]] = []
        page_texts: list[str] = []
        for page_path in image_paths:
            annotations = extract_annotations(
                image_path=page_path,
                framework=args.framework,
                recognition_level=args.recognition_level,
                languages=languages,
                confidence_threshold=args.confidence_threshold,
            )
            page_text = "\n".join(item["text"] for item in annotations)
            page_entries.append(
                {
                    "image_path": str(page_path),
                    "annotations_count": len(annotations),
                    "ocr_text": page_text,
                }
            )
            page_texts.append(page_text)

        combined_ocr_text = "\n--- PAGE BREAK ---\n".join(page_texts)

        raw_rows.append(
            {
                "doc_id": doc_id,
                "framework": args.framework,
                "recognition_level": args.recognition_level,
                "languages": languages,
                "pages": page_entries,
                "combined_ocr_text": combined_ocr_text,
            }
        )
        comparison_rows.append(
            compare_doc(
                label_row=row,
                combined_ocr_text=combined_ocr_text,
                min_token_recall=args.min_token_recall,
                include_estado=args.include_estado,
            )
        )

    args.raw_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.parent.mkdir(parents=True, exist_ok=True)

    args.raw_path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in raw_rows) + "\n",
        encoding="utf-8",
    )

    tests_total = sum(row["tests_total"] for row in comparison_rows)
    test_hits = sum(row["test_name_hits"] for row in comparison_rows)
    fields_total = sum(row["fields_total_non_empty"] for row in comparison_rows)
    field_hits = sum(row["field_hits"] for row in comparison_rows)

    summary = {
        "docs_processed": len(comparison_rows),
        "framework": args.framework,
        "recognition_level": args.recognition_level,
        "languages": languages,
        "include_estado": args.include_estado,
        "test_name_coverage": round((test_hits / tests_total), 4) if tests_total else 0.0,
        "field_coverage": round((field_hits / fields_total), 4) if fields_total else 0.0,
        "tests_total": tests_total,
        "test_name_hits": test_hits,
        "fields_total_non_empty": fields_total,
        "field_hits": field_hits,
    }
    report = {"summary": summary, "documents": comparison_rows}
    args.report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print("OCR compare completed.")
    print(f"- Raw OCR output: {args.raw_path}")
    print(f"- Comparison report: {args.report_path}")
    print(
        "- Test name coverage: "
        f"{summary['test_name_hits']}/{summary['tests_total']} "
        f"({summary['test_name_coverage']:.2%})"
    )
    print(
        "- Field coverage: "
        f"{summary['field_hits']}/{summary['fields_total_non_empty']} "
        f"({summary['field_coverage']:.2%})"
    )
    for row in comparison_rows:
        print(
            f"- {row['doc_id']}: "
            f"tests {row['test_name_hits']}/{row['tests_total']}, "
            f"fields {row['field_hits']}/{row['fields_total_non_empty']}, "
            f"weighted {row['weighted_coverage']:.2%}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
