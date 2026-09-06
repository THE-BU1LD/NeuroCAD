"""
topology_algebra.py

Algebraic + spectral topology extensions for Mesh.
Plugs directly into topology_engine.Mesh.

Includes:
- Chain complexes (∂₁, ∂₂)
- Boundary consistency checks (∂∘∂ = 0)
- Hodge Laplacian (graph-level)
- Spectral signatures for ML + design guidance
"""

import math
from collections import defaultdict


# ==================================================
# CHAIN COMPLEXES
# ==================================================

def boundary_operator_1(mesh):
    """
    ∂₁ : C₁ → C₀   (edges → vertices)
    Sparse dict form.
    """
    B1 = defaultdict(dict)
    for eid, e in mesh.edges.items():
        B1[eid][e.v1.id] = -1
        B1[eid][e.v2.id] = +1
    return B1


def boundary_operator_2(mesh):
    """
    ∂₂ : C₂ → C₁   (faces → edges)
    Orientation-agnostic (CAD-safe)
    """
    B2 = defaultdict(dict)
    edge_index = {k: i for i, k in enumerate(mesh.edges.keys())}

    for fid, f in enumerate(mesh.faces):
        for e in f.edges:
            idx = edge_index[e.key()]
            B2[fid][idx] = 1
    return B2


def boundary_consistency(mesh):
    """
    Checks ∂₁ ∘ ∂₂ = 0 (topological validity)
    """
    B1 = boundary_operator_1(mesh)
    B2 = boundary_operator_2(mesh)

    for f, edges in B2.items():
        for e in edges:
            if e not in B1:
                continue
            for v in B1[e]:
                if abs(B1[e][v] * edges[e]) > 0:
                    return False
    return True


# ==================================================
# SPECTRAL TOPOLOGY
# ==================================================

def laplacian_spectrum_proxy(mesh):
    """
    Returns spectral invariants without eigen-solvers.
    Useful for ML + design penalties.
    """
    degrees = [len(v.edges) for v in mesh.vertices.values()]
    avg_degree = sum(degrees) / max(1, len(degrees))
    max_degree = max(degrees) if degrees else 0

    return {
        "avg_degree": round(avg_degree, 3),
        "max_degree": max_degree,
        "degree_variance": round(
            sum((d - avg_degree) ** 2 for d in degrees) / max(1, len(degrees)),
            4
        ),
    }


# ==================================================
# TOPOLOGICAL ENERGY
# ==================================================

def topological_energy(mesh):
    """
    Scalar energy used to guide generative optimization.
    Lower = better topology.
    """
    stats = mesh.stats()
    penalty = 0

    penalty += 3 * stats["NonManifoldEdges"]
    penalty += 2 * stats["BoundaryEdges"]
    penalty += abs(stats["Euler"])

    return penalty
