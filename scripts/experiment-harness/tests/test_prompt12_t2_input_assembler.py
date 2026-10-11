#!/usr/bin/env python3
"""Actual four-materializer offline chain, not mocked command execution."""
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest

HARNESS = Path(__file__).resolve().parents[1]
REPO = HARNESS.parents[1]
ASSEMBLER = HARNESS / "prompt12-t2-input-assembler.py"
FIXTURE_SCRIPT = Path(__file__).with_name("test_prompt12_bounded_production_binding_builder.py")
EXP = "EXP-20261012-DL-18000K-R01"
RUN = "RUN-20261012T120000Z-001"


def import_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FIXTURE = import_file("prompt12_fixture", FIXTURE_SCRIPT)
MODULE = import_file("prompt12_assembler", ASSEMBLER)


class T2InputAssemblerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="prompt12-t2-input-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        baseline, _ = FIXTURE.create_profile(self.root / "baseline")
        self.frozen = {
            "python_executable": baseline["python_executable"],
            "tool_paths": baseline["tool_paths"],
            "traffic_duration_s": 180,
            "trigger_token": "TRIGGER",
            "stable_ms": 40,
            "snapshot_timeout_ms": 1000,
            "timeline_readiness_poll_ms": 100,
            "timeline_readiness_timeout_ms": 5000,
        }
        self.frozen_file = self.root / "frozen.json"
        self.frozen_file.write_text(json.dumps(self.frozen), encoding="utf-8")
        self.admission = {
            "schema": "sci_oran_r6_f_portable_runtime_admission_v1",
            "host": socket.getfqdn(),
            "python_executable": sys.executable,
            "python_version": sys.version.split()[0],
            "jsonschema_required": True,
            "jsonschema_version": "synthetic-test-capability",
            "draft202012_capability": True,
            "qualification_gate": "PASS",
        }
        self.admission_file = self.root / "admission.json"
        self.admission_file.write_text(json.dumps(self.admission), encoding="utf-8")
        self.evidence = self.root / "evidence"
        self.evidence.mkdir()
        self.fifo = self.root / "synthetic-actuator.fifo"
        os.mkfifo(self.fifo)
        self.head = subprocess.check_output(
            ["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True
        ).strip()

    def args(self, *extra):
        return [
            sys.executable, "-B", str(ASSEMBLER),
            "--mode", "offline-validate",
            "--repo", str(REPO),
            "--approved-head", self.head,
            "--evidence-root", str(self.evidence),
            "--experiment-id", EXP,
            "--run-id", RUN,
            "--frozen-config", str(self.frozen_file),
            "--portable-admission", str(self.admission_file),
            *extra,
        ]

    def invoke(self, *extra):
        return subprocess.run(self.args(*extra), capture_output=True, text=True)

    def test_actual_four_materializers_complete_in_disposable_sandbox(self):
        proc = self.invoke()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        value = json.loads(proc.stdout)
        self.assertEqual(value["assembly_gate"], "PASS")
        self.assertEqual(value["scientific_t2"], "NOT_EXECUTED")
        self.assertTrue(value["run_directory_is_disposable"])
        self.assertFalse(value["control_executed"])
        self.assertFalse(value["traffic_executed"])
        self.assertFalse(any(self.evidence.iterdir()))
        self.assertFalse(Path(value["binding_manifest"]).exists())

    def test_offline_rejects_live_bindings_without_touching_evidence(self):
        proc = self.invoke("--fifo-path", str(self.fifo))
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("OFFLINE_MODE_FORBIDS_LIVE_BINDINGS", proc.stderr)
        self.assertFalse(any(self.evidence.iterdir()))

    def test_invalid_identity_fails_before_allocation(self):
        cmd = self.args()
        pos = cmd.index("--run-id")
        cmd[pos + 1] = "RUN-20261011T120000Z-001"
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("RUN_DATE_MISMATCH", proc.stderr)
        self.assertFalse(any(self.evidence.iterdir()))

    def test_mismatched_git_head_fails_before_allocation(self):
        cmd = self.args()
        pos = cmd.index("--approved-head")
        cmd[pos + 1] = "0" * 40
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("GIT_HEAD_MISMATCH", proc.stderr)
        self.assertFalse(any(self.evidence.iterdir()))

    def test_missing_portable_admission_fails_before_allocation(self):
        cmd = self.args()
        pos = cmd.index("--portable-admission")
        cmd[pos + 1] = str(self.root / "nonexistent.json")
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("PORTABLE_ADMISSION_NOT_FILE", proc.stderr)
        self.assertFalse(any(self.evidence.iterdir()))

    def test_unqualified_portable_admission_fails_closed(self):
        self.admission["qualification_gate"] = "FAIL"
        self.admission_file.write_text(json.dumps(self.admission), encoding="utf-8")
        proc = self.invoke()
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("RUNTIME_PROFILE_REJECTED", proc.stderr)
        self.assertFalse(any(self.evidence.iterdir()))

    def test_assembly_consumes_run_and_prevents_replay(self):
        first = MODULE.prepare_inputs(
            self.evidence, EXP, RUN, self.frozen_file,
            self.admission_file, self.fifo, HARNESS, offline=False,
        )
        self.assertEqual(first["assembly_gate"], "PASS")
        path = self.evidence / EXP / RUN / "runtime" / "t2-input-assembly.json"
        self.assertEqual(json.loads(path.read_text())["schema"], MODULE.SCHEMA)
        self.assertFalse(Path(first["single_transition_output"]).exists())
        with self.assertRaisesRegex(MODULE.AssemblyError, "RUN_ID_ALREADY_CONSUMED"):
            MODULE.prepare_inputs(self.evidence, EXP, RUN, self.frozen_file,
                                  self.admission_file, self.fifo, HARNESS, offline=False)

    def test_post_allocation_failure_retains_consumed_run_evidence(self):
        self.frozen["traffic_duration_s"] = 120
        self.frozen_file.write_text(json.dumps(self.frozen), encoding="utf-8")
        with self.assertRaises(MODULE.AssemblyError):
            MODULE.prepare_inputs(self.evidence, EXP, RUN, self.frozen_file,
                                  self.admission_file, self.fifo, HARNESS, offline=False)
        run_dir = self.evidence / EXP / RUN
        self.assertTrue(run_dir.is_dir())
        failure_path = run_dir / "runtime" / "t2-input-assembly.failure.json"
        self.assertTrue(failure_path.exists())
        record = json.loads(failure_path.read_text())
        self.assertFalse(record["run_replay_allowed"])
        self.assertFalse(record["control_executed"])

    def test_prepare_mode_rejected_outside_runtime_host(self):
        if socket.gethostname().split(".")[0] == "tb3-dell":
            self.skipTest("requires non-runtime qualification host")
        cmd = self.args()
        cmd[cmd.index("--mode") + 1] = "prepare"
        cmd += ["--fifo-path", str(self.fifo),
                "--preparation-token", MODULE.AUTH_TOKEN]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("HOST_NOT_TB3_DELL", proc.stderr)
        self.assertFalse(any(self.evidence.iterdir()))

    def test_scientific_action_paths_are_absent_from_source(self):
        source = ASSEMBLER.read_text(encoding="utf-8")
        self.assertNotIn("docker", source.lower().split("def main")[1])
        self.assertNotIn("ansible-playbook", source)
        self.assertNotIn("sci-oran-user-plane-smoke.sh", source)
        self.assertNotIn("sci-oran-doctor.sh", source)


if __name__ == "__main__":
    unittest.main()
