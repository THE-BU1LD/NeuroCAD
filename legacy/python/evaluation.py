# evaluation.py
from typing import Dict, Any

from physics import structural_diagnostics, assembly_diagnostics
from fatigue import fatigue_diagnostics


# --------------------------------------------------
# CONFIGURABLE WEIGHTS
# --------------------------------------------------

WEIGHTS = {
    "physics": 0.4,
    "fatigue": 0.3,
    "learning": 0.3,
}

# Risk thresholds
PASS_THRESHOLD = 0.35
FAIL_THRESHOLD = 0.7


# --------------------------------------------------
# NORMALIZATION HELPERS
# --------------------------------------------------

def normalize_risk(value: float, max_value: float) -> float:
    return min(1.0, max(0.0, value / max_value))


# --------------------------------------------------
# CORE EVALUATION
# --------------------------------------------------

def evaluate_design(
    assembly,
    learned_risk: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    Returns a single verdict for the entire design.
    """

    # -----------------------
    # Physics
    # -----------------------
    assembly_diag = assembly_diagnostics(assembly)
    physics_risk = normalize_risk(
        assembly_diag["max_part_risk"], max_value=5
    )

    # -----------------------
    # Fatigue
    # -----------------------
    fatigue_scores = []
    fatigue_notes = []

    for part in assembly.parts:
        f = fatigue_diagnostics(part)
        fatigue_scores.append(f["fatigue_risk"])
        fatigue_notes.extend(f["notes"])

    fatigue_risk = (
        sum(fatigue_scores) / len(fatigue_scores)
        if fatigue_scores
        else 0.0
    )

    # -----------------------
    # Learned risk
    # -----------------------
    learned_risk_value = 0.0
    learned_confidence = "none"
    learned_notes = []

    if learned_risk:
        learned_risk_value = learned_risk.get("risk", 0.0)
        learned_confidence = learned_risk.get("confidence", "low")
        learned_notes = learned_risk.get("notes", [])

    # -----------------------
    # Weighted fusion
    # -----------------------
    final_score = (
        WEIGHTS["physics"] * physics_risk
        + WEIGHTS["fatigue"] * fatigue_risk
        + WEIGHTS["learning"] * learned_risk_value
    )

    # -----------------------
    # Verdict
    # -----------------------
    if final_score < PASS_THRESHOLD:
        verdict = "PASS"
    elif final_score < FAIL_THRESHOLD:
        verdict = "CAUTION"
    else:
        verdict = "FAIL"

    return {
        "verdict": verdict,
        "score": round(final_score, 3),
        "confidence": learned_confidence,
        "breakdown": {
            "physics_risk": round(physics_risk, 3),
            "fatigue_risk": round(fatigue_risk, 3),
            "learned_risk": round(learned_risk_value, 3),
        },
        "explanations": sorted(
            set(
                assembly_diag["unique_risks"]
                + fatigue_notes
                + learned_notes
            )
        ),
    }
