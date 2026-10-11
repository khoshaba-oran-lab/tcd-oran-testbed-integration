#!/usr/bin/env python3
"""Synthetic smoke and Doctor processes; no real traffic or network access."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

HARNESS = Path(__file__).resolve().parents[1]
SOURCE = HARNESS / "prompt12-t2-readiness-sequence.py"
spec = importlib.util.spec_from_file_location("prompt12_readiness", SOURCE)
MODULE = importlib.util.module_from_spec(spec)
spec.loader.exec_module(MODULE)

DOCTOR_PASS = "\n".join([
    "USER_PLANE_READINESS_GATE=PASS",
    "HOST_RESOURCE_READINESS_GATE=PASS",
    "READINESS_FRESHNESS_GATE=PASS",
    "FINAL_ARTIFACT_SCI_ORAN_READY_GATE=PASS",
    "SCI_ORAN_READY_GATE=PASS",
    "FAILURE_REASON=NONE",
    "DOCTOR_EXIT_CODE=0",
])


class ReadinessSequenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="prompt12-readiness-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.ops = self.root / "ops"
        self.ops.mkdir()
        self.latest = self.root / "latest.env"
        self.trace = self.root / "calls.log"
        self.smoke = self.root / "smoke.py"
        self.doctor = self.root / "doctor.py"
        self.write_smoke()
        self.write_doctor()

    def write_smoke(self, rc=0, create_evidence=True, gate="PASS"):
        self.smoke.write_text(
            "import pathlib,sys\n"
            + f"with pathlib.Path({str(self.trace)!r}).open('a') as f: f.write('smoke\\n')\n"
            + (f"pathlib.Path({str(self.latest)!r}).write_text('SMOKE_ID=TEST\\n')\n" if create_evidence else "")
            + f"print('SMOKE_ID=UPSMK-FAKE-001')\n"
            + f"print('USER_PLANE_FUNCTIONAL_SMOKE_GATE={gate}')\n"
            + f"print('LATEST_EVIDENCE={self.latest}')\n"
            + f"sys.exit({rc})\n",
            encoding="utf-8",
        )

    def write_doctor(self, rc=0, output=DOCTOR_PASS):
        self.doctor.write_text(
            "import pathlib,sys\n"
            + f"with pathlib.Path({str(self.trace)!r}).open('a') as f: f.write('doctor\\n')\n"
            + f"print({output!r})\n"
            + f"sys.exit({rc})\n",
            encoding="utf-8",
        )

    def execute(self, operation_id="UP-TEST-001"):
        return MODULE.run_sequence(
            [sys.executable, str(self.smoke)],
            [sys.executable, str(self.doctor)],
            self.ops, operation_id, self.latest,
        )

    def test_real_processes_execute_smoke_then_doctor_once(self):
        result = self.execute()
        self.assertEqual(self.trace.read_text().splitlines(), ["smoke", "doctor"])
        self.assertEqual(result["readiness_handoff_gate"], "PASS")
        self.assertEqual(result["scientific_t2"], "NOT_EXECUTED")
        self.assertFalse(result["control_executed"])
        self.assertTrue((self.ops / "UP-TEST-001" / "smoke.stdout").is_file())
        self.assertTrue((self.ops / "UP-TEST-001" / "doctor.stdout").is_file())
        self.assertTrue((self.ops / "UP-TEST-001" / "outcome.json").is_file())
        self.assertFalse((self.ops / "UP-TEST-001" / "failure.json").exists())

    def test_failed_smoke_never_runs_doctor(self):
        self.write_smoke(rc=5)
        with self.assertRaisesRegex(MODULE.ReadinessError, "smoke_RC_5"):
            self.execute()
        self.assertEqual(self.trace.read_text().splitlines(), ["smoke"])
        failure = json.loads((self.ops / "UP-TEST-001" / "failure.json").read_text())
        self.assertEqual(failure["stage"], "SMOKE")
        self.assertFalse(failure["automatic_retry"])

    def test_nonpassing_smoke_marker_blocks_doctor(self):
        self.write_smoke(gate="FAIL")
        with self.assertRaisesRegex(MODULE.ReadinessError, "SMOKE_FUNCTIONAL_GATE_NOT_PASS"):
            self.execute()
        self.assertEqual(self.trace.read_text().splitlines(), ["smoke"])

    def test_stale_smoke_evidence_is_not_reused(self):
        self.write_smoke(create_evidence=False)
        self.latest.write_text("old\n")
        old = time.time() - 3000
        os.utime(self.latest, times=(old, old))
        with self.assertRaisesRegex(MODULE.ReadinessError, "SMOKE_EVIDENCE_NOT_NEW"):
            self.execute()
        self.assertEqual(self.trace.read_text().splitlines(), ["smoke"])

    def test_doctor_failed_gate_blocks_success(self):
        self.write_doctor(output=DOCTOR_PASS.replace("SCI_ORAN_READY_GATE=PASS", "SCI_ORAN_READY_GATE=FAIL"))
        with self.assertRaisesRegex(MODULE.ReadinessError, "DOCTOR_GATE_NOT_PASS"):
            self.execute()
        self.assertEqual(self.trace.read_text().splitlines(), ["smoke", "doctor"])
        self.assertFalse((self.ops / "UP-TEST-001" / "outcome.json").exists())
        self.assertTrue((self.ops / "UP-TEST-001" / "failure.json").exists())

    def test_doctor_nonzero_exit_blocks_success(self):
        self.write_doctor(rc=20)
        with self.assertRaisesRegex(MODULE.ReadinessError, "doctor_RC_20"):
            self.execute()
        self.assertTrue((self.ops / "UP-TEST-001" / "doctor.stdout").exists())

    def test_operation_replay_blocked_after_success(self):
        self.execute()
        with self.assertRaisesRegex(MODULE.ReadinessError, "OPERATION_ID_ALREADY_CONSUMED"):
            self.execute()
        self.assertEqual(self.trace.read_text().splitlines(), ["smoke", "doctor"])

    def test_operation_replay_blocked_after_failure(self):
        self.write_smoke(rc=1)
        with self.assertRaises(MODULE.ReadinessError):
            self.execute()
        with self.assertRaisesRegex(MODULE.ReadinessError, "OPERATION_ID_ALREADY_CONSUMED"):
            self.execute()
        self.assertEqual(self.trace.read_text().splitlines(), ["smoke"])

    def test_operation_id_rejects_path_escape(self):
        with self.assertRaisesRegex(MODULE.ReadinessError, "OPERATION_ID_INVALID"):
            self.execute("../../escape")
        self.assertFalse(self.trace.exists())

    def test_only_expected_production_script_paths_are_in_main(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn('"sci-oran-user-plane-smoke.sh"', source)
        self.assertIn('"sci-oran-doctor.sh"', source)
        self.assertNotIn("ansible-playbook", source)
        self.assertNotIn("--control-authorization-token", source)


if __name__ == "__main__":
    unittest.main()
