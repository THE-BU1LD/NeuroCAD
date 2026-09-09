# system_optimizer.py
from joint_optimizer import JointOptimizer


class SystemOptimizer:
    def __init__(self, joints, loads, cycles=None):
        self.joint_opt = JointOptimizer(joints, loads, cycles)

    def optimize(self, rounds=3):
        print("[SYSTEM] Starting system optimization")
        for r in range(rounds):
            print(f"[SYSTEM] Round {r+1}")
            self.joint_opt.optimize(steps=150, verbose=False)
        return self.joint_opt.summary()
