# engineering.py
from typing import Any, Dict, List
import math

EPS = 1e-6

# Optional aero integration (soft dependency)
try:
    import aerodynamics
except ImportError:
    aerodynamics = None


# ==========================================================
# MATERIAL HEURISTICS (EXTENDED)
# ==========================================================

MATERIAL_LIMITS = {
    "PLA": {
        "max_slenderness": 10,
        "min_wall_ratio": 0.18,
        "min_feature": 0.6,
        "stiffness_factor": 1.0,
    },
    "PETG": {
        "max_slenderness": 12,
        "min_wall_ratio": 0.15,
        "min_feature": 0.7,
        "stiffness_factor": 0.85,
    },
    "NYLON": {
        "max_slenderness": 14,
        "min_wall_ratio": 0.12,
        "min_feature": 0.8,
        "stiffness_factor": 0.65,
    },
}


def _material_limits(mat: str):
    return MATERIAL_LIMITS.get(mat.upper(), MATERIAL_LIMITS["PLA"])


# ==========================================================
# SCORING UTILITIES
# ==========================================================

SEVERITY_WEIGHT = {
    "low": 0.5,
    "medium": 1.0,
    "high": 2.0,
}


def _issue(severity, score, **kwargs):
    return {
        "severity": severity,
        "score": round(min(1.0, score), 3),
        **kwargs,
    }


# ==========================================================
# STRUCTURAL CHECKS
# ==========================================================

def structural_checks(obj: Any) -> List[Dict[str, Any]]:
    issues = []
    parts = obj.parts if hasattr(obj, "parts") else [obj]

    for p in parts:
        prim = getattr(p, "primitive", "").lower()
        mat = getattr(p, "material", "PLA")
        limits = _material_limits(mat)

        # ------------------
        # Slenderness & Buckling
        # ------------------
        if prim in {"cylinder", "prism"}:
            r = getattr(p, "radius", None)
            h = getattr(p, "height", None)

            if r and h:
                slender = h / max(r, EPS)
                limit = limits["max_slenderness"]

                if slender > limit:
                    excess = slender / limit
                    nonlinear = (excess - 1) ** 2
                    stiffness = limits["stiffness_factor"]

                    score = nonlinear / stiffness
                    severity = (
                        "high" if excess > 1.5 else
                        "medium" if excess > 1.2 else
                        "low"
                    )

                    issues.append(_issue(
                        type="structural",
                        severity=severity,
                        score=score,
                        message=f"Slenderness {slender:.1f} exceeds {limit}",
                        suggestion="Increase radius, reduce height, or add ribs"
                    ))

        # ------------------
        # Hollow wall safety
        # ------------------
        if getattr(p, "hollow", False):
            wall = getattr(p, "wall_thickness", None)
            r = getattr(p, "radius", None)

            if r:
                min_ratio = limits["min_wall_ratio"]
                ratio = 0 if wall is None else wall / r

                if ratio < min_ratio:
                    score = (min_ratio - ratio) / min_ratio
                    issues.append(_issue(
                        type="structural",
                        severity="high",
                        score=score,
                        message="Insufficient wall thickness for hollow part",
                        suggestion="Increase wall thickness or reduce radius"
                    ))

    return issues


# ==========================================================
# MANUFACTURABILITY / PRINTABILITY
# ==========================================================

def manufacturability_checks(obj: Any) -> List[Dict[str, Any]]:
    issues = []
    parts = obj.parts if hasattr(obj, "parts") else [obj]

    for p in parts:
        prim = getattr(p, "primitive", "").lower()
        mat = getattr(p, "material", "PLA")
        limits = _material_limits(mat)

        # ------------------
        # Aspect & taper risk
        # ------------------
        if prim == "cylinder":
            h = getattr(p, "height", 0)
            r = getattr(p, "radius", 0)
            taper = getattr(p, "taper", 0.0)

            if r > 0:
                aspect = h / r
                if aspect > 8 and taper < 0.15:
                    score = (aspect - 8) / 8
                    issues.append(_issue(
                        type="manufacturing",
                        severity="medium",
                        score=score,
                        message="Tall untapered cylinder may require supports",
                        suggestion="Add taper, chamfer, or segment the part"
                    ))

        # ------------------
        # Minimum feature size (material-aware)
        # ------------------
        min_feat = limits["min_feature"]
        for attr in ("radius", "height", "thickness", "wall_thickness"):
            v = getattr(p, attr, None)
            if v is not None and v < min_feat:
                score = (min_feat - v) / min_feat
                issues.append(_issue(
                    type="manufacturing",
                    severity="high",
                    score=score,
                    message=f"Feature '{attr}' below printable threshold for {mat}",
                    suggestion=f"Increase feature size (> {min_feat}mm)"
                ))

    return issues


# ==========================================================
# AERODYNAMIC CHECKS
# ==========================================================

def aerodynamic_checks(obj: Any) -> List[Dict[str, Any]]:
    if aerodynamics is None:
        return []

    issues = []
    result = (
        aerodynamics.analyze_assembly(obj.parts)
        if hasattr(obj, "parts")
        else aerodynamics.analyze(obj)
    )

    for d in result.get("diagnostics", []):
        issues.append(_issue(
            type="aerodynamic",
            severity="medium",
            score=0.6,
            message=d,
            suggestion=""
        ))

    for s in result.get("suggestions", []):
        issues.append(_issue(
            type="aerodynamic",
            severity="low",
            score=0.25,
            message="Optimization opportunity",
            suggestion=s
        ))

    return issues


# ==========================================================
# UNIFIED ENGINEERING ANALYSIS
# ==========================================================

def analyze_engineering(obj: Any) -> Dict[str, Any]:
    structural = structural_checks(obj)
    manufacturing = manufacturability_checks(obj)
    aerodynamic = aerodynamic_checks(obj)

    all_issues = structural + manufacturing + aerodynamic

    weighted_risk = sum(
        i["score"] * SEVERITY_WEIGHT[i["severity"]]
        for i in all_issues
    )

    confidence = math.exp(-weighted_risk)

    max_severity = (
        "high" if any(i["severity"] == "high" for i in all_issues)
        else "medium" if any(i["severity"] == "medium" for i in all_issues)
        else "low"
    )

    return {
        "structural": structural,
        "manufacturing": manufacturing,
        "aerodynamic": aerodynamic,
        "summary": {
            "weighted_risk": round(weighted_risk, 3),
            "confidence": round(confidence, 3),
            "issue_count": len(all_issues),
            "max_severity": max_severity,
        }
    }
