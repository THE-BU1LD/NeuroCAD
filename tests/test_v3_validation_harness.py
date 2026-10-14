"""Verifier fault injection; no production physics or tensor imports."""
from __future__ import annotations

import importlib.util
import math
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("v3_harness", Path(__file__).parents[1] / "scripts/validate_physics_v3.py")
HARNESS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HARNESS)


class ComparatorTests(unittest.TestCase):
    def test_nonfinite_boolean_and_shape_mismatch_fail(self):
        for value in (math.nan, math.inf, -math.inf, True, "1"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                HARNESS.compare(value, 1, {"atol": 1e-9, "rtol": 1e-9})
        with self.assertRaises(ValueError):
            HARNESS.compare([1], [1, 2], {"atol": 1e-9, "rtol": 1e-9})

    def test_incorrect_reference_cannot_pass(self):
        with self.assertRaises(ValueError):
            HARNESS.compare(0, 2.1, {"atol": 1e-9, "rtol": 1e-9})
        HARNESS.compare([0, 2.1], [0, 2.1], {"atol": 1e-9, "rtol": 1e-9})

    def test_absolute_and_relative_tolerances(self):
        HARNESS.compare(1e-10, 0, {"atol": 1e-9, "rtol": 1e-9})
        HARNESS.compare(1e9 + 0.5, 1e9, {"atol": 1e-9, "rtol": 1e-9})
        with self.assertRaises(ValueError):
            HARNESS.compare(1e9 + 2, 1e9, {"atol": 1e-9, "rtol": 1e-9})


if __name__ == "__main__":
    unittest.main()
