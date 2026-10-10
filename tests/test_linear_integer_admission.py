"""Lossy conversion cannot certify an integer system as exactly solved."""

from __future__ import annotations

import numpy as np
import pytest

from core.scientific_kernel import linear_system_diagnostics


@pytest.mark.parametrize("field", ["matrix", "rhs", "solution"])
@pytest.mark.parametrize("value", [2**53 + 1, -(2**53 + 1), np.uint64(2**63 + 1)])
def test_unrepresentable_integer_cannot_be_rounded_into_an_exact_solution(field, value):
    rounded = float(value)
    arguments = {"matrix": ((1,),), "rhs": (rounded,), "solution": (rounded,)}
    if field == "matrix":
        arguments.update(matrix=((value,),), solution=(1,))
    else:
        arguments[field] = (value,)
    # Each supplied equation has true residual magnitude one. Casting the
    # distinct integer and rounded float to the same float64 gives false zero.
    with pytest.raises(ValueError, match="lossless|exactly representable"):
        linear_system_diagnostics(**arguments)


@pytest.mark.parametrize("field", ["matrix", "rhs", "solution"])
def test_original_mixed_float_integer_values_are_checked_before_numpy_coercion(field):
    value = 2**53 + 1
    rounded = float(value)
    if field == "matrix":
        arguments = {"matrix": ((0.0, value),), "rhs": (rounded,), "solution": (0.0, 1.0)}
    else:
        arguments = {
            "matrix": ((1.0, 0.0), (0.0, 1.0)),
            "rhs": (0.0, rounded), "solution": (0.0, rounded),
        }
        arguments[field] = (0.0, value)
    with pytest.raises(ValueError, match="lossless|exactly representable"):
        linear_system_diagnostics(**arguments)


@pytest.mark.parametrize("value", [2**53, 2**63, -(2**63), np.uint64(2**64 - 2048)])
def test_exactly_representable_large_integers_remain_supported(value):
    result = linear_system_diagnostics(((1,),), (0,), (value,))
    assert result["residual_norm"] == abs(float(value))
    assert result["relative_backward_error"] == 1.0
    assert result["rank"] == 1
