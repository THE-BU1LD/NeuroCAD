"""
stochastic_geometry.py

Advanced stochastic calculus + probabilistic geometry kernel.
Supports:
- Brownian motion
- Langevin dynamics
- Hamiltonian Monte Carlo
- Simulated annealing
- Design mutation fields
- Parameter diffusion
- Geometry exploration
- Adaptive temperature schedules
- Deterministic seeding
- Multi-point exploration
"""

import math
import random
import numpy as np


# ============================================================
# SEED CONTROL
# ============================================================

def set_seed(seed: int):
    random.seed(seed)
    np.random.seed(seed)


# ============================================================
# BASIC STOCHASTIC MOTION
# ============================================================

def brownian_step(vec, sigma=0.05):
    return (
        vec[0] + random.gauss(0, sigma),
        vec[1] + random.gauss(0, sigma),
        vec[2] + random.gauss(0, sigma),
    )


def brownian_step_np(vec, sigma=0.05):
    return vec + np.random.normal(0, sigma, size=vec.shape)


def geometric_langevin_step(x, grad, lr=0.02, noise=0.01):
    return (
        x[0] - lr * grad[0] + random.gauss(0, noise),
        x[1] - lr * grad[1] + random.gauss(0, noise),
        x[2] - lr * grad[2] + random.gauss(0, noise),
    )


def langevin_step_np(x, grad, lr=0.02, noise=0.01):
    return x - lr * grad + np.random.normal(0, noise, size=x.shape)


# ============================================================
# HAMILTONIAN MONTE CARLO
# ============================================================

def leapfrog(x, p, grad_fn, step_size, steps):
    x = np.copy(x)
    p = np.copy(p)

    p -= 0.5 * step_size * grad_fn(x)

    for _ in range(steps - 1):
        x += step_size * p
        p -= step_size * grad_fn(x)

    x += step_size * p
    p -= 0.5 * step_size * grad_fn(x)

    return x, -p


def hmc_step(x, energy_fn, grad_fn, step_size=0.01, steps=10):
    p0 = np.random.normal(0, 1, size=x.shape)
    current_energy = energy_fn(x) + 0.5 * np.sum(p0 ** 2)

    x_new, p_new = leapfrog(x, p0, grad_fn, step_size, steps)
    new_energy = energy_fn(x_new) + 0.5 * np.sum(p_new ** 2)

    if metropolis_accept(current_energy, new_energy):
        return x_new
    return x


# ============================================================
# SIMULATED ANNEALING
# ============================================================

def metropolis_accept(old_energy, new_energy, temp=0.5):
    if new_energy < old_energy:
        return True
    p = math.exp(-(new_energy - old_energy) / max(temp, 1e-8))
    return random.random() < p


class Annealer:

    def __init__(self, temp_start=1.0, temp_end=0.01, steps=1000):
        self.temp_start = temp_start
        self.temp_end = temp_end
        self.steps = steps

    def temperature(self, step):
        alpha = step / max(self.steps - 1, 1)
        return self.temp_start * (1 - alpha) + self.temp_end * alpha

    def optimize(self, x0, energy_fn, mutate_fn):
        x = x0
        best = x0
        best_e = energy_fn(x0)

        for step in range(self.steps):
            temp = self.temperature(step)
            candidate = mutate_fn(x)
            e_new = energy_fn(candidate)

            if metropolis_accept(best_e, e_new, temp):
                x = candidate
                if e_new < best_e:
                    best = candidate
                    best_e = e_new

        return best


# ============================================================
# PARAMETER MUTATION
# ============================================================

def mutate_parameters(params, temperature=0.3):
    out = {}
    for k, v in params.items():
        if isinstance(v, (int, float)):
            out[k] = v * (1 + random.gauss(0, temperature))
        elif isinstance(v, (list, tuple)):
            out[k] = type(v)(
                v[i] * (1 + random.gauss(0, temperature))
                if isinstance(v[i], (int, float))
                else v[i]
                for i in range(len(v))
            )
        else:
            out[k] = v
    return out


def gaussian_mutation(vec, sigma=0.1):
    return vec + np.random.normal(0, sigma, size=vec.shape)


def directional_mutation(vec, direction, scale=0.1):
    return vec + scale * np.array(direction)


# ============================================================
# ENERGY FUNCTIONS
# ============================================================

def quadratic_energy(x):
    return np.sum(x ** 2)


def l1_energy(x):
    return np.sum(np.abs(x))


def smoothness_energy(points):
    diffs = np.diff(points, axis=0)
    return np.sum(diffs ** 2)


def curvature_energy(points):
    d1 = np.diff(points, axis=0)
    d2 = np.diff(d1, axis=0)
    return np.sum(d2 ** 2)


# ============================================================
# MULTI-PARTICLE EXPLORATION
# ============================================================

class ParticleSwarm:

    def __init__(self, n_particles, dim):
        self.n = n_particles
        self.dim = dim
        self.positions = np.random.randn(n_particles, dim)
        self.velocities = np.random.randn(n_particles, dim)
        self.best_pos = np.copy(self.positions)
        self.best_energy = np.full(n_particles, np.inf)

    def step(self, energy_fn, inertia=0.7, cognitive=1.5, social=1.5):
        global_best_idx = np.argmin(self.best_energy)
        global_best = self.best_pos[global_best_idx]

        for i in range(self.n):
            energy = energy_fn(self.positions[i])

            if energy < self.best_energy[i]:
                self.best_energy[i] = energy
                self.best_pos[i] = self.positions[i]

            r1 = random.random()
            r2 = random.random()

            self.velocities[i] = (
                inertia * self.velocities[i]
                + cognitive * r1 * (self.best_pos[i] - self.positions[i])
                + social * r2 * (global_best - self.positions[i])
            )

            self.positions[i] += self.velocities[i]

        return global_best


# ============================================================
# DIFFUSION FIELDS
# ============================================================

def isotropic_diffusion(points, sigma=0.01):
    return points + np.random.normal(0, sigma, size=points.shape)


def anisotropic_diffusion(points, directions, sigma=0.01):
    noise = np.random.normal(0, sigma, size=points.shape)
    return points + noise * directions


# ============================================================
# GEOMETRIC RANDOM FIELDS
# ============================================================

def random_field(points, scale=1.0):
    return np.sin(scale * points[:, 0]) * np.cos(scale * points[:, 1])


def fractal_field(points, octaves=4):
    val = np.zeros(len(points))
    for i in range(octaves):
        val += (1 / (2 ** i)) * random_field(points * (2 ** i))
    return val


# ============================================================
# ADAPTIVE TEMPERATURE
# ============================================================

class AdaptiveTemperature:

    def __init__(self, initial=1.0):
        self.temp = initial

    def update(self, acceptance_ratio):
        if acceptance_ratio < 0.2:
            self.temp *= 0.9
        elif acceptance_ratio > 0.5:
            self.temp *= 1.1
        return self.temp


# ============================================================
# GRADIENT ESTIMATION
# ============================================================

def finite_difference_grad(x, energy_fn, eps=1e-5):
    grad = np.zeros_like(x)
    for i in range(len(x)):
        x1 = np.copy(x)
        x2 = np.copy(x)
        x1[i] += eps
        x2[i] -= eps
        grad[i] = (energy_fn(x1) - energy_fn(x2)) / (2 * eps)
    return grad


# ============================================================
# STOCHASTIC SHAPE EVOLUTION
# ============================================================

class ShapeEvolver:

    def __init__(self, energy_fn):
        self.energy_fn = energy_fn

    def evolve(self, x, iterations=100, lr=0.01, noise=0.02):
        for _ in range(iterations):
            grad = finite_difference_grad(x, self.energy_fn)
            x = langevin_step_np(x, grad, lr=lr, noise=noise)
        return x


# ============================================================
# MULTI-START GLOBAL SEARCH
# ============================================================

def multi_start_optimize(energy_fn, dim, starts=20):
    best = None
    best_e = np.inf

    for _ in range(starts):
        x = np.random.randn(dim)
        e = energy_fn(x)
        if e < best_e:
            best = x
            best_e = e

    return best


# ============================================================
# STOCHASTIC CONSTRAINT PROJECTION
# ============================================================

def project_to_sphere(x, radius=1.0):
    norm = np.linalg.norm(x)
    if norm == 0:
        return x
    return radius * x / norm


def project_to_box(x, low=-1.0, high=1.0):
    return np.clip(x, low, high)


# ============================================================
# RANDOM WALK SAMPLER
# ============================================================

class RandomWalkSampler:

    def __init__(self, energy_fn, step_sigma=0.1):
        self.energy_fn = energy_fn
        self.step_sigma = step_sigma

    def sample(self, x0, steps=1000):
        x = np.copy(x0)
        samples = []

        for _ in range(steps):
            candidate = gaussian_mutation(x, self.step_sigma)
            if metropolis_accept(self.energy_fn(x), self.energy_fn(candidate)):
                x = candidate
            samples.append(np.copy(x))

        return np.array(samples)


# ============================================================
# END
# ============================================================
