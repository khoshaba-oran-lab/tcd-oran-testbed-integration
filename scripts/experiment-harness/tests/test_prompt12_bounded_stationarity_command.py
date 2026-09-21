#!/usr/bin/env python3

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "prompt12-bounded-stationarity-command.py"
)


FAKE_TOOL_TEMPLATE = r"""
import json
import os
import pathlib
import sys

ROLE = __ROLE__


def value(flag):
    return sys.argv[sys.argv.index(flag) + 1]


output = pathlib.Path(value("--output"))
output.parent.mkdir(parents=True, exist_ok=True)

if ROLE == "evaluator":
    mode = os.environ.get("FAKE_EVALUATOR_MODE", "pass")
    if mode == "invalid":
        output.write_text("not-json\n", encoding="utf-8")
    else:
        output.write_text(
            json.dumps({
                "output_stationarity_gate": "PASS",
                "minimum_phase_duration_gate": "PASS",
                "statistical_phase_candidate": "PASS",
            }) + "\n",
            encoding="utf-8",
        )
    print("OUTPUT_STATIONARITY_GATE=PASS")
    print("fake evaluator diagnostic", file=sys.stderr)
    sys.exit(int(os.environ.get("FAKE_EVALUATOR_RC", "0")))

output.write_text("{}\n", encoding="utf-8")
print(ROLE.upper() + "_GATE=PASS")
"""


def create_tool(path, role):
    path.write_text(
        textwrap.dedent(FAKE_TOOL_TEMPLATE).replace("__ROLE__", repr(role)),
        encoding="utf-8",
    )


def create_layout(root):
    raw = root / "source.raw"
    timestamps = root / "source.timestamps.jsonl"
    schema = root / "schema.json"
    parser = root / "parser.py"
    canonicalizer = root / "canonicalizer.py"
    evaluator = root / "evaluator.py"

    raw.write_text("receiver evidence\n", encoding="utf-8")
    timestamps.write_text('{"sequence":0}\n', encoding="utf-8")
    schema.write_text("{}\n", encoding="utf-8")
    create_tool(parser, "parser")
    create_tool(canonicalizer, "canonicalizer")
    create_tool(evaluator, "evaluator")

    return {
        "raw": raw,
        "timestamps": timestamps,
        "schema": schema,
        "parser": parser,
        "canonicalizer": canonicalizer,
        "evaluator": evaluator,
        "evidence": root / "evidence",
    }


def command(layout, mode="initial-pre-step"):
    return [
        sys.executable,
        str(SCRIPT),
        "--python-executable",
        sys.executable,
        "--parser",
        str(layout["parser"]),
        "--canonicalizer",
        str(layout["canonicalizer"]),
        "--evaluator",
        str(layout["evaluator"]),
        "--raw-input",
        str(layout["raw"]),
        "--timestamp-input",
        str(layout["timestamps"]),
        "--schema",
        str(layout["schema"]),
        "--experiment-id",
        "EXP-20260920-DL-18000K-R01",
        "--run-id",
        "RUN-20260920T050000Z-001",
        "--mode",
        mode,
        "--evidence-root",
        str(layout["evidence"]),
        "--stable-ms",
        "0",
        "--snapshot-timeout-ms",
        "200",
    ]


def run(argv, environment=None):
    return subprocess.run(
        argv,
        text=True,
        capture_output=True,
        check=False,
        env=environment,
    )


def attempt_directories(layout):
    if not layout["evidence"].exists():
        return []
    return sorted(
        path
        for path in layout["evidence"].iterdir()
        if path.is_dir()
    )


class BoundedStationarityCommandTests(unittest.TestCase):
    def test_initial_mode_emits_only_report_json(self):
        with tempfile.TemporaryDirectory() as raw:
            layout = create_layout(Path(raw))
            proc = run(command(layout))

            self.assertEqual(proc.returncode, 0, proc.stderr)
            report = json.loads(proc.stdout)
            self.assertEqual(report["output_stationarity_gate"], "PASS")
            attempts = attempt_directories(layout)
            self.assertEqual(len(attempts), 1)
            evaluator_log = (
                attempts[0] / "logs" / "evaluator.stdout.log"
            ).read_text(encoding="utf-8")
            self.assertIn("OUTPUT_STATIONARITY_GATE=PASS", evaluator_log)
            self.assertNotIn("OUTPUT_STATIONARITY_GATE=", proc.stdout)

    def test_post_mode_binds_timeline_and_control_index(self):
        with tempfile.TemporaryDirectory() as raw:
            layout = create_layout(Path(raw))
            timeline = Path(raw) / "actuator.jsonl"
            timeline.write_text('{"event":"applied_readback"}\n', encoding="utf-8")
            argv = command(layout, "post-step") + [
                "--actuator-timeline",
                str(timeline),
                "--control-index",
                "3",
            ]

            proc = run(argv)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            attempt = attempt_directories(layout)[0]
            commands = json.loads(
                (attempt / "commands.json").read_text(encoding="utf-8")
            )
            self.assertIn("actuator-transitions", commands["canonicalizer"])
            self.assertIn("--control-index", commands["evaluator"])
            self.assertIn("3", commands["evaluator"])

    def test_each_invocation_uses_unique_attempt_directory(self):
        with tempfile.TemporaryDirectory() as raw:
            layout = create_layout(Path(raw))
            first = run(command(layout))
            second = run(command(layout))

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(len(attempt_directories(layout)), 2)

    def test_post_mode_rejects_missing_post_arguments(self):
        with tempfile.TemporaryDirectory() as raw:
            layout = create_layout(Path(raw))
            proc = run(command(layout, "post-step"))

            self.assertEqual(proc.returncode, 64)
            self.assertEqual(proc.stdout, "")
            self.assertIn("POST_MODE_ARGUMENT_MISSING", proc.stderr)
            self.assertEqual(attempt_directories(layout), [])

    def test_evaluator_failure_is_not_forwarded_to_stdout(self):
        with tempfile.TemporaryDirectory() as raw:
            layout = create_layout(Path(raw))
            environment = os.environ.copy()
            environment["FAKE_EVALUATOR_RC"] = "9"
            proc = run(command(layout), environment)

            self.assertEqual(proc.returncode, 70)
            self.assertEqual(proc.stdout, "")
            self.assertIn("EVALUATOR_FAILED_RC_9", proc.stderr)

    def test_invalid_evaluator_report_is_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            layout = create_layout(Path(raw))
            environment = os.environ.copy()
            environment["FAKE_EVALUATOR_MODE"] = "invalid"
            proc = run(command(layout), environment)

            self.assertEqual(proc.returncode, 65)
            self.assertEqual(proc.stdout, "")
            self.assertIn("EVALUATOR_REPORT_INVALID", proc.stderr)

    def test_implementation_uses_argv_without_shell(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("subprocess.run(", source)
        self.assertNotIn("shell=True", source)
        self.assertNotIn("bash -lc", source)



class StationarityLiveSnapshotExtensionTests(
    unittest.TestCase
):
    def test_exports_absolute_canonical_snapshot(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            layout = create_layout(root)

            proc = subprocess.run(
                command(layout),
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(
                proc.returncode,
                0,
                proc.stderr,
            )

            report = json.loads(proc.stdout)
            canonical = Path(
                report[
                    "canonical_interval_snapshot_path"
                ]
            )

            self.assertTrue(canonical.is_absolute())
            self.assertTrue(canonical.is_file())
            self.assertEqual(
                canonical.name,
                "intervals.canonical.jsonl",
            )
            self.assertEqual(
                canonical.parent.name,
                "processed",
            )
            self.assertTrue(
                canonical.parent.parent.name.startswith(
                    "attempt-"
                )
            )

    def test_post_step_builds_bounded_incremental_timeline(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            layout = create_layout(root)
            timeline_tool = root / "timeline-tool.py"

            timeline_tool.write_text(
                "\n".join([
                    "import json",
                    "import pathlib",
                    "import sys",
                    "output = pathlib.Path(sys.argv[sys.argv.index('--output') + 1])",
                    "output.parent.mkdir(parents=True, exist_ok=True)",
                    "output.write_text(",
                    "    ''.join(json.dumps({'event_index': i}) + '\\n' for i in range(1, 4)),",
                    "    encoding='utf-8',",
                    ")",
                ]) + "\n",
                encoding="utf-8",
            )

            token = "@PROMPT12_ACTUATOR_TIMELINE@"
            timeline_command = [
                sys.executable,
                str(timeline_tool),
                "--output",
                token,
            ]

            argv = command(
                layout,
                "post-step",
            ) + [
                "--control-index",
                "1",
                "--timeline-command-json",
                json.dumps(timeline_command),
                "--expected-timeline-event-count",
                "3",
                "--timeline-readiness-timeout-ms",
                "500",
                "--timeline-readiness-poll-ms",
                "10",
            ]

            proc = subprocess.run(
                argv,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(
                proc.returncode,
                0,
                proc.stderr,
            )

            report = json.loads(proc.stdout)
            canonical = Path(
                report[
                    "canonical_interval_snapshot_path"
                ]
            )
            attempt = canonical.parent.parent
            timeline_snapshot = (
                attempt
                / "raw"
                / "actuator-timeline.jsonl"
            )

            self.assertTrue(
                timeline_snapshot.is_file()
            )
            self.assertEqual(
                len(
                    [
                        line
                        for line in timeline_snapshot.read_text(
                            encoding="utf-8"
                        ).splitlines()
                        if line
                    ]
                ),
                3,
            )


if __name__ == "__main__":
    unittest.main()
