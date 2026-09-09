"""
HARD ADVERSARIAL AUTONOMOUS CAD TEST
----------------------------------
Tests:
- Noisy / deceptive aerodynamics
- Hidden structural failure basin
- Tight design constraints
- Optimizer robustness

PASSING THIS = research-grade system
"""

import random
import optimizer
from optimizer import Optimizer
from geometry import generate_scad
from learning import DesignLearner
from surrogate import SurrogateModel
from aerodynamics import analyze


# ==========================================================
# 1. TEST DESIGN OBJECT
# ==========================================================

class HardTestPart:
    def __init__(self):
        self.primitive = "cylinder"
        self.material = "PLA"

        # tight design space
        self.radius = 6.0
        self.height = 30.0

        # aero features
        self.aero = True
        self.taper = 0.25
        self.nose = "cone"
        self.tail = True


# ==========================================================
# 2. ADVERSARIAL VALIDATOR
# ==========================================================

class AdversarialValidator:
    def validate(self, obj):
        r = obj.radius
        h = obj.height

        # hidden resonance failure basin
        if 6.2 < r < 6.6 and 28.0 < h < 32.0:
            raise ValueError("Resonant structural failure")

        # visible constraint
        if h / r > 18:
            raise ValueError("Buckling risk")

        if r <= 0 or h <= 0:
            raise ValueError("Invalid geometry")


# ==========================================================
# 3. ADVERSARIAL AERODYNAMICS (LYING PHYSICS)
# ==========================================================

class AdversarialAero:
    def analyze(self, obj):
        base = analyze(obj)

        # 25% chance of lying
        if random.random() < 0.25:
            base["drag_force"] *= random.uniform(0.6, 1.4)
            base.setdefault("diagnostics", []).append("sensor_noise")

        return base


# ==========================================================
# 4. MONKEY-PATCH OPTIMIZER AERO
# ==========================================================

adversarial = AdversarialAero()

def noisy_aero(obj):
    return adversarial.analyze(obj)

optimizer._aero_metrics = noisy_aero


# ==========================================================
# 5. HARD DESIGN CLAMP (ANTI-CHEESE)
# ==========================================================

def clamp_design(obj):
    obj.radius = max(4.0, min(8.0, obj.radius))
    obj.height = max(20.0, min(40.0, obj.height))


# ==========================================================
# 6. RUN THE HARD TEST
# ==========================================================

def run():
    base = HardTestPart()
    validator = AdversarialValidator()

    learner = DesignLearner()
    surrogate = SurrogateModel(k=10)

    opt = Optimizer(
        max_iters=200,
        elite_frac=0.15,
        random_seed=42,
        learner=learner
    )

    best = opt.optimize(base, validator)

    print("\n=== BEST DESIGN FOUND ===")
    print(vars(best))

    scad = generate_scad(best)
    with open("hard_best.scad", "w") as f:
        f.write(scad)

    print("\nSCAD written to hard_best.scad")
    print("Open it in OpenSCAD and inspect geometry.")


if __name__ == "__main__":
    run()
