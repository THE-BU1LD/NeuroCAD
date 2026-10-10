"""Analytic polynomial identities, including zero-valued design variables."""

from __future__ import annotations

import numpy as np
import pytest

from core.scientific_kernel import Jet, value_gradient_hessian


@pytest.mark.parametrize("base", [0., -3., 2.])
@pytest.mark.parametrize("exponent", [0, 1, 2, 3, 4])
def test_monomial_derivatives_at_zero_and_nonzero_points(base, exponent):
    value, gradient, hessian = value_gradient_hessian(lambda x: x[0] ** exponent, (base,))
    expected_value = base ** exponent
    expected_first = 0. if exponent == 0 else exponent * base ** (exponent - 1)
    expected_second = 0. if exponent < 2 else exponent * (exponent - 1) * base ** (exponent - 2)
    assert value == pytest.approx(expected_value)
    np.testing.assert_allclose(gradient, [expected_first], rtol=0, atol=1e-14)
    np.testing.assert_allclose(hessian, [[expected_second]], rtol=0, atol=1e-14)


def test_identity_power_preserves_composed_derivatives_at_zero():
    composed = Jet(0., np.array([2., -1.]), np.array([[3., 4.], [4., 5.]]))
    result = composed ** 1
    assert result.value == 0.
    np.testing.assert_array_equal(result.gradient, composed.gradient)
    np.testing.assert_array_equal(result.hessian, composed.hessian)


def test_constant_power_has_no_spurious_derivatives_at_zero():
    composed = Jet(0., np.array([2., -1.]), np.array([[3., 4.], [4., 5.]]))
    result = composed ** 0
    assert result.value == 1.
    np.testing.assert_array_equal(result.gradient, np.zeros(2))
    np.testing.assert_array_equal(result.hessian, np.zeros((2, 2)))


def test_multivariate_polynomial_hessian_at_origin():
    value, gradient, hessian = value_gradient_hessian(
        lambda x: x[0] ** 0 + x[0] ** 1 + x[0] ** 2 * x[1], (0., 2.),
    )
    assert value == 1.
    np.testing.assert_array_equal(gradient, [1., 0.])
    np.testing.assert_array_equal(hessian, [[4., 0.], [0., 0.]])


@pytest.mark.parametrize("index", [True, False, .5, -1, 2])
def test_invalid_variable_indices_cannot_create_multiaxis_gradients(index):
    with pytest.raises(ValueError, match="index|shape"):
        Jet.variable(1., index, 2)


@pytest.mark.parametrize("size", [True, False, 1.5, 0, 129])
def test_variable_and_constant_dimensions_require_bounded_integers(size):
    with pytest.raises(ValueError, match="shape|size"):
        Jet.variable(1., 0, size)
    with pytest.raises(ValueError, match="size"):
        Jet.constant(1., size)


def test_derivative_result_must_match_input_dimension():
    with pytest.raises(ValueError, match="dimension"):
        value_gradient_hessian(lambda x: Jet.constant(1., 2), (1.,))


@pytest.mark.parametrize("exponent", [-2, -1, .5, 1.5])
def test_undefined_or_unsupported_zero_power_derivatives_still_fail(exponent):
    with pytest.raises(ValueError):
        value_gradient_hessian(lambda x: x[0] ** exponent, (0.,))

