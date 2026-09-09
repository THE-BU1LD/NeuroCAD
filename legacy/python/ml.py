# ml.py
import random
import math


class TinyNeuralScorer:
    """
    Lightweight joint intelligence.
    Approximates a GNN-style message passing system.
    """

    def __init__(self, dim=6):
        self.w = [random.uniform(-0.5, 0.5) for _ in range(dim)]
        self.b = random.uniform(-0.1, 0.1)

    def encode_joint(self, joint, load):
        return [
            joint.stiffness,
            joint.damping,
            load / joint.max_load,
            joint.part_a.mass,
            joint.part_b.mass,
            joint.part_a.inertia_proxy() + joint.part_b.inertia_proxy(),
        ]

    def forward(self, x):
        z = sum(w * xi for w, xi in zip(self.w, x)) + self.b
        return 1 / (1 + math.exp(-z))

    def score(self, joint, load):
        return self.forward(self.encode_joint(joint, load))

    def train_step(self, joint, load, target, lr=0.01):
        x = self.encode_joint(joint, load)
        y = self.forward(x)
        err = y - target

        for i in range(len(self.w)):
            self.w[i] -= lr * err * x[i]
        self.b -= lr * err
