import copy
import logging
import random
import math
from dataclasses import dataclass
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from physics import mass as compute_mass
from aerodynamics import analyze, analyze_assembly

log = logging.getLogger("CAD-Optimizer")
log.setLevel(logging.INFO)


# ==========================================================
# UTILITIES
# ==========================================================

def _aero_metrics(obj) -> Dict:
    if hasattr(obj, "parts"):
        return analyze_assembly(obj.parts)
    return analyze(obj)


def _compute_total_mass(obj) -> float:
    if hasattr(obj, "parts"):
        return sum(float(compute_mass(p)) for p in obj.parts)
    return float(compute_mass(obj))


# ==========================================================
# SCORE MODEL
# ==========================================================

@dataclass
class CandidateScore:
    mass: float
    drag: float
    risk: float
    penalty: float

    def total(self) -> float:
        return (
            0.5 * self.mass +
            2.0 * self.drag +
            600.0 * self.risk +
            self.penalty
        )

    def explain(self) -> str:
        return (
            f"mass={self.mass:.2f} "
            f"drag={self.drag:.3f} "
            f"risk={self.risk:.3f} "
            f"penalty={self.penalty:.0f}"
        )


# ==========================================================
# CANDIDATE SCORING
# ==========================================================

def _score_candidate(candidate, validator, learner=None) -> CandidateScore:
    penalty = 0.0

    try:
        aero = _aero_metrics(candidate)
        drag = float(aero.get("drag_force", aero.get("total_drag", 0.0)))

        for d in aero.get("diagnostics", []):
            d = d.lower()
            if "bluff" in d:
                penalty += 300
            elif "high drag" in d:
                penalty += 250
            elif "frontal" in d:
                penalty += 200

        validator.validate(candidate)
        mass = _compute_total_mass(candidate)

        risk = 0.0
        if learner:
            parts = getattr(candidate, "parts", [candidate])
            for p in parts:
                risk += learner.risk_score(
                    getattr(p, "primitive", "unknown"),
                    getattr(p, "material", "PLA"),
                )
            risk /= max(1, len(parts))

        return CandidateScore(mass, drag, risk, penalty)

    except Exception:
        return CandidateScore(
            mass=1e6,
            drag=1e6,
            risk=1.0,
            penalty=1e6,
        )


# ==========================================================
# OPTIMIZER
# ==========================================================

class Optimizer:

    def __init__(
        self,
        max_iters: int = 150,
        population_size: int = 12,
        elite_frac: float = 0.2,
        temperature: float = 1.0,
        cooling: float = 0.98,
        random_seed: Optional[int] = 0,
        learner=None,
    ):
        self.max_iters = max_iters
        self.population_size = population_size
        self.elite_frac = elite_frac
        self.temperature = temperature
        self.cooling = cooling
        self.learner = learner

        self.strategy_stats = defaultdict(lambda: {"tries": 0, "wins": 0})

        if random_seed is not None:
            random.seed(random_seed)

    # ------------------------------------------------------
    # STRATEGIES
    # ------------------------------------------------------

    def _streamline(self, base):
        cand = copy.deepcopy(base)
        for p in getattr(cand, "parts", [cand]):
            setattr(p, "streamlined", True)
        return [(cand, "streamline")]

    def _reduce_frontal(self, base):
        cand = copy.deepcopy(base)
        for p in getattr(cand, "parts", [cand]):
            if hasattr(p, "width"):
                p.width *= 0.9
            if hasattr(p, "height"):
                p.height *= 0.9
        return [(cand, "reduce_frontal")]

    def _elongate(self, base):
        cand = copy.deepcopy(base)
        for p in getattr(cand, "parts", [cand]):
            if getattr(p, "primitive", "") == "cylinder":
                p.height *= 1.15
                p.radius *= 0.92
        return [(cand, "elongate")]

    def _stochastic_mutation(self, base):
        cand = copy.deepcopy(base)
        f = 1 + random.uniform(-0.05, 0.05)
        for p in getattr(cand, "parts", [cand]):
            if hasattr(p, "radius"):
                p.radius *= f
            if hasattr(p, "height"):
                p.height *= f
        return [(cand, "stochastic")]

    # ------------------------------------------------------
    # STRATEGY SELECTION (UCB1)
    # ------------------------------------------------------

    def _select_strategy(self, strategies):
        total_tries = sum(v["tries"] for v in self.strategy_stats.values()) + 1

        best_score = -1
        best_strat = None

        for s in strategies:
            name = s.__name__
            stat = self.strategy_stats[name]
            tries = stat["tries"]
            wins = stat["wins"]

            if tries == 0:
                return s

            exploit = wins / tries
            explore = math.sqrt(math.log(total_tries) / tries)
            score = exploit + self.temperature * explore

            if score > best_score:
                best_score = score
                best_strat = s

        return best_strat

    # ------------------------------------------------------
    # ANNEAL ACCEPTANCE
    # ------------------------------------------------------

    def _accept(self, old, new):
        if new.total() < old.total():
            return True
        delta = new.total() - old.total()
        prob = math.exp(-delta / max(self.temperature, 1e-6))
        return random.random() < prob

    # ------------------------------------------------------
    # MAIN OPTIMIZATION LOOP
    # ------------------------------------------------------

    def optimize(self, obj, validator):

        population = [copy.deepcopy(obj)]
        scored: List[Tuple[Any, CandidateScore]] = []

        strategies = [
            self._streamline,
            self._reduce_frontal,
            self._elongate,
            self._stochastic_mutation,
        ]

        best_obj = copy.deepcopy(obj)
        best_score = _score_candidate(best_obj, validator, self.learner)

        stagnation = 0

        for step in range(self.max_iters):

            new_population = []

            for base in population:
                strat = self._select_strategy(strategies)
                children = strat(base)

                for child, name in children:
                    self.strategy_stats[name]["tries"] += 1

                    score = _score_candidate(child, validator, self.learner)

                    if self._accept(best_score, score):
                        new_population.append(child)

                    if score.total() < best_score.total():
                        best_obj = child
                        best_score = score
                        self.strategy_stats[name]["wins"] += 1
                        stagnation = 0

                    log.info(
                        "[%03d] %-15s | %s | total=%.2f",
                        step,
                        name,
                        score.explain(),
                        score.total(),
                    )

            if not new_population:
                new_population.append(copy.deepcopy(best_obj))

            population = sorted(
                new_population,
                key=lambda c: _score_candidate(c, validator, self.learner).total()
            )[:self.population_size]

            self.temperature *= self.cooling
            stagnation += 1

            if stagnation > 30:
                log.info("Early stop due to stagnation.")
                break

        log.info("\n=== FINAL BEST DESIGN ===")
        log.info(best_score.explain())

        for name, s in self.strategy_stats.items():
            if s["tries"]:
                log.info(
                    "Strategy %-15s success %.2f",
                    name,
                    s["wins"] / s["tries"],
                )

        return best_obj
