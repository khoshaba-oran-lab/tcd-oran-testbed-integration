#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


HERE = pathlib.Path(__file__).resolve().parent
HARNESS = HERE.parent

SCRIPT = (
    HARNESS
    / "prompt12-resume-precontrol-materializer.py"
)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def sample_manifest(root: pathlib.Path) -> pathlib.Path:
    run = root / "run"

    initial = [
        sys.executable,
        str(
            HARNESS
            / "prompt12-bounded-precontrol-handoff.py"
        ),
        "--attempt-root",
        str(
            run
            / "evidence"
            / "precontrol-handoff"
            / "T1"
        ),
        "--precontrol-output",
        str(
            run
            / "precontrol"
            / "T1.json"
        ),
        "--stationarity-command",
        sys.executable,
        str(
            HARNESS
            / "prompt12-bounded-stationarity-command.py"
        ),
        "--python-executable",
        sys.executable,
        "--raw-input",
        str(run / "raw" / "iperf.log"),
        "--timestamp-input",
        str(run / "raw" / "timestamps.jsonl"),
        "--schema",
        str(root / "schema.json"),
        "--experiment-id",
        "EXP-001",
        "--run-id",
        "RUN-001",
        "--mode",
        "initial-pre-step",
        "--evidence-root",
        str(
            run
            / "evidence"
            / "stationarity"
            / "initial"
        ),
        "--stable-ms",
        "40",
        "--snapshot-timeout-ms",
        "1000",
        "--freshness-command",
        sys.executable,
        str(
            HARNESS
            / "prompt12-precontrol-freshness.py"
        ),
        "--input",
        "@PROMPT12_CANONICAL_INTERVALS@",
        "--experiment-id",
        "EXP-001",
        "--run-id",
        "RUN-001",
        "--decision-utc-ns",
        "@PROMPT12_DECISION_UTC_NS@",
        "--selected-output",
        str(
            run
            / "precontrol"
            / "T1.selected.jsonl"
        ),
        "--stationarity-output",
        "@PROMPT12_STATIONARITY_JSON@",
        "--output",
        "@PROMPT12_PRECONTROL_JSON@",
    ]

    transitions = []

    for index in range(1, 7):
        transitions.append(
            {
                "label": f"T{index}",
                "trigger_command": [
                    "trigger",
                    f"T{index}",
                ],
                "post_stationarity_command": [
                    "post",
                    f"T{index}",
                ],
            }
        )

    manifest = {
        "initial_stationarity_command": initial,
        "transitions": transitions,
    }

    path = root / "manifest.json"

    path.write_text(
        json.dumps(
            manifest,
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    return path


def run_materializer(
    manifest: pathlib.Path,
    output: pathlib.Path,
    index: int | None,
):
    argv = [
        sys.executable,
        str(SCRIPT),
        "--manifest",
        str(manifest),
    ]

    if index is not None:
        argv.extend(
            [
                "--initial-transition-index",
                str(index),
            ]
        )

    argv.extend(
        [
            "--output",
            str(output),
        ]
    )

    return subprocess.run(
        argv,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


class ResumePrecontrolMaterializerTests(
    unittest.TestCase
):
    def test_index_one_preserves_full_sequence_initial_command(self):
        with tempfile.TemporaryDirectory() as raw:
            root = pathlib.Path(raw)
            manifest = sample_manifest(root)

            original = json.loads(
                manifest.read_text(
                    encoding="utf-8"
                )
            )

            before_sha = sha256(manifest)

            output = root / "index1.json"

            proc = run_materializer(
                manifest,
                output,
                1,
            )

            self.assertEqual(
                proc.returncode,
                0,
                proc.stderr,
            )

            report = json.loads(
                output.read_text(
                    encoding="utf-8"
                )
            )

            self.assertEqual(
                report["command"],
                original[
                    "initial_stationarity_command"
                ],
            )

            self.assertEqual(
                report["first_scientific_transition"],
                "T1",
            )

            self.assertEqual(
                sha256(manifest),
                before_sha,
            )

    def test_index_two_materializes_initial_pre_step_for_t2(self):
        with tempfile.TemporaryDirectory() as raw:
            root = pathlib.Path(raw)
            manifest = sample_manifest(root)

            before_sha = sha256(manifest)

            output = root / "index2.json"

            proc = run_materializer(
                manifest,
                output,
                2,
            )

            self.assertEqual(
                proc.returncode,
                0,
                proc.stderr,
            )

            report = json.loads(
                output.read_text(
                    encoding="utf-8"
                )
            )

            command = report["command"]

            self.assertEqual(
                report["initial_transition_index"],
                2,
            )

            self.assertEqual(
                report["first_scientific_transition"],
                "T2",
            )

            self.assertEqual(
                report["precontrol_semantics"],
                "initial-pre-step",
            )

            self.assertFalse(
                report[
                    "synthetic_prior_transition_events"
                ]
            )

            self.assertFalse(
                report[
                    "skipped_transition_bindings_consumed"
                ]
            )

            self.assertFalse(
                report["command_executed"]
            )

            mode_index = command.index("--mode")
            self.assertEqual(
                command[mode_index + 1],
                "initial-pre-step",
            )

            output_index = command.index(
                "--precontrol-output"
            )
            self.assertTrue(
                command[
                    output_index + 1
                ].endswith(
                    "/precontrol/T2.json"
                )
            )

            selected_index = command.index(
                "--selected-output"
            )
            self.assertTrue(
                command[
                    selected_index + 1
                ].endswith(
                    "/precontrol/T2.selected.jsonl"
                )
            )

            attempt_index = command.index(
                "--attempt-root"
            )
            self.assertTrue(
                command[
                    attempt_index + 1
                ].endswith(
                    "/precontrol-handoff/T2"
                )
            )

            evidence_index = command.index(
                "--evidence-root"
            )
            self.assertTrue(
                command[
                    evidence_index + 1
                ].endswith(
                    "/stationarity/resume-T2"
                )
            )

            for forbidden in (
                "--control-index",
                "--timeline-command-json",
                "--expected-timeline-event-count",
                "--actuator-timeline",
            ):
                self.assertNotIn(
                    forbidden,
                    command,
                )

            self.assertEqual(
                sha256(manifest),
                before_sha,
            )

    def test_missing_cursor_fails_closed(self):
        with tempfile.TemporaryDirectory() as raw:
            root = pathlib.Path(raw)
            manifest = sample_manifest(root)
            output = root / "missing.json"

            proc = run_materializer(
                manifest,
                output,
                None,
            )

            self.assertNotEqual(
                proc.returncode,
                0,
            )

            self.assertFalse(
                output.exists()
            )

    def test_invalid_cursor_fails_closed(self):
        for index in (0, 7):
            with self.subTest(index=index):
                with tempfile.TemporaryDirectory() as raw:
                    root = pathlib.Path(raw)
                    manifest = sample_manifest(root)
                    output = root / "invalid.json"

                    proc = run_materializer(
                        manifest,
                        output,
                        index,
                    )

                    self.assertNotEqual(
                        proc.returncode,
                        0,
                    )

                    self.assertFalse(
                        output.exists()
                    )

    def test_existing_output_fails_closed(self):
        with tempfile.TemporaryDirectory() as raw:
            root = pathlib.Path(raw)
            manifest = sample_manifest(root)
            output = root / "existing.json"

            output.write_text(
                "{}\n",
                encoding="utf-8",
            )

            proc = run_materializer(
                manifest,
                output,
                2,
            )

            self.assertNotEqual(
                proc.returncode,
                0,
            )

    def test_t1_post_step_contract_is_not_modified(self):
        with tempfile.TemporaryDirectory() as raw:
            root = pathlib.Path(raw)
            manifest = sample_manifest(root)

            before = json.loads(
                manifest.read_text(
                    encoding="utf-8"
                )
            )

            output = root / "index2.json"

            proc = run_materializer(
                manifest,
                output,
                2,
            )

            self.assertEqual(
                proc.returncode,
                0,
                proc.stderr,
            )

            after = json.loads(
                manifest.read_text(
                    encoding="utf-8"
                )
            )

            self.assertEqual(
                after["transitions"],
                before["transitions"],
            )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
