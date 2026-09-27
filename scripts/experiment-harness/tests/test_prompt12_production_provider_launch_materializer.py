#!/usr/bin/env python3

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve()
MODULE_PATH = HERE.parents[1] / (
    "prompt12-production-provider-launch-materializer.py"
)

SPEC = importlib.util.spec_from_file_location(
    "prompt12_production_provider_launch_materializer",
    MODULE_PATH,
)

if SPEC is None or SPEC.loader is None:
    raise RuntimeError("failed to load materializer module")

materializer = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = materializer
SPEC.loader.exec_module(materializer)


class ProductionProviderLaunchMaterializerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)

        self.reader = root / "reader"
        self.wrapper = root / "wrapper"

        self.reader.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        self.wrapper.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")

        self.reader.chmod(0o755)
        self.wrapper.chmod(0o755)

        self.old_reader = materializer.READER_PATH
        self.old_wrapper = materializer.WRAPPER_PATH

        materializer.READER_PATH = self.reader
        materializer.WRAPPER_PATH = self.wrapper

        self.paths = [
            "/runtime/bindings/t1.json",
            "/runtime/bindings/t2.json",
            "/runtime/bindings/t3.json",
            "/runtime/bindings/t4.json",
            "/runtime/bindings/t5.json",
            "/runtime/bindings/t6.json",
        ]

    def tearDown(self):
        materializer.READER_PATH = self.old_reader
        materializer.WRAPPER_PATH = self.old_wrapper
        self.tmp.cleanup()

    def build(self, **overrides):
        values = {
            "experiment_id": "exp-001",
            "run_id": "run-001",
            "fifo_path": "/runtime/provider.fifo",
            "ratio_binding_paths": list(self.paths),
        }
        values.update(overrides)
        return materializer.build_provider_launch_argv(**values)

    def test_01_valid_contract_constructs_exact_argv(self):
        result = self.build()

        self.assertEqual(
            result,
            [
                str(self.reader),
                "--fifo-path",
                "/runtime/provider.fifo",
                "--actuator-argv-json",
                json.dumps([str(self.wrapper)], separators=(",", ":")),
                "--experiment-id",
                "exp-001",
                "--run-id",
                "run-001",
                "--ratio-binding-paths-json",
                json.dumps(self.paths, separators=(",", ":")),
            ],
        )

    def test_02_ratio_binding_order_is_preserved(self):
        result = self.build()
        encoded = result[result.index("--ratio-binding-paths-json") + 1]
        self.assertEqual(json.loads(encoded), self.paths)

    def test_03_actuator_argv_contains_only_wrapper(self):
        result = self.build()
        encoded = result[result.index("--actuator-argv-json") + 1]
        self.assertEqual(json.loads(encoded), [str(self.wrapper)])

    def test_04_empty_experiment_id_fails_closed(self):
        with self.assertRaises(materializer.ContractError):
            self.build(experiment_id="")

    def test_05_whitespace_experiment_id_fails_closed(self):
        with self.assertRaises(materializer.ContractError):
            self.build(experiment_id="   ")

    def test_06_empty_run_id_fails_closed(self):
        with self.assertRaises(materializer.ContractError):
            self.build(run_id="")

    def test_07_whitespace_run_id_fails_closed(self):
        with self.assertRaises(materializer.ContractError):
            self.build(run_id="\t")

    def test_08_empty_fifo_path_fails_closed(self):
        with self.assertRaises(materializer.ContractError):
            self.build(fifo_path="")

    def test_09_relative_fifo_path_fails_closed(self):
        with self.assertRaises(materializer.ContractError):
            self.build(fifo_path="runtime/provider.fifo")

    def test_10_ratio_binding_paths_must_be_list(self):
        with self.assertRaises(materializer.ContractError):
            self.build(ratio_binding_paths="not-a-list")

    def test_11_five_ratio_binding_paths_fail_closed(self):
        with self.assertRaises(materializer.ContractError):
            self.build(ratio_binding_paths=self.paths[:5])

    def test_12_seven_ratio_binding_paths_fail_closed(self):
        with self.assertRaises(materializer.ContractError):
            self.build(ratio_binding_paths=self.paths + ["/runtime/bindings/t7.json"])

    def test_13_empty_ratio_binding_path_fails_closed(self):
        paths = list(self.paths)
        paths[2] = ""
        with self.assertRaises(materializer.ContractError):
            self.build(ratio_binding_paths=paths)

    def test_14_whitespace_ratio_binding_path_fails_closed(self):
        paths = list(self.paths)
        paths[2] = "   "
        with self.assertRaises(materializer.ContractError):
            self.build(ratio_binding_paths=paths)

    def test_15_relative_ratio_binding_path_fails_closed(self):
        paths = list(self.paths)
        paths[2] = "runtime/bindings/t3.json"
        with self.assertRaises(materializer.ContractError):
            self.build(ratio_binding_paths=paths)

    def test_16_non_string_ratio_binding_path_fails_closed(self):
        paths = list(self.paths)
        paths[2] = 3
        with self.assertRaises(materializer.ContractError):
            self.build(ratio_binding_paths=paths)

    def test_17_missing_reader_fails_closed(self):
        self.reader.unlink()
        with self.assertRaises(materializer.ContractError):
            self.build()

    def test_18_non_executable_reader_fails_closed(self):
        self.reader.chmod(0o644)
        with self.assertRaises(materializer.ContractError):
            self.build()

    def test_19_missing_wrapper_fails_closed(self):
        self.wrapper.unlink()
        with self.assertRaises(materializer.ContractError):
            self.build()

    def test_20_non_executable_wrapper_fails_closed(self):
        self.wrapper.chmod(0o644)
        with self.assertRaises(materializer.ContractError):
            self.build()

    def test_21_cli_missing_required_input_fails_closed(self):
        parser = materializer.build_parser()

        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                parser.parse_args([])

        self.assertEqual(raised.exception.code, 2)

    def test_22_cli_unexpected_extra_input_fails_closed(self):
        parser = materializer.build_parser()

        argv = [
            "--experiment-id", "exp-001",
            "--run-id", "run-001",
            "--fifo-path", "/runtime/provider.fifo",
            "--ratio-binding-paths-json", json.dumps(self.paths),
            "--unexpected-input", "value",
        ]

        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                parser.parse_args(argv)

        self.assertEqual(raised.exception.code, 2)

    def test_23_malformed_ratio_binding_json_fails_closed(self):
        stderr = io.StringIO()
        stdout = io.StringIO()

        argv = [
            "--experiment-id", "exp-001",
            "--run-id", "run-001",
            "--fifo-path", "/runtime/provider.fifo",
            "--ratio-binding-paths-json", "{bad-json",
        ]

        with contextlib.redirect_stdout(stdout):
            with contextlib.redirect_stderr(stderr):
                rc = materializer.main(argv)

        self.assertEqual(rc, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("ERROR=", stderr.getvalue())

    def test_24_main_outputs_json_compatible_list_only(self):
        stdout = io.StringIO()
        stderr = io.StringIO()

        argv = [
            "--experiment-id", "exp-001",
            "--run-id", "run-001",
            "--fifo-path", "/runtime/provider.fifo",
            "--ratio-binding-paths-json", json.dumps(self.paths),
        ]

        with contextlib.redirect_stdout(stdout):
            with contextlib.redirect_stderr(stderr):
                rc = materializer.main(argv)

        self.assertEqual(rc, 0)
        self.assertEqual(stderr.getvalue(), "")

        result = json.loads(stdout.getvalue())
        self.assertIsInstance(result, list)
        self.assertEqual(result[0], str(self.reader))

    def test_25_no_implicit_default_for_required_cli_inputs(self):
        parser = materializer.build_parser()

        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                parser.parse_args(
                    [
                        "--experiment-id", "exp-001",
                        "--run-id", "run-001",
                        "--fifo-path", "/runtime/provider.fifo",
                    ]
                )

    def test_26_source_has_no_process_execution_api(self):
        source = MODULE_PATH.read_text(encoding="utf-8")

        forbidden = (
            "import subprocess",
            "from subprocess",
            "os.system(",
            "os.exec",
            "os.spawn",
        )

        for token in forbidden:
            self.assertNotIn(token, source)

    def test_27_contract_schema_is_exact(self):
        self.assertEqual(
            materializer.CONTRACT_SCHEMA,
            "sci_oran_prompt12_v2_production_provider_launch_materializer_contract_v1",
        )

    def test_28_static_paths_name_only_production_components(self):
        self.assertEqual(
            self.old_reader.name,
            "prompt12-production-local-fifo-reader.py",
        )
        self.assertEqual(
            self.old_wrapper.name,
            "prompt12-production-actuator-wrapper.py",
        )


if __name__ == "__main__":
    unittest.main()
