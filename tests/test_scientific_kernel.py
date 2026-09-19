from __future__ import annotations

import math

import numpy as np
import pytest

from core.scientific_kernel import (
    Interval,
    Jet,
    NonlinearConstraint,
    jet_exp,
    jet_sin,
    linear_system_diagnostics,
    minimize_constrained,
    monte_carlo_propagate,
    parse_unit,
    quantity,
    solve_nonlinear_constraints,
    value_gradient_hessian,
)


def test_quantities_convert_and_derive_dimensions() -> None:
    assert quantity(1, "m").to("mm") == pytest.approx(1_000)
    pressure = quantity(1, "N") / quantity(1, "mm^2")
    assert pressure.to("MPa") == pytest.approx(1)
    assert quantity(750, "mL").to("L") == pytest.approx(0.75)


def test_quantities_reject_dimensionally_invalid_operations() -> None:
    with pytest.raises(ValueError, match="incompatible dimensions"):
        quantity(1, "m") + quantity(1, "s")
    with pytest.raises(ValueError, match="cannot convert"):
        quantity(1, "kg").to("mm")
    with pytest.raises(ValueError, match="unknown"):
        parse_unit("furlong/fortnight")


def test_second_order_automatic_differentiation_matches_reference() -> None:
    value, gradient, hessian = value_gradient_hessian(
        lambda variables: variables[0] ** 2 * variables[1] + jet_sin(variables[1]),
        (2.0, 0.5),
    )
    assert value == pytest.approx(2.0 + math.sin(0.5))
    assert gradient == pytest.approx([2.0, 4.0 + math.cos(0.5)])
    np.testing.assert_allclose(hessian, [[1.0, 4.0], [4.0, -math.sin(0.5)]])


def test_automatic_differentiation_composes_exp_and_division() -> None:
    value, gradient, hessian = value_gradient_hessian(
        lambda variables: jet_exp(variables[0]) / variables[1],
        (0.0, 2.0),
    )
    assert value == pytest.approx(0.5)
    assert gradient == pytest.approx([0.5, -0.25])
    np.testing.assert_allclose(hessian, [[0.5, -0.25], [-0.25, 0.25]])


def test_intervals_enclose_roundoff_and_reject_zero_divisor() -> None:
    result = Interval(0.1, 0.1) + Interval(0.2, 0.2)
    assert result.lower <= 0.3 <= result.upper
    product = Interval(-2, 3) * Interval(4, 5)
    assert product.lower <= -10 and product.upper >= 15
    with pytest.raises(ZeroDivisionError, match="contains zero"):
        Interval(1, 2) / Interval(-1, 1)
    assert Interval(0, 4).sqrt().lower == 0


def test_nonlinear_solver_satisfies_circle_and_symmetry_constraints() -> None:
    constraints = (
        NonlinearConstraint("unit circle", lambda value: value[0] ** 2 + value[1] ** 2 - 1),
        NonlinearConstraint("equal coordinates", lambda value: value[0] - value[1]),
    )
    result = solve_nonlinear_constraints((0.7, 0.6), constraints)
    assert result.converged
    assert result.conflicts == ()
    assert result.solution == pytest.approx([math.sqrt(0.5), math.sqrt(0.5)])


def test_nonlinear_solver_reports_conflicting_requirements() -> None:
    result = solve_nonlinear_constraints(
        (0.5,),
        (
            NonlinearConstraint("must be zero", lambda value: value[0]),
            NonlinearConstraint("must be one", lambda value: value[0] - 1),
        ),
        max_iterations=20,
    )
    assert not result.converged
    assert {item["name"] for item in result.conflicts} == {"must be zero", "must be one"}


def test_nonlinear_solver_handles_inequalities_and_bounds() -> None:
    result = solve_nonlinear_constraints(
        (0.0,),
        (NonlinearConstraint("minimum wall", lambda value: value[0] - 2.0, relation="ge"),),
        bounds=((0.0, 10.0),),
    )
    assert result.converged
    assert result.solution[0] >= 2.0 - 1e-8


def test_local_optimizer_minimizes_with_bounds() -> None:
    result = minimize_constrained(
        lambda value: (value[0] - 3.0) ** 2 + (value[1] + 2.0) ** 2,
        (0.0, 0.0),
        bounds=((0.0, 5.0), (-5.0, 0.0)),
        tolerance=1e-7,
    )
    assert result.converged
    assert result.feasible
    assert result.solution == pytest.approx([3.0, -2.0], abs=1e-6)
    assert result.objective < 1e-12


def test_local_optimizer_recognizes_bound_optimum_and_actual_feasibility() -> None:
    at_bound = minimize_constrained(lambda value: (value[0] + 2.0) ** 2, (3.0,), bounds=((0.0, 5.0),))
    assert at_bound.converged
    assert at_bound.solution == pytest.approx((0.0,))

    infeasible = minimize_constrained(
        lambda value: value[0] ** 2,
        (0.0,),
        constraints=(NonlinearConstraint("must exceed one", lambda value: value[0] - 1.0, relation="ge"),),
        max_iterations=1,
        penalty=1e-6,
    )
    assert not infeasible.feasible
    assert infeasible.conflicts[0]["name"] == "must exceed one"


def test_monte_carlo_is_seeded_and_matches_linear_reference() -> None:
    first = monte_carlo_propagate(
        lambda value: 2.0 * value[0] - value[1],
        (1.0, 2.0),
        ((0.25, 0.0), (0.0, 1.0)),
        samples=20_000,
        seed=42,
    )
    second = monte_carlo_propagate(
        lambda value: 2.0 * value[0] - value[1],
        (1.0, 2.0),
        ((0.25, 0.0), (0.0, 1.0)),
        samples=20_000,
        seed=42,
    )
    assert first == second
    assert first["mean"] == pytest.approx(0.0, abs=0.04)
    assert first["standard_deviation"] == pytest.approx(math.sqrt(2), rel=0.03)
    assert "not empirical validation" in first["claim_boundary"]


def test_linear_diagnostics_report_residual_and_conditioning() -> None:
    result = linear_system_diagnostics(((3.0, 1.0), (1.0, 2.0)), (9.0, 8.0), (2.0, 3.0))
    assert result["rank"] == 2
    assert result["residual_norm"] == pytest.approx(0)
    assert result["relative_backward_error"] == pytest.approx(0)
    assert result["ill_conditioned"] is False


def test_public_jet_constructor_enforces_immutable_finite_derivatives() -> None:
    gradient = np.array([1.0, 2.0])
    hessian = np.eye(2)
    value = Jet(3.0, gradient, hessian)
    gradient[0] = 99
    hessian[0, 0] = 99
    assert value.gradient.tolist() == [1.0, 2.0]
    assert value.hessian.tolist() == [[1.0, 0.0], [0.0, 1.0]]
    assert not value.gradient.flags.writeable
    assert not value.hessian.flags.writeable
    with pytest.raises(ValueError, match="gradient"):
        Jet(1.0, np.array([math.nan]), np.zeros((1, 1)))
    with pytest.raises(ValueError, match="hessian"):
        Jet(1.0, np.ones(2), np.zeros((3, 3)))
    with pytest.raises(ValueError, match="symmetric"):
        Jet(1.0, np.ones(2), np.array([[0.0, 1.0], [0.0, 0.0]]))


def test_solvers_never_evaluate_functions_outside_declared_bounds() -> None:
    visited: list[float] = []

    def bounded_objective(value: np.ndarray) -> float:
        assert 0.0 <= value[0] <= 1.0
        visited.append(float(value[0]))
        return (value[0] + 1.0) ** 2

    optimized = minimize_constrained(
        bounded_objective,
        (0.0,),
        bounds=((0.0, 1.0),),
    )
    assert optimized.converged
    assert optimized.solution == (0.0,)
    assert visited

    constraint = NonlinearConstraint(
        "stay at lower bound",
        lambda value: bounded_objective(value) - 1.21,
    )
    solved = solve_nonlinear_constraints((0.0,), (constraint,), bounds=((0.0, 1.0),))
    assert solved.converged


@pytest.mark.parametrize(
    "call",
    [
        lambda: solve_nonlinear_constraints((math.nan,), (NonlinearConstraint("x", lambda value: value[0]),)),
        lambda: minimize_constrained(lambda value: math.inf, (0.0,)),
        lambda: monte_carlo_propagate(lambda value: value[0], (0.0,), ((-1.0,),), samples=10),
        lambda: linear_system_diagnostics(((1.0, 2.0),), (1.0, 2.0), (1.0, 2.0)),
    ],
)
def test_scientific_kernel_rejects_invalid_inputs(call: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        call()  # type: ignore[operator]
