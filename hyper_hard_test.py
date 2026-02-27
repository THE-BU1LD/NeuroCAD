# hyper_hard_test.py

from connector import Joint, joint_diagnostics
from stress_test import monte_carlo_test, adversarial_test
from joint_optimizer import JointOptimizer
from neural import TinyNeuralScorer

import random

random.seed(42)

# ==================================================
# BASIC PART MODEL
# ==================================================

class Part:
    def __init__(self, name, mass):
        self.name = name
        self.mass = mass


# ==================================================
# BUILD SYSTEM
# ==================================================

fuselage = Part("fuselage", 420)
wing = Part("wing", 140)
flap = Part("flap", 35)

hinge = Joint(
    type_="revolute",
    part_a=wing,
    part_b=flap,
    position=(1.2, 0, 0),
    axis=(0, 1, 0),
    limits=(-25, 25),
    stiffness=0.35,
    damping=0.15,
    max_load=55,
    fatigue_limit=8e5,
)

fixed = Joint(
    type_="fixed",
    part_a=fuselage,
    part_b=wing,
    position=(0, 0, 0),
    stiffness=0.9,
    damping=0.05,
    max_load=500,
    fatigue_limit=5e6,
)

joints = [hinge, fixed]

# ==================================================
# LOAD CASE
# ==================================================

loads = {
    hinge: 110,
    fixed: 320,
}

cycles = {
    hinge: 3e5,
    fixed: 8e5,
}

# ==================================================
# DIAGNOSTICS
# ==================================================

print("\n=== JOINT DIAGNOSTICS ===")
issues = joint_diagnostics(joints, loads, cycles)
for i in issues:
    print(i)

# ==================================================
# MONTE CARLO STRESS TEST
# ==================================================

print("\n=== MONTE CARLO FAILURES ===")
failures = monte_carlo_test(joints, loads, trials=250)
print(f"Failure count: {len(failures)}")
print(f"Failure rate: {len(failures) / (250 * len(joints)):.2f}")

# ==================================================
# ADVERSARIAL TEST
# ==================================================

print("\n=== ADVERSARIAL STRESS ===")
for j, risk in adversarial_test(joints):
    print(j.describe(), "risk =", round(risk, 3))

# ==================================================
# OPTIMIZATION
# ==================================================

print("\n=== JOINT OPTIMIZATION ===")

optimizer = JointOptimizer(joints, loads, cycles)
initial_risk = optimizer.total_risk()

print(f"Initial total risk: {initial_risk:.4f}")

best = optimizer.optimize(steps=200, lr=0.08, verbose=True)

print(f"Optimized total risk: {best:.4f}")

print("\n--- Optimized Joint Summary ---")
for row in optimizer.summary():
    print(row)

# ==================================================
# POST-OPTIMIZATION STRESS
# ==================================================

print("\n=== POST-OPTIMIZATION MONTE CARLO ===")
post_failures = monte_carlo_test(joints, loads, trials=250)
print(f"Failure rate after optimization: "
      f"{len(post_failures) / (250 * len(joints)):.2f}")

# ==================================================
# NEURAL RISK ESTIMATION
# ==================================================

print("\n=== NEURAL RISK ===")

scorer = TinyNeuralScorer()

total_mass = fuselage.mass + wing.mass + flap.mass
slenderness = 28
drag = 11.5

risk, confidence = scorer.score(
    mass=total_mass,
    slenderness=slenderness,
    drag=drag,
    aero_complexity=1.1,
)

print("Risk:", round(risk, 4))
print("Confidence:", round(confidence, 4))
print("Weights:", scorer.explain())
