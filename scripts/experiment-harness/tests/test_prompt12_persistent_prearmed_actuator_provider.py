#!/usr/bin/env python3
import json
import os
import pathlib
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[3]
PROVIDER = (
    ROOT
    / "scripts"
    / "experiment-harness"
    / "prompt12-persistent-prearmed-actuator-provider.py"
)
AUTHORIZATION = "AUTHORISE_PROMPT12_PROVIDER_ADMISSION"
FIFO_TOKEN = "@PROMPT12_ACTUATOR_FIFO@"


def write_launch(path, argv):
    path.write_text(
        json.dumps(argv) + "\n",
        encoding="utf-8",
    )


def command(
    runtime_root,
    fifo_path,
    launch_path,
    authorization=AUTHORIZATION,
    timeout_ms="1500",
    poll_ms="20",
):
    return [
        sys.executable,
        str(PROVIDER),
        "run",
        "--runtime-root",
        str(runtime_root),
        "--fifo-path",
        str(fifo_path),
        "--provider-launch-json",
        str(launch_path),
        "--provider-identity",
        "prompt12-test-provider",
        "--readiness-timeout-ms",
        str(timeout_ms),
        "--readiness-poll-ms",
        str(poll_ms),
        "--admission-authorization-token",
        authorization,
    ]


def run_once(*args, cwd=None):
    return subprocess.run(
        list(args),
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env={
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
        },
    )


def wait_for_file(path, process, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.is_file():
            return
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            raise AssertionError(
                "provider exited before evidence: "
                + stdout
                + stderr
            )
        time.sleep(0.02)
    raise AssertionError(
        "timed out waiting for " + str(path)
    )


def stop_manager(process):
    if process.poll() is None:
        process.send_signal(signal.SIGTERM)
    try:
        return process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        return process.communicate(timeout=5)


def reader_argv(marker=None):
    code = (
        "import os,sys,time\n"
        "fifo=sys.argv[1]\n"
        "marker=sys.argv[2] if len(sys.argv)>2 else None\n"
        "fd=os.open(fifo,os.O_RDONLY|os.O_NONBLOCK)\n"
        "deadline=time.monotonic()+30\n"
        "while time.monotonic()<deadline:\n"
        "  try:\n"
        "    data=os.read(fd,4096)\n"
        "  except BlockingIOError:\n"
        "    data=b''\n"
        "  if data and marker:\n"
        "    open(marker,'wb').write(data)\n"
        "    break\n"
        "  time.sleep(0.02)\n"
    )
    argv = [
        sys.executable,
        "-c",
        code,
        FIFO_TOKEN,
    ]
    if marker is not None:
        argv.append(str(marker))
    return argv


class PersistentPrearmedProviderTests(unittest.TestCase):
    def test_contract_reports_nonexecuting_boundary(self):
        proc = run_once(
            sys.executable,
            str(PROVIDER),
            "contract",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(
            "FIFO_CREATION=EXCLUSIVE",
            proc.stdout,
        )
        self.assertIn(
            "SHELL_EXECUTION_CAPABILITY=ABSENT",
            proc.stdout,
        )
        self.assertIn(
            "TRIGGER_WRITE_CAPABILITY=ABSENT",
            proc.stdout,
        )
        self.assertIn(
            "CLEANUP_IS_SEPARATE_ACTION=YES",
            proc.stdout,
        )

    def test_invalid_authorization_creates_nothing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            runtime = root / "runtime"
            launch = root / "launch.json"
            write_launch(launch, reader_argv())
            proc = run_once(
                *command(
                    runtime,
                    runtime / "actuator.fifo",
                    launch,
                    authorization="INVALID",
                )
            )
            self.assertEqual(proc.returncode, 77)
            self.assertFalse(runtime.exists())
            self.assertIn(
                "PROVIDER_ADMISSION_AUTHORIZATION_INVALID",
                proc.stderr,
            )

    def test_relative_runtime_root_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            launch = root / "launch.json"
            write_launch(launch, reader_argv())
            proc = run_once(
                *command(
                    pathlib.Path("relative-runtime"),
                    pathlib.Path(
                        "relative-runtime/actuator.fifo"
                    ),
                    launch,
                ),
                cwd=root,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn(
                "RUNTIME_ROOT_NOT_ABSOLUTE",
                proc.stderr,
            )

    def test_fifo_outside_runtime_root_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            runtime = root / "runtime"
            launch = root / "launch.json"
            write_launch(launch, reader_argv())
            proc = run_once(
                *command(
                    runtime,
                    root / "other.fifo",
                    launch,
                )
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertFalse(runtime.exists())
            self.assertIn(
                "FIFO_PATH_NOT_CANONICAL",
                proc.stderr,
            )

    def test_existing_runtime_root_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            runtime = root / "runtime"
            runtime.mkdir()
            marker = runtime / "preserve"
            marker.write_text("unchanged", encoding="utf-8")
            launch = root / "launch.json"
            write_launch(launch, reader_argv())
            proc = run_once(
                *command(
                    runtime,
                    runtime / "actuator.fifo",
                    launch,
                )
            )
            self.assertEqual(proc.returncode, 73)
            self.assertEqual(
                marker.read_text(encoding="utf-8"),
                "unchanged",
            )
            self.assertIn(
                "RUNTIME_ROOT_ALREADY_EXISTS",
                proc.stderr,
            )

    def test_non_array_launch_json_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            runtime = root / "runtime"
            launch = root / "launch.json"
            launch.write_text(
                json.dumps({"command": "invalid"}) + "\n",
                encoding="utf-8",
            )
            proc = run_once(
                *command(
                    runtime,
                    runtime / "actuator.fifo",
                    launch,
                )
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertFalse(runtime.exists())
            self.assertIn(
                "PROVIDER_LAUNCH_ARGV_INVALID",
                proc.stderr,
            )

    def test_fifo_token_cardinality_is_exactly_one(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            cases = [
                [sys.executable, "-c", "import time;time.sleep(1)"],
                [
                    sys.executable,
                    "-c",
                    "import time;time.sleep(1)",
                    FIFO_TOKEN,
                    FIFO_TOKEN,
                ],
            ]
            for index, argv in enumerate(cases):
                with self.subTest(index=index):
                    runtime = root / f"runtime-{index}"
                    launch = root / f"launch-{index}.json"
                    write_launch(launch, argv)
                    proc = run_once(
                        *command(
                            runtime,
                            runtime / "actuator.fifo",
                            launch,
                        )
                    )
                    self.assertNotEqual(proc.returncode, 0)
                    self.assertFalse(runtime.exists())
                    self.assertIn(
                        "FIFO_TOKEN_OCCURRENCE_COUNT_INVALID",
                        proc.stderr,
                    )

    def test_stub_reader_produces_complete_admission(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            runtime = root / "runtime"
            fifo = runtime / "actuator.fifo"
            launch = root / "launch.json"
            write_launch(launch, reader_argv())
            manager = subprocess.Popen(
                command(runtime, fifo, launch),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={
                    **os.environ,
                    "PYTHONDONTWRITEBYTECODE": "1",
                },
            )
            try:
                admission_path = (
                    runtime / "provider-admission.json"
                )
                wait_for_file(admission_path, manager)
                admission = json.loads(
                    admission_path.read_text(
                        encoding="utf-8"
                    )
                )
                required = {
                    "execution_host",
                    "fifo_path",
                    "fifo_mode",
                    "fifo_uid",
                    "fifo_gid",
                    "provider_pid",
                    "provider_process_start_identity",
                    "provider_restart_count",
                    "reader_readiness_gate",
                    "admission_utc",
                }
                self.assertTrue(
                    required.issubset(admission)
                )
                self.assertEqual(
                    admission["state"],
                    "ADMITTED",
                )
                self.assertEqual(
                    admission["reader_readiness_gate"],
                    "PASS",
                )
                self.assertEqual(
                    admission["provider_restart_count"],
                    0,
                )
                self.assertEqual(
                    admission["fifo_mode"],
                    "0600",
                )
                self.assertEqual(
                    admission["trigger_write_attempt_count"],
                    0,
                )
                self.assertFalse(
                    admission["control_executed"]
                )
                self.assertFalse(
                    admission["traffic_executed"]
                )
                self.assertTrue(
                    stat.S_ISFIFO(fifo.stat().st_mode)
                )
            finally:
                stdout, stderr = stop_manager(manager)
            self.assertEqual(
                manager.returncode,
                0,
                stderr + stdout,
            )

    def test_admission_writes_no_trigger_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            runtime = root / "runtime"
            fifo = runtime / "actuator.fifo"
            marker = root / "unexpected-trigger"
            launch = root / "launch.json"
            write_launch(
                launch,
                reader_argv(marker),
            )
            manager = subprocess.Popen(
                command(runtime, fifo, launch),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={
                    **os.environ,
                    "PYTHONDONTWRITEBYTECODE": "1",
                },
            )
            try:
                wait_for_file(
                    runtime / "provider-admission.json",
                    manager,
                )
                time.sleep(0.25)
                self.assertFalse(marker.exists())
            finally:
                stdout, stderr = stop_manager(manager)
            self.assertEqual(
                manager.returncode,
                0,
                stderr + stdout,
            )

    def test_readiness_timeout_preserves_partial_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            runtime = root / "runtime"
            fifo = runtime / "actuator.fifo"
            launch = root / "launch.json"
            write_launch(
                launch,
                [
                    sys.executable,
                    "-c",
                    "import time;time.sleep(30)",
                    FIFO_TOKEN,
                ],
            )
            proc = run_once(
                *command(
                    runtime,
                    fifo,
                    launch,
                    timeout_ms="120",
                    poll_ms="20",
                )
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertTrue(runtime.is_dir())
            self.assertTrue(
                stat.S_ISFIFO(fifo.stat().st_mode)
            )
            failure = json.loads(
                (
                    runtime / "provider-failure.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(
                failure["failure_reason"],
                "READER_READINESS_TIMEOUT",
            )
            self.assertFalse(
                failure["runtime_paths_removed"]
            )
            self.assertEqual(
                failure["trigger_write_attempt_count"],
                0,
            )

    def test_child_exit_before_readiness_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            runtime = root / "runtime"
            fifo = runtime / "actuator.fifo"
            launch = root / "launch.json"
            write_launch(
                launch,
                [
                    sys.executable,
                    "-c",
                    "raise SystemExit(7)",
                    FIFO_TOKEN,
                ],
            )
            proc = run_once(
                *command(
                    runtime,
                    fifo,
                    launch,
                    timeout_ms="1000",
                    poll_ms="20",
                )
            )
            self.assertNotEqual(proc.returncode, 0)
            failure = json.loads(
                (
                    runtime / "provider-failure.json"
                ).read_text(encoding="utf-8")
            )
            self.assertTrue(
                failure["failure_reason"].startswith(
                    "PROVIDER_EXITED_BEFORE_READINESS:"
                )
            )
            self.assertEqual(
                failure["provider_restart_count"],
                0,
            )
            self.assertFalse(
                failure["automatic_retry"]
            )


if __name__ == "__main__":
    unittest.main()
