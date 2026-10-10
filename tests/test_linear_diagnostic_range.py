from __future__ import annotations

import json
from decimal import Decimal, localcontext

import numpy as np
import pytest

from core.scientific_kernel import linear_system_diagnostics


@pytest.mark.parametrize("coefficient,estimate,target,residual,relative", [
    (2**32, 2**32, 0, float(2**64), 1.0),
    (1e200, 1.0, 0.0, 1e200, 1.0),
    (1e-200, 1.0, 0.0, 1e-200, 1.0),
    (1e308, 1.0, 5e307, 5e307, 1 / 3),
])
def test_scalar_diagnostics_match_hand_computable_residuals(coefficient, estimate, target, residual, relative):
    report = linear_system_diagnostics(((coefficient,),), (target,), (estimate,))
    assert report["residual_norm"] == pytest.approx(residual, rel=1e-14, abs=0)
    assert report["relative_backward_error"] == pytest.approx(relative, rel=1e-14, abs=0)
    assert report["condition_number"] == 1.0
    assert report["rank"] == 1
    json.dumps(report, allow_nan=False)


@pytest.mark.parametrize("scale", [1e-250, 1e-100, 1.0, 1e100, 1e250])
def test_backward_error_is_scale_invariant_against_decimal_oracle(scale):
    # A=[[3,1],[1,2]], x=[2,3], b=[8,8] gives residual [1,0].
    with localcontext() as context:
        context.prec = 80
        expected = float(Decimal(1) / (Decimal(195).sqrt() + Decimal(128).sqrt()))
    report = linear_system_diagnostics(
        ((3 * scale, scale), (scale, 2 * scale)),
        (8 * scale, 8 * scale), (2.0, 3.0),
    )
    assert report["residual_norm"] == pytest.approx(scale, rel=1e-13, abs=0)
    assert report["relative_backward_error"] == pytest.approx(expected, rel=1e-13, abs=0)
    assert report["rank"] == 2


@pytest.mark.parametrize("slot", ["matrix", "rhs", "solution"])
def test_integer_values_must_survive_float64_conversion_exactly(slot):
    args = {"matrix": ((1,),), "rhs": (1,), "solution": (1,)}
    args[slot] = ((2**53 + 1,),) if slot == "matrix" else (2**53 + 1,)
    with pytest.raises(ValueError, match="float64"):
        linear_system_diagnostics(**args)


def test_unrepresentable_residual_is_rejected_instead_of_nonfinite_report():
    with pytest.raises(ValueError, match="finite|representable"):
        linear_system_diagnostics(((1e308,),), (-1e308,), (2.0,))


def test_zero_system_and_singular_system_keep_documented_diagnostics():
    zero = linear_system_diagnostics(((0.0,),), (0.0,), (0.0,))
    assert zero["residual_norm"] == zero["relative_backward_error"] == 0
    assert zero["condition_number"] is None and zero["rank"] == 0
    singular = linear_system_diagnostics(((1.0, 2.0), (2.0, 4.0)), (3.0, 6.0), (1.0, 1.0))
    assert singular["rank"] == 1 and singular["ill_conditioned"]


def test_uint64_representable_values_do_not_wrap():
    report = linear_system_diagnostics(np.array([[2**63]], dtype=np.uint64), (0,), (2,))
    assert report["residual_norm"] == float(2**64)
    assert report["relative_backward_error"] == 1.0


@pytest.mark.parametrize("coefficient,estimate", [(1e-200, 1e-200), (np.nextafter(0.0, 1.0), 0.25)])
def test_nonzero_product_underflow_cannot_report_a_perfect_solve(coefficient, estimate):
    with pytest.raises(ValueError, match="underflow|representable"):
        linear_system_diagnostics(((coefficient,),), (0.0,), (estimate,))


def test_exact_zero_products_remain_valid_at_tiny_scales():
    report = linear_system_diagnostics(((1e-200, 0.0),), (0.0,), (0.0, 1e-200))
    assert report["residual_norm"] == report["relative_backward_error"] == 0.0
