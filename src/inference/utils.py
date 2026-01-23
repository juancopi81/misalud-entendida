"""Utility functions for MedGemma inference."""

import json

from src.logger import get_logger

logger = get_logger(__name__)


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
    raw_len = len(response or "")

    # Strategy 1: Handle complete thinking mode
    if "<unused95>" in response:
        thinking, remainder = response.split("<unused95>", 1)
        logger.debug(
            "Thinking segment detected (len=%d, raw_len=%d)", len(thinking), raw_len
        )
        response = remainder.strip()
    else:
        logger.debug("No thinking delimiter found (raw_len=%d)", raw_len)

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
        logger.debug("Response is valid JSON shape (len=%d)", len(stripped))
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
                logger.debug("Extracted JSON candidate (len=%d)", len(candidate))
                return candidate
        except json.JSONDecodeError:
            continue

    # Strategy 4: Return cleaned response (let caller handle parse failure)
    open_braces = stripped.count("{")
    close_braces = stripped.count("}")
    open_brackets = stripped.count("[")
    close_brackets = stripped.count("]")
    if open_braces != close_braces or open_brackets != close_brackets:
        logger.debug(
            "Unbalanced JSON delimiters: {=%d, }=%d, [=%d, ]=%d",
            open_braces,
            close_braces,
            open_brackets,
            close_brackets,
        )
    logger.debug("Returning stripped response (len=%d)", len(stripped))
    return stripped
