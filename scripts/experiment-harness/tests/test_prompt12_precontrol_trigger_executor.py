#!/usr/bin/env python3

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


EXECUTOR = (
    Path(__file__).resolve().parents[1]
    / "prompt12-precontrol-trigger-executor.py"
)

LATEST_SAMPLE_NS = 1_787_855_272_184_943_590
DECISION_NS = LATEST_SAMPLE_NS + 500_000_000


def precontrol_fixture():
    return {
        "selection": "latest_50_complete_contiguous_samples",
        "selected_complete_count": 50,
        "stationarity_window_binding_gate": "PASS",
        "output_stationarity_gate": "PASS",
        "freshness_gate": "PASS",
        "precontrol_admission_gate": "PASS",
        "latest_sample_timestamp_utc_ns": LATEST_SAMPLE_NS,
        "decision_utc_ns": DECISION_NS,
        "maximum_allowed_age_ms": "800",
    }


def run_executor(mode, executor_start_ns):
    with tempfile.TemporaryDirectory(
        prefix="prompt12-executor-test-"
    ) as tmp:
        root = Path(tmp)
        source = root / "precontrol.json"
        output = root / "result.json"

        source.write_text(
            json.dumps(precontrol_fixture()) + "\n",
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                sys.executable,
                str(EXECUTOR),
                "--precontrol-json",
                str(source),
                "--mode",
                mode,
                "--max-age-ms",
                "800",
                "--executor-start-utc-ns",
                str(executor_start_ns),
                "--output",
                str(output),
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        result = None
        if output.is_file():
            result = json.loads(
                output.read_text(encoding="utf-8")
            )

        return proc, result


class ExecutorOfflineClockRegressionTest(unittest.TestCase):

    def test_no_control_injected_clock_passes(self):
        proc, result = run_executor(
            "no-control",
            DECISION_NS,
        )

        self.assertEqual(proc.returncode, 0)
        self.assertIsNotNone(result)

        self.assertEqual(
            result["EXECUTOR_GATE"],
            "PASS",
        )
        self.assertEqual(
            result["NO_CONTROL_DRY_RUN_GATE"],
            "PASS",
        )
        self.assertEqual(
            result["EXECUTOR_START_UTC_NS"],
            DECISION_NS,
        )
        self.assertEqual(
            result["EXECUTOR_START_TIME_SOURCE"],
            "EXPLICIT_NO_CONTROL_ARGUMENT",
        )
        self.assertEqual(
            result[
                "EXECUTOR_START_AFTER_SOURCE_DECISION_GATE"
            ],
            "PASS",
        )
        self.assertEqual(
            result["EXECUTOR_START_SAMPLE_AGE_GATE"],
            "PASS",
        )
        self.assertEqual(
            result["EXECUTOR_START_SAMPLE_AGE_MS"],
            "500",
        )
        self.assertEqual(
            result["CONTROL_EXECUTED"],
            "NO",
        )
        self.assertEqual(
            result["TRIGGER_WRITE_ATTEMPT_COUNT"],
            0,
        )
        self.assertEqual(
            result["TRIGGER_WRITE_SUCCESS_COUNT"],
            0,
        )
        self.assertEqual(
            result["SCIENTIFIC_TRIGGER_CONSUMED"],
            "NO",
        )

    def test_fifo_rejects_injected_clock(self):
        proc, result = run_executor(
            "fifo",
            DECISION_NS,
        )

        self.assertEqual(proc.returncode, 33)
        self.assertIsNotNone(result)

        self.assertEqual(
            result["EXECUTOR_GATE"],
            "FAIL_CLOSED",
        )
        self.assertEqual(
            result["FAIL_CLOSED_REASON"],
            "EXECUTOR_START_OVERRIDE_FORBIDDEN_IN_FIFO_MODE",
        )
        self.assertEqual(
            result["CONTROL_EXECUTED"],
            "NO",
        )
        self.assertEqual(
            result["TRIGGER_WRITE_ATTEMPT_COUNT"],
            0,
        )
        self.assertEqual(
            result["TRIGGER_WRITE_SUCCESS_COUNT"],
            0,
        )
        self.assertEqual(
            result["SCIENTIFIC_TRIGGER_CONSUMED"],
            "NO",
        )

    def test_predecision_injected_clock_fails_closed(self):
        proc, result = run_executor(
            "no-control",
            DECISION_NS - 1,
        )

        self.assertEqual(proc.returncode, 35)
        self.assertIsNotNone(result)

        self.assertEqual(
            result["EXECUTOR_GATE"],
            "FAIL_CLOSED",
        )
        self.assertEqual(
            result["FAIL_CLOSED_REASON"],
            "EXECUTOR_START_PRECEDES_SOURCE_DECISION",
        )
        self.assertEqual(
            result[
                "EXECUTOR_START_AFTER_SOURCE_DECISION_GATE"
            ],
            "FAIL",
        )
        self.assertEqual(
            result["CONTROL_EXECUTED"],
            "NO",
        )
        self.assertEqual(
            result["TRIGGER_WRITE_ATTEMPT_COUNT"],
            0,
        )
        self.assertEqual(
            result["TRIGGER_WRITE_SUCCESS_COUNT"],
            0,
        )
        self.assertEqual(
            result["SCIENTIFIC_TRIGGER_CONSUMED"],
            "NO",
        )


if __name__ == "__main__":
    unittest.main()
