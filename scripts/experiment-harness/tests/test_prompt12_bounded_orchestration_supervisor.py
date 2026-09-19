#!/usr/bin/env python3
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "prompt12-bounded-orchestration-supervisor.py"
)

spec = importlib.util.spec_from_file_location("supervisor", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def valid_plan(marker):
    command = [sys.executable, "-c", f"open({str(marker)!r}, 'w').write('x')"]
    return {
        "schema": module.SCHEMA,
        "traffic_command": command,
        "initial_stationarity_command": command,
        "finalization_command": command,
        "transitions": [
            {
                "label": f"T{index}",
                "trigger_command": command,
                "post_stationarity_command": command,
            }
            for index in range(1, 7)
        ],
    }


class SupervisorTests(unittest.TestCase):
    def test_contract_arithmetic(self):
        self.assertEqual(module.PRE_MAX_S, module.PRE_MIN_S + 2 * module.EXTENSION_S)
        self.assertEqual(module.POST_MAX_S, module.POST_MIN_S + 2 * module.EXTENSION_S)
        self.assertEqual(module.OBSERVATION_MAX_S, module.PRE_MAX_S + 6 * module.POST_MAX_S)
        self.assertEqual(module.EXPERIMENT_MAX_S, 180)

    def test_no_control_executes_nothing(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            marker = root / "executed"
            plan = root / "plan.json"
            output = root / "output.json"
            plan.write_text(json.dumps(valid_plan(marker)), encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(SCRIPT), "--plan", str(plan), "--mode", "no-control", "--output", str(output)],
                text=True,
                capture_output=True,
                check=False,
            )
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(proc.returncode, 0)
            self.assertFalse(marker.exists())
            self.assertEqual(report["NO_CONTROL_DRY_RUN_GATE"], "PASS")
            self.assertEqual(report["CONTROL_EXECUTED"], "NO")
            self.assertEqual(report["TRIGGER_WRITE_ATTEMPT_COUNT"], 0)

    def test_live_without_enable_fails_closed(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            marker = root / "executed"
            plan = root / "plan.json"
            output = root / "output.json"
            plan.write_text(json.dumps(valid_plan(marker)), encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(SCRIPT), "--plan", str(plan), "--mode", "live", "--output", str(output)],
                text=True,
                capture_output=True,
                check=False,
            )
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(proc.returncode, 77)
            self.assertFalse(marker.exists())
            self.assertEqual(report["SUPERVISOR_GATE"], "FAIL_CLOSED")
            self.assertEqual(report["FAIL_CLOSED_REASON"], "LIVE_CONTROL_NOT_ENABLED")

    def test_live_without_token_fails_closed(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            marker = root / "executed"
            plan = root / "plan.json"
            output = root / "output.json"
            plan.write_text(json.dumps(valid_plan(marker)), encoding="utf-8")
            environment = os.environ.copy()
            environment["SCI_ORAN_PROMPT12_LIVE_CONTROL_ENABLE"] = "YES"
            proc = subprocess.run(
                [sys.executable, str(SCRIPT), "--plan", str(plan), "--mode", "live", "--output", str(output)],
                text=True,
                capture_output=True,
                check=False,
                env=environment,
            )
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(proc.returncode, 77)
            self.assertFalse(marker.exists())
            self.assertEqual(
                report["FAIL_CLOSED_REASON"],
                "LIVE_CONTROL_AUTHORIZATION_TOKEN_INVALID",
            )

    def test_extension_limit_fails_closed(self):
        module.DurationBudget.validate_extension_count(2)
        with self.assertRaises(module.SupervisorError) as caught:
            module.DurationBudget.validate_extension_count(3)
        self.assertEqual(caught.exception.reason, "MAX_STATIONARITY_EXTENSIONS_EXCEEDED")

    def test_global_timeout_fails_closed(self):
        budget = module.DurationBudget(0, clock=lambda: 181)
        with self.assertRaises(module.SupervisorError) as caught:
            budget.require_remaining("EXPERIMENT_TIMEOUT")
        self.assertEqual(caught.exception.reason, "EXPERIMENT_TIMEOUT")

    def test_observation_target_cannot_exceed_phase_limit(self):
        budget = module.DurationBudget(0, clock=lambda: 0)
        with self.assertRaises(module.SupervisorError) as caught:
            module.wait_for_observation(22, budget, 0, "pre")
        self.assertEqual(caught.exception.reason, "PRE_STEP_TIMEOUT")

    def test_live_sequence_attempts_each_trigger_once(self):
        plan = valid_plan(Path("unused"))
        report = module.base_report("live")

        class Traffic:
            pid = 123

            @staticmethod
            def poll():
                return None

        calls = []

        def fake_run(argv, budget, reason, **kwargs):
            calls.append((argv, reason))
            return subprocess.CompletedProcess(argv, 0, "ok\n", "")

        environment = {
            "SCI_ORAN_PROMPT12_LIVE_CONTROL_ENABLE": "YES",
        }

        with mock.patch.dict(os.environ, environment, clear=True), \
             mock.patch.object(module.subprocess, "Popen", return_value=Traffic()), \
             mock.patch.object(module, "stationarity_gate", return_value=0), \
             mock.patch.object(module, "run_command", side_effect=fake_run), \
             mock.patch.object(module, "terminate_process"):
            rc = module.run_live(plan, report, module.LIVE_TOKEN)

        self.assertEqual(rc, 0)
        self.assertEqual(report["SUPERVISOR_GATE"], "PASS")
        self.assertEqual(report["TRIGGER_WRITE_ATTEMPT_COUNT"], 6)
        self.assertEqual(report["TRIGGER_WRITE_SUCCESS_COUNT"], 6)
        trigger_calls = [reason for _, reason in calls if "_TRIGGER_FAILED" in reason]
        self.assertEqual(len(trigger_calls), 6)
        self.assertEqual(calls[-1][1], "FINALIZATION_FAILED")

    def test_trigger_failure_prohibits_later_trigger(self):
        plan = valid_plan(Path("unused"))
        report = module.base_report("live")

        class Traffic:
            pid = 123

            @staticmethod
            def poll():
                return None

        traffic = Traffic()
        trigger_number = 0
        reasons = []

        def fake_run(argv, budget, reason, **kwargs):
            nonlocal trigger_number
            reasons.append(reason)
            if "_TRIGGER_FAILED" in reason:
                trigger_number += 1
                if trigger_number == 3:
                    raise module.SupervisorError("T3_TRIGGER_FAILED:RC_1", 1)
            return subprocess.CompletedProcess(argv, 0, "ok\n", "")

        environment = {
            "SCI_ORAN_PROMPT12_LIVE_CONTROL_ENABLE": "YES",
        }

        with mock.patch.dict(os.environ, environment, clear=True), \
             mock.patch.object(module.subprocess, "Popen", return_value=traffic), \
             mock.patch.object(module, "stationarity_gate", return_value=0), \
             mock.patch.object(module, "run_command", side_effect=fake_run), \
             mock.patch.object(module, "terminate_process") as terminate:
            with self.assertRaises(module.SupervisorError):
                module.run_live(plan, report, module.LIVE_TOKEN)

        terminate.assert_called_once_with(traffic)
        self.assertNotIn("FINALIZATION_FAILED", reasons)
        self.assertEqual(trigger_number, 3)
        self.assertEqual(report["TRIGGER_WRITE_ATTEMPT_COUNT"], 3)
        self.assertEqual(report["TRIGGER_WRITE_SUCCESS_COUNT"], 2)
        self.assertEqual(
            report["SCIENTIFIC_TRIGGER_REPLAY_DECISION"],
            "NEVER_AUTOMATICALLY_REPLAY",
        )


if __name__ == "__main__":
    unittest.main()
