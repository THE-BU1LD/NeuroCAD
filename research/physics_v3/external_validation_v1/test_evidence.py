"""Synthetic integrity tests, not external scientific evidence."""

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("external_evidence", Path(__file__).with_name("evidence.py"))
audit_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit_module)


class EvidenceIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        raw = self.root / "synthetic.txt"
        raw.write_text("SYNTHETIC UNIT TEST ONLY\n", encoding="utf-8")
        self.artifact = {"path": raw.name, "sha256": audit_module.digest(raw)}
        self.plan = {
            "study_id": "synthetic-test",
            "kind": "physical",
            "capability": "test",
            "applicability_envelope": "test only",
            "exclusions": "all real claims",
            "release_sha256": "a" * 64,
            "source_commit": "b" * 40,
            "operator_id": "test-operator",
            "reference_provenance": "synthetic",
            "stop_rule": "one case",
            "outcomes_observed": False,
            "frozen_artifacts": [self.artifact],
            "cases": [
                {
                    "id": "case1",
                    "procedure": "synthetic integrity check",
                    "required_artifacts": sorted(audit_module.REQUIRED_ROLES["physical"]),
                    "units": "mm",
                    "apparatus": "synthetic",
                    "calibration_plan": "synthetic",
                    "uncertainty_budget": "synthetic",
                    "input_measurement_plan": "synthetic",
                    "atol": 0.1,
                    "rtol": 0,
                    "max_expanded_uncertainty": 0.05,
                    "coverage_factor": 2,
                }
            ],
        }
        self.plan_path = self.root / "plan.json"
        self.freeze_path = self.root / "freeze.json"
        self.evidence_path = self.root / "evidence.json"

    def prepare(self):
        self.plan_path.write_text(json.dumps(self.plan), encoding="utf-8")
        audit_module.freeze(self.plan_path, self.freeze_path)
        self.record = {
            "study_id": self.plan["study_id"],
            "freeze_sha256": audit_module.digest(self.freeze_path),
            "operator_id": "test-operator",
            "synthetic": False,
            "started_at": "2099-01-01T00:00:00+00:00",
            "cases": [
                {
                    "id": "case1",
                    "status": "PASS",
                    "predicted": 1.01,
                    "measured": 1,
                    "expanded_uncertainty": 0.02,
                    "coverage_factor": 2,
                    "units": "mm",
                    "artifacts": {r: self.artifact for r in self.plan["cases"][0]["required_artifacts"]},
                }
            ],
        }

    def result(self):
        self.evidence_path.write_text(json.dumps(self.record), encoding="utf-8")
        return audit_module.audit(self.freeze_path, self.evidence_path)

    def test_complete_numbers_do_not_advance_scientific_gate(self):
        self.prepare()
        result = self.result()
        self.assertTrue(result["all_case_criteria_pass"])
        self.assertEqual(result["status"], "EVIDENCE_COMPLETE_REVIEW_REQUIRED")
        self.assertFalse(result["scientific_gate_advanced"])

    def test_numerical_failure_is_retained(self):
        self.prepare()
        self.record["cases"][0]["predicted"] = 2
        result = self.result()
        self.assertEqual(result["status"], "EVIDENCE_COMPLETE_REVIEW_REQUIRED")
        self.assertEqual(result["comparisons"][0]["status"], "FAIL")
        self.assertFalse(result["all_case_criteria_pass"])

    def test_uncertainty_cannot_be_inflated_to_pass(self):
        self.prepare()
        self.record["cases"][0]["expanded_uncertainty"] = 100
        self.assertFalse(self.result()["all_case_criteria_pass"])

    def test_missing_duplicate_cases_and_synthetic_evidence_rejected(self):
        self.prepare()
        original = copy.deepcopy(self.record)
        for mutation in ("missing", "duplicate", "synthetic", "early"):
            with self.subTest(mutation=mutation):
                self.record = copy.deepcopy(original)
                if mutation == "missing":
                    self.record["cases"] = []
                if mutation == "duplicate":
                    self.record["cases"] *= 2
                if mutation == "synthetic":
                    self.record["synthetic"] = True
                if mutation == "early":
                    self.record["started_at"] = "2000-01-01T00:00:00+00:00"
                self.assertEqual(self.result()["status"], "INCOMPLETE_OR_INVALID")

    def test_hash_tampering_and_path_escape_rejected(self):
        self.prepare()
        self.record["cases"][0]["artifacts"]["calibration"] = {"path": "../outside", "sha256": "a" * 64}
        self.assertEqual(self.result()["status"], "INCOMPLETE_OR_INVALID")
        (self.root / "synthetic.txt").write_text("changed", encoding="utf-8")
        self.assertEqual(self.result()["status"], "INCOMPLETE_OR_INVALID")

    def test_embedded_plan_cannot_change(self):
        self.prepare()
        frozen = audit_module.read(self.freeze_path)
        frozen["plan"]["cases"][0]["atol"] = 100
        self.freeze_path.write_text(json.dumps(frozen), encoding="utf-8")
        self.record["freeze_sha256"] = audit_module.digest(self.freeze_path)
        self.assertIn("embedded plan changed after freeze", self.result()["errors"])

    def test_draft_and_outcome_aware_plans_refused(self):
        for path in Path(__file__).with_name("templates").glob("*_plan.json"):
            self.assertTrue(audit_module.validate_plan(audit_module.read(path)))
        self.plan["outcomes_observed"] = True
        self.assertTrue(audit_module.validate_plan(self.plan))

    def test_output_collision_refused(self):
        self.prepare()
        with self.assertRaises(FileExistsError):
            audit_module.freeze(self.plan_path, self.freeze_path)

    def test_nonfinite_or_boolean_numbers_refused(self):
        self.prepare()
        for value in (float("nan"), float("inf"), True):
            self.record["cases"][0]["predicted"] = value
            self.assertEqual(self.result()["status"], "INCOMPLETE_OR_INVALID")

    def test_independence_required(self):
        self.plan["kind"] = "reproduction"
        self.plan["cases"][0]["required_artifacts"] = sorted(audit_module.REQUIRED_ROLES["reproduction"])
        self.plan["implementer_ids"] = ["test-operator"]
        self.assertTrue(audit_module.validate_plan(self.plan))
        self.plan["implementer_ids"] = ["implementer"]
        self.prepare()
        self.assertEqual(self.result()["status"], "INCOMPLETE_OR_INVALID")
        for key in ("clean_install", "outside_source_tree", "no_implementation_contribution", "all_frozen_cases_attempted"):
            self.record["cases"][0][key] = True
        self.assertEqual(self.result()["status"], "EVIDENCE_COMPLETE_REVIEW_REQUIRED")

    def test_usability_cannot_omit_participants_or_rubric(self):
        self.plan.update(
            kind="usability",
            implementer_ids=["implementer"],
            minimum_participants=5,
            recruitment_criteria="synthetic",
            consent_and_privacy="synthetic",
        )
        self.plan["cases"][0]["required_artifacts"] = sorted(audit_module.REQUIRED_ROLES["usability"])
        self.prepare()
        self.assertEqual(self.result()["status"], "INCOMPLETE_OR_INVALID")
        people = [
            {
                "id": f"u{i}",
                "consented": True,
                "eligible": True,
                "completed_without_help": True,
                "correct_loads_and_materials": True,
                "understands_limits": True,
                "distinguishes_screening": True,
            }
            for i in range(5)
        ]
        self.record["cases"][0]["participants"] = people
        self.assertTrue(self.result()["all_case_criteria_pass"])
        people[0]["understands_limits"] = False
        self.assertFalse(self.result()["all_case_criteria_pass"])


if __name__ == "__main__":
    unittest.main()
