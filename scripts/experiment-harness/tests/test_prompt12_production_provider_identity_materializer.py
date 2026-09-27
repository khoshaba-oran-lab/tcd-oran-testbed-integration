#!/usr/bin/env python3

import hashlib
import importlib.util
import json
import pathlib
import re
import subprocess
import sys
import unittest


HERE = pathlib.Path(__file__).resolve().parent
HARNESS = HERE.parent

SCRIPT = (
    HARNESS
    / "prompt12-production-provider-identity-materializer.py"
)

RUNTIME_MATERIALIZER = (
    HARNESS
    / "prompt12-production-runtime-root-materializer.py"
)

PROVIDER = (
    HARNESS
    / "prompt12-persistent-prearmed-actuator-provider.py"
)


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


MODULE = load_module(
    SCRIPT,
    "prompt12_provider_identity_materializer",
)

RUNTIME_MODULE = load_module(
    RUNTIME_MATERIALIZER,
    "prompt12_runtime_root_materializer",
)


class ProviderIdentityMaterializerTests(unittest.TestCase):
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

    def test_script_exists(self):
        self.assertTrue(SCRIPT.is_file())

    def test_schema_exact(self):
        self.assertEqual(
            MODULE.SCHEMA,
            "sci_oran_prompt12_v2_production_"
            "provider_identity_materializer_v1",
        )

    def test_prefix_exact(self):
        self.assertEqual(
            MODULE.PREFIX,
            "prompt12-provider-",
        )

    def test_known_derivation_exact(self):
        experiment_id = "EXP-TEST-001"
        run_id = "RUN-TEST-001"

        payload = (
            experiment_id.encode("utf-8")
            + b"\x00"
            + run_id.encode("utf-8")
        )

        expected = (
            "prompt12-provider-"
            + hashlib.sha256(payload).hexdigest()[:32]
        )

        actual = MODULE.deterministic_provider_identity(
            experiment_id,
            run_id,
        )

        self.assertEqual(actual, expected)

    def test_same_inputs_same_identity(self):
        a = MODULE.deterministic_provider_identity(
            "EXP-A",
            "RUN-A",
        )
        b = MODULE.deterministic_provider_identity(
            "EXP-A",
            "RUN-A",
        )

        self.assertEqual(a, b)

    def test_different_experiment_changes_identity(self):
        a = MODULE.deterministic_provider_identity(
            "EXP-A",
            "RUN-A",
        )
        b = MODULE.deterministic_provider_identity(
            "EXP-B",
            "RUN-A",
        )

        self.assertNotEqual(a, b)

    def test_different_run_changes_identity(self):
        a = MODULE.deterministic_provider_identity(
            "EXP-A",
            "RUN-A",
        )
        b = MODULE.deterministic_provider_identity(
            "EXP-A",
            "RUN-B",
        )

        self.assertNotEqual(a, b)

    def test_identity_length_exact(self):
        value = MODULE.deterministic_provider_identity(
            "EXP-A",
            "RUN-A",
        )

        self.assertEqual(len(value), 50)

    def test_identity_suffix_is_lowercase_hex(self):
        value = MODULE.deterministic_provider_identity(
            "EXP-A",
            "RUN-A",
        )

        suffix = value.removeprefix(
            "prompt12-provider-"
        )

        self.assertRegex(
            suffix,
            r"^[0-9a-f]{32}$",
        )

    def test_identity_matches_provider_pattern(self):
        value = MODULE.deterministic_provider_identity(
            "EXP-A",
            "RUN-A",
        )

        self.assertRegex(
            value,
            r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$",
        )

    def test_provider_source_pattern_still_exact(self):
        text = PROVIDER.read_text(encoding="utf-8")

        self.assertIn(
            'IDENTITY_PATTERN = '
            're.compile(r"^[A-Za-z0-9]'
            '[A-Za-z0-9._-]{0,127}$")',
            text,
        )

    def test_reuses_runtime_digest_convention(self):
        experiment_id = "EXP-A"
        run_id = "RUN-A"

        provider_identity = (
            MODULE.deterministic_provider_identity(
                experiment_id,
                run_id,
            )
        )

        runtime_leaf = (
            RUNTIME_MODULE.deterministic_leaf(
                experiment_id,
                run_id,
            )
        )

        self.assertEqual(
            provider_identity.removeprefix(
                "prompt12-provider-"
            ),
            runtime_leaf.removeprefix(
                "prompt12-runtime-"
            ),
        )

    def test_empty_experiment_rejected(self):
        with self.assertRaises(MODULE.ContractError):
            MODULE.deterministic_provider_identity(
                "",
                "RUN-A",
            )

    def test_whitespace_experiment_rejected(self):
        with self.assertRaises(MODULE.ContractError):
            MODULE.deterministic_provider_identity(
                "   ",
                "RUN-A",
            )

    def test_empty_run_rejected(self):
        with self.assertRaises(MODULE.ContractError):
            MODULE.deterministic_provider_identity(
                "EXP-A",
                "",
            )

    def test_whitespace_run_rejected(self):
        with self.assertRaises(MODULE.ContractError):
            MODULE.deterministic_provider_identity(
                "EXP-A",
                "   ",
            )

    def test_nonstring_experiment_rejected(self):
        with self.assertRaises(MODULE.ContractError):
            MODULE.deterministic_provider_identity(
                123,
                "RUN-A",
            )

    def test_nonstring_run_rejected(self):
        with self.assertRaises(MODULE.ContractError):
            MODULE.deterministic_provider_identity(
                "EXP-A",
                123,
            )

    def test_materializer_exact_shape(self):
        result = MODULE.materialize_provider_identity(
            "EXP-A",
            "RUN-A",
        )

        self.assertEqual(
            set(result),
            {
                "schema",
                "provider_identity",
            },
        )

    def test_cli_success_exact_json_shape(self):
        completed = self.cli(
            "--experiment-id",
            "EXP-A",
            "--run-id",
            "RUN-A",
        )

        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stderr, "")

        value = json.loads(completed.stdout)

        self.assertEqual(
            set(value),
            {
                "schema",
                "provider_identity",
            },
        )

        self.assertEqual(
            value["schema"],
            MODULE.SCHEMA,
        )

        self.assertEqual(
            value["provider_identity"],
            MODULE.deterministic_provider_identity(
                "EXP-A",
                "RUN-A",
            ),
        )

    def test_cli_empty_experiment_fails(self):
        completed = self.cli(
            "--experiment-id",
            "",
            "--run-id",
            "RUN-A",
        )

        self.assertEqual(completed.returncode, 2)
        self.assertIn(
            "ERROR=EXPERIMENT_ID_EMPTY",
            completed.stderr,
        )

    def test_cli_empty_run_fails(self):
        completed = self.cli(
            "--experiment-id",
            "EXP-A",
            "--run-id",
            "",
        )

        self.assertEqual(completed.returncode, 2)
        self.assertIn(
            "ERROR=RUN_ID_EMPTY",
            completed.stderr,
        )

    def test_cli_missing_experiment_fails(self):
        completed = self.cli(
            "--run-id",
            "RUN-A",
        )

        self.assertNotEqual(completed.returncode, 0)

    def test_cli_missing_run_fails(self):
        completed = self.cli(
            "--experiment-id",
            "EXP-A",
        )

        self.assertNotEqual(completed.returncode, 0)

    def test_cli_unexpected_option_fails(self):
        completed = self.cli(
            "--experiment-id",
            "EXP-A",
            "--run-id",
            "RUN-A",
            "--unexpected",
            "value",
        )

        self.assertNotEqual(completed.returncode, 0)

    def test_cli_unexpected_positional_fails(self):
        completed = self.cli(
            "--experiment-id",
            "EXP-A",
            "--run-id",
            "RUN-A",
            "unexpected",
        )

        self.assertNotEqual(completed.returncode, 0)

    def test_source_has_no_runtime_or_mutation_api(self):
        text = SCRIPT.read_text(encoding="utf-8")

        forbidden = [
            "import os",
            "from os ",
            "import pathlib",
            "import subprocess",
            "import time",
            "import datetime",
            "import random",
            "import uuid",
            "/proc/",
            "os.getpid",
            "Popen(",
            "mkfifo(",
            "mkdir(",
            "makedirs(",
            "unlink(",
            "remove(",
            "rename(",
        ]

        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
