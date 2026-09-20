#!/usr/bin/env python3

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "prompt12-bounded-finalization-command.py"
)

TIMELINE_TOKEN = "@PROMPT12_ACTUATOR_TIMELINE@"


def make_timeline(
    root,
    event_count=6,
    rc=0,
    invalid=False,
):
    script = root / "timeline.py"
    order = root / "order.log"
    marker = root / "timeline.executed"

    script.write_text(
        "\n".join([
            "import json",
            "import pathlib",
            "import sys",
            f"order = pathlib.Path({str(order)!r})",
            f"marker = pathlib.Path({str(marker)!r})",
            "with order.open('a', encoding='utf-8') as handle:",
            "    handle.write('timeline\\n')",
            "marker.write_text('executed\\n', encoding='utf-8')",
            f"rc = {rc}",
            "if rc:",
            "    raise SystemExit(rc)",
            "output = pathlib.Path(sys.argv[sys.argv.index('--output') + 1])",
            "output.parent.mkdir(parents=True, exist_ok=True)",
            (
                "output.write_text('invalid\\n', encoding='utf-8')"
                if invalid
                else (
                    "output.write_text("
                    + repr(
                        "".join(
                            json.dumps(
                                {
                                    "event_index": index,
                                    "schema": "actuatorEvent",
                                },
                                sort_keys=True,
                            )
                            + "\n"
                            for index in range(1, event_count + 1)
                        )
                    )
                    + ", encoding='utf-8')"
                )
            ),
        ]) + "\n",
        encoding="utf-8",
    )

    command = [
        sys.executable,
        str(script),
        "--output",
        TIMELINE_TOKEN,
    ]

    return command, order, marker


def make_pipeline(
    root,
    staging,
    canonical,
    rc=0,
    create_outputs=True,
):
    script = root / "pipeline.py"
    order = root / "order.log"
    marker = root / "pipeline.executed"

    script.write_text(
        "\n".join([
            "import json",
            "import pathlib",
            "import sys",
            f"order = pathlib.Path({str(order)!r})",
            f"marker = pathlib.Path({str(marker)!r})",
            "with order.open('a', encoding='utf-8') as handle:",
            "    handle.write('pipeline\\n')",
            "marker.write_text('executed\\n', encoding='utf-8')",
            "timeline = pathlib.Path(sys.argv[sys.argv.index('--timeline') + 1])",
            "if not timeline.is_file():",
            "    raise SystemExit(76)",
            f"rc = {rc}",
            "if rc:",
            "    raise SystemExit(rc)",
            f"create_outputs = {create_outputs!r}",
            "if create_outputs:",
            f"    staging = pathlib.Path({str(staging)!r})",
            f"    canonical = pathlib.Path({str(canonical)!r})",
            "    staging.parent.mkdir(parents=True, exist_ok=True)",
            "    canonical.parent.mkdir(parents=True, exist_ok=True)",
            "    staging.write_text(",
            "        json.dumps({'record': 'staging'}) + '\\n',",
            "        encoding='utf-8',",
            "    )",
            "    canonical.write_text(",
            "        json.dumps({'record': 'canonical'}) + '\\n',",
            "        encoding='utf-8',",
            "    )",
        ]) + "\n",
        encoding="utf-8",
    )

    command = [
        sys.executable,
        str(script),
        "--timeline",
        TIMELINE_TOKEN,
    ]

    return command, order, marker


def run_finalization(
    root,
    timeline_command,
    pipeline_command,
    timeline_output=None,
    staging_output=None,
    canonical_output=None,
):
    timeline_output = (
        timeline_output
        if timeline_output is not None
        else root / "actuator-timeline.jsonl"
    )
    staging_output = (
        staging_output
        if staging_output is not None
        else root / "processed" / "staging.jsonl"
    )
    canonical_output = (
        canonical_output
        if canonical_output is not None
        else root / "processed" / "canonical.jsonl"
    )

    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--attempt-root",
            str(root / "attempts"),
            "--python-executable",
            sys.executable,
            "--timeline-output",
            str(timeline_output),
            "--staging-output",
            str(staging_output),
            "--canonical-output",
            str(canonical_output),
            "--expected-event-count",
            "6",
            "--timeline-command",
            *timeline_command,
            "--pipeline-command",
            *pipeline_command,
        ],
        text=True,
        capture_output=True,
        check=False,
    )


class BoundedFinalizationCommandTests(unittest.TestCase):
    def test_contract_has_no_runtime_capability(self):
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "contract"],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(
            "EXECUTION_ORDER=ACTUATOR_TIMELINE_THEN_RECEIVER_PIPELINE",
            proc.stdout,
        )
        self.assertIn(
            "DOCKER_EXECUTION_CAPABILITY=ABSENT",
            proc.stdout,
        )
        self.assertIn(
            "CONTROL_EXECUTED=NO",
            proc.stdout,
        )

    def test_success_runs_timeline_before_pipeline(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            staging = root / "processed" / "staging.jsonl"
            canonical = root / "processed" / "canonical.jsonl"

            timeline, order, _ = make_timeline(root)
            pipeline, _, _ = make_pipeline(
                root,
                staging,
                canonical,
            )

            proc = run_finalization(
                root,
                timeline,
                pipeline,
                staging_output=staging,
                canonical_output=canonical,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(
                order.read_text(encoding="utf-8"),
                "timeline\npipeline\n",
            )

            report = json.loads(proc.stdout)
            self.assertEqual(
                report["finalization_gate"],
                "PASS",
            )
            self.assertEqual(
                report["timeline_event_count"],
                6,
            )
            self.assertEqual(
                report["canonical_record_count"],
                1,
            )
            self.assertFalse(report["control_executed"])

    def test_timeline_failure_prohibits_pipeline(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            staging = root / "processed" / "staging.jsonl"
            canonical = root / "processed" / "canonical.jsonl"

            timeline, _, _ = make_timeline(root, rc=7)
            pipeline, _, pipeline_marker = make_pipeline(
                root,
                staging,
                canonical,
            )

            proc = run_finalization(
                root,
                timeline,
                pipeline,
                staging_output=staging,
                canonical_output=canonical,
            )

            self.assertEqual(proc.returncode, 7)
            self.assertFalse(pipeline_marker.exists())
            self.assertIn(
                "TIMELINE_COMMAND_FAILED_RC_7",
                proc.stderr,
            )

    def test_invalid_timeline_prohibits_pipeline(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            staging = root / "processed" / "staging.jsonl"
            canonical = root / "processed" / "canonical.jsonl"

            timeline, _, _ = make_timeline(
                root,
                invalid=True,
            )
            pipeline, _, pipeline_marker = make_pipeline(
                root,
                staging,
                canonical,
            )

            proc = run_finalization(
                root,
                timeline,
                pipeline,
                staging_output=staging,
                canonical_output=canonical,
            )

            self.assertEqual(proc.returncode, 65)
            self.assertFalse(pipeline_marker.exists())
            self.assertIn(
                "TIMELINE_OUTPUT_INVALID_JSONL",
                proc.stderr,
            )

    def test_pipeline_failure_preserves_timeline(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            timeline_output = root / "timeline.jsonl"
            staging = root / "processed" / "staging.jsonl"
            canonical = root / "processed" / "canonical.jsonl"

            timeline, _, _ = make_timeline(root)
            pipeline, _, pipeline_marker = make_pipeline(
                root,
                staging,
                canonical,
                rc=8,
            )

            proc = run_finalization(
                root,
                timeline,
                pipeline,
                timeline_output=timeline_output,
                staging_output=staging,
                canonical_output=canonical,
            )

            self.assertEqual(proc.returncode, 8)
            self.assertTrue(timeline_output.is_file())
            self.assertTrue(pipeline_marker.is_file())
            self.assertFalse(canonical.exists())
            self.assertIn(
                "PIPELINE_COMMAND_FAILED_RC_8",
                proc.stderr,
            )

    def test_existing_output_blocks_before_commands(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            timeline_output = root / "timeline.jsonl"
            staging = root / "processed" / "staging.jsonl"
            canonical = root / "processed" / "canonical.jsonl"
            timeline_output.write_text(
                "sentinel\n",
                encoding="utf-8",
            )

            timeline, _, timeline_marker = make_timeline(root)
            pipeline, _, pipeline_marker = make_pipeline(
                root,
                staging,
                canonical,
            )

            proc = run_finalization(
                root,
                timeline,
                pipeline,
                timeline_output=timeline_output,
                staging_output=staging,
                canonical_output=canonical,
            )

            self.assertEqual(proc.returncode, 65)
            self.assertFalse(timeline_marker.exists())
            self.assertFalse(pipeline_marker.exists())
            self.assertEqual(
                timeline_output.read_text(encoding="utf-8"),
                "sentinel\n",
            )
            self.assertIn(
                "TIMELINE_OUTPUT_ALREADY_EXISTS",
                proc.stderr,
            )

    def test_missing_canonical_output_fails_closed(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            staging = root / "processed" / "staging.jsonl"
            canonical = root / "processed" / "canonical.jsonl"

            timeline, _, _ = make_timeline(root)
            pipeline, _, _ = make_pipeline(
                root,
                staging,
                canonical,
                create_outputs=False,
            )

            proc = run_finalization(
                root,
                timeline,
                pipeline,
                staging_output=staging,
                canonical_output=canonical,
            )

            self.assertEqual(proc.returncode, 65)
            self.assertFalse(canonical.exists())
            self.assertIn(
                "STAGING_OUTPUT_MISSING",
                proc.stderr,
            )

    def test_shell_string_command_is_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            staging = root / "processed" / "staging.jsonl"
            canonical = root / "processed" / "canonical.jsonl"

            pipeline, _, _ = make_pipeline(
                root,
                staging,
                canonical,
            )

            proc = run_finalization(
                root,
                [
                    "bash",
                    "-lc",
                    "printf unsafe",
                    TIMELINE_TOKEN,
                ],
                pipeline,
                staging_output=staging,
                canonical_output=canonical,
            )

            self.assertEqual(proc.returncode, 64)
            self.assertFalse((root / "attempts").exists())
            self.assertIn(
                "TIMELINE_SHELL_STRING_PROHIBITED",
                proc.stderr,
            )

    def test_timeline_tokens_are_mandatory(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            staging = root / "processed" / "staging.jsonl"
            canonical = root / "processed" / "canonical.jsonl"

            timeline = [
                sys.executable,
                "-c",
                "raise SystemExit(0)",
            ]
            pipeline, _, _ = make_pipeline(
                root,
                staging,
                canonical,
            )

            proc = run_finalization(
                root,
                timeline,
                pipeline,
                staging_output=staging,
                canonical_output=canonical,
            )

            self.assertEqual(proc.returncode, 64)
            self.assertFalse((root / "attempts").exists())
            self.assertIn(
                "TIMELINE_OUTPUT_TOKEN_COUNT_INVALID",
                proc.stderr,
            )


if __name__ == "__main__":
    unittest.main()
