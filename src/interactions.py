"""Drug interaction checker for common dangerous combinations.

This module provides a hardcoded database of known drug interactions
commonly encountered in Colombian healthcare settings. It's designed
to alert patients about potential risks when tracking multiple medications.

Note: This is not a comprehensive drug interaction database. Always
consult a healthcare professional for medical advice.
"""

from dataclasses import dataclass


@dataclass
class Interaction:
    """A drug interaction warning."""

    drugs: tuple[str, str]
    severity: str  # "alta", "media", "baja"
    warning: str


# Common dangerous drug interactions
# Keys are sorted tuples of lowercase drug names
KNOWN_INTERACTIONS: dict[tuple[str, str], dict[str, str]] = {
    # High severity - bleeding risk
    ("aspirina", "warfarina"): {
        "severity": "alta",
        "warning": "Aumenta significativamente el riesgo de sangrado. Consulte a su médico inmediatamente.",
    },
    ("ibuprofeno", "warfarina"): {
        "severity": "alta",
        "warning": "Aumenta el riesgo de sangrado gastrointestinal. Evite esta combinación.",
    },
    ("aspirina", "clopidogrel"): {
        "severity": "alta",
        "warning": "Alto riesgo de sangrado. Solo use bajo supervisión médica estricta.",
    },
    # High severity - metabolic
    ("alcohol", "metformina"): {
        "severity": "alta",
        "warning": "Riesgo de acidosis láctica, una condición grave. Evite el alcohol.",
    },
    ("metformina", "contraste yodado"): {
        "severity": "alta",
        "warning": "Suspenda metformina antes de estudios con contraste. Consulte a su médico.",
    },
    # High severity - cardiac
    ("digoxina", "amiodarona"): {
        "severity": "alta",
        "warning": "Puede causar toxicidad por digoxina. Requiere ajuste de dosis.",
    },
    ("atenolol", "verapamilo"): {
        "severity": "alta",
        "warning": "Riesgo de bradicardia severa y bloqueo cardíaco. Evite esta combinación.",
    },
    # Medium severity - potassium/renal
    ("enalapril", "potasio"): {
        "severity": "media",
        "warning": "Puede aumentar el potasio en sangre (hiperpotasemia). Requiere monitoreo.",
    },
    ("losartan", "potasio"): {
        "severity": "media",
        "warning": "Puede aumentar el potasio en sangre. Requiere monitoreo periódico.",
    },
    ("enalapril", "espironolactona"): {
        "severity": "media",
        "warning": "Riesgo de hiperpotasemia. Monitoree niveles de potasio regularmente.",
    },
    ("losartan", "espironolactona"): {
        "severity": "media",
        "warning": "Riesgo de hiperpotasemia. Requiere control de laboratorio.",
    },
    # Medium severity - blood sugar
    ("glibenclamida", "alcohol"): {
        "severity": "media",
        "warning": "El alcohol puede causar hipoglucemia severa. Limite el consumo.",
    },
    ("insulina", "alcohol"): {
        "severity": "media",
        "warning": "El alcohol puede enmascarar síntomas de hipoglucemia. Precaución.",
    },
    # Medium severity - CNS
    ("alprazolam", "alcohol"): {
        "severity": "alta",
        "warning": "Combinación peligrosa. Puede causar sedación excesiva y depresión respiratoria.",
    },
    ("clonazepam", "alcohol"): {
        "severity": "alta",
        "warning": "Riesgo de sedación profunda y problemas respiratorios. No combine.",
    },
    ("tramadol", "alcohol"): {
        "severity": "alta",
        "warning": "Aumenta el riesgo de depresión respiratoria. Evite el alcohol.",
    },
    # Medium severity - antibiotics
    ("metronidazol", "alcohol"): {
        "severity": "media",
        "warning": "Causa reacción tipo disulfiram (náuseas, vómitos). No consuma alcohol.",
    },
    ("ciprofloxacino", "antiácidos"): {
        "severity": "media",
        "warning": "Los antiácidos reducen la absorción. Tome con 2 horas de diferencia.",
    },
    # Low severity but important
    ("levotiroxina", "calcio"): {
        "severity": "baja",
        "warning": "El calcio reduce la absorción. Tome con 4 horas de diferencia.",
    },
    ("levotiroxina", "hierro"): {
        "severity": "baja",
        "warning": "El hierro reduce la absorción. Tome con 4 horas de diferencia.",
    },
    ("omeprazol", "clopidogrel"): {
        "severity": "media",
        "warning": "Omeprazol puede reducir la efectividad del clopidogrel. Consulte alternativas.",
    },
}


def normalize_drug_name(name: str) -> str:
    """Normalize a drug name for comparison.

    Removes common suffixes, converts to lowercase, and handles
    common variations in drug naming.
    """
    name = name.lower().strip()

    # Remove common suffixes
    suffixes_to_remove = [
        " tabletas",
        " tableta",
        " capsulas",
        " capsula",
        " mg",
        " ml",
        " gotas",
        " jarabe",
        " suspension",
        " inyectable",
    ]
    for suffix in suffixes_to_remove:
        if name.endswith(suffix):
            name = name[: -len(suffix)]

    # Map common brand names to generic names (Colombian market)
    brand_to_generic = {
        "glucophage": "metformina",
        "glafornil": "metformina",
        "aspirina": "aspirina",  # keep as is
        "cardioaspirina": "aspirina",
        "coumadin": "warfarina",
        "sintrom": "acenocumarol",
        "plavix": "clopidogrel",
        "lipitor": "atorvastatina",
        "crestor": "rosuvastatina",
        "viagra": "sildenafil",
        "cialis": "tadalafil",
        "rivotril": "clonazepam",
        "alprazolam": "alprazolam",
        "xanax": "alprazolam",
        "eutirox": "levotiroxina",
        "synthroid": "levotiroxina",
    }

    return brand_to_generic.get(name, name)


def check_interactions(medications: list[str]) -> list[Interaction]:
    """Check for known drug interactions among a list of medications.

    Args:
        medications: List of medication names (can be brand or generic names)

    Returns:
        List of Interaction objects for any detected interactions

    Example:
        >>> interactions = check_interactions(["warfarina", "aspirina"])
        >>> for i in interactions:
        ...     print(f"[{i.severity.upper()}] {i.drugs[0]} + {i.drugs[1]}")
        ...     print(f"  {i.warning}")
    """
    if len(medications) < 2:
        return []

    # Normalize all medication names
    normalized = [(med, normalize_drug_name(med)) for med in medications]

    warnings = []

    # Check each pair of medications
    for i, (orig1, norm1) in enumerate(normalized):
        for orig2, norm2 in normalized[i + 1 :]:
            # Create sorted key for lookup
            key = tuple(sorted([norm1, norm2]))

            if key in KNOWN_INTERACTIONS:
                interaction_data = KNOWN_INTERACTIONS[key]
                warnings.append(
                    Interaction(
                        drugs=(orig1, orig2),
                        severity=interaction_data["severity"],
                        warning=interaction_data["warning"],
                    )
                )

    # Sort by severity (alta first, then media, then baja)
    severity_order = {"alta": 0, "media": 1, "baja": 2}
    warnings.sort(key=lambda x: severity_order.get(x.severity, 3))

    return warnings


def main():
    """Smoke test for interaction checker."""
    print("=" * 60)
    print("Drug Interaction Checker - Smoke Test")
    print("=" * 60)

    # Test 1: High severity interaction
    print("\n[Test 1] Warfarina + Aspirina")
    meds = ["Warfarina", "Aspirina"]
    results = check_interactions(meds)
    for r in results:
        print(f"  [{r.severity.upper()}] {r.drugs[0]} + {r.drugs[1]}")
        print(f"  {r.warning}")

    # Test 2: Multiple medications
    print("\n[Test 2] Multiple medications")
    meds = ["Metformina", "Losartan", "Potasio", "Alcohol"]
    results = check_interactions(meds)
    print(f"  Found {len(results)} interactions:")
    for r in results:
        print(f"  [{r.severity.upper()}] {r.drugs[0]} + {r.drugs[1]}")

    # Test 3: No interactions
    print("\n[Test 3] No known interactions")
    meds = ["Acetaminofen", "Vitamina C"]
    results = check_interactions(meds)
    print(f"  Found {len(results)} interactions")

    # Test 4: Brand name resolution
    print("\n[Test 4] Brand names (Glucophage = Metformina)")
    meds = ["Glucophage", "Alcohol"]
    results = check_interactions(meds)
    for r in results:
        print(f"  [{r.severity.upper()}] {r.drugs[0]} + {r.drugs[1]}")
        print(f"  {r.warning}")

    print("\n" + "=" * 60)
    print("Smoke test completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
