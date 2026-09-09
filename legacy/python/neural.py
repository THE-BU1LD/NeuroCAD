# neural.py
import random
import math
import json
from typing import Dict, Tuple, List


# ============================================================
# UTILS
# ============================================================

def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def sigmoid(z: float) -> float:
    z = clamp(z, -30, 30)
    return 1.0 / (1.0 + math.exp(-z))


# ============================================================
# TINY NEURAL SCORER (Improved)
# ============================================================

class TinyNeuralScorer:
    """
    Lightweight neural risk estimator.
    Online-trainable, interpretable, stable.
    """

    def __init__(self, adaptive_scaling=True):
        self.w = [random.uniform(-0.12, 0.12) for _ in range(4)]
        self.b = random.uniform(-0.02, 0.02)

        # normalization anchors
        self.mass_ref = 1000.0
        self.slender_ref = 20.0
        self.drag_ref = 10.0

        self.adaptive_scaling = adaptive_scaling
        self.samples = 0

        # running statistics (for uncertainty estimation)
        self.running_mean = 0.0
        self.running_var = 0.0

    # ==================================================
    # CORE
    # ==================================================

    def score(
        self,
        mass: float,
        slenderness: float,
        drag: float,
        aero_complexity: float = 0.0,
    ) -> Tuple[float, float]:

        x = self._features(mass, slenderness, drag, aero_complexity)
        z = sum(w * xi for w, xi in zip(self.w, x)) + self.b
        risk = sigmoid(z)

        # entropy-based confidence
        entropy = -(
            risk * math.log(risk + 1e-8)
            + (1 - risk) * math.log(1 - risk + 1e-8)
        )

        data_conf = 1 - math.exp(-self.samples / 25)
        confidence = data_conf * (1 - entropy)

        # uncertainty via variance
        variance = self.running_var
        uncertainty_penalty = clamp(variance, 0.0, 0.5)
        confidence *= (1 - uncertainty_penalty)

        return round(risk, 5), round(confidence, 5)

    # ==================================================
    # TRAINING
    # ==================================================

    def train(
        self,
        mass: float,
        slenderness: float,
        drag: float,
        aero_complexity: float,
        outcome: int,
        lr: float = 0.04,
        weight_decay: float = 0.002,
        grad_clip: float = 1.0,
    ):

        x = self._features(mass, slenderness, drag, aero_complexity)
        z = sum(w * xi for w, xi in zip(self.w, x)) + self.b
        pred = sigmoid(z)

        error = outcome - pred

        # gradient descent
        for i in range(len(self.w)):
            grad = clamp(error * x[i], -grad_clip, grad_clip)
            self.w[i] += lr * grad
            self.w[i] *= (1 - weight_decay)

        self.b += lr * clamp(error, -grad_clip, grad_clip)

        self.samples += 1
        self._update_statistics(pred)

        if self.adaptive_scaling:
            self._update_scaling(mass, slenderness, drag)

    # ==================================================
    # BATCH TRAINING
    # ==================================================

    def train_batch(self, batch: List[Tuple], epochs=1):
        for _ in range(epochs):
            for sample in batch:
                self.train(*sample)

    # ==================================================
    # INTERPRETABILITY
    # ==================================================

    def explain(self) -> Dict[str, float]:
        labels = [
            "mass",
            "slenderness",
            "drag",
            "aero_complexity",
        ]
        return {lbl: round(w, 5) for lbl, w in zip(labels, self.w)}

    def gradient_importance(self) -> Dict[str, float]:
        total = sum(abs(w) for w in self.w) + 1e-8
        labels = ["mass", "slenderness", "drag", "aero_complexity"]
        return {
            lbl: round(abs(w) / total, 4)
            for lbl, w in zip(labels, self.w)
        }

    # ==================================================
    # PERSISTENCE
    # ==================================================

    def save(self, path="tiny_model.json"):
        data = {
            "weights": self.w,
            "bias": self.b,
            "samples": self.samples,
            "mass_ref": self.mass_ref,
            "slender_ref": self.slender_ref,
            "drag_ref": self.drag_ref,
        }
        with open(path, "w") as f:
            json.dump(data, f)

    def load(self, path="tiny_model.json"):
        with open(path, "r") as f:
            data = json.load(f)
        self.w = data["weights"]
        self.b = data["bias"]
        self.samples = data["samples"]
        self.mass_ref = data["mass_ref"]
        self.slender_ref = data["slender_ref"]
        self.drag_ref = data["drag_ref"]

    # ==================================================
    # INTERNAL
    # ==================================================

    def _features(self, mass, slender, drag, aero):
        return [
            clamp(mass / self.mass_ref, 0.0, 2.0),
            clamp(slender / self.slender_ref, 0.0, 2.0),
            clamp(drag / self.drag_ref, 0.0, 2.0),
            clamp(aero, 0.0, 1.0),
        ]

    def _update_statistics(self, pred):
        delta = pred - self.running_mean
        self.running_mean += delta / (self.samples + 1)
        delta2 = pred - self.running_mean
        self.running_var += delta * delta2

    def _update_scaling(self, mass, slender, drag):
        # Slowly adapt references
        self.mass_ref = 0.99 * self.mass_ref + 0.01 * mass
        self.slender_ref = 0.99 * self.slender_ref + 0.01 * slender
        self.drag_ref = 0.99 * self.drag_ref + 0.01 * drag


# ============================================================
# ENSEMBLE WRAPPER (Optional Power Mode)
# ============================================================

class TinyEnsemble:

    def __init__(self, n_models=5):
        self.models = [TinyNeuralScorer() for _ in range(n_models)]

    def score(self, *args):
        preds = []
        confs = []

        for m in self.models:
            r, c = m.score(*args)
            preds.append(r)
            confs.append(c)

        mean_pred = sum(preds) / len(preds)
        variance = sum((p - mean_pred) ** 2 for p in preds) / len(preds)

        confidence = sum(confs) / len(confs)
        confidence *= (1 - clamp(variance, 0.0, 0.5))

        return round(mean_pred, 5), round(confidence, 5)

    def train(self, *args):
        for m in self.models:
            m.train(*args)
