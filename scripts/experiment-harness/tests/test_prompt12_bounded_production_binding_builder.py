#!/usr/bin/env python3

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest


HARNESS = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = pathlib.Path(
    os.environ.get(
        "PROMPT12_TEST_BINDING_BUILDER",
        str(HARNESS / "prompt12-bounded-production-binding-builder.py"),
    )
)
PLAN_BUILDER = pathlib.Path(
    os.environ.get(
        "PROMPT12_TEST_PLAN_BUILDER",
        str(HARNESS / "prompt12-bounded-sequence-plan-builder.py"),
    )
)


TOOL_KEYS = (
    "traffic_adapter",
    "stationarity_adapter",
    "precontrol_handoff",
    "finalization_adapter",
    "parser",
    "canonicalizer",
    "stationarity_evaluator",
    "freshness_evaluator",
    "trigger_executor",
    "timeline_builder",
    "receiver_pipeline",
    "schema",
    "freshness_policy",
)


def create_file(path, content="stub\n", executable=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if executable:
        path.chmod(0o755)
    return path


def create_profile(root):
    tools = {}
    for key in TOOL_KEYS:
        suffix = ".sh" if key in (
            "traffic_adapter",
            "receiver_pipeline",
        ) else ".py"
        path = create_file(
            root / "tools" / f"{key}{suffix}",
            executable=key in (
                "traffic_adapter",
                "receiver_pipeline",
            ),
        )
        tools[key] = str(path)

    timeline_json = []
    for index in range(1, 7):
        path = create_file(
            root / "timeline-commands" / f"T{index}.json",
            json.dumps(["tool", "@PROMPT12_ACTUATOR_TIMELINE@"]) + "\n",
        )
        timeline_json.append(str(path))

    profile = {
        "schema": "sci_oran_prompt12_bounded_sequence_runtime_profile_v1",
        "python_executable": sys.executable,
        "experiment_id": "EXP-20260921-DL-18000K-R01",
        "run_id": "RUN-20260921T130000Z-001",
        "run_directory": str(root / "run"),
        "receiver_container_name": "prompt12-r01-receiver",
        "traffic_duration_s": 180,
        "actuator_fifo_path": str(root / "runtime" / "actuator.fifo"),
        "control_authorization_token": "AUTHORISE_PROMPT12_FIFO_CONTROL",
        "trigger_token": "TRIGGER",
        "max_age_ms": 500,
        "stable_ms": 0,
        "snapshot_timeout_ms": 1000,
        "timeline_readiness_timeout_ms": 1000,
        "timeline_readiness_poll_ms": 10,
        "tool_paths": tools,
        "data_paths": {
            "actuator_command_input": str(root / "runtime" / "command.jsonl"),
            "actuator_applied_input": str(root / "runtime" / "applied.jsonl"),
            "actuator_ack_input": str(root / "runtime" / "ack.jsonl"),
        },
        "incremental_timeline_command_json": timeline_json,
    }
    path = root / "profile.json"
    path.write_text(
        json.dumps(profile, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return profile, path


def run_builder(profile_path, output_path):
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--profile",
            str(profile_path),
            "--output",
            str(output_path),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


class ProductionBindingBuilderTests(unittest.TestCase):
    def test_builds_exact_six_transition_binding(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            _, profile_path = create_profile(root)
            output = root / "binding.json"

            proc = run_builder(profile_path, output)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            binding = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(
                binding["schema"],
                "sci_oran_prompt12_bounded_sequence_bindings_v1",
            )
            self.assertEqual(
                [item["label"] for item in binding["transitions"]],
                [f"T{index}" for index in range(1, 7)],
            )
            self.assertTrue(all(
                isinstance(value, list) and value
                for value in (
                    binding["traffic_command"],
                    binding["initial_stationarity_command"],
                    binding["finalization_command"],
                )
            ))

    def test_generated_binding_is_accepted_by_plan_builder(self):
        if not PLAN_BUILDER.is_file():
            self.skipTest("plan builder fixture unavailable")
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            _, profile_path = create_profile(root)
            binding = root / "binding.json"
            plan = root / "plan.json"
            built = run_builder(profile_path, binding)
            self.assertEqual(built.returncode, 0, built.stderr)

            proc = subprocess.run(
                [
                    sys.executable,
                    str(PLAN_BUILDER),
                    "--binding",
                    str(binding),
                    "--output",
                    str(plan),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            value = json.loads(plan.read_text(encoding="utf-8"))
            self.assertEqual(
                value["schema"],
                "sci_oran_prompt12_bounded_sequence_v1",
            )

    def test_existing_output_is_rejected_without_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            _, profile_path = create_profile(root)
            output = root / "binding.json"
            output.write_text("sentinel\n", encoding="utf-8")

            proc = run_builder(profile_path, output)

            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("OUTPUT_ALREADY_EXISTS", proc.stderr)
            self.assertEqual(
                output.read_text(encoding="utf-8"),
                "sentinel\n",
            )

    def test_missing_runtime_field_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            profile, profile_path = create_profile(root)
            del profile["actuator_fifo_path"]
            profile_path.write_text(
                json.dumps(profile) + "\n",
                encoding="utf-8",
            )

            proc = run_builder(profile_path, root / "binding.json")

            self.assertNotEqual(proc.returncode, 0)
            self.assertIn(
                "PROFILE_MISSING_KEYS:actuator_fifo_path",
                proc.stderr,
            )

    def test_invalid_timeline_command_count_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            profile, profile_path = create_profile(root)
            profile["incremental_timeline_command_json"] = (
                profile["incremental_timeline_command_json"][:5]
            )
            profile_path.write_text(
                json.dumps(profile) + "\n",
                encoding="utf-8",
            )

            proc = run_builder(profile_path, root / "binding.json")

            self.assertNotEqual(proc.returncode, 0)
            self.assertIn(
                "INCREMENTAL_TIMELINE_COMMAND_JSON_COUNT_INVALID",
                proc.stderr,
            )

    def test_builder_does_not_execute_bound_tools(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            marker = root / "executed"
            profile, profile_path = create_profile(root)
            payload = (
                "#!/bin/sh\n"
                + "printf executed > "
                + repr(str(marker))
                + "\n"
            )
            for key, value in profile["tool_paths"].items():
                path = pathlib.Path(value)
                path.write_text(payload, encoding="utf-8")
                if key in ("traffic_adapter", "receiver_pipeline"):
                    path.chmod(0o755)

            proc = run_builder(profile_path, root / "binding.json")

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertFalse(marker.exists())
            self.assertIn("COMMAND_EXECUTED=NO", proc.stdout)


if __name__ == "__main__":
    unittest.main()
