#!/usr/bin/env python3

import importlib.util
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


HERE = pathlib.Path(__file__).resolve().parent
SOURCE = (
    HERE.parent
    / "prompt12-production-provider-manager-launcher.py"
)

SPEC = importlib.util.spec_from_file_location(
    "prompt12_provider_manager_launcher",
    SOURCE,
)

module = importlib.util.module_from_spec(
    SPEC
)

SPEC.loader.exec_module(
    module
)


class ProviderManagerLauncherTests(
    unittest.TestCase
):
    def write_json(
        self,
        path,
        value,
    ):
        path.write_text(
            json.dumps(
                value,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    def create_provider_stub(
        self,
        root,
        *,
        mismatch=False,
        no_admission=False,
    ):
        path = root / "provider-stub.py"

        mismatch_literal = (
            "True"
            if mismatch
            else "False"
        )

        no_admission_literal = (
            "True"
            if no_admission
            else "False"
        )

        path.write_text(
            f"""#!/usr/bin/env python3
import argparse
import json
import os
import pathlib
import signal
import time

MISMATCH = {mismatch_literal}
NO_ADMISSION = {no_admission_literal}

parser = argparse.ArgumentParser()
sub = parser.add_subparsers(dest="command", required=True)
run = sub.add_parser("run")
run.add_argument("--runtime-root", required=True)
run.add_argument("--fifo-path", required=True)
run.add_argument("--provider-launch-json", required=True)
run.add_argument("--provider-identity", required=True)
run.add_argument("--readiness-timeout-ms", required=True)
run.add_argument("--readiness-poll-ms", required=True)
run.add_argument("--admission-authorization-token", required=True)
args = parser.parse_args()

root = pathlib.Path(args.runtime_root)
fifo = pathlib.Path(args.fifo_path)

root.mkdir(mode=0o750)
os.mkfifo(fifo, 0o600)

if NO_ADMISSION:
    while True:
        time.sleep(1)

boot = pathlib.Path(
    "/proc/sys/kernel/random/boot_id"
).read_text(encoding="utf-8").strip()

raw = pathlib.Path(
    f"/proc/{{os.getpid()}}/stat"
).read_text(encoding="utf-8")

rp = raw.rfind(")")
tail = raw[rp + 2:].split()
identity = f"{{boot}}:{{os.getpid()}}:{{tail[19]}}"

provider_identity = args.provider_identity

if MISMATCH:
    provider_identity = "wrong-provider-identity"

admission = {{
    "schema":
        "sci_oran_prompt12_persistent_prearmed_actuator_provider_admission_v1",
    "state": "ADMITTED",
    "execution_host": os.uname().nodename,
    "runtime_root": str(root),
    "fifo_path": str(fifo),
    "fifo_mode": "0600",
    "fifo_uid": fifo.stat().st_uid,
    "fifo_gid": fifo.stat().st_gid,
    "provider_identity": provider_identity,
    "provider_pid": os.getpid(),
    "provider_process_start_identity": identity,
    "provider_restart_count": 0,
    "provider_launch_argv_sha256": "stub",
    "reader_readiness_gate": "PASS",
    "readiness_method":
        "O_WRONLY_NONBLOCK_ZERO_BYTE_OPEN",
    "readiness_writer_fd_held": True,
    "trigger_write_attempt_count": 0,
    "trigger_write_success_count": 0,
    "control_executed": False,
    "traffic_executed": False,
    "admission_utc":
        "2099-01-01T00:00:00.000000Z",
}}

with (
    root / "provider-admission.json"
).open(
    "x",
    encoding="utf-8",
) as handle:
    json.dump(admission, handle)
    handle.write("\\n")

while True:
    time.sleep(1)
""",
            encoding="utf-8",
        )

        path.chmod(0o700)

        return path

    def create_fixture(
        self,
        root,
        *,
        timeout_ms=1000,
        poll_ms=20,
        mismatch=False,
        no_admission=False,
    ):
        runtime_root = (
            root
            / "prompt12-runtime-test"
        )

        fifo_path = (
            runtime_root
            / "actuator.fifo"
        )

        allocation = (
            root
            / "allocation.json"
        )

        launch = (
            root
            / "provider-launch.json"
        )

        frozen = (
            root
            / "frozen.json"
        )

        record = (
            root
            / "launcher-record.json"
        )

        provider = (
            self.create_provider_stub(
                root,
                mismatch=mismatch,
                no_admission=no_admission,
            )
        )

        self.write_json(
            allocation,
            {
                "schema":
                    "sci_oran_r6_prompt12_r01_prelaunch_allocation_v1",
                "experiment_id":
                    "EXP-20990101-DL-18000K-R01",
                "run_id":
                    "RUN-20990101T000000Z-001",
                "runtime_root":
                    str(runtime_root),
                "fifo_path":
                    str(fifo_path),
                "provider_identity":
                    "prompt12-provider-test",
                "r01_identity_allocated":
                    True,
                "runtime_root_created":
                    False,
                "fifo_created":
                    False,
                "provider_started":
                    False,
                "reader_started":
                    False,
                "runtime_profile_materialized":
                    False,
                "ratio_bindings_materialized":
                    False,
                "trigger_executed":
                    False,
                "control_executed":
                    False,
                "traffic_executed":
                    False,
            },
        )

        self.write_json(
            launch,
            [
                sys.executable,
                "-c",
                "import time;time.sleep(60)",
                module.FIFO_TOKEN,
            ],
        )

        self.write_json(
            frozen,
            {
                "timeline_readiness_timeout_ms":
                    timeout_ms,
                "timeline_readiness_poll_ms":
                    poll_ms,
            },
        )

        return {
            "runtime_root":
                runtime_root,
            "fifo_path":
                fifo_path,
            "allocation":
                allocation,
            "launch":
                launch,
            "frozen":
                frozen,
            "record":
                record,
            "provider":
                provider,
        }

    def command(
        self,
        fixture,
    ):
        return [
            sys.executable,
            str(SOURCE),
            "run",
            "--allocation-json",
            str(fixture["allocation"]),
            "--provider-launch-json",
            str(fixture["launch"]),
            "--frozen-config",
            str(fixture["frozen"]),
            "--provider-source",
            str(fixture["provider"]),
            "--launcher-record",
            str(fixture["record"]),
        ]

    def terminate_recorded_manager(
        self,
        record,
    ):
        if not record.is_file():
            return

        value = json.loads(
            record.read_text(
                encoding="utf-8"
            )
        )

        pid = value["manager_pid"]

        try:
            os.killpg(
                pid,
                signal.SIGTERM,
            )
        except ProcessLookupError:
            return

        deadline = (
            time.monotonic()
            + 2
        )

        while (
            time.monotonic()
            < deadline
        ):
            if not pathlib.Path(
                f"/proc/{pid}"
            ).exists():
                return

            time.sleep(0.02)

        try:
            os.killpg(
                pid,
                signal.SIGKILL,
            )
        except ProcessLookupError:
            pass

    def test_contract_boundary(self):
        proc = subprocess.run(
            [
                sys.executable,
                str(SOURCE),
                "contract",
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(
            proc.returncode,
            0,
            proc.stderr,
        )

        self.assertIn(
            "MANAGER_START_NEW_SESSION=YES",
            proc.stdout,
        )

        self.assertIn(
            "AUTOMATIC_RESTART=NO",
            proc.stdout,
        )

        self.assertIn(
            "TRIGGER_WRITE_CAPABILITY=ABSENT",
            proc.stdout,
        )

        self.assertIn(
            "PRB_CONTROL_CAPABILITY=ABSENT",
            proc.stdout,
        )

        self.assertIn(
            "TRAFFIC_CAPABILITY=ABSENT",
            proc.stdout,
        )

    def test_source_has_no_scientific_execution_capability(
        self,
    ):
        source = SOURCE.read_text(
            encoding="utf-8"
        )

        self.assertNotIn(
            "os.mkfifo",
            source,
        )

        self.assertNotIn(
            "os.write(",
            source,
        )

        self.assertNotIn(
            "SCI_ORAN_MAX_PRB_RATIO",
            source,
        )

        self.assertNotIn(
            "iperf",
            source.lower(),
        )

        self.assertNotIn(
            "subprocess.run([\"docker\"",
            source.lower(),
        )

        self.assertNotIn(
            "subprocess.popen([\"docker\"",
            source.lower(),
        )

        self.assertNotIn(
            "os.system(",
            source,
        )

        self.assertNotIn(
            "docker.from_env",
            source.lower(),
        )

        self.assertEqual(
            source.count(
                "subprocess.Popen("
            ),
            1,
        )

    def test_successful_launch_persists_manager_after_launcher_exit(
        self,
    ):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(
                temporary
            )

            fixture = self.create_fixture(
                root
            )

            try:
                proc = subprocess.run(
                    self.command(
                        fixture
                    ),
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )

                self.assertEqual(
                    proc.returncode,
                    0,
                    proc.stderr,
                )

                self.assertTrue(
                    fixture[
                        "record"
                    ].is_file()
                )

                record = json.loads(
                    fixture[
                        "record"
                    ].read_text(
                        encoding="utf-8"
                    )
                )

                manager_pid = (
                    record["manager_pid"]
                )

                self.assertTrue(
                    pathlib.Path(
                        f"/proc/{manager_pid}"
                    ).exists()
                )

                self.assertTrue(
                    fixture[
                        "runtime_root"
                    ].is_dir()
                )

                self.assertTrue(
                    stat.S_ISFIFO(
                        fixture[
                            "fifo_path"
                        ].stat().st_mode
                    )
                )

                self.assertEqual(
                    record[
                        "reader_readiness_gate"
                    ],
                    "PASS",
                )

                self.assertFalse(
                    record[
                        "automatic_restart"
                    ]
                )

                self.assertFalse(
                    record[
                        "control_executed"
                    ]
                )

                self.assertFalse(
                    record[
                        "traffic_executed"
                    ]
                )

            finally:
                self.terminate_recorded_manager(
                    fixture["record"]
                )

    def test_existing_runtime_root_fails_before_launch(
        self,
    ):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(
                temporary
            )

            fixture = self.create_fixture(
                root
            )

            fixture[
                "runtime_root"
            ].mkdir()

            proc = subprocess.run(
                self.command(
                    fixture
                ),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertNotEqual(
                proc.returncode,
                0,
            )

            self.assertIn(
                "RUNTIME_ROOT_ALREADY_EXISTS",
                proc.stderr,
            )

            self.assertFalse(
                fixture[
                    "record"
                ].exists()
            )

    def test_admission_identity_mismatch_fails_closed(
        self,
    ):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(
                temporary
            )

            fixture = self.create_fixture(
                root,
                mismatch=True,
            )

            proc = subprocess.run(
                self.command(
                    fixture
                ),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertNotEqual(
                proc.returncode,
                0,
            )

            self.assertIn(
                "PROVIDER_ADMISSION_PROVIDER_IDENTITY_MISMATCH",
                proc.stderr,
            )

            self.assertFalse(
                fixture[
                    "record"
                ].exists()
            )

    def test_admission_timeout_fails_closed(
        self,
    ):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(
                temporary
            )

            fixture = self.create_fixture(
                root,
                timeout_ms=120,
                poll_ms=20,
                no_admission=True,
            )

            proc = subprocess.run(
                self.command(
                    fixture
                ),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertNotEqual(
                proc.returncode,
                0,
            )

            self.assertIn(
                "PROVIDER_ADMISSION_TIMEOUT",
                proc.stderr,
            )

            self.assertFalse(
                fixture[
                    "record"
                ].exists()
            )


if __name__ == "__main__":
    unittest.main()
