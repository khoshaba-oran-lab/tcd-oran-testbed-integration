#!/usr/bin/env python3

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest


REPO = pathlib.Path(__file__).resolve().parents[3]
CONFIG = (
    REPO
    / "experiments"
    / "manifests"
    / "prompt12-bounded-sequence-production-frozen-config-v1.json"
)
MATERIALIZER = (
    REPO
    / "scripts"
    / "experiment-harness"
    / "prompt12-bounded-runtime-profile-materializer.py"
)
PYTHON = pathlib.Path(
    "/home/khoshaba/sci-oran/venvs/"
    "prompt12-py39-jsonschema-4.25.1/bin/python"
)

EXPECTED_ROOT_KEYS = {
    "python_executable",
    "tool_paths",
    "traffic_duration_s",
    "trigger_token",
    "stable_ms",
    "snapshot_timeout_ms",
    "timeline_readiness_timeout_ms",
    "timeline_readiness_poll_ms",
}

EXPECTED_TOOL_RELATIVE = {
    "traffic_adapter":
        "scripts/experiment-harness/adapters/"
        "prompt12-bounded-traffic-session.sh",
    "stationarity_adapter":
        "scripts/experiment-harness/"
        "prompt12-bounded-stationarity-command.py",
    "precontrol_handoff":
        "scripts/experiment-harness/"
        "prompt12-bounded-precontrol-handoff.py",
    "finalization_adapter":
        "scripts/experiment-harness/"
        "prompt12-bounded-finalization-command.py",
    "parser":
        "scripts/experiment-harness/"
        "parse-iperf-receiver.py",
    "canonicalizer":
        "scripts/experiment-harness/"
        "canonicalize-iperf-receiver-t2.py",
    "stationarity_evaluator":
        "scripts/experiment-harness/"
        "evaluate-output-stationarity.py",
    "freshness_evaluator":
        "scripts/experiment-harness/"
        "prompt12-precontrol-freshness.py",
    "trigger_executor":
        "scripts/experiment-harness/"
        "prompt12-precontrol-trigger-executor.py",
    "timeline_builder":
        "scripts/experiment-harness/"
        "build-actuator-timeline.py",
    "receiver_pipeline":
        "scripts/experiment-harness/"
        "prompt12-receiver-pipeline.sh",
    "schema":
        "datasets/schemas/"
        "sci-oran-prompt12-siso-v1.0.0.schema.json",
    "freshness_policy":
        "scripts/experiment-harness/contracts/"
        "prompt12-precontrol-freshness-v1.env",
}


class ProductionFrozenConfigTests(unittest.TestCase):
    def load_config(self):
        return json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_exact_root_keys(self):
        self.assertEqual(
            set(self.load_config()),
            EXPECTED_ROOT_KEYS,
        )

    def test_frozen_values(self):
        value = self.load_config()
        self.assertEqual(value["python_executable"], str(PYTHON))
        self.assertEqual(value["traffic_duration_s"], 180)
        self.assertEqual(value["trigger_token"], "TRIGGER")
        self.assertEqual(value["stable_ms"], 40)
        self.assertEqual(value["snapshot_timeout_ms"], 1000)
        self.assertEqual(
            value["timeline_readiness_timeout_ms"],
            5000,
        )
        self.assertEqual(
            value["timeline_readiness_poll_ms"],
            100,
        )

    def test_exact_tool_bindings(self):
        expected = {
            key: str((REPO / relative).resolve())
            for key, relative in EXPECTED_TOOL_RELATIVE.items()
        }
        self.assertEqual(
            self.load_config()["tool_paths"],
            expected,
        )

    def test_all_bound_paths_exist(self):
        value = self.load_config()
        self.assertTrue(PYTHON.is_file())
        self.assertTrue(os.access(PYTHON, os.X_OK))
        for path_text in value["tool_paths"].values():
            path = pathlib.Path(path_text)
            self.assertTrue(path.is_absolute())
            self.assertTrue(path.is_file(), path)

    def test_materializer_accepts_production_config(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            evidence = root / "evidence"
            evidence.mkdir()
            fifo = root / "actuator.fifo"
            os.mkfifo(fifo)

            proc = subprocess.run(
                [
                    sys.executable,
                    str(MATERIALIZER),
                    "--frozen-config",
                    str(CONFIG),
                    "--evidence-root",
                    str(evidence),
                    "--experiment-id",
                    "EXP-20990101-DL-18000K-R01",
                    "--run-id",
                    "RUN-20990101T000000Z-001",
                    "--actuator-fifo-path",
                    str(fifo),
                    "--max-age-ms",
                    "500",
                    "--control-authorization-token",
                    "AUTHORISE_PROMPT12_FIFO_CONTROL",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                env={
                    **os.environ,
                    "PYTHONDONTWRITEBYTECODE": "1",
                },
            )

            self.assertEqual(
                proc.returncode,
                0,
                proc.stderr + proc.stdout,
            )
            report = json.loads(proc.stdout)
            self.assertEqual(
                report["materialization_gate"],
                "PASS",
            )
            self.assertIs(report["command_executed"], False)
            self.assertIs(report["control_executed"], False)


if __name__ == "__main__":
    unittest.main()
