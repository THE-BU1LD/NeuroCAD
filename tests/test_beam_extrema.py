"""Known-counterexample regression; no physical or independent-validation claim."""

import importlib.util
import sys
import unittest
from fractions import Fraction
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("beam_extrema_subject", Path(__file__).parents[1] / "core/physics_advanced.py")
SUBJECT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SUBJECT
SPEC.loader.exec_module(SUBJECT)


class BeamExtremaTests(unittest.TestCase):
    def response(self, force, load, **extra):
        return SUBJECT.cantilever_beam(SUBJECT.CantileverBeamInput(
            length_mm=120, elastic_modulus_mpa=70000, second_moment_mm4=6000,
            section_modulus_mm3=600, tip_force_n=force, uniform_load_n_per_mm=load, **extra,
        ))["results"]

    def test_retained_counterexample_and_yield_consequence(self):
        result = self.response(-42, 0.7, yield_strength_mpa=2, safety_factor=1)
        self.assertAlmostEqual(result["maximum_bending_stress_mpa"], 2.1)
        self.assertAlmostEqual(result["yield_utilization"], 1.05)
        self.assertFalse(result["constraint_satisfied"])
        self.assertAlmostEqual(result["fixed_end_moment_n_mm"], 0)
        self.assertAlmostEqual(result["tip_deflection_mm"], -0.0144)

    def test_exact_rational_extrema_and_sign_symmetry(self):
        # Independent quadratic vertex expression -F**2/(2*w), plus endpoints.
        for force in (-180, -120, -84, -42, -1, 0, 1, 42, 84, 120, 180):
            for load in (Fraction(-7, 10), Fraction(0), Fraction(7, 10)):
                with self.subTest(force=force, load=load):
                    candidates = [Fraction(0), force * 120 + load * 120**2 / 2]
                    if load and 0 < -Fraction(force) / load < 120:
                        candidates.append(-Fraction(force)**2 / (2 * load))
                    expected = float(max(map(abs, candidates)) / 600)
                    self.assertAlmostEqual(self.response(force, float(load))["maximum_bending_stress_mpa"], expected)

    def test_no_section_modulus_has_no_stress_claim(self):
        result = SUBJECT.cantilever_beam(SUBJECT.CantileverBeamInput(
            length_mm=120, elastic_modulus_mpa=70000, second_moment_mm4=6000,
            tip_force_n=-42, uniform_load_n_per_mm=0.7,
        ))["results"]
        self.assertIsNone(result["maximum_bending_stress_mpa"])
        self.assertIsNone(result["yield_utilization"])


if __name__ == "__main__":
    unittest.main()
