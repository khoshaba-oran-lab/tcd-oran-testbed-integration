import pathlib
import subprocess
import tempfile
import textwrap
import unittest


TEST_DIR = pathlib.Path(__file__).resolve().parent
HARNESS = TEST_DIR.parent

ADAPTER = (
    HARNESS
    / "adapters"
    / "prompt12-bounded-traffic-session.sh"
)


def prepare_outputs_source():
    text = ADAPTER.read_text(encoding="utf-8")

    start = text.index("prepare_outputs()\n{")
    end = text.index(
        "\n}\n\ncleanup_session()",
        start,
    )

    return text[start:end + 2]


def run_bash(body, root):
    script = (
        "set -u\n"
        "set -o pipefail\n"
        "SESSION_CONTROL_STDOUT=''\n"
        "SESSION_CONTROL_STDERR=''\n"
        + prepare_outputs_source()
        + "\n"
        + textwrap.dedent(body)
    )

    return subprocess.run(
        [
            "/usr/bin/bash",
            "-c",
            script,
            "prompt12-test",
            str(root),
        ],
        text=True,
        capture_output=True,
        check=False,
    )


class AttemptScopedControlLogTests(unittest.TestCase):

    def test_source_uses_attempt_scoped_control_paths(self):
        text = ADAPTER.read_text(encoding="utf-8")

        self.assertIn(
            "local session_attempt_id",
            text,
        )
        self.assertIn(
            'date -u \'+%s%N\'',
            text,
        )
        self.assertIn(
            '${raw_output}.session.${session_attempt_id}.stdout.log',
            text,
        )
        self.assertIn(
            '${raw_output}.session.${session_attempt_id}.stderr.log',
            text,
        )

        self.assertNotIn(
            'SESSION_CONTROL_STDOUT="${raw_output}.session.stdout.log"',
            text,
        )
        self.assertNotIn(
            'SESSION_CONTROL_STDERR="${raw_output}.session.stderr.log"',
            text,
        )

    def test_stale_legacy_control_logs_do_not_block(self):
        with tempfile.TemporaryDirectory() as raw:
            root = pathlib.Path(raw)

            proc = run_bash(
                r'''
                root="$1"
                raw_output="$root/iperf3-receiver.stdout.log"
                timestamp_output="$root/iperf3-receiver.timestamps.jsonl"
                stderr_output="$root/iperf3-receiver.stderr.log"

                legacy_stdout="${raw_output}.session.stdout.log"
                legacy_stderr="${raw_output}.session.stderr.log"

                : > "$legacy_stdout"
                : > "$legacy_stderr"

                prepare_outputs \
                    "$raw_output" \
                    "$timestamp_output" \
                    "$stderr_output"

                rc=$?

                printf 'RC=%s\n' "$rc"
                printf 'CONTROL_STDOUT=%s\n' "$SESSION_CONTROL_STDOUT"
                printf 'CONTROL_STDERR=%s\n' "$SESSION_CONTROL_STDERR"

                test "$rc" -eq 0
                test "$SESSION_CONTROL_STDOUT" != "$legacy_stdout"
                test "$SESSION_CONTROL_STDERR" != "$legacy_stderr"
                test -e "$legacy_stdout"
                test -e "$legacy_stderr"
                ''',
                root,
            )

            self.assertEqual(
                proc.returncode,
                0,
                proc.stderr,
            )
            self.assertIn(
                "RC=0",
                proc.stdout,
            )

    def test_two_attempts_get_distinct_control_paths(self):
        with tempfile.TemporaryDirectory() as raw:
            root = pathlib.Path(raw)

            proc = run_bash(
                r'''
                root="$1"
                raw_output="$root/iperf3-receiver.stdout.log"
                timestamp_output="$root/iperf3-receiver.timestamps.jsonl"
                stderr_output="$root/iperf3-receiver.stderr.log"

                prepare_outputs \
                    "$raw_output" \
                    "$timestamp_output" \
                    "$stderr_output" ||
                    exit $?

                first_stdout="$SESSION_CONTROL_STDOUT"
                first_stderr="$SESSION_CONTROL_STDERR"

                : > "$first_stdout"
                : > "$first_stderr"

                sleep 0.01

                prepare_outputs \
                    "$raw_output" \
                    "$timestamp_output" \
                    "$stderr_output" ||
                    exit $?

                second_stdout="$SESSION_CONTROL_STDOUT"
                second_stderr="$SESSION_CONTROL_STDERR"

                test "$first_stdout" != "$second_stdout"
                test "$first_stderr" != "$second_stderr"

                test -e "$first_stdout"
                test -e "$first_stderr"

                test ! -e "$second_stdout"
                test ! -e "$second_stderr"

                printf 'DISTINCT_CONTROL_PATHS=PASS\n'
                ''',
                root,
            )

            self.assertEqual(
                proc.returncode,
                0,
                proc.stderr,
            )
            self.assertIn(
                "DISTINCT_CONTROL_PATHS=PASS",
                proc.stdout,
            )

    def test_scientific_evidence_collision_remains_rc73(self):
        with tempfile.TemporaryDirectory() as raw:
            root = pathlib.Path(raw)

            proc = run_bash(
                r'''
                root="$1"
                raw_output="$root/iperf3-receiver.stdout.log"
                timestamp_output="$root/iperf3-receiver.timestamps.jsonl"
                stderr_output="$root/iperf3-receiver.stderr.log"

                : > "$raw_output"

                prepare_outputs \
                    "$raw_output" \
                    "$timestamp_output" \
                    "$stderr_output"

                rc=$?

                printf 'RC=%s\n' "$rc"

                test "$rc" -eq 73
                ''',
                root,
            )

            self.assertEqual(
                proc.returncode,
                0,
                proc.stderr,
            )
            self.assertIn(
                "RC=73",
                proc.stdout,
            )


if __name__ == "__main__":
    unittest.main()
