#!/usr/bin/env python3

import importlib.util
import json
import os
import pathlib
import signal
import subprocess
import sys
import tempfile
import time
import unittest


HERE = pathlib.Path(__file__).resolve().parent
HARNESS = HERE.parent
SCRIPT = HARNESS / "prompt12-production-cleanup.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "prompt12_cleanup",
        SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MODULE = load_module()


def strong_identity(pid):
    boot_id = pathlib.Path(
        "/proc/sys/kernel/random/boot_id"
    ).read_text(encoding="utf-8").strip()

    text = pathlib.Path(
        f"/proc/{pid}/stat"
    ).read_text(encoding="utf-8")

    right = text.rfind(")")
    fields = text[right + 2:].split()

    return f"{boot_id}:{pid}:{fields[19]}"


class CleanupTests(unittest.TestCase):
    def make_runtime(self, pid, identity):
        td = tempfile.TemporaryDirectory()
        root = pathlib.Path(td.name).resolve()

        admission = {
            "schema":
                MODULE.ADMISSION_SCHEMA,
            "provider_pid": pid,
            "provider_process_start_identity":
                identity,
        }

        (root / "provider-admission.json").write_text(
            json.dumps(admission),
            encoding="utf-8",
        )

        # Evidence that cleanup must preserve.
        (root / "evidence.txt").write_text(
            "preserve",
            encoding="utf-8",
        )

        os.mkfifo(root / "actuator.fifo")

        return td, root

    def start_target(self):
        return subprocess.Popen(
            [
                sys.executable,
                "-c",
                (
                    "import signal,time,sys;"
                    "signal.signal("
                    "signal.SIGTERM,"
                    "lambda *_: sys.exit(0));"
                    "time.sleep(60)"
                ),
            ],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def terminate_if_needed(self, process):
        if process.poll() is None:
            try:
                os.killpg(
                    process.pid,
                    signal.SIGKILL,
                )
            except ProcessLookupError:
                pass
            process.wait(timeout=5)

    def test_success_terminates_exact_group_and_preserves_evidence(self):
        process = self.start_target()

        try:
            identity = strong_identity(process.pid)
            td, root = self.make_runtime(
                process.pid,
                identity,
            )

            try:
                result = MODULE.cleanup(str(root))

                process.wait(timeout=5)

                self.assertEqual(
                    result["termination"],
                    "SIGTERM",
                )
                self.assertTrue(
                    result["runtime_root_preserved"]
                )
                self.assertTrue(
                    result["fifo_preserved"]
                )
                self.assertTrue(
                    result["evidence_preserved"]
                )

                self.assertTrue(root.is_dir())
                self.assertTrue(
                    (root / "actuator.fifo").exists()
                )
                self.assertEqual(
                    (root / "evidence.txt").read_text(
                        encoding="utf-8"
                    ),
                    "preserve",
                )
            finally:
                td.cleanup()
        finally:
            self.terminate_if_needed(process)

    def test_wait_until_gone_accepts_matching_zombie(self):
        process = subprocess.Popen(
            [
                sys.executable,
                "-c",
                "pass",
            ],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        try:
            identity = strong_identity(process.pid)

            deadline = time.monotonic() + 5.0
            observed_state = None

            while time.monotonic() < deadline:
                snapshot = MODULE.read_process_snapshot(
                    process.pid
                )

                if snapshot is None:
                    self.fail(
                        "child disappeared before parent reap"
                    )

                observed_state = snapshot["state"]

                if observed_state == "Z":
                    break

                time.sleep(0.01)

            self.assertEqual(
                observed_state,
                "Z",
            )

            self.assertTrue(
                MODULE.wait_until_gone(
                    process.pid,
                    identity,
                    500,
                )
            )
        finally:
            process.wait(timeout=5)

    def test_identity_mismatch_fails_without_signal(self):
        process = self.start_target()

        try:
            td, root = self.make_runtime(
                process.pid,
                "invalid:identity:value",
            )

            try:
                with self.assertRaises(
                    MODULE.CleanupError
                ):
                    MODULE.cleanup(str(root))

                self.assertIsNone(process.poll())
            finally:
                td.cleanup()
        finally:
            self.terminate_if_needed(process)

    def test_missing_admission_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td).resolve()

            with self.assertRaises(
                MODULE.CleanupError
            ):
                MODULE.cleanup(str(root))

    def test_relative_runtime_root_rejected(self):
        with self.assertRaises(
            MODULE.CleanupError
        ):
            MODULE.canonical_existing_directory(
                "relative/path"
            )

    def test_cli_missing_runtime_root_fails(self):
        completed = subprocess.run(
            [sys.executable, str(SCRIPT)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

        self.assertNotEqual(
            completed.returncode,
            0,
        )

    def test_source_has_no_artifact_deletion_or_broad_kill(self):
        text = SCRIPT.read_text(encoding="utf-8")

        forbidden = [
            "shutil.rmtree",
            ".unlink(",
            "os.remove(",
            "os.rmdir(",
            "os.system(",
            "shell=True",
            "pkill",
            "killall",
            "docker ",
            "docker compose",
        ]

        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, text)

    def test_cleanup_schema_exact(self):
        self.assertEqual(
            MODULE.SCHEMA,
            "sci_oran_prompt12_v2_production_cleanup_v1",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
