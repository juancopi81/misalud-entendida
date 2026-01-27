#!/usr/bin/env python3
"""
Integration validation script for drug name matching.

Validates match_drug_to_cum against the REAL CUM API (requires internet).
For fast, offline unit tests, use: uv run pytest tests/test_drug_matcher.py

Run all validation cases:
    uv run python scripts/validate_drug_matcher.py --all

Validate specific drug:
    uv run python scripts/validate_drug_matcher.py --drug "LOSARTAN 50MG"

Verbose output:
    uv run python scripts/validate_drug_matcher.py --all --verbose
"""

import argparse
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.drug_matcher import DrugMatchResult, match_drug_to_cum

# Match types that indicate a successful match
SUCCESS_MATCH_TYPES = ("exact", "active_ingredient", "fuzzy")

# Test cases: (input, expected_match_type, expected_ingredient_contains)
TEST_CASES = [
    # Basic active ingredient
    ("METFORMINA", "active_ingredient", "METFORMINA"),
    # Product with dosage
    ("LOSARTAN 50MG", "exact", "LOSARTAN"),
    # Case insensitive
    ("losartan", "exact", "LOSARTAN"),
    # Complex name with form words
    ("ACETAMINOFEN 500 MG TABLETAS", "active_ingredient", "ACETAMINOFEN"),
    # Nonexistent drug - should fail gracefully
    ("NONEXISTENT_DRUG_XYZ_12345", "none", None),
    # Empty input
    ("", "none", None),
    # Just dosage (edge case)
    ("500MG", "none", None),
]


def validate_single_drug(drug_name: str, verbose: bool = False) -> DrugMatchResult:
    """Validate matching a single drug against real API and print results."""
    print(f"\n{'='*60}")
    print(f"Testing: '{drug_name}'")
    print("=" * 60)

    result = match_drug_to_cum(drug_name)

    print(f"  Match type: {result.match_type}")
    print(f"  Confidence: {result.confidence:.0%}")
    print(f"  Normalized: {result.query_normalized}")

    if result.record:
        print(f"\n  Best Match:")
        print(f"    Product: {result.record.producto}")
        print(f"    Ingredient: {result.record.principioactivo}")
        print(f"    Concentration: {result.record.concentracion_valor}{result.record.unidadmedida}")
        print(f"    Form: {result.record.formafarmaceutica}")
        print(f"    Status: {result.record.estadoregistro}")
        print(f"    Expediente: {result.record.expedientecum}")

        if result.other_matches:
            print(f"\n  Other matches ({len(result.other_matches)}):")
            for i, alt in enumerate(result.other_matches[:3], 1):
                print(f"    {i}. {alt.producto} ({alt.principioactivo})")
    else:
        print("  No match found")

    if verbose and result.debug_info:
        print(f"\n  Debug info:")
        for key, value in result.debug_info.items():
            print(f"    {key}: {value}")

    return result


def run_all_validations(verbose: bool = False) -> tuple[int, int]:
    """Run all validation cases and return (passed, failed) counts."""
    passed = 0
    failed = 0

    print("\n" + "=" * 60)
    print("RUNNING ALL VALIDATION CASES")
    print("=" * 60)

    for drug_input, expected_type, expected_ingredient in TEST_CASES:
        print(f"\n[Validate] '{drug_input}'")
        print(f"  Expected: match_type={expected_type}, ingredient contains '{expected_ingredient}'")

        result = match_drug_to_cum(drug_input)

        # Check match type - accept any success type if we expected a success type
        if expected_type in SUCCESS_MATCH_TYPES:
            type_ok = result.match_type in SUCCESS_MATCH_TYPES
        else:
            type_ok = result.match_type == expected_type

        # Check ingredient - use explicit None check to handle empty string edge case
        if expected_ingredient is not None:
            ingredient_ok = (
                result.record is not None
                and expected_ingredient in result.record.principioactivo.upper()
            )
        else:
            # Expected no match
            ingredient_ok = result.record is None

        # Report result
        if type_ok and ingredient_ok:
            print(f"  PASS: Got match_type={result.match_type}")
            if result.record:
                print(f"        Product: {result.record.producto}")
                print(f"        Ingredient: {result.record.principioactivo}")
            passed += 1
        else:
            print(f"  FAIL:")
            print(f"    Got match_type={result.match_type} (expected {expected_type})")
            if result.record:
                print(f"    Got ingredient={result.record.principioactivo}")
            else:
                print(f"    Got no match")
            failed += 1

        if verbose and result.debug_info:
            print(f"  Debug: {result.debug_info}")

    return passed, failed


def main():
    parser = argparse.ArgumentParser(
        description="Test drug name matching functionality",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --all              Run all test cases
  %(prog)s --drug "LOSARTAN"  Test a specific drug
  %(prog)s --all --verbose    Run all tests with debug output
        """,
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all predefined test cases",
    )
    parser.add_argument(
        "--drug",
        type=str,
        help="Test a specific drug name",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show verbose output including debug info",
    )

    args = parser.parse_args()

    if not args.all and not args.drug:
        parser.print_help()
        print("\nError: Must specify --all or --drug")
        sys.exit(1)

    if args.all:
        passed, failed = run_all_validations(verbose=args.verbose)
        print("\n" + "=" * 60)
        print(f"RESULTS: {passed} passed, {failed} failed")
        print("=" * 60)
        sys.exit(0 if failed == 0 else 1)

    if args.drug:
        validate_single_drug(args.drug, verbose=args.verbose)
        sys.exit(0)


if __name__ == "__main__":
    main()
