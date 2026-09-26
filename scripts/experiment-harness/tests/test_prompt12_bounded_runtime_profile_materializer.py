#!/usr/bin/env python3

import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "prompt12-bounded-runtime-profile-materializer.py"
BUILDER = ROOT / "prompt12-bounded-production-binding-builder.py"
BUILDER_TEST = pathlib.Path(__file__).resolve().parent / (
    "test_prompt12_bounded_production_binding_builder.py"
)


def load_builder_test_module():
    spec = importlib.util.spec_from_file_location(
        "prompt12_builder_test_fixture",
        BUILDER_TEST,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_baseline_profile(root):
    module = load_builder_test_module()
    candidate = getattr(module, "create_profile", None)
    if not callable(candidate):
        raise RuntimeError("CREATE_PROFILE_FIXTURE_NOT_FOUND")
    value = candidate(root)
    if (
        not isinstance(value, tuple)
        or len(value) != 2
        or not isinstance(value[0], dict)
        or not isinstance(value[1], pathlib.Path)
    ):
        raise RuntimeError("CREATE_PROFILE_FIXTURE_RESULT_INVALID")
    profile, profile_path = value
    if not profile_path.is_file():
        raise RuntimeError("CREATE_PROFILE_FIXTURE_OUTPUT_MISSING")
    return profile


def write_json(path, value):
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class RuntimeProfileMaterializerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temporary.name)
        baseline_root = self.root / "baseline"
        baseline_root.mkdir()
        self.baseline = make_baseline_profile(baseline_root)
        self.frozen = {
            "python_executable": self.baseline["python_executable"],
            "tool_paths": self.baseline["tool_paths"],
            "traffic_duration_s": self.baseline["traffic_duration_s"],
            "trigger_token": self.baseline["trigger_token"],
            "stable_ms": self.baseline["stable_ms"],
            "snapshot_timeout_ms": self.baseline["snapshot_timeout_ms"],
            "timeline_readiness_poll_ms": self.baseline[
                "timeline_readiness_poll_ms"
            ],
            "timeline_readiness_timeout_ms": self.baseline[
                "timeline_readiness_timeout_ms"
            ],
        }
        self.frozen_path = self.root / "frozen.json"
        write_json(self.frozen_path, self.frozen)
        self.fifo = self.root / "actuator.fifo"
        os.mkfifo(self.fifo)
        self.evidence = self.root / "evidence"
        self.evidence.mkdir()

    def tearDown(self):
        self.temporary.cleanup()

    def command(self, **overrides):
        values = {
            "evidence_root": str(self.evidence),
            "experiment_id": self.baseline["experiment_id"],
            "run_id": self.baseline["run_id"],
            "frozen_config": str(self.frozen_path),
            "actuator_fifo_path": str(self.fifo),
            "max_age_ms": str(self.baseline["max_age_ms"]),
            "control_authorization_token": self.baseline[
                "control_authorization_token"
            ],
        }
        values.update(overrides)
        return [
            sys.executable,
            str(SCRIPT),
            "--evidence-root",
            values["evidence_root"],
            "--experiment-id",
            values["experiment_id"],
            "--run-id",
            values["run_id"],
            "--frozen-config",
            values["frozen_config"],
            "--actuator-fifo-path",
            values["actuator_fifo_path"],
            "--max-age-ms",
            values["max_age_ms"],
            "--control-authorization-token",
            values["control_authorization_token"],
        ]

    def run_materializer(self, **overrides):
        return subprocess.run(
            self.command(**overrides),
            text=True,
            capture_output=True,
            check=False,
        )

    def successful_materialization(self):
        proc = self.run_materializer()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        report = json.loads(proc.stdout)
        profile_path = pathlib.Path(report["runtime_profile"])
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        return proc, report, profile_path, profile

    def test_contract_has_no_execution_capability(self):
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "contract"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("COMMAND_EXECUTION_CAPABILITY=ABSENT", proc.stdout)
        self.assertIn("DOCKER_EXECUTION_CAPABILITY=ABSENT", proc.stdout)
        self.assertIn("CONTROL_EXECUTED=NO", proc.stdout)

    def test_materialized_profile_is_accepted_by_builder_after_point_4(self):
        _, _, profile_path, profile = self.successful_materialization()

        binding = self.root / "binding.json"

        proc = subprocess.run(
            [
                sys.executable,
                str(BUILDER),
                "--profile",
                str(profile_path),
                "--output",
                str(binding),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(binding.is_file())

        value = json.loads(
            binding.read_text(encoding="utf-8")
        )

        self.assertEqual(
            len(value["transitions"]),
            6,
        )

        self.assertEqual(
            [
                item["ratio_bind_command"][
                    item["ratio_bind_command"].index(
                        "--output"
                    )
                    + 1
                ]
                for item in value["transitions"]
            ],
            profile["ratio_binding_paths"],
        )

    def test_profile_has_exact_fields_and_private_mode(self):
        _, report, profile_path, profile = self.successful_materialization()
        self.assertEqual(len(profile), 19)
        self.assertEqual(profile["schema"], "sci_oran_prompt12_bounded_sequence_runtime_profile_v1")
        self.assertEqual(profile_path.stat().st_mode & 0o777, 0o600)
        allocation = json.loads(
            pathlib.Path(report["allocation_record"]).read_text(encoding="utf-8")
        )
        self.assertFalse(allocation["authorization_value_recorded"])
        self.assertNotIn("control_authorization_token", allocation)

    def test_six_ratio_binding_paths_are_deterministic_and_unmaterialized(self):
        _, _, _, profile = self.successful_materialization()

        paths = [
            pathlib.Path(value)
            for value in profile["ratio_binding_paths"]
        ]

        self.assertEqual(len(paths), 6)

        expected_parent = (
            pathlib.Path(profile["run_directory"])
            / "runtime"
            / "ratio-bindings"
        )

        self.assertTrue(expected_parent.is_dir())
        self.assertEqual(
            expected_parent.stat().st_mode & 0o777,
            0o700,
        )

        self.assertEqual(
            [path.name for path in paths],
            [
                "T1.binding.json",
                "T2.binding.json",
                "T3.binding.json",
                "T4.binding.json",
                "T5.binding.json",
                "T6.binding.json",
            ],
        )

        for path in paths:
            self.assertTrue(path.is_absolute())
            self.assertEqual(path.parent, expected_parent)
            self.assertFalse(path.exists())

    def test_six_incremental_commands_have_frozen_prefixes(self):
        _, _, _, profile = self.successful_materialization()
        expected = ["50", "50,75", "50,75,100", "50,75,100,75", "50,75,100,75,50", "50,75,100,75,50,25"]
        self.assertEqual(len(profile["incremental_timeline_command_json"]), 6)
        for path_text, ratios in zip(profile["incremental_timeline_command_json"], expected):
            command = json.loads(pathlib.Path(path_text).read_text(encoding="utf-8"))
            self.assertEqual(command[command.index("--requested-ratios") + 1], ratios)
            self.assertEqual(command[command.index("--output") + 1], "@PROMPT12_ACTUATOR_TIMELINE@")

    def test_invalid_experiment_id_creates_no_run(self):
        proc = self.run_materializer(experiment_id="EXP-invalid")
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(list(self.evidence.iterdir()), [])

    def test_regular_file_is_not_accepted_as_fifo(self):
        regular = self.root / "not-fifo"
        regular.write_text("x\n", encoding="utf-8")
        proc = self.run_materializer(actuator_fifo_path=str(regular))
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(list(self.evidence.iterdir()), [])

    def test_existing_run_directory_is_not_overwritten(self):
        run_directory = self.evidence / self.baseline["experiment_id"] / self.baseline["run_id"]
        run_directory.mkdir(parents=True)
        sentinel = run_directory / "sentinel"
        sentinel.write_text("preserve\n", encoding="utf-8")
        proc = self.run_materializer()
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "preserve\n")

    def test_missing_frozen_key_is_rejected_before_allocation(self):
        broken = dict(self.frozen)
        del broken["stable_ms"]
        broken_path = self.root / "broken-frozen.json"
        write_json(broken_path, broken)
        proc = self.run_materializer(frozen_config=str(broken_path))
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(list(self.evidence.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
