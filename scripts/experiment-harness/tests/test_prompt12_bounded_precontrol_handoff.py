#!/usr/bin/env python3

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "prompt12-bounded-precontrol-handoff.py"
)

STATIONARITY_TOKEN = "@PROMPT12_STATIONARITY_JSON@"
PRECONTROL_TOKEN = "@PROMPT12_PRECONTROL_JSON@"
DECISION_TOKEN = "@PROMPT12_DECISION_UTC_NS@"
CANONICAL_TOKEN = "@PROMPT12_CANONICAL_INTERVALS@"



def make_stationarity(
    root,
    gate,
    raw=None,
    marker=None,
):
    script = root / "stationarity.py"
    canonical = (
        root
        / "attempt-stationarity-test"
        / "processed"
        / "intervals.canonical.jsonl"
    )
    canonical.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    canonical.write_text(
        '{"record":"canonical"}\n',
        encoding="utf-8",
    )

    if raw is None:
        raw = json.dumps(
            {
                "canonical_interval_snapshot_path":
                    str(canonical.resolve()),
                "output_stationarity_gate": gate,
                "window_pair_index": [1, 2],
            },
            sort_keys=True,
            separators=(",", ":"),
        ) + "\n"

    lines = [
        "import pathlib",
        "import sys",
    ]

    if marker is not None:
        lines.append(
            f"pathlib.Path({str(marker)!r}).write_text("
            "'executed\\n', encoding='utf-8')"
        )

    lines.append(f"sys.stdout.write({raw!r})")

    script.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    return [sys.executable, str(script)], raw




def make_freshness(root, admission="PASS"):
    script = root / "freshness.py"
    marker = root / "freshness.executed"

    script.write_text(
        "\n".join([
            "import json",
            "import pathlib",
            "import sys",
            f"marker = pathlib.Path({str(marker)!r})",
            "marker.write_text('executed\\n', encoding='utf-8')",
            "input_path = pathlib.Path(sys.argv[sys.argv.index('--input') + 1])",
            "output_path = pathlib.Path(sys.argv[sys.argv.index('--output') + 1])",
            "canonical_path = pathlib.Path(sys.argv[sys.argv.index('--canonical-input') + 1])",
            "if not canonical_path.is_file():",
            "    raise SystemExit(79)",
            "official = json.loads(input_path.read_text(encoding='utf-8'))",
            "admission = sys.argv[sys.argv.index('--admission') + 1]",
            "result = {",
            "    'selection': 'latest_50_complete_contiguous_samples',",
            "    'stationarity_window_binding_gate': 'PASS',",
            "    'output_stationarity_gate': 'PASS',",
            "    'freshness_gate': 'PASS',",
            "    'precontrol_admission_gate': admission,",
            "    'official_stationarity_report': official,",
            "}",
            "output_path.write_text(",
            "    json.dumps(result, sort_keys=True) + '\\n',",
            "    encoding='utf-8',",
            ")",
        ]) + "\n",
        encoding="utf-8",
    )

    command = [
        sys.executable,
        str(script),
        "--input",
        STATIONARITY_TOKEN,
        "--canonical-input",
        CANONICAL_TOKEN,
        "--output",
        PRECONTROL_TOKEN,
        "--decision-utc-ns",
        DECISION_TOKEN,
        "--admission",
        admission,
    ]

    return command, marker



def run_handoff(root, stationarity, freshness, output=None):
    if output is None:
        output = root / "precontrol.json"

    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--attempt-root",
            str(root / "attempts"),
            "--precontrol-output",
            str(output),
            "--stationarity-command",
            *stationarity,
            "--freshness-command",
            *freshness,
        ],
        text=True,
        capture_output=True,
        check=False,
    )


class BoundedPrecontrolHandoffTests(unittest.TestCase):
    def test_contract_has_no_execution_capability(self):
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "contract"],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(
            "COMMAND_FORM=ARGV_ONLY",
            proc.stdout,
        )
        self.assertIn(
            "TRIGGER_WRITE_CAPABILITY=ABSENT",
            proc.stdout,
        )
        self.assertIn(
            "CONTROL_EXECUTED=NO",
            proc.stdout,
        )

    def test_pass_publishes_precontrol_and_preserves_stdout(self):
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            stationarity, expected_stdout = make_stationarity(
                root,
                "PASS",
            )
            freshness, marker = make_freshness(root)
            output = root / "precontrol.json"

            proc = run_handoff(
                root,
                stationarity,
                freshness,
                output,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(proc.stdout, expected_stdout)
            self.assertTrue(marker.is_file())
            self.assertTrue(output.is_file())

            record = json.loads(
                output.read_text(encoding="utf-8")
            )
            self.assertEqual(
                record["precontrol_admission_gate"],
                "PASS",
            )
            self.assertEqual(
                record["official_stationarity_report"]
                ["output_stationarity_gate"],
                "PASS",
            )

    def test_stationarity_fail_skips_freshness_and_output(self):
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            stationarity, expected_stdout = make_stationarity(
                root,
                "FAIL",
            )
            freshness, marker = make_freshness(root)
            output = root / "precontrol.json"

            proc = run_handoff(
                root,
                stationarity,
                freshness,
                output,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(proc.stdout, expected_stdout)
            self.assertFalse(marker.exists())
            self.assertFalse(output.exists())

    def test_existing_output_blocks_before_stationarity(self):
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            stationarity_marker = root / "stationarity.executed"
            stationarity, _ = make_stationarity(
                root,
                "PASS",
                marker=stationarity_marker,
            )
            freshness, _ = make_freshness(root)
            output = root / "precontrol.json"
            output.write_text("sentinel\n", encoding="utf-8")

            proc = run_handoff(
                root,
                stationarity,
                freshness,
                output,
            )

            self.assertEqual(proc.returncode, 65)
            self.assertFalse(stationarity_marker.exists())
            self.assertEqual(
                output.read_text(encoding="utf-8"),
                "sentinel\n",
            )
            self.assertIn(
                "PRECONTROL_OUTPUT_ALREADY_EXISTS",
                proc.stderr,
            )

    def test_invalid_stationarity_json_fails_closed(self):
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            stationarity, _ = make_stationarity(
                root,
                "PASS",
                raw="not-json\n",
            )
            freshness, marker = make_freshness(root)
            output = root / "precontrol.json"

            proc = run_handoff(
                root,
                stationarity,
                freshness,
                output,
            )

            self.assertEqual(proc.returncode, 65)
            self.assertFalse(marker.exists())
            self.assertFalse(output.exists())
            self.assertIn(
                "STATIONARITY_STDOUT_INVALID_JSON",
                proc.stderr,
            )

    def test_freshness_failure_does_not_publish(self):
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            stationarity, _ = make_stationarity(
                root,
                "PASS",
            )
            freshness = [
                sys.executable,
                "-c",
                "raise SystemExit(9)",
                STATIONARITY_TOKEN,
                CANONICAL_TOKEN,
                PRECONTROL_TOKEN,
            ]
            output = root / "precontrol.json"

            proc = run_handoff(
                root,
                stationarity,
                freshness,
                output,
            )

            self.assertEqual(proc.returncode, 9)
            self.assertFalse(output.exists())
            self.assertIn(
                "FRESHNESS_COMMAND_FAILED_RC_9",
                proc.stderr,
            )

    def test_nonpassing_precontrol_is_not_published(self):
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            stationarity, _ = make_stationarity(
                root,
                "PASS",
            )
            freshness, marker = make_freshness(
                root,
                admission="FAIL",
            )
            output = root / "precontrol.json"

            proc = run_handoff(
                root,
                stationarity,
                freshness,
                output,
            )

            self.assertEqual(proc.returncode, 65)
            self.assertTrue(marker.is_file())
            self.assertFalse(output.exists())
            self.assertIn(
                "PRECONTROL_CANDIDATE_GATE_NOT_PASS",
                proc.stderr,
            )

    def test_shell_string_command_is_rejected(self):
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            freshness, _ = make_freshness(root)

            proc = run_handoff(
                root,
                ["bash", "-lc", "printf unsafe"],
                freshness,
            )

            self.assertEqual(proc.returncode, 64)
            self.assertFalse((root / "attempts").exists())
            self.assertIn(
                "STATIONARITY_SHELL_STRING_PROHIBITED",
                proc.stderr,
            )

    def test_freshness_tokens_are_mandatory(self):
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            stationarity, _ = make_stationarity(
                root,
                "PASS",
            )
            freshness = [
                sys.executable,
                "-c",
                "raise SystemExit(0)",
                STATIONARITY_TOKEN,
            ]

            proc = run_handoff(
                root,
                stationarity,
                freshness,
            )

            self.assertEqual(proc.returncode, 64)
            self.assertFalse((root / "attempts").exists())
            self.assertIn(
                "FRESHNESS_PRECONTROL_TOKEN_COUNT_INVALID",
                proc.stderr,
            )


if __name__ == "__main__":
    unittest.main()
