# stress_test.py
import random


def monte_carlo_test(joints, base_loads, trials=200):
    failures = []

    for _ in range(trials):
        for j in joints:
            load = base_loads[j] * random.uniform(0.6, 1.6)
            risk = j.risk_score(
                applied_load=load,
                cycles=random.randint(int(1e4), int(1e6))
            )
            if risk > 1.0:
                failures.append((j, risk))

    return failures


def adversarial_test(joints):
    worst = []
    for j in joints:
        load = j.max_load * 1.8
        risk = j.risk_score(
            applied_load=load,
            cycles=1e7
        )
        worst.append((j, risk))

    return sorted(worst, key=lambda x: -x[1])
