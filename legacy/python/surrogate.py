# surrogate.py
"""
Production-grade surrogate intelligence model.

Upgrades over baseline:
- numerically stable normalization
- KD-like neighbor pruning via cached normalized params
- soft failure bias via Bayesian smoothing
- uncertainty calibrated with effective sample size
- distance-aware confidence + reliability separation
- JSON persistence hooks
"""

import math
import json
from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional


# ==================================================
# DATA STRUCTURES
# ==================================================

@dataclass
class MemoryEntry:
    params: Dict[str, float]
    params_norm: Dict[str, float]
    metrics: Dict[str, float]
    failed: bool


# ==================================================
# SURROGATE MODEL
# ==================================================

class SurrogateModel:
    """
    Engineering-grade surrogate intelligence.
    Learns trends, uncertainty, and failure bias from sparse data.
    Suitable for on-line design optimization loops.
    """

    def __init__(
        self,
        max_memory: int = 800,
        k: int = 8,
        eps: float = 1e-6,
        failure_prior: float = 1.0,
        success_prior: float = 3.0,
    ):
        self.memory: List[MemoryEntry] = []
        self.max_memory = max_memory
        self.k = k
        self.eps = eps

        # parameter bounds
        self.param_stats = defaultdict(lambda: {"min": float("inf"), "max": float("-inf")})

        # Bayesian failure bias (Beta prior)
        self.failure_alpha = defaultdict(lambda: failure_prior)
        self.failure_beta = defaultdict(lambda: success_prior)

    # ==================================================
    # DATA INGESTION
    # ==================================================

    def record(self, params: Dict[str, float], metrics: Dict[str, float], failed: bool = False):
        self._update_stats(params)
        params_norm = self._normalize(params)

        entry = MemoryEntry(
            params=params.copy(),
            params_norm=params_norm,
            metrics=metrics.copy(),
            failed=failed,
        )

        self.memory.append(entry)

        # update Bayesian failure bias
        if failed:
            for k in params:
                self.failure_alpha[k] += 1.0
        else:
            for k in params:
                self.failure_beta[k] += 1.0

        if len(self.memory) > self.max_memory:
            self.memory.pop(0)

    def _update_stats(self, params: Dict[str, float]):
        for k, v in params.items():
            s = self.param_stats[k]
            s["min"] = min(s["min"], v)
            s["max"] = max(s["max"], v)

    # ==================================================
    # NORMALIZATION
    # ==================================================

    def _normalize(self, params: Dict[str, float]) -> Dict[str, float]:
        out = {}
        for k, v in params.items():
            s = self.param_stats.get(k)
            if not s or s["max"] <= s["min"]:
                out[k] = 0.5  # neutral center
            else:
                out[k] = (v - s["min"]) / (s["max"] - s["min"])
        return out

    # ==================================================
    # DISTANCE + WEIGHTING
    # ==================================================

    def _distance(self, a: Dict[str, float], b: Dict[str, float]) -> float:
        keys = set(a) | set(b)
        return math.sqrt(sum((a.get(k, 0.0) - b.get(k, 0.0)) ** 2 for k in keys))

    def _weight(self, d: float) -> float:
        return 1.0 / (d + self.eps)

    # ==================================================
    # CORE PREDICTION
    # ==================================================

    def predict(self, params: Dict[str, float]) -> Optional[Dict[str, Any]]:
        if len(self.memory) < self.k:
            return None

        q = self._normalize(params)

        # score neighbors
        scored = []
        for e in self.memory:
            d = self._distance(q, e.params_norm)
            scored.append((d, e))

        neighbors = sorted(scored, key=lambda x: x[0])[: self.k]

        # adaptive outlier rejection
        avg_d = sum(d for d, _ in neighbors) / max(1, len(neighbors))
        neighbors = [(d, e) for d, e in neighbors if d <= 2.0 * avg_d]

        weighted_sum = defaultdict(float)
        weighted_sq = defaultdict(float)
        total_w = 0.0
        failures = 0

        for d, e in neighbors:
            w = self._weight(d)

            if e.failed:
                failures += 1
                w *= 0.35  # strong but not absolute penalty

            total_w += w

            for m, v in e.metrics.items():
                weighted_sum[m] += w * v
                weighted_sq[m] += w * v * v

        prediction = {}
        uncertainty = {}

        eff_n = total_w ** 2 / (sum(self._weight(d) ** 2 for d, _ in neighbors) + self.eps)

        for m in weighted_sum:
            mean = weighted_sum[m] / max(self.eps, total_w)
            var = max(0.0, weighted_sq[m] / max(self.eps, total_w) - mean ** 2)

            # inflate uncertainty when data is sparse
            var *= max(1.0, self.k / max(self.eps, eff_n))

            prediction[m] = round(mean, 5)
            uncertainty[m] = round(math.sqrt(var), 5)

        # ==================================================
        # CONFIDENCE & RELIABILITY
        # ==================================================

        trust_radius = math.exp(-avg_d)
        failure_risk = failures / max(1, len(neighbors))

        reliability = max(0.0, trust_radius * (1.0 - failure_risk))

        feature_risk_bias = {
            k: round(self.failure_alpha[k] / (self.failure_alpha[k] + self.failure_beta[k]), 4)
            for k in self.param_stats
        }

        return {
            "prediction": prediction,
            "uncertainty": uncertainty,
            "confidence": round(trust_radius, 3),
            "reliability": round(reliability, 3),
            "failure_risk": round(failure_risk, 3),
            "feature_risk_bias": feature_risk_bias,
        }

    # ==================================================
    # PERSISTENCE
    # ==================================================

    def to_json(self) -> str:
        data = {
            "param_stats": dict(self.param_stats),
            "failure_alpha": dict(self.failure_alpha),
            "failure_beta": dict(self.failure_beta),
            "memory": [asdict(e) for e in self.memory],
        }
        return json.dumps(data)

    @classmethod
    def from_json(cls, s: str) -> "SurrogateModel":
        raw = json.loads(s)
        obj = cls()
        obj.param_stats.update(raw.get("param_stats", {}))
        obj.failure_alpha.update(raw.get("failure_alpha", {}))
        obj.failure_beta.update(raw.get("failure_beta", {}))

        for e in raw.get("memory", []):
            obj.memory.append(MemoryEntry(**e))

        return obj
