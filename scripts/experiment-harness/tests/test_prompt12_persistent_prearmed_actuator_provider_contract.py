#!/usr/bin/env python3

import json
import pathlib
import unittest


REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parents[3]

CONTRACT = (
    REPOSITORY_ROOT
    / "experiments"
    / "manifests"
    / "prompt12-persistent-prearmed-actuator-provider-contract-v1.json"
)

EXPECTED_TOP_LEVEL_KEYS = {
    "admission_states",
    "architecture",
    "executable",
    "existing_component_roles",
    "guards",
    "host_semantics",
    "live_runtime_admitted",
    "provider_implemented",
    "required_admission_evidence",
    "required_provider_responsibilities",
    "schema",
    "unresolved_runtime_bindings",
}


class PersistentPrearmedActuatorProviderContractTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(
            CONTRACT.read_text(encoding="utf-8")
        )

    def test_exact_top_level_keys(self):
        self.assertEqual(
            set(self.contract),
            EXPECTED_TOP_LEVEL_KEYS,
        )

    def test_identity_and_safety_flags(self):
        self.assertEqual(
            self.contract["schema"],
            (
                "sci_oran_prompt12_persistent_prearmed_"
                "actuator_provider_contract_v1"
            ),
        )
        self.assertEqual(
            self.contract["architecture"],
            "persistent_prearmed_fifo_v2",
        )
        self.assertEqual(
            self.contract["host_semantics"],
            "supervisor_local_filesystem",
        )
        self.assertIs(
            self.contract["executable"],
            False,
        )
        self.assertIs(
            self.contract["provider_implemented"],
            True,
        )
        self.assertIs(
            self.contract["live_runtime_admitted"],
            False,
        )

    def test_exact_existing_component_roles(self):
        self.assertEqual(
            self.contract["existing_component_roles"],
            {
                "atomic_prestart": "excluded_legacy_path",
                "binding_builder": "argv_only_fifo_binding",
                "orchestration_supervisor": (
                    "local_argv_supervisor"
                ),
                "runtime_profile_materializer": (
                    "explicit_path_validator_and_profile_binder"
                ),
                "trigger_executor": (
                    "fifo_writer_and_type_validator"
                ),
            },
        )

    def test_responsibilities_and_state_order(self):
        responsibilities = self.contract[
            "required_provider_responsibilities"
        ]

        self.assertEqual(len(responsibilities), 8)
        self.assertEqual(
            len(responsibilities),
            len(set(responsibilities)),
        )
        self.assertEqual(
            self.contract["admission_states"],
            [
                "ABSENT",
                "FIFO_CREATED",
                "PROVIDER_STARTED",
                "READER_READY",
                "ADMITTED",
                "STOPPED",
            ],
        )

    def test_evidence_and_unresolved_bindings(self):
        evidence = self.contract[
            "required_admission_evidence"
        ]
        bindings = self.contract[
            "unresolved_runtime_bindings"
        ]

        self.assertEqual(len(evidence), 10)
        self.assertEqual(len(evidence), len(set(evidence)))
        self.assertEqual(len(bindings), 7)
        self.assertEqual(len(bindings), len(set(bindings)))
        self.assertIn("fifo_path", evidence)
        self.assertIn("reader_readiness_gate", evidence)
        self.assertIn("provider_launch_argv", bindings)
        self.assertIn("cleanup_argv", bindings)

    def test_exact_guards_are_false(self):
        guards = self.contract["guards"]

        self.assertEqual(
            set(guards),
            {
                "broad_filesystem_scan_allowed",
                "implicit_fifo_path_allowed",
                "legacy_atomic_prestart_allowed",
                "prb_control_allowed_during_admission",
                "r01_authorised",
                "traffic_allowed_during_admission",
                "trigger_allowed_during_admission",
            },
        )
        self.assertTrue(
            all(value is False for value in guards.values())
        )


if __name__ == "__main__":
    unittest.main()
