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
                "ratio_bind_command": command,
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
            return subprocess.CompletedProcess(
                argv,
                0,
                (
                    "RATIO_BOUND=PASS\n"
                    if "_RATIO_BIND_FAILED" in reason
                    else "ok\n"
                ),
                "",
            )

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

    def test_success_stops_traffic_before_finalization(self):
        plan = valid_plan(Path("unused"))
        report = module.base_report("live")
        events = []

        class Traffic:
            pid = 123

            @staticmethod
            def poll():
                return None

        traffic = Traffic()

        def fake_run(argv, budget, reason, **kwargs):
            if reason == "FINALIZATION_FAILED":
                events.append("finalization")
            return subprocess.CompletedProcess(
                argv,
                0,
                (
                    "RATIO_BOUND=PASS\n"
                    if "_RATIO_BIND_FAILED" in reason
                    else "ok\n"
                ),
                "",
            )

        def fake_terminate(process):
            events.append(("terminate", process))

        environment = {
            "SCI_ORAN_PROMPT12_LIVE_CONTROL_ENABLE": "YES",
        }

        with mock.patch.dict(os.environ, environment, clear=True):
            with mock.patch.object(
                module.subprocess,
                "Popen",
                return_value=traffic,
            ):
                with mock.patch.object(
                    module,
                    "stationarity_gate",
                    return_value=0,
                ):
                    with mock.patch.object(
                        module,
                        "run_command",
                        side_effect=fake_run,
                    ):
                        with mock.patch.object(
                            module,
                            "terminate_process",
                            side_effect=fake_terminate,
                        ):
                            rc = module.run_live(
                                plan,
                                report,
                                module.LIVE_TOKEN,
                            )

        self.assertEqual(rc, 0)
        self.assertEqual(
            events,
            [
                ("terminate", traffic),
                "finalization",
                ("terminate", None),
            ],
        )

    def test_ratio_bind_precedes_each_trigger(self):
        plan = valid_plan(Path("unused"))
        report = module.base_report("live")

        class Traffic:
            pid = 123

            @staticmethod
            def poll():
                return None

        reasons = []

        def fake_run(argv, budget, reason, **kwargs):
            reasons.append(reason)

            stdout = (
                "RATIO_BOUND=PASS\n"
                if "_RATIO_BIND_FAILED" in reason
                else "ok\n"
            )

            return subprocess.CompletedProcess(
                argv,
                0,
                stdout,
                "",
            )

        environment = {
            "SCI_ORAN_PROMPT12_LIVE_CONTROL_ENABLE": "YES",
        }

        with mock.patch.dict(os.environ, environment, clear=True), \
             mock.patch.object(module.subprocess, "Popen", return_value=Traffic()), \
             mock.patch.object(module, "stationarity_gate", return_value=0), \
             mock.patch.object(module, "run_command", side_effect=fake_run), \
             mock.patch.object(module, "terminate_process"):
            rc = module.run_live(
                plan,
                report,
                module.LIVE_TOKEN,
            )

        self.assertEqual(rc, 0)

        transition_reasons = [
            reason
            for reason in reasons
            if "_RATIO_BIND_FAILED" in reason
            or "_TRIGGER_FAILED" in reason
        ]

        self.assertEqual(
            transition_reasons,
            [
                item
                for index in range(1, 7)
                for item in (
                    f"T{index}_RATIO_BIND_FAILED",
                    f"T{index}_TRIGGER_FAILED",
                )
            ],
        )

        self.assertEqual(
            report["TRIGGER_WRITE_ATTEMPT_COUNT"],
            6,
        )
        self.assertEqual(
            report["TRIGGER_WRITE_SUCCESS_COUNT"],
            6,
        )

    def test_ratio_bind_failure_prohibits_trigger(self):
        plan = valid_plan(Path("unused"))
        report = module.base_report("live")

        class Traffic:
            pid = 123

            @staticmethod
            def poll():
                return None

        reasons = []

        def fake_run(argv, budget, reason, **kwargs):
            reasons.append(reason)

            if reason == "T3_RATIO_BIND_FAILED":
                raise module.SupervisorError(
                    "T3_RATIO_BIND_FAILED:RC_1",
                    1,
                )

            stdout = (
                "RATIO_BOUND=PASS\n"
                if "_RATIO_BIND_FAILED" in reason
                else "ok\n"
            )

            return subprocess.CompletedProcess(
                argv,
                0,
                stdout,
                "",
            )

        environment = {
            "SCI_ORAN_PROMPT12_LIVE_CONTROL_ENABLE": "YES",
        }

        with mock.patch.dict(os.environ, environment, clear=True), \
             mock.patch.object(module.subprocess, "Popen", return_value=Traffic()), \
             mock.patch.object(module, "stationarity_gate", return_value=0), \
             mock.patch.object(module, "run_command", side_effect=fake_run), \
             mock.patch.object(module, "terminate_process"):
            with self.assertRaises(module.SupervisorError):
                module.run_live(
                    plan,
                    report,
                    module.LIVE_TOKEN,
                )

        self.assertIn(
            "T3_RATIO_BIND_FAILED",
            reasons,
        )
        self.assertNotIn(
            "T3_TRIGGER_FAILED",
            reasons,
        )
        self.assertNotIn(
            "T4_RATIO_BIND_FAILED",
            reasons,
        )
        self.assertEqual(
            report["TRIGGER_WRITE_ATTEMPT_COUNT"],
            2,
        )
        self.assertEqual(
            report["TRIGGER_WRITE_SUCCESS_COUNT"],
            2,
        )

    def test_missing_ratio_bound_pass_marker_prohibits_trigger(self):
        plan = valid_plan(Path("unused"))
        report = module.base_report("live")

        class Traffic:
            pid = 123

            @staticmethod
            def poll():
                return None

        reasons = []

        def fake_run(argv, budget, reason, **kwargs):
            reasons.append(reason)

            if reason == "T2_RATIO_BIND_FAILED":
                stdout = "RATIO_BINDING_WRITTEN=YES\n"
            elif "_RATIO_BIND_FAILED" in reason:
                stdout = "RATIO_BOUND=PASS\n"
            else:
                stdout = "ok\n"

            return subprocess.CompletedProcess(
                argv,
                0,
                stdout,
                "",
            )

        environment = {
            "SCI_ORAN_PROMPT12_LIVE_CONTROL_ENABLE": "YES",
        }

        with mock.patch.dict(os.environ, environment, clear=True), \
             mock.patch.object(module.subprocess, "Popen", return_value=Traffic()), \
             mock.patch.object(module, "stationarity_gate", return_value=0), \
             mock.patch.object(module, "run_command", side_effect=fake_run), \
             mock.patch.object(module, "terminate_process"):
            with self.assertRaisesRegex(
                module.SupervisorError,
                "T2_RATIO_BIND_PASS_MARKER_MISSING",
            ):
                module.run_live(
                    plan,
                    report,
                    module.LIVE_TOKEN,
                )

        self.assertNotIn(
            "T2_TRIGGER_FAILED",
            reasons,
        )
        self.assertNotIn(
            "T3_RATIO_BIND_FAILED",
            reasons,
        )
        self.assertEqual(
            report["TRIGGER_WRITE_ATTEMPT_COUNT"],
            1,
        )
        self.assertEqual(
            report["TRIGGER_WRITE_SUCCESS_COUNT"],
            1,
        )

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
            return subprocess.CompletedProcess(
                argv,
                0,
                (
                    "RATIO_BOUND=PASS\n"
                    if "_RATIO_BIND_FAILED" in reason
                    else "ok\n"
                ),
                "",
            )

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
