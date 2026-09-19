"""Unit-safe numerical foundations for agent-proposed engineering work.

The APIs in this module are deliberately solver-agnostic. They provide bounded
local methods, diagnostics, and explicit failure reports; they do not claim to
replace domain solvers such as OpenFOAM, CalculiX, or FEniCS.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np

MAX_VARIABLES = 128
MAX_CONSTRAINTS = 512
MAX_ITERATIONS = 10_000
BASE_DIMENSIONS = ("mass", "length", "time", "temperature", "current", "amount", "luminous_intensity")


def _finite(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite number")
    return result


@dataclass(frozen=True)
class Dimension:
    powers: tuple[int, int, int, int, int, int, int] = (0, 0, 0, 0, 0, 0, 0)

    def __post_init__(self) -> None:
        if len(self.powers) != len(BASE_DIMENSIONS) or any(isinstance(value, bool) or not isinstance(value, int) for value in self.powers):
            raise TypeError("dimension powers must contain seven integers")

    def __mul__(self, other: Dimension) -> Dimension:
        return Dimension(tuple(a + b for a, b in zip(self.powers, other.powers, strict=True)))  # type: ignore[arg-type]

    def __truediv__(self, other: Dimension) -> Dimension:
        return Dimension(tuple(a - b for a, b in zip(self.powers, other.powers, strict=True)))  # type: ignore[arg-type]

    def __pow__(self, exponent: int) -> Dimension:
        if isinstance(exponent, bool) or not isinstance(exponent, int):
            raise TypeError("dimension exponent must be an integer")
        return Dimension(tuple(value * exponent for value in self.powers))  # type: ignore[arg-type]

    def label(self) -> str:
        terms = [f"{name}^{power}" for name, power in zip(BASE_DIMENSIONS, self.powers, strict=True) if power]
        return "dimensionless" if not terms else " ".join(terms)


DIMENSIONLESS = Dimension()
MASS = Dimension((1, 0, 0, 0, 0, 0, 0))
LENGTH = Dimension((0, 1, 0, 0, 0, 0, 0))
TIME = Dimension((0, 0, 1, 0, 0, 0, 0))
TEMPERATURE = Dimension((0, 0, 0, 1, 0, 0, 0))
CURRENT = Dimension((0, 0, 0, 0, 1, 0, 0))
AMOUNT = Dimension((0, 0, 0, 0, 0, 1, 0))
LUMINOUS_INTENSITY = Dimension((0, 0, 0, 0, 0, 0, 1))


@dataclass(frozen=True)
class Unit:
    symbol: str
    scale_to_si: float
    dimension: Dimension

    def __post_init__(self) -> None:
        if not isinstance(self.symbol, str) or not self.symbol or len(self.symbol) > 128:
            raise ValueError("unit symbol must contain 1 to 128 characters")
        if not isinstance(self.dimension, Dimension):
            raise TypeError("unit dimension must be a Dimension")
        scale = _finite(self.scale_to_si, "unit scale")
        if scale <= 0:
            raise ValueError("unit scale must be positive")


_UNIT_DEFINITIONS = (
    Unit("1", 1.0, DIMENSIONLESS),
    Unit("kg", 1.0, MASS),
    Unit("g", 1e-3, MASS),
    Unit("m", 1.0, LENGTH),
    Unit("mm", 1e-3, LENGTH),
    Unit("cm", 1e-2, LENGTH),
    Unit("km", 1e3, LENGTH),
    Unit("s", 1.0, TIME),
    Unit("min", 60.0, TIME),
    Unit("h", 3600.0, TIME),
    Unit("K", 1.0, TEMPERATURE),
    Unit("A", 1.0, CURRENT),
    Unit("mol", 1.0, AMOUNT),
    Unit("cd", 1.0, LUMINOUS_INTENSITY),
    Unit("Hz", 1.0, TIME**-1),
    Unit("N", 1.0, MASS * LENGTH / TIME**2),
    Unit("Pa", 1.0, MASS / LENGTH / TIME**2),
    Unit("kPa", 1e3, MASS / LENGTH / TIME**2),
    Unit("MPa", 1e6, MASS / LENGTH / TIME**2),
    Unit("GPa", 1e9, MASS / LENGTH / TIME**2),
    Unit("J", 1.0, MASS * LENGTH**2 / TIME**2),
    Unit("W", 1.0, MASS * LENGTH**2 / TIME**3),
    Unit("L", 1e-3, LENGTH**3),
    Unit("mL", 1e-6, LENGTH**3),
)
UNITS = {unit.symbol: unit for unit in _UNIT_DEFINITIONS}
_UNIT_FACTOR = re.compile(r"(?P<symbol>1|[A-Za-z]+)(?:\^(?P<exponent>[+-]?\d+))?")


def parse_unit(expression: str) -> Unit:
    """Parse a bounded product/quotient of registered SI-derived units."""

    if not isinstance(expression, str) or not expression.strip() or len(expression) > 128:
        raise ValueError("unit expression must contain 1 to 128 characters")
    compact = expression.replace(" ", "")
    pieces = re.split(r"([*/])", compact)
    if not pieces or any(piece == "" for piece in pieces):
        raise ValueError(f"invalid unit expression {expression!r}")
    scale = 1.0
    dimension = DIMENSIONLESS
    operation = "*"
    normalized: list[str] = []
    for index, piece in enumerate(pieces):
        if index % 2:
            if piece not in {"*", "/"}:
                raise ValueError(f"invalid unit operator {piece!r}")
            operation = piece
            normalized.append(piece)
            continue
        match = _UNIT_FACTOR.fullmatch(piece)
        if match is None or match.group("symbol") not in UNITS:
            raise ValueError(f"unknown or invalid unit factor {piece!r}")
        base = UNITS[match.group("symbol")]
        exponent = int(match.group("exponent") or "1")
        if not -12 <= exponent <= 12:
            raise ValueError("unit exponents are limited to -12 through 12")
        if operation == "/":
            exponent = -exponent
        scale *= base.scale_to_si**exponent
        dimension = dimension * (base.dimension**exponent)
        normalized.append(piece)
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError("unit expression exceeds the finite numerical range")
    return Unit("".join(normalized), scale, dimension)


@dataclass(frozen=True)
class Quantity:
    """A physical quantity stored in SI base units with dimensional checking."""

    si_value: float
    dimension: Dimension

    def __post_init__(self) -> None:
        _finite(self.si_value, "quantity value")
        if not isinstance(self.dimension, Dimension):
            raise TypeError("quantity dimension must be a Dimension")

    @classmethod
    def from_value(cls, value: float, unit: str) -> Quantity:
        parsed = parse_unit(unit)
        return cls(_finite(value, "quantity value") * parsed.scale_to_si, parsed.dimension)

    def to(self, unit: str) -> float:
        parsed = parse_unit(unit)
        if parsed.dimension != self.dimension:
            raise ValueError(f"cannot convert {self.dimension.label()} to {parsed.dimension.label()}")
        return self.si_value / parsed.scale_to_si

    def _matching(self, other: Quantity) -> None:
        if not isinstance(other, Quantity) or other.dimension != self.dimension:
            other_label = other.dimension.label() if isinstance(other, Quantity) else type(other).__name__
            raise ValueError(f"incompatible dimensions: {self.dimension.label()} and {other_label}")

    def __add__(self, other: Quantity) -> Quantity:
        self._matching(other)
        return Quantity(self.si_value + other.si_value, self.dimension)

    def __sub__(self, other: Quantity) -> Quantity:
        self._matching(other)
        return Quantity(self.si_value - other.si_value, self.dimension)

    def __mul__(self, other: Quantity | float) -> Quantity:
        if isinstance(other, Quantity):
            return Quantity(self.si_value * other.si_value, self.dimension * other.dimension)
        return Quantity(self.si_value * _finite(other, "scalar"), self.dimension)

    def __rmul__(self, other: float) -> Quantity:
        return self * other

    def __truediv__(self, other: Quantity | float) -> Quantity:
        if isinstance(other, Quantity):
            if other.si_value == 0:
                raise ZeroDivisionError("quantity divisor is zero")
            return Quantity(self.si_value / other.si_value, self.dimension / other.dimension)
        divisor = _finite(other, "scalar")
        if divisor == 0:
            raise ZeroDivisionError("scalar divisor is zero")
        return Quantity(self.si_value / divisor, self.dimension)

    def __pow__(self, exponent: int) -> Quantity:
        if isinstance(exponent, bool) or not isinstance(exponent, int) or not -12 <= exponent <= 12:
            raise ValueError("quantity exponent must be an integer from -12 through 12")
        return Quantity(self.si_value**exponent, self.dimension**exponent)


def quantity(value: float, unit: str) -> Quantity:
    return Quantity.from_value(value, unit)


@dataclass(frozen=True)
class Jet:
    """A second-order forward-mode automatic-differentiation value."""

    value: float
    gradient: np.ndarray
    hessian: np.ndarray

    def __post_init__(self) -> None:
        value = _finite(self.value, "automatic-differentiation value")
        gradient = np.asarray(self.gradient)
        hessian = np.asarray(self.hessian)
        if gradient.ndim != 1 or not 1 <= len(gradient) <= MAX_VARIABLES:
            raise ValueError(f"gradient must contain 1 to {MAX_VARIABLES} values")
        if gradient.dtype.kind not in "iuf" or not np.isfinite(gradient).all():
            raise ValueError("gradient must contain only finite numbers")
        if hessian.shape != (len(gradient), len(gradient)) or hessian.dtype.kind not in "iuf" or not np.isfinite(hessian).all():
            raise ValueError("hessian must be a finite square matrix matching the gradient")
        gradient_copy = gradient.astype(float, copy=True)
        hessian_copy = hessian.astype(float, copy=True)
        if not np.allclose(hessian_copy, hessian_copy.T, rtol=0, atol=1e-12):
            raise ValueError("hessian must be symmetric")
        gradient_copy.setflags(write=False)
        hessian_copy.setflags(write=False)
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "gradient", gradient_copy)
        object.__setattr__(self, "hessian", hessian_copy)

    @classmethod
    def variable(cls, value: float, index: int, size: int) -> Jet:
        if not 1 <= size <= MAX_VARIABLES or not 0 <= index < size:
            raise ValueError("invalid automatic-differentiation variable shape")
        gradient = np.zeros(size)
        gradient[index] = 1.0
        return cls(_finite(value, "variable"), gradient, np.zeros((size, size)))

    @classmethod
    def constant(cls, value: float, size: int) -> Jet:
        if not 1 <= size <= MAX_VARIABLES:
            raise ValueError("invalid automatic-differentiation size")
        return cls(_finite(value, "constant"), np.zeros(size), np.zeros((size, size)))

    def _coerce(self, other: Jet | float) -> Jet:
        if isinstance(other, Jet):
            if other.gradient.shape != self.gradient.shape:
                raise ValueError("automatic-differentiation dimensions do not match")
            return other
        return Jet.constant(other, len(self.gradient))

    def __add__(self, other: Jet | float) -> Jet:
        right = self._coerce(other)
        return Jet(self.value + right.value, self.gradient + right.gradient, self.hessian + right.hessian)

    def __radd__(self, other: float) -> Jet:
        return self + other

    def __neg__(self) -> Jet:
        return Jet(-self.value, -self.gradient, -self.hessian)

    def __sub__(self, other: Jet | float) -> Jet:
        return self + -self._coerce(other)

    def __rsub__(self, other: float) -> Jet:
        return self._coerce(other) - self

    def __mul__(self, other: Jet | float) -> Jet:
        right = self._coerce(other)
        gradient = self.gradient * right.value + right.gradient * self.value
        hessian = (
            self.hessian * right.value
            + right.hessian * self.value
            + np.outer(self.gradient, right.gradient)
            + np.outer(right.gradient, self.gradient)
        )
        return Jet(self.value * right.value, gradient, hessian)

    def __rmul__(self, other: float) -> Jet:
        return self * other

    def reciprocal(self) -> Jet:
        if self.value == 0:
            raise ZeroDivisionError("automatic-differentiation divisor is zero")
        gradient = -self.gradient / self.value**2
        hessian = 2.0 * np.outer(self.gradient, self.gradient) / self.value**3 - self.hessian / self.value**2
        return Jet(1.0 / self.value, gradient, hessian)

    def __truediv__(self, other: Jet | float) -> Jet:
        return self * self._coerce(other).reciprocal()

    def __rtruediv__(self, other: float) -> Jet:
        return self._coerce(other) * self.reciprocal()

    def __pow__(self, exponent: float) -> Jet:
        power = _finite(exponent, "exponent")
        if self.value <= 0 and not power.is_integer():
            raise ValueError("fractional powers require a positive value")
        if self.value == 0 and power < 2:
            raise ValueError("power derivative is singular at zero")
        value = self.value**power
        first = power * self.value ** (power - 1)
        second = power * (power - 1) * self.value ** (power - 2) if power != 1 else 0.0
        return Jet(value, first * self.gradient, first * self.hessian + second * np.outer(self.gradient, self.gradient))


def _jet_unary(value: Jet, function: Callable[[float], float], first: Callable[[float], float], second: Callable[[float], float]) -> Jet:
    result = function(value.value)
    gradient_factor = first(value.value)
    hessian = gradient_factor * value.hessian + second(value.value) * np.outer(value.gradient, value.gradient)
    if not math.isfinite(result) or not np.isfinite(hessian).all():
        raise ValueError("automatic-differentiation result is non-finite")
    return Jet(result, gradient_factor * value.gradient, hessian)


def jet_sin(value: Jet) -> Jet:
    return _jet_unary(value, math.sin, math.cos, lambda x: -math.sin(x))


def jet_cos(value: Jet) -> Jet:
    return _jet_unary(value, math.cos, lambda x: -math.sin(x), lambda x: -math.cos(x))


def jet_exp(value: Jet) -> Jet:
    return _jet_unary(value, math.exp, math.exp, math.exp)


def jet_log(value: Jet) -> Jet:
    if value.value <= 0:
        raise ValueError("log requires a positive value")
    return _jet_unary(value, math.log, lambda x: 1.0 / x, lambda x: -1.0 / x**2)


def jet_sqrt(value: Jet) -> Jet:
    if value.value <= 0:
        raise ValueError("sqrt derivatives require a positive value")
    return value**0.5


def value_gradient_hessian(function: Callable[[tuple[Jet, ...]], Jet], values: tuple[float, ...]) -> tuple[float, np.ndarray, np.ndarray]:
    if not 1 <= len(values) <= MAX_VARIABLES:
        raise ValueError(f"automatic differentiation requires 1 to {MAX_VARIABLES} variables")
    variables = tuple(Jet.variable(value, index, len(values)) for index, value in enumerate(values))
    result = function(variables)
    if not isinstance(result, Jet) or not np.isfinite(result.gradient).all() or not np.isfinite(result.hessian).all():
        raise ValueError("automatic-differentiation function must return one finite Jet")
    return result.value, result.gradient.copy(), result.hessian.copy()


@dataclass(frozen=True)
class Interval:
    lower: float
    upper: float

    def __post_init__(self) -> None:
        lower, upper = _finite(self.lower, "interval lower"), _finite(self.upper, "interval upper")
        if lower > upper:
            raise ValueError("interval lower bound exceeds upper bound")

    @staticmethod
    def _down(value: float) -> float:
        return math.nextafter(value, -math.inf)

    @staticmethod
    def _up(value: float) -> float:
        return math.nextafter(value, math.inf)

    def __add__(self, other: Interval) -> Interval:
        return Interval(self._down(self.lower + other.lower), self._up(self.upper + other.upper))

    def __sub__(self, other: Interval) -> Interval:
        return Interval(self._down(self.lower - other.upper), self._up(self.upper - other.lower))

    def __mul__(self, other: Interval) -> Interval:
        products = (self.lower * other.lower, self.lower * other.upper, self.upper * other.lower, self.upper * other.upper)
        return Interval(self._down(min(products)), self._up(max(products)))

    def __truediv__(self, other: Interval) -> Interval:
        if other.lower <= 0 <= other.upper:
            raise ZeroDivisionError("interval divisor contains zero")
        reciprocal = Interval(self._down(1.0 / other.upper), self._up(1.0 / other.lower))
        return self * reciprocal

    def sqrt(self) -> Interval:
        if self.lower < 0:
            raise ValueError("interval square root requires a non-negative lower bound")
        lower = 0.0 if self.lower == 0 else self._down(math.sqrt(self.lower))
        return Interval(lower, self._up(math.sqrt(self.upper)))


@dataclass(frozen=True)
class NonlinearConstraint:
    name: str
    function: Callable[[np.ndarray], float]
    relation: str = "eq"
    tolerance: float = 1e-8
    scale: float = 1.0

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip() or len(self.name) > 128:
            raise ValueError("constraint name must contain 1 to 128 characters")
        if self.relation not in {"eq", "le", "ge"}:
            raise ValueError("constraint relation must be eq, le, or ge")
        if _finite(self.tolerance, "constraint tolerance") < 0:
            raise ValueError("constraint tolerance must be non-negative")
        if _finite(self.scale, "constraint scale") <= 0:
            raise ValueError("constraint scale must be positive")


def _constraint_raw(constraint: NonlinearConstraint, point: np.ndarray) -> float:
    return _finite(constraint.function(point.copy()), f"constraint {constraint.name!r} result")


def _violation(constraint: NonlinearConstraint, raw: float) -> float:
    if constraint.relation == "eq":
        return raw / constraint.scale
    if constraint.relation == "le":
        return max(0.0, raw / constraint.scale)
    return max(0.0, -raw / constraint.scale)


def _constraint_vector(constraints: tuple[NonlinearConstraint, ...], point: np.ndarray) -> np.ndarray:
    return np.asarray([_violation(item, _constraint_raw(item, point)) for item in constraints])


def _bounds(count: int, bounds: tuple[tuple[float | None, float | None], ...] | None) -> tuple[np.ndarray, np.ndarray]:
    if bounds is None:
        return np.full(count, -np.inf), np.full(count, np.inf)
    if len(bounds) != count:
        raise ValueError("bounds must contain one pair per variable")
    lower, upper = np.full(count, -np.inf), np.full(count, np.inf)
    for index, pair in enumerate(bounds):
        if not isinstance(pair, tuple) or len(pair) != 2:
            raise ValueError("each bound must be a (lower, upper) tuple")
        if pair[0] is not None:
            lower[index] = _finite(pair[0], f"bounds[{index}].lower")
        if pair[1] is not None:
            upper[index] = _finite(pair[1], f"bounds[{index}].upper")
        if lower[index] > upper[index]:
            raise ValueError(f"bounds[{index}] lower exceeds upper")
    return lower, upper


def _finite_difference_jacobian(
    function: Callable[[np.ndarray], np.ndarray],
    point: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
) -> np.ndarray:
    baseline = function(point)
    jacobian = np.empty((len(baseline), len(point)))
    for index, value in enumerate(point):
        step = np.cbrt(np.finfo(float).eps) * max(1.0, abs(float(value)))
        plus, minus = point.copy(), point.copy()
        plus[index] = min(upper[index], value + step)
        minus[index] = max(lower[index], value - step)
        span = plus[index] - minus[index]
        jacobian[:, index] = 0.0 if span == 0 else (function(plus) - function(minus)) / span
    return jacobian


@dataclass(frozen=True)
class ConstraintSolution:
    solution: tuple[float, ...]
    converged: bool
    iterations: int
    residual_norm: float
    condition_number: float | None
    conflicts: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "solution": list(self.solution),
            "converged": self.converged,
            "iterations": self.iterations,
            "residual_norm": self.residual_norm,
            "condition_number": self.condition_number,
            "conflicts": list(self.conflicts),
        }


def solve_nonlinear_constraints(
    initial: tuple[float, ...],
    constraints: tuple[NonlinearConstraint, ...],
    *,
    bounds: tuple[tuple[float | None, float | None], ...] | None = None,
    max_iterations: int = 100,
    tolerance: float = 1e-9,
) -> ConstraintSolution:
    """Solve a bounded nonlinear feasibility problem with damped least squares."""

    if not 1 <= len(initial) <= MAX_VARIABLES:
        raise ValueError(f"constraint solve requires 1 to {MAX_VARIABLES} variables")
    if not 1 <= len(constraints) <= MAX_CONSTRAINTS:
        raise ValueError(f"constraint solve requires 1 to {MAX_CONSTRAINTS} constraints")
    if isinstance(max_iterations, bool) or not isinstance(max_iterations, int) or not 1 <= max_iterations <= MAX_ITERATIONS:
        raise ValueError(f"max_iterations must be 1 to {MAX_ITERATIONS}")
    target_tolerance = _finite(tolerance, "solver tolerance")
    if target_tolerance <= 0:
        raise ValueError("solver tolerance must be positive")
    point = np.asarray([_finite(value, f"initial[{index}]") for index, value in enumerate(initial)])
    lower, upper = _bounds(len(point), bounds)
    point = np.clip(point, lower, upper)
    damping = 1e-6
    condition: float | None = None
    iterations = 0
    for iterations in range(1, max_iterations + 1):
        residual = _constraint_vector(constraints, point)
        norm = float(np.linalg.norm(residual))
        if norm <= target_tolerance:
            break
        jacobian = _finite_difference_jacobian(
            lambda value: _constraint_vector(constraints, value),
            point,
            lower,
            upper,
        )
        normal = jacobian.T @ jacobian
        condition_value = float(np.linalg.cond(normal))
        condition = condition_value if math.isfinite(condition_value) else None
        try:
            step = np.linalg.solve(normal + damping * np.eye(len(point)), -(jacobian.T @ residual))
        except np.linalg.LinAlgError:
            step = np.linalg.lstsq(jacobian, -residual, rcond=None)[0]
        candidate = np.clip(point + step, lower, upper)
        candidate_norm = float(np.linalg.norm(_constraint_vector(constraints, candidate)))
        if candidate_norm < norm:
            point, damping = candidate, max(damping / 3.0, 1e-15)
        else:
            damping = min(damping * 10.0, 1e15)
    residual = _constraint_vector(constraints, point)
    norm = float(np.linalg.norm(residual))
    conflicts: list[dict[str, Any]] = []
    for constraint, normalized in zip(constraints, residual, strict=True):
        raw = _constraint_raw(constraint, point)
        if abs(float(normalized)) > max(target_tolerance, constraint.tolerance / constraint.scale):
            conflicts.append({"name": constraint.name, "relation": constraint.relation, "residual": raw, "tolerance": constraint.tolerance})
    return ConstraintSolution(
        tuple(float(value) for value in point),
        norm <= target_tolerance and not conflicts,
        iterations,
        norm,
        condition,
        tuple(conflicts),
    )


@dataclass(frozen=True)
class OptimizationResult:
    solution: tuple[float, ...]
    objective: float
    feasible: bool
    converged: bool
    iterations: int
    gradient_norm: float
    conflicts: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "solution": list(self.solution),
            "objective": self.objective,
            "feasible": self.feasible,
            "converged": self.converged,
            "iterations": self.iterations,
            "gradient_norm": self.gradient_norm,
            "conflicts": list(self.conflicts),
        }


def minimize_constrained(
    objective: Callable[[np.ndarray], float],
    initial: tuple[float, ...],
    *,
    constraints: tuple[NonlinearConstraint, ...] = (),
    bounds: tuple[tuple[float | None, float | None], ...] | None = None,
    max_iterations: int = 500,
    tolerance: float = 1e-8,
    penalty: float = 1e4,
) -> OptimizationResult:
    """Minimize a scalar objective with projected finite-difference descent."""

    if not 1 <= len(initial) <= MAX_VARIABLES:
        raise ValueError(f"optimization requires 1 to {MAX_VARIABLES} variables")
    if len(constraints) > MAX_CONSTRAINTS:
        raise ValueError(f"optimization supports at most {MAX_CONSTRAINTS} constraints")
    if isinstance(max_iterations, bool) or not isinstance(max_iterations, int) or not 1 <= max_iterations <= MAX_ITERATIONS:
        raise ValueError(f"max_iterations must be 1 to {MAX_ITERATIONS}")
    target = _finite(tolerance, "optimization tolerance")
    penalty_value = _finite(penalty, "optimization penalty")
    if target <= 0 or penalty_value <= 0:
        raise ValueError("optimization tolerance and penalty must be positive")
    point = np.asarray([_finite(value, f"initial[{index}]") for index, value in enumerate(initial)])
    lower, upper = _bounds(len(point), bounds)
    point = np.clip(point, lower, upper)

    def augmented(value: np.ndarray) -> float:
        base = _finite(objective(value.copy()), "objective result")
        residual = _constraint_vector(constraints, value) if constraints else np.zeros(0)
        result = base + penalty_value * float(residual @ residual)
        return _finite(result, "augmented objective")

    converged = False
    gradient_norm = math.inf
    iterations = 0
    for iterations in range(1, max_iterations + 1):
        baseline = augmented(point)
        gradient = np.empty(len(point))
        for index, value in enumerate(point):
            step = np.cbrt(np.finfo(float).eps) * max(1.0, abs(float(value)))
            plus, minus = point.copy(), point.copy()
            plus[index] = min(upper[index], value + step)
            minus[index] = max(lower[index], value - step)
            span = plus[index] - minus[index]
            gradient[index] = 0.0 if span == 0 else (augmented(plus) - augmented(minus)) / span
        projected_gradient = gradient.copy()
        projected_gradient[(point <= lower) & (gradient > 0)] = 0.0
        projected_gradient[(point >= upper) & (gradient < 0)] = 0.0
        gradient_norm = float(np.linalg.norm(projected_gradient))
        if gradient_norm <= target:
            converged = True
            break
        direction = -projected_gradient
        step_size = 1.0
        accepted = False
        while step_size >= 1e-12:
            candidate = np.clip(point + step_size * direction, lower, upper)
            if augmented(candidate) <= baseline - 1e-4 * step_size * gradient_norm**2:
                point, accepted = candidate, True
                break
            step_size *= 0.5
        if not accepted:
            break
    conflicts: list[dict[str, Any]] = []
    if constraints:
        residual = _constraint_vector(constraints, point)
        for constraint, normalized in zip(constraints, residual, strict=True):
            raw = _constraint_raw(constraint, point)
            if abs(float(normalized)) > constraint.tolerance / constraint.scale:
                conflicts.append(
                    {
                        "name": constraint.name,
                        "relation": constraint.relation,
                        "residual": raw,
                        "tolerance": constraint.tolerance,
                    }
                )
    return OptimizationResult(
        tuple(float(value) for value in point),
        _finite(objective(point.copy()), "objective result"),
        not conflicts,
        converged,
        iterations,
        gradient_norm,
        tuple(conflicts),
    )


def monte_carlo_propagate(
    function: Callable[[np.ndarray], float],
    mean: tuple[float, ...],
    covariance: tuple[tuple[float, ...], ...],
    *,
    samples: int = 10_000,
    seed: int = 0,
) -> dict[str, Any]:
    """Reproducibly propagate a correlated normal input through a scalar model."""

    count = len(mean)
    if not 1 <= count <= MAX_VARIABLES:
        raise ValueError(f"Monte Carlo requires 1 to {MAX_VARIABLES} variables")
    if isinstance(samples, bool) or not isinstance(samples, int) or not 2 <= samples <= 1_000_000:
        raise ValueError("samples must be an integer from 2 through 1,000,000")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("seed must be an integer")
    center = np.asarray([_finite(value, f"mean[{index}]") for index, value in enumerate(mean)])
    matrix = np.asarray(covariance)
    if matrix.shape != (count, count) or matrix.dtype.kind not in "iuf" or not np.isfinite(matrix).all():
        raise ValueError(f"covariance must be a finite {count} x {count} numeric matrix")
    matrix = matrix.astype(float)
    if not np.allclose(matrix, matrix.T, rtol=0, atol=1e-12):
        raise ValueError("covariance must be symmetric")
    matrix = (matrix + matrix.T) / 2.0
    if float(np.linalg.eigvalsh(matrix).min()) < -1e-12:
        raise ValueError("covariance must be positive semidefinite")
    draws = np.random.default_rng(seed).multivariate_normal(center, matrix, size=samples, check_valid="raise")
    outcomes = np.asarray([_finite(function(draw), "Monte Carlo outcome") for draw in draws])
    standard_deviation = float(np.std(outcomes, ddof=1))
    return {
        "schema_version": "neurocad-monte-carlo-v1",
        "samples": samples,
        "seed": seed,
        "mean": float(np.mean(outcomes)),
        "standard_deviation": standard_deviation,
        "standard_error": standard_deviation / math.sqrt(samples),
        "quantiles": {str(level): float(np.quantile(outcomes, level)) for level in (0.005, 0.025, 0.5, 0.975, 0.995)},
        "claim_boundary": "sampling estimate under the declared distribution; not empirical validation or a safety guarantee",
    }


def linear_system_diagnostics(matrix: tuple[tuple[float, ...], ...], rhs: tuple[float, ...], solution: tuple[float, ...]) -> dict[str, Any]:
    """Report rank, conditioning, and scaled residual for a linear solve."""

    coefficients = np.asarray(matrix)
    target = np.asarray(rhs)
    estimate = np.asarray(solution)
    if coefficients.ndim != 2 or coefficients.dtype.kind not in "iuf" or not np.isfinite(coefficients).all():
        raise ValueError("matrix must be a finite numeric matrix")
    rows, columns = coefficients.shape
    if not 1 <= rows <= 4096 or not 1 <= columns <= 4096:
        raise ValueError("matrix dimensions must be from 1 through 4096")
    if target.shape != (rows,) or estimate.shape != (columns,) or target.dtype.kind not in "iuf" or estimate.dtype.kind not in "iuf":
        raise ValueError("rhs and solution dimensions must match the matrix")
    if not np.isfinite(target).all() or not np.isfinite(estimate).all():
        raise ValueError("rhs and solution must be finite")
    residual = coefficients @ estimate - target
    residual_norm = float(np.linalg.norm(residual))
    denominator = float(np.linalg.norm(coefficients) * np.linalg.norm(estimate) + np.linalg.norm(target))
    condition = float(np.linalg.cond(coefficients))
    return {
        "shape": [rows, columns],
        "rank": int(np.linalg.matrix_rank(coefficients)),
        "condition_number": condition if math.isfinite(condition) else None,
        "residual_norm": residual_norm,
        "relative_backward_error": residual_norm / denominator if denominator else residual_norm,
        "ill_conditioned": not math.isfinite(condition) or condition > 1.0 / math.sqrt(np.finfo(float).eps),
    }
