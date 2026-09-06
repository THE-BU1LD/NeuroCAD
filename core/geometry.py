from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Primitive:
    kind: str
    dims: dict[str, Any] = field(default_factory=dict)

    def with_param(self, key: str, value: Any) -> Primitive:
        d = dict(self.dims)
        d[key] = value
        return Primitive(self.kind, d)

    def to_component_params(self) -> dict[str, Any]:
        return {"geometry": {"kind": self.kind, **self.dims}}


def box(w: float, h: float, d: float, *, center: bool = True) -> Primitive:
    return Primitive("box", {"size": (float(w), float(h), float(d)), "center": center})


def cylinder(r: float, h: float, *, center: bool = True) -> Primitive:
    return Primitive("cylinder", {"radius": float(r), "height": float(h), "center": center})


def sphere(r: float, *, center: bool = True) -> Primitive:
    return Primitive("sphere", {"radius": float(r), "center": center})


def cone(r1: float, r2: float, h: float, *, center: bool = True) -> Primitive:
    return Primitive("cone", {"r1": float(r1), "r2": float(r2), "height": float(h), "center": center})


def torus(R: float, r: float) -> Primitive:
    return Primitive("torus", {"R": float(R), "r": float(r)})
