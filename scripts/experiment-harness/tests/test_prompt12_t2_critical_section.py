#!/usr/bin/env python3
"""Entirely offline regression tests: no Docker, FIFO or scientific traffic."""

import importlib.util
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "prompt12-t2-critical-section.py"
SPEC = importlib.util.spec_from_file_location("t2_critical", SCRIPT)
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


def build_plan(run):
    source = run / "precontrol" / "T2.json"
    ratio = run / "runtime" / "ratio-bindings" / "T2.binding.json"
    output = run / "control" / "T2.executor.json"
    return {
        "schema": RUNNER.SCHEMA,
        "transition_label": "T2", "transition_index": 2,
        "executed_transition_ordinal": 1,
        "expected_actuator_transaction_count": 1,
        "expected_timeline_event_count": 3,
        "synthetic_prior_transition_events": False,
        "skipped_transition_bindings_consumed": False,
        "t3_handoff_present": False, "t3_trigger_present": False,
        "command_executed": False, "control_executed": False,
        "traffic_executed": False,
        "initial_precontrol_command": [
            sys.executable, str(SCRIPT.with_name("prompt12-bounded-precontrol-handoff.py")),
            "--attempt-root", str(run / "evidence" / "precontrol-handoff" / "T2"),
            "--precontrol-output", str(source),
            "--stationarity-command", "stationarity-stub",
            "--freshness-command", "freshness-stub",
        ],
        "ratio_bind_command": [
            sys.executable, str(SCRIPT.with_name("prompt12-pretrigger-ratio-binding-writer.py")),
            "--transition-label", "T2", "--transition-index", "2",
            "--requested-ratio-pct", "75", "--output", str(ratio),
        ],
        "trigger_command": [
            sys.executable, str(SCRIPT.with_name("prompt12-precontrol-trigger-executor.py")),
            "--precontrol-json", str(source), "--mode", "fifo",
            "--max-age-ms", "800", "--output", str(output),
            "--fifo-path", str(run / "actuator.fifo"),
            "--trigger-token", "TRIGGER", "--control-authorization-token",
            RUNNER.CONTROL_PLACEHOLDER,
        ],
    }


def stationarity(gate="PASS"):
    return json.dumps({
        "output_stationarity_gate": gate,
        "minimum_phase_duration_gate": gate,
        "statistical_phase_candidate": gate,
    }) + "\n"


class CriticalSectionOfflineQualification(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="prompt12-critical-mock-")
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.run = self.root / "T2-SYNTHETIC" / "EXP-SYNTHETIC" / "RUN-SYNTHETIC-OFFLINE"
        (self.run / "control").mkdir(parents=True)
        self.plan = build_plan(self.run)
        self.path = self.root / "materialization.json"
        self.path.write_text(json.dumps(self.plan), encoding="utf-8")
        self.report, self.commands, self.output = RUNNER.load_plan(self.path)

    def invoke(self, side_effect):
        with mock.patch.object(RUNNER, "run_child", side_effect=side_effect):
            return RUNNER.run_live(
                self.report, self.commands, self.output,
                "sci-oran-phasec-mock-operation-0001", RUNNER.CONTROL_TOKEN,
            )

    def test_inspection_mode_cannot_execute_or_write(self):
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--materialization", str(self.path),
             "--mode", "inspect"], capture_output=True, text=True, check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("PROMPT12_T2_CRITICAL_INSPECTION=PASS", proc.stdout)
        self.assertIn("CONTROL_EXECUTED=NO", proc.stdout)
        self.assertEqual(list((self.run / "control").iterdir()), [])

    def test_malformed_and_nonfrozen_plan_fails_inspection(self):
        self.plan["transition_index"] = 3
        self.path.write_text(json.dumps(self.plan), encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--materialization", str(self.path)],
            capture_output=True, text=True, check=False,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("T2_FROZEN_INVARIANT_FAILED", proc.stderr)

    def test_policy_800_and_trigger_source_must_be_frozen(self):
        self.plan["trigger_command"][self.plan["trigger_command"].index("--max-age-ms") + 1] = "801"
        self.path.write_text(json.dumps(self.plan), encoding="utf-8")
        with self.assertRaises(RUNNER.CriticalError):
            RUNNER.load_plan(self.path)
        self.plan["trigger_command"][self.plan["trigger_command"].index("--max-age-ms") + 1] = "800"
        self.plan["trigger_command"][self.plan["trigger_command"].index("--precontrol-json") + 1] = "/other/T2.json"
        self.path.write_text(json.dumps(self.plan), encoding="utf-8")
        with self.assertRaises(RUNNER.CriticalError):
            RUNNER.load_plan(self.path)

    def test_fake_tool_with_correct_basename_is_rejected(self):
        impostor = self.root / "prompt12-precontrol-trigger-executor.py"
        impostor.write_text("# synthetic impostor; never executed\n", encoding="utf-8")
        self.plan["trigger_command"][1] = str(impostor)
        self.path.write_text(json.dumps(self.plan), encoding="utf-8")
        with self.assertRaises(RUNNER.CriticalError) as caught:
            RUNNER.load_plan(self.path)
        self.assertIn("COMMAND_SOURCE_IDENTITY_MISMATCH", str(caught.exception))

    def test_live_requires_explicit_environment_and_two_tokens(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            proc = subprocess.run(
                [sys.executable, str(SCRIPT), "--materialization", str(self.path),
                 "--mode", "live", "--operation-id", "sci-oran-phasec-mock-operation-0001",
                 "--live-authorization-token", RUNNER.LIVE_TOKEN,
                 "--control-authorization-token", RUNNER.CONTROL_TOKEN],
                capture_output=True, text=True, check=False,
            )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("T2_LIVE_AUTHORIZATION_INVALID", proc.stderr)
        self.assertEqual(list((self.run / "control").iterdir()), [])

    def test_pass_orders_precontrol_ratio_trigger_and_locks_replay(self):
        steps = []

        def stub(argv, label):
            steps.append(label)
            if label == "PRECONTROL":
                return subprocess.CompletedProcess(argv, 0, stationarity(), "")
            if label == "RATIO_BIND":
                return subprocess.CompletedProcess(argv, 0, "RATIO_BOUND=PASS\n", "")
            self.assertEqual(label, "TRIGGER")
            self.assertEqual(argv[-1], RUNNER.CONTROL_TOKEN)
            self.assertNotIn(RUNNER.CONTROL_PLACEHOLDER, argv)
            self.output.write_text(json.dumps({
                "EXECUTOR_GATE": "PASS", "CONTROL_EXECUTED": "YES",
                "SCIENTIFIC_TRIGGER_CONSUMED": "YES",
                "TRIGGER_WRITE_ATTEMPT_COUNT": 1,
                "TRIGGER_WRITE_SUCCESS_COUNT": 1,
                "EXECUTOR_START_SAMPLE_AGE_GATE": "PASS",
            }), encoding="utf-8")
            return subprocess.CompletedProcess(argv, 0, "EXECUTOR_GATE=PASS\n", "")

        result = self.invoke(stub)
        self.assertEqual(steps, ["PRECONTROL", "RATIO_BIND", "TRIGGER"])
        self.assertEqual(result["output_stationarity_gate"], "PASS")
        self.assertRegex(result["readback_window_start_utc"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{6}Z$")
        intent = self.run / "control" / "T2.trigger-intent.json"
        outcome = self.run / "control" / "T2.critical-outcome.json"
        self.assertTrue(intent.is_file())
        self.assertTrue((self.root / "T2-SYNTHETIC" / ".t2-operation-claims" / "sci-oran-phasec-mock-operation-0001.json").is_file())
        self.assertEqual(json.loads(outcome.read_text())["state"], "TRIGGER_CONFIRMED_AWAITING_READBACK")
        with self.assertRaises(RUNNER.CriticalError) as caught:
            self.invoke(stub)
        self.assertIn("ALREADY_CONSUMED", str(caught.exception))
        self.assertEqual(steps, ["PRECONTROL", "RATIO_BIND", "TRIGGER"])

    def test_operation_id_cannot_be_reused_in_another_run(self):
        def pre_fail(argv, label):
            return subprocess.CompletedProcess(argv, 0, stationarity("FAIL"), "")
        with self.assertRaises(RUNNER.CriticalError):
            self.invoke(pre_fail)
        second_run = self.root / "T2-SYNTHETIC" / "EXP-SECOND" / "RUN-SECOND"
        (second_run / "control").mkdir(parents=True)
        other = self.root / "other.json"
        other.write_text(json.dumps(build_plan(second_run)), encoding="utf-8")
        plan, commands, output = RUNNER.load_plan(other)
        with mock.patch.object(RUNNER, "run_child") as child:
            with self.assertRaises(RUNNER.CriticalError) as caught:
                RUNNER.run_live(plan, commands, output, "sci-oran-phasec-mock-operation-0001", RUNNER.CONTROL_TOKEN)
            self.assertIn("OPERATION_ID_ALREADY_CONSUMED", str(caught.exception))
            child.assert_not_called()

    def test_stationarity_failure_never_attempts_binding_or_trigger(self):
        steps = []
        def stub(argv, label):
            steps.append(label)
            return subprocess.CompletedProcess(argv, 0, stationarity("FAIL"), "")
        with self.assertRaises(RUNNER.CriticalError):
            self.invoke(stub)
        self.assertEqual(steps, ["PRECONTROL"])
        state = json.loads((self.run / "control" / "T2.critical-outcome.json").read_text())
        self.assertEqual(state["trigger_dispatch_attempted"], False)
        self.assertTrue((self.run / "control" / "T2.trigger-intent.json").exists())

    def test_ratio_failure_never_calls_executor(self):
        steps = []
        def stub(argv, label):
            steps.append(label)
            if label == "PRECONTROL":
                return subprocess.CompletedProcess(argv, 0, stationarity(), "")
            raise RUNNER.CriticalError("RATIO_BIND_FAILED:RC_2")
        with self.assertRaises(RUNNER.CriticalError):
            self.invoke(stub)
        self.assertEqual(steps, ["PRECONTROL", "RATIO_BIND"])
        self.assertTrue((self.run / "control" / "T2.trigger-intent.json").exists())

    def test_unknown_after_dispatch_is_persisted_and_not_retried(self):
        steps = []
        def stub(argv, label):
            steps.append(label)
            if label == "PRECONTROL":
                return subprocess.CompletedProcess(argv, 0, stationarity(), "")
            if label == "RATIO_BIND":
                return subprocess.CompletedProcess(argv, 0, "RATIO_BOUND=PASS\n", "")
            raise RUNNER.CriticalError("TRIGGER_EXECUTION_UNKNOWN:TimeoutExpired")
        with self.assertRaises(RUNNER.CriticalError):
            self.invoke(stub)
        self.assertEqual(steps, ["PRECONTROL", "RATIO_BIND", "TRIGGER"])
        outcome = json.loads((self.run / "control" / "T2.critical-outcome.json").read_text())
        self.assertTrue(outcome["trigger_dispatch_attempted"])
        self.assertFalse(outcome["trigger_execution_confirmed"])
        self.assertEqual(outcome["scientific_trigger_replay_decision"], "NEVER_AUTOMATICALLY_REPLAY")
        with self.assertRaises(RUNNER.CriticalError):
            self.invoke(stub)
        self.assertEqual(steps.count("TRIGGER"), 1)


if __name__ == "__main__":
    unittest.main()
