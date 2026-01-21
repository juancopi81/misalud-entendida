"""Utility functions for MedGemma inference."""

import json


def extract_json_from_response(response: str) -> str:
    """Extract JSON from model response, handling thinking mode gracefully.

    MedGemma 1.5 may enter "thinking mode" with format:
    <unused94>thought\n...thinking...<unused95>...actual JSON...

    This function handles:
    1. Normal thinking mode (split on <unused95>)
    2. Truncated thinking (extract JSON from anywhere)
    3. Raw JSON output (no thinking)

    Args:
        response: Raw model output

    Returns:
        Extracted JSON string, or original response if no JSON found
    """
    # Strategy 1: Handle complete thinking mode
    if "<unused95>" in response:
        response = response.split("<unused95>", 1)[1].strip()

    # Strategy 2: Strip markdown code fences if present
    stripped = response.strip()
    if stripped.startswith("```"):
        # Remove opening fence (```json or ```)
        lines = stripped.split("\n", 1)
        if len(lines) > 1:
            stripped = lines[1]
        # Remove closing fence
        if stripped.rstrip().endswith("```"):
            stripped = stripped.rstrip()[:-3].rstrip()

    # If response looks like valid JSON, return it
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped

    # Strategy 3: Extract JSON object containing expected keys
    # Find all { } pairs and try to parse them
    brace_depth = 0
    json_start = -1
    json_candidates = []

    for i, char in enumerate(stripped):
        if char == "{":
            if brace_depth == 0:
                json_start = i
            brace_depth += 1
        elif char == "}":
            brace_depth -= 1
            if brace_depth == 0 and json_start != -1:
                candidate = stripped[json_start : i + 1]
                json_candidates.append(candidate)
                json_start = -1

    # Try candidates from last to first (answer usually at end)
    for candidate in reversed(json_candidates):
        try:
            parsed = json.loads(candidate)
            # Verify it has expected keys
            if "medicamentos" in parsed or "resultados" in parsed:
                return candidate
        except json.JSONDecodeError:
            continue

    # Strategy 4: Return cleaned response (let caller handle parse failure)
    return stripped
