#!/usr/bin/env python3

import importlib.util
import json
import pathlib
import subprocess
import sys
import unittest


HERE = pathlib.Path(__file__).resolve().parent
HARNESS = HERE.parent

SCRIPT = (
    HARNESS
    / "prompt12-production-cleanup-argv-materializer.py"
)

CLEANUP = (
    HARNESS
    / "prompt12-production-cleanup.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "prompt12_cleanup_argv_materializer",
        SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MODULE = load_module()


class CleanupArgvMaterializerTests(unittest.TestCase):
    def cli(self, *args):
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                *args,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

    def test_schema_exact(self):
        self.assertEqual(
            MODULE.SCHEMA,
            "sci_oran_prompt12_v2_production_"
            "cleanup_argv_materializer_v1",
        )

    def test_exact_argv(self):
        root = "/home/khoshaba/sci-oran/prompt12-runtime-test"

        value = MODULE.materialize_cleanup_argv(
            root
        )

        self.assertEqual(
            value,
            {
                "schema": MODULE.SCHEMA,
                "cleanup_argv": [
                    str(CLEANUP.resolve()),
                    "--runtime-root",
                    root,
                ],
            },
        )

    def test_relative_runtime_root_rejected(self):
        with self.assertRaises(
            MODULE.ContractError
        ):
            MODULE.materialize_cleanup_argv(
                "relative/path"
            )

    def test_empty_runtime_root_rejected(self):
        with self.assertRaises(
            MODULE.ContractError
        ):
            MODULE.materialize_cleanup_argv("")

    def test_filesystem_root_rejected(self):
        with self.assertRaises(
            MODULE.ContractError
        ):
            MODULE.materialize_cleanup_argv("/")

    def test_parent_escape_rejected(self):
        with self.assertRaises(
            MODULE.ContractError
        ):
            MODULE.materialize_cleanup_argv(
                "/home/khoshaba/../escape"
            )

    def test_cli_success(self):
        root = "/home/khoshaba/sci-oran/prompt12-runtime-test"

        completed = self.cli(
            "--runtime-root",
            root,
        )

        self.assertEqual(completed.returncode, 0)

        value = json.loads(completed.stdout)

        self.assertEqual(
            value["cleanup_argv"],
            [
                str(CLEANUP.resolve()),
                "--runtime-root",
                root,
            ],
        )

    def test_cli_missing_runtime_root_fails(self):
        completed = self.cli()

        self.assertNotEqual(
            completed.returncode,
            0,
        )

    def test_cli_unexpected_input_fails(self):
        completed = self.cli(
            "--runtime-root",
            "/home/khoshaba/sci-oran/run",
            "--unexpected",
            "x",
        )

        self.assertNotEqual(
            completed.returncode,
            0,
        )

    def test_source_has_no_process_execution(self):
        text = SCRIPT.read_text(encoding="utf-8")

        forbidden = [
            "subprocess",
            "os.system",
            "Popen(",
            "shell=True",
        ]

        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
