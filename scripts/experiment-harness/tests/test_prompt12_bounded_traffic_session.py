#!/usr/bin/env python3
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "adapters"
    / "prompt12-bounded-traffic-session.sh"
)


def write_executable(path, content):
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def create_fake_environment(root):
    adapter_log = root / "adapter.log"
    docker_log = root / "docker.log"
    fake_adapter = root / "fake-traffic-adapter.sh"
    fake_docker = root / "docker"

    write_executable(
        fake_adapter,
        """#!/usr/bin/env bash
set -u
printf '%s\\n' "$*" >> "$FAKE_ADAPTER_LOG"

case "$1" in
    create-receiver)
        exit "${FAKE_CREATE_RC:-0}"
        ;;
    capture-receiver)
        : > "$3"
        : > "$4"
        : > "$5"
        sleep "${FAKE_CAPTURE_SLEEP:-0.10}"
        exit "${FAKE_CAPTURE_RC:-0}"
        ;;
    wait-receiver-ready)
        exit "${FAKE_READY_RC:-0}"
        ;;
    run-client)
        sleep "${FAKE_CLIENT_SLEEP:-0.01}"
        exit "${FAKE_CLIENT_RC:-0}"
        ;;
    *)
        exit 64
        ;;
esac
""",
    )

    write_executable(
        fake_docker,
        """#!/usr/bin/env bash
set -u
printf '%s\\n' "$*" >> "$FAKE_DOCKER_LOG"
exit "${FAKE_DOCKER_RC:-0}"
""",
    )

    environment = os.environ.copy()
    environment.update(
        {
            "PATH": f"{root}:{environment['PATH']}",
            "SCI_ORAN_PROMPT12_LIVE_TRAFFIC_ENABLE": "YES",
            "SCI_ORAN_PROMPT12_SESSION_TRAFFIC_ADAPTER": str(
                fake_adapter
            ),
            "SCI_ORAN_PROMPT12_SESSION_INT_TIMEOUT_S": "1",
            "SCI_ORAN_PROMPT12_SESSION_TERM_TIMEOUT_S": "1",
            "FAKE_ADAPTER_LOG": str(adapter_log),
            "FAKE_DOCKER_LOG": str(docker_log),
        }
    )

    return environment, adapter_log, docker_log


def session_arguments(root):
    return [
        "prompt12-test-receiver",
        "30",
        str(root / "raw" / "receiver.stdout.log"),
        str(root / "raw" / "receiver.timestamps.jsonl"),
        str(root / "raw" / "receiver.stderr.log"),
    ]


def run_script(mode, arguments, environment):
    return subprocess.run(
        ["bash", str(SCRIPT), mode, *arguments],
        text=True,
        capture_output=True,
        check=False,
        env=environment,
    )


class BoundedTrafficSessionTests(unittest.TestCase):
    def test_contract_executes_nothing(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            environment, adapter_log, docker_log = (
                create_fake_environment(root)
            )

            proc = run_script("contract", [], environment)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(proc.stderr, "")
            self.assertFalse(adapter_log.exists())
            self.assertFalse(docker_log.exists())
            self.assertIn("CONTROL_EXECUTED=NO", proc.stdout)

    def test_plan_executes_nothing(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            environment, adapter_log, docker_log = (
                create_fake_environment(root)
            )

            proc = run_script(
                "plan",
                session_arguments(root),
                environment,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(proc.stderr, "")
            self.assertFalse(adapter_log.exists())
            self.assertFalse(docker_log.exists())
            self.assertIn("TRAFFIC_COMMAND_ARGC=7", proc.stdout)
            self.assertIn("CONTROL_EXECUTED=NO", proc.stdout)

    def test_run_without_live_enable_fails_closed(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            environment, adapter_log, docker_log = (
                create_fake_environment(root)
            )
            environment.pop(
                "SCI_ORAN_PROMPT12_LIVE_TRAFFIC_ENABLE"
            )

            proc = run_script(
                "run",
                session_arguments(root),
                environment,
            )

            self.assertEqual(proc.returncode, 77)
            self.assertFalse(adapter_log.exists())
            self.assertFalse(docker_log.exists())
            self.assertIn(
                "PROMPT12_LIVE_TRAFFIC_INTERLOCK=BLOCKED",
                proc.stderr,
            )

    def test_create_failure_does_not_remove_foreign_receiver(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            environment, adapter_log, docker_log = (
                create_fake_environment(root)
            )
            environment["FAKE_CREATE_RC"] = "9"

            proc = run_script(
                "run",
                session_arguments(root),
                environment,
            )

            self.assertEqual(proc.returncode, 9)
            self.assertTrue(adapter_log.exists())
            self.assertFalse(docker_log.exists())
            self.assertEqual(
                adapter_log.read_text(encoding="utf-8").splitlines(),
                ["create-receiver prompt12-test-receiver"],
            )

    def test_successful_session_removes_owned_receiver(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            environment, adapter_log, docker_log = (
                create_fake_environment(root)
            )
            arguments = session_arguments(root)

            proc = run_script("run", arguments, environment)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            calls = adapter_log.read_text(
                encoding="utf-8"
            ).splitlines()

            self.assertIn(
                "create-receiver prompt12-test-receiver",
                calls,
            )
            self.assertTrue(
                any(call.startswith("capture-receiver ") for call in calls)
            )
            self.assertTrue(
                any(
                    call.startswith("wait-receiver-ready ")
                    for call in calls
                )
            )
            self.assertIn("run-client 30", calls)
            self.assertEqual(
                docker_log.read_text(encoding="utf-8").strip(),
                "rm -f -- prompt12-test-receiver",
            )
            self.assertTrue(Path(arguments[2]).is_file())
            self.assertTrue(Path(arguments[3]).is_file())
            self.assertTrue(Path(arguments[4]).is_file())
            self.assertIn(
                "PROMPT12_TRAFFIC_SESSION_GATE=PASS",
                proc.stdout,
            )

    def test_client_failure_still_removes_owned_receiver(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            environment, _, docker_log = create_fake_environment(root)
            environment["FAKE_CLIENT_RC"] = "11"

            proc = run_script(
                "run",
                session_arguments(root),
                environment,
            )

            self.assertEqual(proc.returncode, 11)
            self.assertEqual(
                docker_log.read_text(encoding="utf-8").strip(),
                "rm -f -- prompt12-test-receiver",
            )
            self.assertIn(
                "FAIL_REASON=SESSION_BODY_RC_11",
                proc.stderr,
            )

    def test_source_declares_signal_cleanup_without_shell_string(self):
        source = SCRIPT.read_text(encoding="utf-8")

        self.assertIn("trap 'handle_signal 130' INT", source)
        self.assertIn("trap 'handle_signal 143' TERM", source)
        self.assertIn(
            'if [ "$SESSION_RECEIVER_CREATED" = "YES" ]',
            source,
        )
        self.assertNotIn("bash -lc", source)
        self.assertNotIn("eval ", source)


if __name__ == "__main__":
    unittest.main()
