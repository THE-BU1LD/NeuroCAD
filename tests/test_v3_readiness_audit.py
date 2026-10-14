"""Readiness must resist forged checkboxes, evidence drift and stale source."""
from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("readiness", Path(__file__).parents[1] / "scripts/audit_v3_readiness.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "core").mkdir()
        (self.root / "core/model.py").write_text("# version 1\n", encoding="utf-8")
        self.evidence = self.root / "result.json"
        self.evidence.write_text(json.dumps({"status": "PASS", "passed": 5}), encoding="utf-8")
        self.manifest = {
            "schema_version": 1,
            "verified_source": {"commit": "a" * 40, "production_globs": ["core/*.py"],
                                "files": {"core/model.py": MODULE.sha256(self.root / "core/model.py")}},
            "items": [{"id": "calculation", "title": "Calculation", "state": "DONE", "acceptance": "Five cases pass",
                       "evidence": [{"path": "result.json", "sha256": MODULE.sha256(self.evidence),
                                     "assertions": [{"pointer": "/status", "equals": "PASS"},
                                                    {"pointer": "/passed", "equals": 5}]}]}],
        }

    def run_audit(self):
        return MODULE.audit(self.root, self.manifest)

    def test_valid_completion(self):
        self.assertTrue(self.run_audit()["complete"])

    def test_blocked_is_not_completion(self):
        self.manifest["items"].append({"id": "physical", "title": "Measure", "state": "BLOCKED",
                                       "acceptance": "Measured errors within declared limits", "reason": "No measurements",
                                       "next_action": "Collect calibrated measurements"})
        result = self.run_audit()
        self.assertEqual(result["audit_status"], "PASS")
        self.assertFalse(result["complete"])

    def test_hash_tampering(self):
        self.evidence.write_text('{"status":"PASS","passed":99}', encoding="utf-8")
        self.assertEqual(self.run_audit()["audit_status"], "FAIL")

    def test_changed_claim_even_with_rehashed_evidence(self):
        self.evidence.write_text('{"status":"FAIL","passed":5}', encoding="utf-8")
        self.manifest["items"][0]["evidence"][0]["sha256"] = MODULE.sha256(self.evidence)
        self.assertFalse(self.run_audit()["complete"])

    def test_source_drift(self):
        (self.root / "core/model.py").write_text("# changed\n", encoding="utf-8")
        result = self.run_audit()
        self.assertEqual(result["audit_status"], "PASS")
        self.assertFalse(result["current_source_matches_verified_inventory"])
        self.assertFalse(result["complete"])

    def test_added_production_file(self):
        (self.root / "core/new.py").write_text("# unverified\n", encoding="utf-8")
        self.assertFalse(self.run_audit()["complete"])

    def test_done_without_evidence(self):
        self.manifest["items"][0]["evidence"] = []
        self.assertEqual(self.run_audit()["audit_status"], "FAIL")

    def test_duplicate_identity(self):
        self.manifest["items"].append(copy.deepcopy(self.manifest["items"][0]))
        self.assertEqual(self.run_audit()["audit_status"], "FAIL")

    def test_boolean_not_numeric_receipt(self):
        self.manifest["items"][0]["evidence"][0]["assertions"][1] = {"pointer": "/passed", "equals": True}
        self.assertFalse(self.run_audit()["complete"])

    def test_path_escape(self):
        self.manifest["items"][0]["evidence"][0]["path"] = "../result.json"
        self.assertEqual(self.run_audit()["audit_status"], "FAIL")

    def test_symlink_escape(self):
        try:
            (self.root / "outside.json").symlink_to(self.root.parent / "outside.json")
        except OSError as exc:
            self.skipTest(f"Host cannot create symlink fixture: {exc}")
        self.manifest["items"][0]["evidence"][0]["path"] = "outside.json"
        self.assertEqual(self.run_audit()["audit_status"], "FAIL")

    def test_open_without_next_action(self):
        self.manifest["items"][0]["state"] = "TODO"
        self.assertEqual(self.run_audit()["audit_status"], "FAIL")

    def test_cli_blocks_false_completion_and_preserves_output(self):
        self.manifest["items"][0].update(state="BLOCKED", reason="Missing external measurement", next_action="Measure")
        (self.root / "input.json").write_text(json.dumps(self.manifest), encoding="utf-8")
        command = [sys.executable, str(Path(MODULE.__file__)), "--root", str(self.root), "--manifest", "input.json",
                   "--require-complete", "--output", str(self.root / "receipt.json")]
        result = subprocess.run(command, text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 3)
        original = (self.root / "receipt.json").read_bytes()
        result = subprocess.run(command, text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 1)
        self.assertEqual((self.root / "receipt.json").read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
