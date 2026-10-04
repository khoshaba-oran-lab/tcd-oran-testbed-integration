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
HARNESS = HERE.parent
SCRIPT = HARNESS / "prompt12-stale-runtime-retirement.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "prompt12_stale_runtime_retirement",
        SCRIPT,
    )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MODULE = load_module()


def strong_identity(pid):
    boot_id = pathlib.Path(
        "/proc/sys/kernel/random/boot_id"
    ).read_text(
        encoding="utf-8"
    ).strip()

    text = pathlib.Path(
        f"/proc/{pid}/stat"
    ).read_text(
        encoding="utf-8"
    )

    right = text.rfind(")")
    fields = text[right + 2:].split()

    return (
        f"{boot_id}:{pid}:{fields[19]}"
    )


def absent_pid():
    candidate = 100000000

    while pathlib.Path(
        f"/proc/{candidate}"
    ).exists():
        candidate += 1

    return candidate


class RetirementTests(unittest.TestCase):

    def make_runtime(
        self,
        parent,
        pid,
        identity,
    ):
        root = (
            pathlib.Path(parent)
            / "prompt12-runtime-test"
        )

        root.mkdir()

        fifo = root / "actuator.fifo"
        os.mkfifo(fifo, 0o600)

        admission = {
            "schema":
                MODULE.ADMISSION_SCHEMA,
            "state": "ADMITTED",
            "runtime_root": str(root),
            "fifo_path": str(fifo),
            "provider_pid": pid,
            "provider_process_start_identity":
                identity,
            "provider_identity":
                "prompt12-provider-test",
        }

        (
            root
            / "provider-admission.json"
        ).write_text(
            json.dumps(
                admission,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

        (
            root
            / "provider.stdout.log"
        ).write_text(
            "preserve-evidence\n",
            encoding="utf-8",
        )

        return root

    def test_success_preserves_evidence_and_releases_source(self):
        with tempfile.TemporaryDirectory() as td:
            parent = pathlib.Path(td).resolve()
            pid = absent_pid()

            root = self.make_runtime(
                parent,
                pid,
                f"old-boot:{pid}:1",
            )

            retirement = (
                parent
                / "retirement-container"
            )

            result = MODULE.retire(
                str(root),
                str(retirement),
            )

            retired = (
                retirement
                / root.name
            )

            self.assertFalse(
                root.exists()
            )

            self.assertTrue(
                retired.is_dir()
            )

            self.assertEqual(
                (
                    retired
                    / "provider.stdout.log"
                ).read_text(
                    encoding="utf-8"
                ),
                "preserve-evidence\n",
            )

            self.assertTrue(
                stat.S_ISFIFO(
                    (
                        retired
                        / "actuator.fifo"
                    ).stat().st_mode
                )
            )

            self.assertTrue(
                result[
                    "recorded_provider_pid_absent"
                ]
            )

            self.assertEqual(
                result[
                    "live_runtime_reference_count"
                ],
                0,
            )

            self.assertTrue(
                result[
                    "source_path_released"
                ]
            )

            self.assertTrue(
                result[
                    "evidence_preserved"
                ]
            )

    def test_recorded_pid_live_fails_without_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            parent = pathlib.Path(td).resolve()

            root = self.make_runtime(
                parent,
                os.getpid(),
                strong_identity(
                    os.getpid()
                ),
            )

            retirement = (
                parent
                / "retirement-container"
            )

            with self.assertRaisesRegex(
                MODULE.RetirementError,
                "RECORDED_PROVIDER_PID_STILL_EXISTS",
            ):
                MODULE.retire(
                    str(root),
                    str(retirement),
                )

            self.assertTrue(
                root.is_dir()
            )

            self.assertFalse(
                retirement.exists()
            )

    def test_live_runtime_reference_fails_without_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            parent = pathlib.Path(td).resolve()
            pid = absent_pid()

            root = self.make_runtime(
                parent,
                pid,
                f"old-boot:{pid}:1",
            )

            retirement = (
                parent
                / "retirement-container"
            )

            process = subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    "import time; time.sleep(60)",
                    str(root),
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            try:
                time.sleep(0.1)

                with self.assertRaisesRegex(
                    MODULE.RetirementError,
                    "LIVE_RUNTIME_REFERENCE_PRESENT",
                ):
                    MODULE.retire(
                        str(root),
                        str(retirement),
                    )

                self.assertTrue(
                    root.is_dir()
                )

                self.assertFalse(
                    retirement.exists()
                )

            finally:
                process.terminate()

                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)

    def test_existing_retirement_root_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            parent = pathlib.Path(td).resolve()
            pid = absent_pid()

            root = self.make_runtime(
                parent,
                pid,
                f"old-boot:{pid}:1",
            )

            retirement = (
                parent
                / "retirement-container"
            )

            retirement.mkdir()

            with self.assertRaisesRegex(
                MODULE.RetirementError,
                "RETIREMENT_ROOT_ALREADY_EXISTS",
            ):
                MODULE.retire(
                    str(root),
                    str(retirement),
                )

            self.assertTrue(
                root.is_dir()
            )

    def test_retirement_root_must_be_sibling(self):
        with tempfile.TemporaryDirectory() as td:
            parent = pathlib.Path(td).resolve()
            pid = absent_pid()

            root = self.make_runtime(
                parent,
                pid,
                f"old-boot:{pid}:1",
            )

            elsewhere = (
                parent
                / "elsewhere"
            )
            elsewhere.mkdir()

            retirement = (
                elsewhere
                / "retirement-container"
            )

            with self.assertRaisesRegex(
                MODULE.RetirementError,
                "RETIREMENT_ROOT_NOT_SIBLING",
            ):
                MODULE.retire(
                    str(root),
                    str(retirement),
                )

            self.assertTrue(
                root.is_dir()
            )

    def test_source_has_no_deletion_or_process_control(self):
        text = SCRIPT.read_text(
            encoding="utf-8"
        )

        forbidden = [
            "shutil.rmtree",
            ".unlink(",
            "os.remove(",
            "os.rmdir(",
            "os.kill",
            "signal.",
            "subprocess",
            "pkill",
            "killall",
            "docker ",
            "shell=True",
        ]

        for token in forbidden:
            with self.subTest(
                token=token
            ):
                self.assertNotIn(
                    token,
                    text,
                )

        self.assertIn(
            "os.rename(",
            text,
        )

    def test_schema_exact(self):
        self.assertEqual(
            MODULE.SCHEMA,
            "sci_oran_prompt12_v2_stale_runtime_retirement_v1",
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
