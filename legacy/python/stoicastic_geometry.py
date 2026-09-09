"""
stochastic_geometry.py

High-performance stochastic geometry module.
Vectorized, reproducible, mesh-scale capable.
Optimized for large CAD pipelines (2GB RAM safe).
"""

import numpy as np


# ==================================================
# RNG CONTROLLER (Deterministic Capable)
# ==================================================

class RNG:
    def __init__(self, seed=None):
        self.rng = np.random.default_rng(seed)

    def normal(self, shape, sigma=1.0):
        return self.rng.normal(0.0, sigma, shape)

    def uniform(self, shape):
        return self.rng.random(shape)

    def scalar(self):
        return float(self.rng.random())


# ==================================================
# STOCHASTIC DIFFERENTIAL GEOMETRY
# ==================================================

def brownian_step(points, sigma=0.05, rng=None):
    """
    Vectorized Brownian motion:
    dX = σ dW
    points: (N,3)
    """
    if rng is None:
        rng = RNG()

    noise = rng.normal(points.shape, sigma)
    return points + noise


def geometric_langevin_step(points, gradients, lr=0.02, noise=0.01, rng=None):
    """
    Vectorized Langevin:
    dX = -∇E dt + √(2σ) dW
    """
    if rng is None:
        rng = RNG()

    stochastic = rng.normal(points.shape, noise)
    return points - lr * gradients + stochastic


# ==================================================
# PARAMETER MUTATION (Vector Safe)
# ==================================================

def mutate_parameters(params, temperature=0.3, rng=None):
    """
    Stable stochastic parameter mutation.
    Keeps values bounded.
    """
    if rng is None:
        rng = RNG()

    out = {}

    for k, v in params.items():
        if isinstance(v, (int, float)):
            scale = 1.0 + rng.normal((1,), temperature)[0]
            out[k] = float(max(1e-6, v * scale))
        elif isinstance(v, (list, tuple)):
            arr = np.array(v, dtype=np.float32)
            scale = 1.0 + rng.normal(arr.shape, temperature)
            out[k] = (arr * scale).tolist()
        else:
            out[k] = v

    return out


# ==================================================
# SIMULATED ANNEALING (Batch)
# ==================================================

def metropolis_accept(old_energy, new_energy, temp=0.5, rng=None):
    """
    Scalar acceptance.
    """
    if rng is None:
        rng = RNG()

    if new_energy < old_energy:
        return True

    delta = new_energy - old_energy
    p = np.exp(-delta / max(temp, 1e-8))
    return rng.scalar() < p


def metropolis_accept_batch(old_energy, new_energy, temp=0.5, rng=None):
    """
    Vectorized acceptance for many candidates.
    old_energy, new_energy: (N,)
    """
    if rng is None:
        rng = RNG()

    old_energy = np.asarray(old_energy)
    new_energy = np.asarray(new_energy)

    accept = new_energy < old_energy

    delta = new_energy - old_energy
    p = np.exp(-delta / max(temp, 1e-8))

    random_draw = rng.uniform(old_energy.shape)

    accept |= random_draw < p

    return accept


# ==================================================
# SHAPE SPACE EXPLORATION ENGINE
# ==================================================

class StochasticExplorer:
    """
    High-level stochastic design-space explorer.
    """

    def __init__(self, temperature=0.3, seed=None):
        self.temperature = temperature
        self.rng = RNG(seed)

    def mutate_param_set(self, params):
        return mutate_parameters(
            params,
            temperature=self.temperature,
            rng=self.rng
        )

    def perturb_vertices(self, vertices, sigma=0.02):
        return brownian_step(vertices, sigma, self.rng)

    def langevin_vertices(self, vertices, gradients, lr=0.02, noise=0.01):
        return geometric_langevin_step(
            vertices,
            gradients,
            lr=lr,
            noise=noise,
            rng=self.rng
        )

    def anneal_step(self, old_energy, new_energy):
        return metropolis_accept(
            old_energy,
            new_energy,
            temp=self.temperature,
            rng=self.rng
        )


# ==================================================
# ENERGY MODELS
# ==================================================

def curvature_energy(normals):
    """
    Energy based on curvature magnitude.
    """
    return np.linalg.norm(normals, axis=1)


def smoothness_energy(vertices, faces):
    """
    Simple Laplacian smoothness energy.
    """
    adjacency = [[] for _ in range(len(vertices))]

    for f in faces:
        adjacency[f[0]].extend([f[1], f[2]])
        adjacency[f[1]].extend([f[0], f[2]])
        adjacency[f[2]].extend([f[0], f[1]])

    energy = np.zeros(len(vertices), dtype=np.float32)

    for i, neighbors in enumerate(adjacency):
        if not neighbors:
            continue
        mean_neighbor = np.mean(vertices[neighbors], axis=0)
        energy[i] = np.linalg.norm(vertices[i] - mean_neighbor)

    return energy


# ==================================================
# Stress Test
# ==================================================

if __name__ == "__main__":

    rng = RNG(seed=42)

    verts = np.random.rand(100000, 3).astype(np.float32)

    explorer = StochasticExplorer(seed=123)

    perturbed = explorer.perturb_vertices(verts, sigma=0.01)

    print("Original mean:", verts.mean())
    print("Perturbed mean:", perturbed.mean())
