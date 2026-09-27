#!/usr/bin/env python3

import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest


HERE = pathlib.Path(__file__).resolve().parent
IMPL = (
    HERE.parent
    / "prompt12-production-fifo-path-materializer.py"
)

SPEC = importlib.util.spec_from_file_location(
    "prompt12_production_fifo_path_materializer",
    IMPL,
)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class FifoPathMaterializerTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.parent = pathlib.Path(
            self.tmp.name
        ).resolve()
        self.runtime_root = (
            self.parent
            / "prompt12-runtime-test"
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_script_exists(self):
        self.assertTrue(IMPL.is_file())

    def test_script_is_executable(self):
        self.assertTrue(
            os.access(IMPL, os.X_OK)
        )

    def test_schema_exact(self):
        self.assertEqual(
            MOD.SCHEMA,
            "sci_oran_prompt12_v2_production_fifo_path_materializer_v1",
        )

    def test_fifo_name_exact(self):
        self.assertEqual(
            MOD.FIFO_NAME,
            "actuator.fifo",
        )

    def test_valid_runtime_root_yields_exact_fifo_path(self):
        value = MOD.materialize_fifo_path(
            str(self.runtime_root)
        )

        self.assertEqual(
            value,
            str(
                self.runtime_root
                / "actuator.fifo"
            ),
        )

    def test_output_is_absolute(self):
        value = pathlib.Path(
            MOD.materialize_fifo_path(
                str(self.runtime_root)
            )
        )

        self.assertTrue(value.is_absolute())

    def test_output_is_direct_child_of_runtime_root(self):
        value = pathlib.Path(
            MOD.materialize_fifo_path(
                str(self.runtime_root)
            )
        )

        self.assertEqual(
            value.parent,
            self.runtime_root,
        )

    def test_empty_runtime_root_rejected(self):
        with self.assertRaises(
            MOD.MaterializerError
        ):
            MOD.materialize_fifo_path("")

    def test_whitespace_runtime_root_rejected(self):
        with self.assertRaises(
            MOD.MaterializerError
        ):
            MOD.materialize_fifo_path("   ")

    def test_relative_runtime_root_rejected(self):
        with self.assertRaises(
            MOD.MaterializerError
        ):
            MOD.materialize_fifo_path(
                "prompt12-runtime-test"
            )

    def test_filesystem_root_rejected(self):
        with self.assertRaises(
            MOD.MaterializerError
        ):
            MOD.materialize_fifo_path("/")

    def test_parent_escape_structure_rejected(self):
        value = (
            str(self.parent)
            + "/child/../runtime"
        )

        with self.assertRaises(
            MOD.MaterializerError
        ):
            MOD.materialize_fifo_path(value)

    def test_existing_derived_fifo_path_rejected(self):
        self.runtime_root.mkdir()

        fifo = (
            self.runtime_root
            / "actuator.fifo"
        )
        fifo.write_text(
            "occupied",
            encoding="utf-8",
        )

        with self.assertRaises(
            MOD.MaterializerError
        ):
            MOD.materialize_fifo_path(
                str(self.runtime_root)
            )

    def test_materializer_does_not_create_runtime_root(self):
        self.assertFalse(
            self.runtime_root.exists()
        )

        MOD.materialize_fifo_path(
            str(self.runtime_root)
        )

        self.assertFalse(
            self.runtime_root.exists()
        )

    def test_materializer_does_not_create_fifo_path(self):
        fifo = (
            self.runtime_root
            / "actuator.fifo"
        )

        MOD.materialize_fifo_path(
            str(self.runtime_root)
        )

        self.assertFalse(
            os.path.lexists(str(fifo))
        )

    def test_cli_missing_runtime_root_fails(self):
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(IMPL),
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(
            proc.returncode,
            0,
        )

    def test_cli_empty_runtime_root_fails(self):
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(IMPL),
                "--runtime-root",
                "",
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(
            proc.returncode,
            0,
        )

    def test_cli_relative_runtime_root_fails(self):
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(IMPL),
                "--runtime-root",
                "relative-root",
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(
            proc.returncode,
            0,
        )

    def test_cli_unexpected_positional_argument_fails(self):
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(IMPL),
                "--runtime-root",
                str(self.runtime_root),
                "unexpected",
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(
            proc.returncode,
            0,
        )

    def test_cli_unexpected_option_fails(self):
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(IMPL),
                "--runtime-root",
                str(self.runtime_root),
                "--unexpected",
                "value",
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(
            proc.returncode,
            0,
        )

    def test_cli_success_returns_exact_json_shape(self):
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(IMPL),
                "--runtime-root",
                str(self.runtime_root),
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(
            proc.returncode,
            0,
            proc.stderr,
        )

        payload = json.loads(
            proc.stdout
        )

        self.assertEqual(
            list(payload.keys()),
            ["fifo_path"],
        )

        self.assertEqual(
            payload["fifo_path"],
            str(
                self.runtime_root
                / "actuator.fifo"
            ),
        )

    def test_cli_success_creates_nothing(self):
        fifo = (
            self.runtime_root
            / "actuator.fifo"
        )

        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(IMPL),
                "--runtime-root",
                str(self.runtime_root),
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(
            proc.returncode,
            0,
            proc.stderr,
        )

        self.assertFalse(
            self.runtime_root.exists()
        )

        self.assertFalse(
            os.path.lexists(str(fifo))
        )

    def test_source_has_no_directory_creation_api(self):
        source = IMPL.read_text(
            encoding="utf-8"
        )

        forbidden = [
            "os.mkdir(",
            "os.makedirs(",
            ".mkdir(",
        ]

        for token in forbidden:
            self.assertNotIn(
                token,
                source,
            )

    def test_source_has_no_fifo_creation_api(self):
        source = IMPL.read_text(
            encoding="utf-8"
        )

        self.assertNotIn(
            "os.mkfifo(",
            source,
        )

    def test_source_has_no_touch_api(self):
        source = IMPL.read_text(
            encoding="utf-8"
        )

        self.assertNotIn(
            ".touch(",
            source,
        )

    def test_source_has_no_tempfile_allocation(self):
        source = IMPL.read_text(
            encoding="utf-8"
        )

        self.assertNotIn(
            "tempfile",
            source,
        )

    def test_source_has_no_process_execution_api(self):
        source = IMPL.read_text(
            encoding="utf-8"
        )

        forbidden = [
            "import subprocess",
            "subprocess.",
            "os.system(",
            "os.popen(",
            "execv(",
            "execve(",
            "spawn",
        ]

        for token in forbidden:
            self.assertNotIn(
                token,
                source,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
