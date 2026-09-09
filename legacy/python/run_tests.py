# run_all_tests.py
from parts import Part
from auto_joint import auto_generate_joints
from system_optimizer import SystemOptimizer
from stress_test import monte_carlo_test, adversarial_test
from ml import TinyNeuralScorer


# Parts (ANY DESIGN)
parts = [
    Part("Wing", 50, (0, 0, 0)),
    Part("Fuselage", 120, (1, 0, 0)),
    Part("Engine", 80, (0.5, 0.8, 0)),
]

# Auto joints
joints = auto_generate_joints(parts)

# Loads
loads = {j: 120.0 for j in joints}

# Optimize system
sys_opt = SystemOptimizer(joints, loads)
summary = sys_opt.optimize()

print("\n[OPTIMIZED JOINTS]")
for s in summary:
    print(s)

# Stress tests
print("\n[MONTE CARLO FAILURES]")
print(len(monte_carlo_test(joints, loads)))

print("\n[ADVERSARIAL TEST]")
for j, r in adversarial_test(joints):
    print(j.describe(), "risk=", round(r, 3))

# ML scoring
model = TinyNeuralScorer()
print("\n[ML SCORES]")
for j in joints:
    print(j.describe(), model.score(j, loads[j]))
