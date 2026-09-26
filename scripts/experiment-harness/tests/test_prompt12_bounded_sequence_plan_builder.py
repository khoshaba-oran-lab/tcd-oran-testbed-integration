#!/usr/bin/env python3
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "prompt12-bounded-sequence-plan-builder.py"
)

spec = importlib.util.spec_from_file_location("plan_builder", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def valid_bindings(marker=None):
    payload = (
        f"open({str(marker)!r}, 'w').write('x')"
        if marker is not None
        else "pass"
    )
    command = [sys.executable, "-c", payload]

    return {
        "schema": module.BINDING_SCHEMA,
        "traffic_command": command,
        "initial_stationarity_command": command,
        "finalization_command": command,
        "transitions": [
            {
                "label": f"T{index}",
                "ratio_bind_command": command,
                "trigger_command": command,
                "post_stationarity_command": command,
            }
            for index in range(1, 7)
        ],
    }


def run_builder(binding, output):
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--binding",
            str(binding),
            "--output",
            str(output),
        ],
        text=True,
        capture_output=True,
        check=False,
    )


class PlanBuilderTests(unittest.TestCase):
    def test_builds_exact_supervisor_plan(self):
        bindings = valid_bindings()
        plan = module.build_plan(bindings)

        self.assertEqual(plan["schema"], module.PLAN_SCHEMA)
        self.assertEqual(
            [item["label"] for item in plan["transitions"]],
            list(module.TRANSITION_LABELS),
        )
        self.assertEqual(len(plan["transitions"]), 6)
        self.assertTrue(
            all(
                set(item) == {
                    "label",
                    "ratio_bind_command",
                    "trigger_command",
                    "post_stationarity_command",
                }
                for item in plan["transitions"]
            )
        )
        self.assertEqual(
            [
                item["ratio_bind_command"]
                for item in plan["transitions"]
            ],
            [
                item["ratio_bind_command"]
                for item in bindings["transitions"]
            ],
        )
        self.assertEqual(
            plan["traffic_command"],
            bindings["traffic_command"],
        )

    def test_rejects_empty_command(self):
        bindings = valid_bindings()
        bindings["traffic_command"] = []

        with self.assertRaisesRegex(
            module.PlanBuilderError,
            "traffic_command",
        ):
            module.build_plan(bindings)

    def test_rejects_empty_ratio_bind_command(self):
        bindings = valid_bindings()
        bindings["transitions"][0]["ratio_bind_command"] = []

        with self.assertRaisesRegex(
            module.PlanBuilderError,
            "ratio_bind_command",
        ):
            module.build_plan(bindings)

    def test_rejects_missing_ratio_bind_command(self):
        bindings = valid_bindings()
        del bindings["transitions"][0]["ratio_bind_command"]

        with self.assertRaisesRegex(
            module.PlanBuilderError,
            "missing keys",
        ):
            module.build_plan(bindings)

    def test_rejects_unexpected_transition_key(self):
        bindings = valid_bindings()
        bindings["transitions"][0]["unexpected"] = True

        with self.assertRaisesRegex(
            module.PlanBuilderError,
            "unexpected keys",
        ):
            module.build_plan(bindings)

    def test_rejects_wrong_transition_order(self):
        bindings = valid_bindings()
        bindings["transitions"][1]["label"] = "T3"

        with self.assertRaisesRegex(
            module.PlanBuilderError,
            "must be T2",
        ):
            module.build_plan(bindings)

    def test_rejects_extra_transition(self):
        bindings = valid_bindings()
        bindings["transitions"].append(
            {
                "label": "T7",
                "ratio_bind_command": ["true"],
                "trigger_command": ["true"],
                "post_stationarity_command": ["true"],
            }
        )

        with self.assertRaisesRegex(
            module.PlanBuilderError,
            "exactly six",
        ):
            module.build_plan(bindings)

    def test_rejects_unexpected_top_level_key(self):
        bindings = valid_bindings()
        bindings["live"] = True

        with self.assertRaisesRegex(
            module.PlanBuilderError,
            "unexpected keys",
        ):
            module.build_plan(bindings)

    def test_cli_writes_plan_without_executing_commands(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            marker = root / "executed"
            binding = root / "binding.json"
            output = root / "plan.json"

            binding.write_text(
                json.dumps(valid_bindings(marker)),
                encoding="utf-8",
            )

            proc = run_builder(binding, output)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertFalse(marker.exists())
            self.assertIn("PLAN_BUILDER_GATE=PASS", proc.stdout)
            self.assertIn("CONTROL_EXECUTED=NO", proc.stdout)

            plan = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(plan["schema"], module.PLAN_SCHEMA)
            self.assertEqual(len(plan["transitions"]), 6)

    def test_cli_refuses_existing_output(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            binding = root / "binding.json"
            output = root / "plan.json"

            binding.write_text(
                json.dumps(valid_bindings()),
                encoding="utf-8",
            )
            output.write_text("sentinel\n", encoding="utf-8")

            proc = run_builder(binding, output)

            self.assertEqual(proc.returncode, 65)
            self.assertEqual(
                output.read_text(encoding="utf-8"),
                "sentinel\n",
            )
            self.assertIn(
                "output path already exists",
                proc.stderr,
            )

    def test_invalid_schema_creates_no_output(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            binding = root / "binding.json"
            output = root / "plan.json"
            bindings = valid_bindings()
            bindings["schema"] = "invalid"

            binding.write_text(
                json.dumps(bindings),
                encoding="utf-8",
            )

            proc = run_builder(binding, output)

            self.assertEqual(proc.returncode, 65)
            self.assertFalse(output.exists())
            self.assertIn(
                "binding manifest schema is invalid",
                proc.stderr,
            )


if __name__ == "__main__":
    unittest.main()
