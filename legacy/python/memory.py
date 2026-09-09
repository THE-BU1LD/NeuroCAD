# design_memory.py
from collections import defaultdict
import copy
import statistics


class DesignMemory:
    """
    Experience-based design memory.
    Learns patterns from success/failure histories.
    """

    def __init__(self, max_history: int = 200):
        self.records = []
        self.max_history = max_history

        # learned statistics
        self.feature_stats = defaultdict(list)
        self.failure_patterns = defaultdict(int)

    # --------------------------------------------------
    # FEATURE EXTRACTION
    # --------------------------------------------------

    def _extract_features(self, design):
        """
        Converts a design into numerical + categorical features.
        """
        feats = {}

        parts = getattr(design, "parts", [design])

        feats["num_parts"] = len(parts)
        feats["mass"] = sum(
            getattr(p, "mass", 0) for p in parts
        )

        feats["cylinders"] = sum(
            1 for p in parts if getattr(p, "primitive", "") == "cylinder"
        )

        feats["streamlined"] = sum(
            1 for p in parts if getattr(p, "streamlined", False)
        )

        feats["materials"] = tuple(
            sorted(getattr(p, "material", "PLA") for p in parts)
        )

        return feats

    # --------------------------------------------------
    # LOGGING
    # --------------------------------------------------

    def log(self, design, score, success: bool):
        feats = self._extract_features(design)

        self.records.append({
            "design": copy.deepcopy(design),
            "features": feats,
            "score": score,
            "success": success
        })

        if len(self.records) > self.max_history:
            self.records.pop(0)

        # Learn statistics
        for k, v in feats.items():
            if isinstance(v, (int, float)):
                self.feature_stats[k].append((v, success))

        if not success:
            key = tuple(sorted(feats.items()))
            self.failure_patterns[key] += 1

    # --------------------------------------------------
    # INSIGHT EXTRACTION
    # --------------------------------------------------

    def preferred_ranges(self):
        """
        Returns feature ranges correlated with success.
        """
        ranges = {}

        for k, vals in self.feature_stats.items():
            good = [v for v, s in vals if s]
            if len(good) >= 5:
                ranges[k] = (
                    min(good),
                    statistics.mean(good),
                    max(good)
                )

        return ranges

    def common_failures(self, top_n=3):
        """
        Most frequent failure feature combinations.
        """
        return sorted(
            self.failure_patterns.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_n]

    # --------------------------------------------------
    # DESIGN SUGGESTION
    # --------------------------------------------------

    def suggest(self, base_design=None):
        """
        Suggests an improved design based on memory.
        """
        if not self.records:
            return None

        successes = [r for r in self.records if r["success"]]
        if not successes:
            return None

        # Pick best historical design
        best = min(successes, key=lambda r: r["score"])
        candidate = copy.deepcopy(best["design"])

        # Apply learned preferences
        prefs = self.preferred_ranges()

        for p in getattr(candidate, "parts", [candidate]):
            if "streamlined" in prefs:
                p.streamlined = True

            if "cylinders" in prefs and getattr(p, "primitive", "") == "cylinder":
                if hasattr(p, "height") and hasattr(p, "radius"):
                    p.height *= 1.05
                    p.radius *= 0.97

        return candidate

    # --------------------------------------------------
    # EXPLANATION (DEMO GOLD)
    # --------------------------------------------------

    def explain(self) -> str:
        return (
            f"Memory size: {len(self.records)} designs\n"
            f"Preferred ranges: {self.preferred_ranges()}\n"
            f"Common failures: {self.common_failures()}"
        )
