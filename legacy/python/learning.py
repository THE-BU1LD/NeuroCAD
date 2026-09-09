"""
learning.py

Improved DesignLearner:
- Use dataclass for per-signature stats
- Stable exponential moving mean/variance (ema and ema_sq)
- Configurable priors and decay
- Serialization (to/from JSON)
- Better risk scoring using Bayesian smoothing (Beta posterior mean)
- Cleaner signature extraction and safety around missing attributes
- More actionable guidance, sorting by severity
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from collections import defaultdict
from typing import Any, Dict, List, Tuple, Optional
import math
import json


# Tunable defaults
DEFAULT_DECAY = 0.85
DEFAULT_PRIOR_SUCCESS = 1.0
DEFAULT_PRIOR_FAILURE = 1.0
MIN_SEEN_CONFIDENT = 6
CONFIDENCE_SCALE_SEEN = 25.0


@dataclass
class PartStats:
    seen: int = 0
    successes: int = 0
    failures: int = 0

    # Exponential moving averages for mean and mean-of-squares to compute variance
    ema_mass: Optional[float] = None
    ema_mass_sq: Optional[float] = None

    ema_drag: Optional[float] = None
    ema_drag_sq: Optional[float] = None

    aero_helpful: int = 0
    aero_harmful: int = 0

    def to_serializable(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PartStats":
        return cls(**d)


class DesignLearner:
    """Adaptive learning engine for CAD agents.

    Stores statistics keyed by a compact signature of primitive/material/hollow/aero/slender_bin.
    Provides observation ingestion, risk scoring, guidance extraction, and simple persistence.
    """

    def __init__(
        self,
        decay: float = DEFAULT_DECAY,
        prior_success: float = DEFAULT_PRIOR_SUCCESS,
        prior_failure: float = DEFAULT_PRIOR_FAILURE,
    ) -> None:
        self.decay = float(decay)
        self.prior_success = float(prior_success)
        self.prior_failure = float(prior_failure)

        # stats keyed by signature tuple -> PartStats
        self.stats: Dict[Tuple[Any, ...], PartStats] = defaultdict(PartStats)

    # ------------------------- Signature extraction -------------------------
    def _safe_get(self, obj: Any, attr: str, default: Any = None) -> Any:
        return getattr(obj, attr, default) if obj is not None else default

    def _signature(self, p: Any) -> Tuple[Any, ...]:
        primitive = self._safe_get(p, "primitive", "unknown")
        material = self._safe_get(p, "material", "PLA")
        hollow = bool(self._safe_get(p, "hollow", False))
        aero = bool(self._safe_get(p, "aero", False))

        r = self._safe_get(p, "radius", None)
        h = self._safe_get(p, "height", None)

        slenderness = 0.0
        try:
            if r and h and float(r) > 0:
                slenderness = float(h) / float(r)
        except Exception:
            slenderness = 0.0

        if slenderness < 3:
            slender_bin = "stubby"
        elif slenderness < 8:
            slender_bin = "moderate"
        else:
            slender_bin = "slender"

        return (primitive, material, hollow, aero, slender_bin)

    # ------------------------- Observation ingestion -------------------------
    def observe(
        self,
        obj: Any,
        success: bool,
        mass: Optional[float] = None,
        drag: Optional[float] = None,
    ) -> None:
        """Ingest an observation. `obj` can be a part or a container with `.parts`.

        Updates counts, EMAs for mass/drag, and aero helpful/harmful counters.
        """
        parts = getattr(obj, "parts", None) or [obj]

        for p in parts:
            sig = self._signature(p)
            s = self.stats[sig]

            s.seen += 1
            if success:
                s.successes += 1
            else:
                s.failures += 1

            # Update EMA for mass
            if mass is not None:
                if s.ema_mass is None:
                    s.ema_mass = float(mass)
                    s.ema_mass_sq = float(mass) * float(mass)
                else:
                    a = self.decay
                    s.ema_mass = a * s.ema_mass + (1.0 - a) * float(mass)
                    s.ema_mass_sq = a * s.ema_mass_sq + (1.0 - a) * (float(mass) ** 2)

            # Update EMA for drag
            if drag is not None:
                if s.ema_drag is None:
                    s.ema_drag = float(drag)
                    s.ema_drag_sq = float(drag) * float(drag)
                else:
                    a = self.decay
                    s.ema_drag = a * s.ema_drag + (1.0 - a) * float(drag)
                    s.ema_drag_sq = a * s.ema_drag_sq + (1.0 - a) * (float(drag) ** 2)

            # Aero effect counters
            if getattr(p, "aero", False):
                if success:
                    s.aero_helpful += 1
                else:
                    s.aero_harmful += 1

    # ------------------------- Risk / confidence utilities -------------------------
    def _posterior_failure_mean(self, s: PartStats) -> float:
        # Beta posterior mean: (failures + prior_failure) / (seen + prior_failure + prior_success)
        denom = s.seen + self.prior_failure + self.prior_success
        if denom <= 0:
            return 0.5
        return (s.failures + self.prior_failure) / denom

    def _ema_variance(self, mean: Optional[float], mean_sq: Optional[float]) -> float:
        if mean is None or mean_sq is None:
            return 0.0
        var = mean_sq - (mean * mean)
        return max(0.0, var)

    def _confidence(self, s: PartStats) -> float:
        # Confidence scales with seen observations, saturates at 1.
        return min(1.0, float(s.seen) / CONFIDENCE_SCALE_SEEN)

    def risk_score(self, p: Any) -> float:
        """Return a risk score in [0, 1].

        Uses Bayesian posterior mean for failure probability, scaled by confidence and
        lightly penalised for high variance in mass/drag.
        """
        sig = self._signature(p)
        s = self.stats.get(sig)

        if s is None or s.seen < 2:
            return 0.30  # cautious cold-start

        failure_mean = self._posterior_failure_mean(s)
        confidence = self._confidence(s)

        mass_var = self._ema_variance(s.ema_mass, s.ema_mass_sq)
        drag_var = self._ema_variance(s.ema_drag, s.ema_drag_sq)

        stability_penalty = 0.0
        # thresholds chosen conservatively; these can be tuned by the outer system
        if mass_var > 1e5:
            stability_penalty += 0.10
        if drag_var > 0.5:
            stability_penalty += 0.10

        score = failure_mean * confidence + stability_penalty
        return max(0.0, min(1.0, score))

    def risk_report(self, p: Any) -> Dict[str, Any]:
        sig = self._signature(p)
        s = self.stats.get(sig)

        if s is None or s.seen < MIN_SEEN_CONFIDENT:
            return {
                "risk": 0.30,
                "confidence": "low",
                "notes": ["Insufficient historical data"],
            }

        failure_mean = self._posterior_failure_mean(s)
        confidence = round(self._confidence(s), 3)

        mass_var = self._ema_variance(s.ema_mass, s.ema_mass_sq)
        drag_var = self._ema_variance(s.ema_drag, s.ema_drag_sq)

        notes: List[str] = []
        if failure_mean > 0.6:
            notes.append("Historically high failure probability")
        if s.aero_harmful > s.aero_helpful:
            notes.append("Aerodynamics often degrades performance")
        if s.ema_mass and s.ema_mass > 800:
            notes.append("Designs frequently overweight")
        if mass_var > 1e5:
            notes.append("High mass instability across iterations")

        return {
            "risk": round(float(failure_mean), 3),
            "confidence": confidence,
            "notes": notes,
            "seen": s.seen,
            "aero_helpful": s.aero_helpful,
            "aero_harmful": s.aero_harmful,
        }

    # ------------------------- Guidance extraction -------------------------
    def design_biases(self, min_seen: int = 6) -> List[str]:
        tips: List[Tuple[float, str]] = []

        for sig, s in self.stats.items():
            if s.seen < min_seen:
                continue

            prim, mat, hollow, aero, slender = sig
            fail_rate = float(s.failures) / float(s.seen) if s.seen > 0 else 0.0

            severity = 0.0
            if fail_rate > 0.65:
                severity += 2.0
            severity += self._confidence(s)

            if fail_rate > 0.65:
                msg = (
                    f"Avoid {prim} ({slender}) in {mat} [hollow={hollow}, aero={aero}] — "
                    f"high failure rate ({fail_rate:.2f})"
                )
                tips.append((severity, msg))

            if s.aero_helpful >= 3 and s.aero_harmful == 0:
                msg = f"Aerodynamics consistently improves {prim} designs in {mat}"
                tips.append((severity, msg))

            if s.ema_mass and s.ema_mass > 900:
                msg = f"{prim} designs tend to be overweight in {mat} — consider scale reduction or hollowing"
                tips.append((severity, msg))

        # sort tips by severity (descending) and return messages only
        tips_sorted = sorted(tips, key=lambda t: -t[0])
        return [t[1] for t in tips_sorted]

    # ------------------------- Summaries / utilities -------------------------
    def summary(self) -> List[str]:
        out: List[str] = []
        for sig, s in sorted(self.stats.items(), key=lambda kv: -kv[1].seen):
            prim, mat, hollow, aero, slender = sig
            failures = s.failures + self.prior_failure
            successes = s.successes + self.prior_success
            risk = failures / (failures + successes) if (failures + successes) > 0 else 0.0

            out.append(
                f"{prim}/{mat} (hollow={hollow}, aero={aero}, {slender}) → "
                f"{s.successes}✓ {s.failures}✗ risk={risk:.2f} seen={s.seen}"
            )
        return out

    # ------------------------- Persistence -------------------------
    def to_json(self) -> str:
        # Convert the stats dict with tuple keys to a serializable dict
        serial = {"decay": self.decay, "prior_success": self.prior_success, "prior_failure": self.prior_failure, "stats": {}}
        for sig, s in self.stats.items():
            key = "|".join(map(str, sig))
            serial["stats"][key] = s.to_serializable()
        return json.dumps(serial)

    @classmethod
    def from_json(cls, payload: str) -> "DesignLearner":
        data = json.loads(payload)
        dl = cls(decay=data.get("decay", DEFAULT_DECAY), prior_success=data.get("prior_success", DEFAULT_PRIOR_SUCCESS), prior_failure=data.get("prior_failure", DEFAULT_PRIOR_FAILURE))
        stats = data.get("stats", {})
        for key, sdict in stats.items():
            sig = tuple(key.split("|"))
            # restore boolean and numeric fields where appropriate
            # keys in sig are (primitive, material, hollow, aero, slender_bin)
            # hollow and aero may be strings; attempt to coerce
            try:
                hollow = sdict.get("hollow")
            except Exception:
                hollow = None
            dl.stats[sig] = PartStats.from_dict(sdict)
        return dl

    def save(self, path: str) -> None:
        with open(path, "w") as f:
            f.write(self.to_json())

    @classmethod
    def load(cls, path: str) -> "DesignLearner":
        with open(path, "r") as f:
            return cls.from_json(f.read())
