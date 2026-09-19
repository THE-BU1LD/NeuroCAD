"""Small, explicit engineering calculations used by NeuroCAD.

These functions are deterministic analytical estimates.  They intentionally do
not present themselves as finite-element analysis or safety certification.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import permutations
from statistics import NormalDist


def _finite_number(value: float, name: str) -> float:
    try:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"{name} must be a finite number")
        result = float(value)
    except OverflowError as exc:
        raise ValueError(f"{name} exceeds the finite numerical range") from exc
    return result


def _positive(value: float, name: str, *, allow_zero: bool = False) -> float:
    result = _finite_number(value, name)
    if result < 0 if allow_zero else result <= 0:
        qualifier = "non-negative" if allow_zero else "positive"
        raise ValueError(f"{name} must be {qualifier}")
    return result


@dataclass(frozen=True)
class ToleranceContribution:
    name: str
    mean_mm: float
    sigma_mm: float
    worst_case_mm: float


@dataclass(frozen=True)
class ToleranceTerm:
    """Auditable first-order contribution to a linear clearance stack."""

    name: str
    mean_effect_mm: float
    sigma_mm: float
    variance_contribution_mm2: float
    variance_fraction: float | None
    worst_case_loss_mm: float

    def to_dict(self) -> dict[str, float | str | None]:
        return {
            "name": self.name,
            "mean_effect_mm": self.mean_effect_mm,
            "sigma_mm": self.sigma_mm,
            "variance_contribution_mm2": self.variance_contribution_mm2,
            "variance_fraction": self.variance_fraction,
            "worst_case_loss_mm": self.worst_case_loss_mm,
        }


@dataclass(frozen=True)
class ToleranceStack:
    nominal_clearance_mm: float
    mean_clearance_mm: float
    sigma_mm: float
    worst_case_low_mm: float
    success_probability: float
    confidence_multiplier: float
    recommended_clearance_mm: float
    target_success_probability: float
    variance_mm2: float
    statistical_low_mm: float
    margin_to_target_mm: float
    worst_case_guard_applied: bool
    contributions: tuple[ToleranceTerm, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "nominal_clearance_mm": self.nominal_clearance_mm,
            "mean_clearance_mm": self.mean_clearance_mm,
            "sigma_mm": self.sigma_mm,
            "worst_case_low_mm": self.worst_case_low_mm,
            "success_probability": self.success_probability,
            "confidence_multiplier": self.confidence_multiplier,
            "recommended_clearance_mm": self.recommended_clearance_mm,
            "target_success_probability": self.target_success_probability,
            "variance_mm2": self.variance_mm2,
            "statistical_low_mm": self.statistical_low_mm,
            "margin_to_target_mm": self.margin_to_target_mm,
            "worst_case_guard_applied": self.worst_case_guard_applied,
            "contributions": [term.to_dict() for term in self.contributions],
        }


@dataclass(frozen=True)
class QuadraticToleranceStack:
    nominal_clearance_mm: float
    mean_clearance_mm: float
    sigma_mm: float
    worst_case_low_mm: float
    moment_matched_success_probability: float
    confidence_multiplier: float
    recommended_clearance_mm: float
    target_success_probability: float
    variance_mm2: float
    statistical_low_mm: float
    margin_to_target_mm: float
    worst_case_guard_applied: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "nominal_clearance_mm": self.nominal_clearance_mm,
            "mean_clearance_mm": self.mean_clearance_mm,
            "sigma_mm": self.sigma_mm,
            "worst_case_low_mm": self.worst_case_low_mm,
            "moment_matched_success_probability": self.moment_matched_success_probability,
            "confidence_multiplier": self.confidence_multiplier,
            "recommended_clearance_mm": self.recommended_clearance_mm,
            "target_success_probability": self.target_success_probability,
            "variance_mm2": self.variance_mm2,
            "statistical_low_mm": self.statistical_low_mm,
            "margin_to_target_mm": self.margin_to_target_mm,
            "worst_case_guard_applied": self.worst_case_guard_applied,
        }


def _target_multiplier(confidence_multiplier: float, target_success_probability: float | None) -> tuple[float, float]:
    if target_success_probability is None:
        confidence = _positive(confidence_multiplier, "confidence_multiplier")
        return confidence, NormalDist().cdf(confidence)
    target = _finite_number(target_success_probability, "target_success_probability")
    if not 0.5 <= target < 1.0:
        raise ValueError("target_success_probability must be at least 0.5 and less than 1")
    return NormalDist().inv_cdf(target), target


def tolerance_stack(
    nominal_clearance_mm: float,
    contributions: tuple[ToleranceContribution, ...],
    *,
    confidence_multiplier: float = 3.0,
    correlations: tuple[tuple[float, ...], ...] | None = None,
    target_success_probability: float | None = None,
    require_nonnegative_worst_case: bool = False,
) -> ToleranceStack:
    """Combine joint-normal variation and explicit worst-case bounds.

    Positive contribution means increase clearance; negative means reduce it.
    ``worst_case_mm`` is the magnitude that may reduce available clearance.
    Correlations follow contribution order, default to independence, and must
    form a symmetric positive-semidefinite unit-diagonal matrix. Means and
    worst-case intervals are separate from the unbounded normal approximation.
    """

    nominal = _positive(nominal_clearance_mm, "nominal_clearance_mm", allow_zero=True)
    confidence, target_probability = _target_multiplier(confidence_multiplier, target_success_probability)
    if not isinstance(require_nonnegative_worst_case, bool):
        raise TypeError("require_nonnegative_worst_case must be a boolean")
    mean_shifts = []
    independent_variances = []
    worst_cases = []
    if len(contributions) > 128:
        raise ValueError("tolerance stacks are limited to 128 contributions")
    names: set[str] = set()
    sigmas = []
    for contribution in contributions:
        if not isinstance(contribution.name, str) or not contribution.name.strip() or contribution.name.strip() in names:
            raise ValueError("tolerance contribution names must be non-empty and unique")
        names.add(contribution.name.strip())
        mean_effect = _finite_number(contribution.mean_mm, f"{contribution.name} mean")
        sigma = _positive(contribution.sigma_mm, f"{contribution.name} sigma", allow_zero=True)
        worst = _positive(contribution.worst_case_mm, f"{contribution.name} worst case", allow_zero=True)
        mean_shifts.append(mean_effect)
        independent_variances.append(sigma * sigma)
        sigmas.append(sigma)
        worst_cases.append(worst)
    # Signed dimensional effects may cancel. Naive incremental addition made
    # the reported clearance depend on input order even for finite inputs.
    try:
        mean_shift = math.fsum(mean_shifts)
        mean = math.fsum([nominal, *mean_shifts])
        variance = math.fsum(independent_variances)
        worst_loss = math.fsum(worst_cases)
    except OverflowError as exc:
        raise ValueError("tolerance stack exceeds the finite numerical range") from exc
    variance_contributions = list(independent_variances)
    if correlations is not None:
        import numpy as np

        matrix = np.asarray(correlations)
        count = len(contributions)
        has_booleans = any(isinstance(value, (bool, np.bool_)) for value in np.asarray(correlations, dtype=object).flat)
        if has_booleans or not count or matrix.shape != (count, count) or matrix.dtype.kind not in "iuf" or not np.isfinite(matrix).all():
            raise ValueError("correlations must be a finite square matrix matching non-empty contributions")
        matrix = matrix.astype(float)
        if (np.abs(matrix) > 1).any() or not np.allclose(matrix, matrix.T, rtol=0, atol=1e-12):
            raise ValueError("correlations must be symmetric with entries in [-1, 1]")
        if not np.allclose(np.diag(matrix), 1, rtol=0, atol=1e-12):
            raise ValueError("correlations must have unit diagonal")
        matrix = (matrix + matrix.T) / 2
        if float(np.linalg.eigvalsh(matrix).min()) < -1e-12:
            raise ValueError("correlations must be positive semidefinite")
        sigma_vector = np.asarray(sigmas)
        with np.errstate(over="ignore", invalid="ignore"):
            marginal_variances = sigma_vector * (matrix @ sigma_vector)
            variance = float(math.fsum(float(value) for value in marginal_variances))
        if not math.isfinite(variance):
            raise ValueError("tolerance stack exceeds the finite numerical range")
        variance = max(0.0, variance)
        variance_contributions = [float(value) for value in marginal_variances]
    if not all(math.isfinite(value) for value in (variance, mean_shift, worst_loss)):
        raise ValueError("tolerance stack exceeds the finite numerical range")
    sigma_total = math.sqrt(variance)
    if sigma_total == 0:
        success = 1.0 if mean >= 0 else 0.0
    else:
        success = 0.5 * (1.0 + math.erf(mean / (sigma_total * math.sqrt(2.0))))
    statistical_low = mean - confidence * sigma_total
    probabilistic_recommendation = confidence * sigma_total - mean_shift
    worst_case_recommendation = worst_loss - mean_shift
    recommended = max(
        0.0,
        probabilistic_recommendation,
        worst_case_recommendation if require_nonnegative_worst_case else 0.0,
    )
    worst_low = mean - worst_loss
    if not all(math.isfinite(value) for value in (mean, recommended, worst_low, statistical_low)):
        raise ValueError("tolerance stack exceeds the finite numerical range")
    term_reports = tuple(
        ToleranceTerm(
            contribution.name.strip(),
            mean_shifts[index],
            sigmas[index],
            variance_contributions[index],
            variance_contributions[index] / variance if variance > 0 else None,
            worst_cases[index],
        )
        for index, contribution in enumerate(contributions)
    )
    return ToleranceStack(
        nominal,
        mean,
        sigma_total,
        worst_low,
        success,
        confidence,
        recommended,
        target_probability,
        variance,
        statistical_low,
        statistical_low,
        require_nonnegative_worst_case,
        term_reports,
    )


def quadratic_tolerance_stack(
    nominal_clearance_mm: float,
    contributions: tuple[ToleranceContribution, ...],
    *,
    sensitivities: tuple[float, ...],
    hessian_per_mm: tuple[tuple[float, ...], ...],
    confidence_multiplier: float = 3.0,
    correlations: tuple[tuple[float, ...], ...] | None = None,
    target_success_probability: float | None = None,
    require_nonnegative_worst_case: bool = False,
) -> QuadraticToleranceStack:
    """Propagate a local quadratic clearance model under normal inputs.

    For input vector ``X`` in millimetres, the local model is
    ``c = nominal + g^T X + 0.5 X^T H X``. Its mean and variance are exact
    moments under the declared multivariate normal distribution. The reported
    success probability is only a moment-matched normal approximation because
    a quadratic form is not generally normally distributed.
    """

    import numpy as np

    nominal = _positive(nominal_clearance_mm, "nominal_clearance_mm", allow_zero=True)
    confidence, target_probability = _target_multiplier(confidence_multiplier, target_success_probability)
    if not isinstance(require_nonnegative_worst_case, bool):
        raise TypeError("require_nonnegative_worst_case must be a boolean")
    count = len(contributions)
    if not 1 <= count <= 128:
        raise ValueError("quadratic tolerance stacks require 1 to 128 contributions")
    names: set[str] = set()
    means: list[float] = []
    sigmas: list[float] = []
    worst_cases: list[float] = []
    for contribution in contributions:
        if not isinstance(contribution.name, str) or not contribution.name.strip() or contribution.name.strip() in names:
            raise ValueError("tolerance contribution names must be non-empty and unique")
        names.add(contribution.name.strip())
        means.append(_finite_number(contribution.mean_mm, f"{contribution.name} mean"))
        sigmas.append(_positive(contribution.sigma_mm, f"{contribution.name} sigma", allow_zero=True))
        worst_cases.append(_positive(contribution.worst_case_mm, f"{contribution.name} worst case", allow_zero=True))

    if len(sensitivities) != count or any(isinstance(value, bool) for value in sensitivities):
        raise ValueError("sensitivities must contain one finite number per contribution")
    gradient = np.asarray(sensitivities)
    hessian = np.asarray(hessian_per_mm)
    correlation = np.eye(count) if correlations is None else np.asarray(correlations)
    for name, matrix in (("hessian_per_mm", hessian), ("correlations", correlation)):
        has_booleans = any(isinstance(value, (bool, np.bool_)) for value in np.asarray(matrix, dtype=object).flat)
        if has_booleans or matrix.shape != (count, count) or matrix.dtype.kind not in "iuf" or not np.isfinite(matrix).all():
            raise ValueError(f"{name} must be a finite {count} x {count} numeric matrix")
    if gradient.dtype.kind not in "iuf" or not np.isfinite(gradient).all():
        raise ValueError("sensitivities must contain one finite number per contribution")
    gradient = gradient.astype(float)
    hessian = hessian.astype(float)
    correlation = correlation.astype(float)
    if not np.allclose(hessian, hessian.T, rtol=0, atol=1e-12):
        raise ValueError("hessian_per_mm must be symmetric")
    hessian = (hessian + hessian.T) / 2.0
    if (np.abs(correlation) > 1).any() or not np.allclose(correlation, correlation.T, rtol=0, atol=1e-12):
        raise ValueError("correlations must be symmetric with entries in [-1, 1]")
    if not np.allclose(np.diag(correlation), 1, rtol=0, atol=1e-12):
        raise ValueError("correlations must have unit diagonal")
    correlation = (correlation + correlation.T) / 2.0
    if float(np.linalg.eigvalsh(correlation).min()) < -1e-12:
        raise ValueError("correlations must be positive semidefinite")

    mean_vector = np.asarray(means, dtype=float)
    sigma_vector = np.asarray(sigmas, dtype=float)
    worst_vector = np.asarray(worst_cases, dtype=float)
    covariance = np.outer(sigma_vector, sigma_vector) * correlation
    with np.errstate(over="ignore", invalid="ignore"):
        center_effect = float(gradient @ mean_vector + 0.5 * mean_vector @ hessian @ mean_vector)
        curvature_bias = 0.5 * float(np.trace(hessian @ covariance))
        effective_gradient = gradient + hessian @ mean_vector
        variance = float(effective_gradient @ covariance @ effective_gradient)
        variance += 0.5 * float(np.trace((hessian @ covariance) @ (hessian @ covariance)))
        interval_loss = float(np.abs(effective_gradient) @ worst_vector)
        interval_loss += 0.5 * float(worst_vector @ np.abs(hessian) @ worst_vector)
    mean_effect = center_effect + curvature_bias
    mean_clearance = nominal + mean_effect
    variance = max(0.0, variance)
    sigma_total = math.sqrt(variance)
    worst_low = nominal + center_effect - interval_loss
    if not all(math.isfinite(value) for value in (mean_effect, mean_clearance, variance, sigma_total, worst_low)):
        raise ValueError("quadratic tolerance stack exceeds the finite numerical range")
    if sigma_total == 0:
        success = 1.0 if mean_clearance >= 0 else 0.0
    else:
        success = 0.5 * (1.0 + math.erf(mean_clearance / (sigma_total * math.sqrt(2.0))))
    statistical_low = mean_clearance - confidence * sigma_total
    probabilistic_recommendation = confidence * sigma_total - mean_effect
    worst_case_recommendation = interval_loss - center_effect
    recommended = max(
        0.0,
        probabilistic_recommendation,
        worst_case_recommendation if require_nonnegative_worst_case else 0.0,
    )
    if not all(math.isfinite(value) for value in (recommended, statistical_low)):
        raise ValueError("quadratic tolerance stack exceeds the finite numerical range")
    return QuadraticToleranceStack(
        nominal,
        mean_clearance,
        sigma_total,
        worst_low,
        success,
        confidence,
        recommended,
        target_probability,
        variance,
        statistical_low,
        statistical_low,
        require_nonnegative_worst_case,
    )


@dataclass(frozen=True)
class CantileverResult:
    second_moment_mm4: float
    maximum_stress_mpa: float
    tip_deflection_mm: float
    strain: float
    safety_factor: float | None

    def to_dict(self) -> dict[str, float | None]:
        return {
            "second_moment_mm4": self.second_moment_mm4,
            "maximum_stress_mpa": self.maximum_stress_mpa,
            "tip_deflection_mm": self.tip_deflection_mm,
            "strain": self.strain,
            "safety_factor": self.safety_factor,
        }


def rectangular_cantilever(
    *,
    force_n: float,
    length_mm: float,
    width_mm: float,
    thickness_mm: float,
    elastic_modulus_mpa: float,
    yield_strength_mpa: float | None = None,
) -> CantileverResult:
    """Euler-Bernoulli estimate for an end-loaded rectangular cantilever."""

    force = _positive(force_n, "force_n", allow_zero=True)
    length = _positive(length_mm, "length_mm")
    width = _positive(width_mm, "width_mm")
    thickness = _positive(thickness_mm, "thickness_mm")
    modulus = _positive(elastic_modulus_mpa, "elastic_modulus_mpa")
    second_moment = width * thickness**3 / 12.0
    moment = force * length
    stress = moment * (thickness / 2.0) / second_moment
    deflection = force * length**3 / (3.0 * modulus * second_moment)
    strain = stress / modulus
    safety_factor = None
    if yield_strength_mpa is not None:
        strength = _positive(yield_strength_mpa, "yield_strength_mpa")
        safety_factor = None if stress == 0 else strength / stress
    return CantileverResult(second_moment, stress, deflection, strain, safety_factor)


@dataclass(frozen=True)
class OrientationCandidate:
    name: str
    support_area_mm2: float
    height_mm: float
    weak_axis_penalty: float
    visible_surface_penalty: float
    bed_contact_mm2: float


@dataclass(frozen=True)
class ScoredOrientation:
    name: str
    score: float
    terms: dict[str, float]


def score_orientations(
    candidates: tuple[OrientationCandidate, ...],
    *,
    support_weight: float = 1.0,
    height_weight: float = 0.1,
    weak_axis_weight: float = 10.0,
    visible_surface_weight: float = 5.0,
    bed_contact_weight: float = 0.05,
) -> tuple[ScoredOrientation, ...]:
    if not candidates:
        raise ValueError("at least one orientation candidate is required")
    weights = {
        "support": _positive(support_weight, "support_weight", allow_zero=True),
        "height": _positive(height_weight, "height_weight", allow_zero=True),
        "weak_axis": _positive(weak_axis_weight, "weak_axis_weight", allow_zero=True),
        "visible_surface": _positive(visible_surface_weight, "visible_surface_weight", allow_zero=True),
        "bed_contact": _positive(bed_contact_weight, "bed_contact_weight", allow_zero=True),
    }
    scored: list[ScoredOrientation] = []
    for candidate in candidates:
        support = _positive(candidate.support_area_mm2, f"{candidate.name}.support_area_mm2", allow_zero=True)
        height = _positive(candidate.height_mm, f"{candidate.name}.height_mm")
        weak = _positive(candidate.weak_axis_penalty, f"{candidate.name}.weak_axis_penalty", allow_zero=True)
        visible = _positive(candidate.visible_surface_penalty, f"{candidate.name}.visible_surface_penalty", allow_zero=True)
        bed = _positive(candidate.bed_contact_mm2, f"{candidate.name}.bed_contact_mm2")
        terms = {
            "support": weights["support"] * support,
            "height": weights["height"] * height,
            "weak_axis": weights["weak_axis"] * weak,
            "visible_surface": weights["visible_surface"] * visible,
            "bed_contact_credit": -weights["bed_contact"] * math.sqrt(bed),
        }
        scored.append(ScoredOrientation(candidate.name, sum(terms.values()), terms))
    return tuple(sorted(scored, key=lambda item: (item.score, item.name)))


def symmetric_positions(count: int, width_mm: float, depth_mm: float, margin_mm: float) -> tuple[tuple[float, float], ...]:
    """Return deterministic positions whose centroid is at the origin."""

    if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 256:
        raise ValueError("count must be an integer from 1 to 256")
    width = _positive(width_mm, "width_mm")
    depth = _positive(depth_mm, "depth_mm")
    margin = _positive(margin_mm, "margin_mm", allow_zero=True)
    radius_x = width / 2 - margin
    radius_y = depth / 2 - margin
    if radius_x < 0 or radius_y < 0:
        raise ValueError("margin leaves no placement region")
    if count == 1:
        return ((0.0, 0.0),)
    if count == 2:
        return ((-radius_x, 0.0), (radius_x, 0.0))
    if count == 4:
        return ((-radius_x, -radius_y), (-radius_x, radius_y), (radius_x, -radius_y), (radius_x, radius_y))
    offset = -math.pi / 2 if count % 2 else -math.pi / 2 + math.pi / count
    positions = tuple(
        (radius_x * math.cos(offset + math.tau * index / count), radius_y * math.sin(offset + math.tau * index / count))
        for index in range(count)
    )
    # Remove floating-point centroid noise so symmetry is an enforceable invariant.
    mean_x = sum(item[0] for item in positions) / count
    mean_y = sum(item[1] for item in positions) / count
    return tuple((x - mean_x, y - mean_y) for x, y in positions)


@dataclass(frozen=True)
class LayoutItem:
    id: str
    size_mm: tuple[float, float]
    may_rotate: bool = True


@dataclass(frozen=True)
class LayoutPlacement:
    id: str
    center_xy_mm: tuple[float, float]
    size_mm: tuple[float, float]
    rotated: bool


def pack_rectangles(
    container_size_mm: tuple[float, float],
    items: tuple[LayoutItem, ...],
    *,
    clearance_mm: float,
) -> tuple[LayoutPlacement, ...]:
    """Deterministic shelf packing for small component-layout proposals.

    This is an explainable feasible-layout generator, not a global optimizer.
    It tries size-descending item orders and both orientations, then returns the
    layout with the smallest used height.
    """

    width = _positive(container_size_mm[0], "container width")
    depth = _positive(container_size_mm[1], "container depth")
    clearance = _positive(clearance_mm, "clearance_mm", allow_zero=True)
    if len(items) > 10:
        raise ValueError("automatic packing is limited to 10 items")
    if len({item.id for item in items}) != len(items) or any(not item.id for item in items):
        raise ValueError("layout item ids must be non-empty and unique")
    for item in items:
        _positive(item.size_mm[0], f"{item.id} width")
        _positive(item.size_mm[1], f"{item.id} depth")
    orders = [tuple(sorted(items, key=lambda item: (-max(item.size_mm), -min(item.size_mm), item.id)))]
    if len(items) <= 7:
        orders.extend(permutations(items))
    best: tuple[float, tuple[tuple[object, ...], ...], tuple[LayoutPlacement, ...]] | None = None
    for order in orders:
        x = clearance
        y = clearance
        row_depth = 0.0
        placements: list[LayoutPlacement] = []
        failed = False
        for item in order:
            options = [(item.size_mm[0], item.size_mm[1], False)]
            if item.may_rotate and item.size_mm[0] != item.size_mm[1]:
                options.append((item.size_mm[1], item.size_mm[0], True))
            options.sort(key=lambda option: (option[1], option[0], option[2]))
            chosen = next((option for option in options if x + option[0] + clearance <= width), None)
            if chosen is None:
                x = clearance
                y += row_depth + clearance
                row_depth = 0.0
                chosen = next((option for option in options if x + option[0] + clearance <= width), None)
            if chosen is None or y + chosen[1] + clearance > depth:
                failed = True
                break
            item_width, item_depth, rotated = chosen
            placements.append(
                LayoutPlacement(
                    item.id,
                    (x + item_width / 2 - width / 2, y + item_depth / 2 - depth / 2),
                    (item_width, item_depth),
                    rotated,
                )
            )
            x += item_width + clearance
            row_depth = max(row_depth, item_depth)
        if not failed:
            used_depth = y + row_depth + clearance
            candidate = tuple(sorted(placements, key=lambda placement: placement.id))
            candidate_key = tuple(
                (placement.id, *placement.center_xy_mm, *placement.size_mm, placement.rotated)
                for placement in candidate
            )
            if best is None or (used_depth, candidate_key) < (best[0], best[1]):
                best = used_depth, candidate_key, candidate
    if best is None:
        raise ValueError("components cannot be packed inside the requested region")
    return best[2]
