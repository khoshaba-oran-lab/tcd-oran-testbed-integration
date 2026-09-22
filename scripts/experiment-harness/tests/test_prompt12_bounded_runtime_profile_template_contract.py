#!/usr/bin/env python3

import ast
import collections
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest


HARNESS = pathlib.Path(__file__).resolve().parents[1]
REPOSITORY = HARNESS.parents[1]
BUILDER = pathlib.Path(
    os.environ.get(
        "PROMPT12_TEST_BINDING_BUILDER",
        str(HARNESS / "prompt12-bounded-production-binding-builder.py"),
    )
)
CONTRACT = pathlib.Path(
    os.environ.get(
        "PROMPT12_TEST_PROFILE_TEMPLATE_CONTRACT",
        str(
            REPOSITORY
            / "experiments"
            / "manifests"
            / "prompt12-bounded-sequence-runtime-profile-template-contract-v1.json"
        ),
    )
)


def builder_profile_keys():
    source = BUILDER.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(BUILDER))
    values = []
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "PROFILE_KEYS":
                values.append(ast.literal_eval(node.value))
    if len(values) != 1:
        raise AssertionError("PROFILE_KEYS assignment count invalid")
    return set(values[0])


def load_contract():
    with CONTRACT.open(encoding="utf-8") as handle:
        return json.load(handle)


class RuntimeProfileTemplateContractTests(unittest.TestCase):
    def test_contract_is_non_executable_and_unauthorised(self):
        value = load_contract()
        self.assertEqual(
            value["schema"],
            "sci_oran_prompt12_bounded_sequence_runtime_profile_template_contract_v1",
        )
        self.assertEqual(
            value["target_profile_schema"],
            "sci_oran_prompt12_bounded_sequence_runtime_profile_v1",
        )
        self.assertIs(value["executable"], False)
        self.assertIs(value["concrete_profile"], False)
        self.assertTrue(all(flag is False for flag in value["guards"].values()))

    def test_contract_covers_exact_builder_profile_keys(self):
        value = load_contract()
        self.assertEqual(
            set(value["parameter_contract"]),
            builder_profile_keys(),
        )
        self.assertEqual(len(value["parameter_contract"]), 18)

    def test_parameter_class_distribution_is_frozen(self):
        value = load_contract()
        observed = collections.Counter(
            entry["class"]
            for entry in value["parameter_contract"].values()
        )
        expected = {
            "FROZEN_STATIC": 9,
            "RUN_ALLOCATED": 6,
            "LIVE_DISCOVERED": 1,
            "AUTHORIZATION_BOUND": 2,
        }
        self.assertEqual(dict(observed), expected)
        self.assertEqual(value["class_counts"], expected)
        for entry in value["parameter_contract"].values():
            self.assertIsInstance(entry["source"], str)
            self.assertTrue(entry["source"])
            self.assertIsInstance(entry["materialization"], str)
            self.assertTrue(entry["materialization"])

    def test_contract_contains_no_concrete_live_identity_or_authorization(self):
        raw = CONTRACT.read_text(encoding="utf-8")
        self.assertNotIn("EXP-20", raw)
        self.assertNotIn("RUN-20", raw)
        self.assertNotIn("AUTHORISE_PROMPT12", raw)
        self.assertNotIn("/tmp/", raw)
        self.assertNotIn(".fifo", raw)

    def test_builder_rejects_template_as_concrete_profile(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = pathlib.Path(temporary) / "binding.json"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(BUILDER),
                    "--profile",
                    str(CONTRACT),
                    "--output",
                    str(output),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("PRODUCTION_BINDING_BUILDER_GATE=FAIL", proc.stderr)
            self.assertIn("COMMAND_EXECUTED=NO", proc.stderr)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
