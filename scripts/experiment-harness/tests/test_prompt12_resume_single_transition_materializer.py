#!/usr/bin/env python3

import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


SCRIPT = (
    pathlib.Path(__file__).resolve().parents[1]
    / "prompt12-resume-single-transition-materializer.py"
)

SPEC = importlib.util.spec_from_file_location(
    "single_transition_materializer",
    SCRIPT,
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def command(name):
    return ["tool", name]


def stationarity_t2():
    return [
        "python3",
        "prompt12-bounded-stationarity-command.py",
        "--mode",
        "post-step",
        "--control-index",
        "2",
        "--expected-timeline-event-count",
        "6",
        "--evidence-root",
        "/evidence/stationarity/T2",
    ]


def wrapped_t2_post():
    return [
        "python3",
        "prompt12-bounded-precontrol-handoff.py",
        "--attempt-root",
        "/evidence/precontrol-handoff/T3",
        "--precontrol-output",
        "/evidence/precontrol/T3.json",
        "--stationarity-command",
        *stationarity_t2(),
    ]


def finalization():
    return [
        "python3",
        "prompt12-bounded-finalization-command.py",
        "--attempt-root",
        "/evidence/finalization",
        "--expected-event-count",
        "18",
        "--timeline-output",
        "/evidence/timeline.jsonl",
        "--staging-output",
        "/evidence/staging.jsonl",
        "--canonical-output",
        "/evidence/canonical.jsonl",
        "--timeline-command",
        "timeline-tool",
        "@PROMPT12_ACTUATOR_TIMELINE@",
        "--pipeline-command",
        "pipeline-tool",
        "@PROMPT12_ACTUATOR_TIMELINE@",
    ]


def binding():
    transitions = []

    for index in range(1, 7):
        if index == 2:
            post = wrapped_t2_post()
        else:
            post = command(f"T{index}-post")

        transitions.append(
            {
                "label": f"T{index}",
                "ratio_bind_command":
                    command(f"T{index}-ratio"),
                "trigger_command":
                    command(f"T{index}-trigger"),
                "post_stationarity_command":
                    post,
            }
        )

    return {
        "schema": "synthetic-production-binding",
        "traffic_command": command("traffic"),
        "initial_stationarity_command":
            command("initial"),
        "finalization_command": finalization(),
        "transitions": transitions,
    }


def resume():
    return {
        "schema":
            "sci_oran_prompt12_resume_precontrol_materialization_v1",
        "initial_transition_index": 2,
        "first_scientific_transition": "T2",
        "precontrol_semantics": "initial-pre-step",
        "synthetic_prior_transition_events": False,
        "skipped_transition_bindings_consumed": False,
        "command_executed": False,
        "command": [
            "python3",
            "prompt12-bounded-precontrol-handoff.py",
            "--attempt-root",
            "/evidence/precontrol-handoff/T2",
            "--stationarity-command",
            "initial-t2-stationarity",
        ],
    }


def option_value(argv, option):
    index = argv.index(option)
    return argv[index + 1]


class MaterializerTests(unittest.TestCase):

    def test_materializes_resumed_t2_only(self):
        result = MODULE.build_materialization(
            binding(),
            resume(),
            2,
        )

        self.assertEqual(
            result["schema"],
            MODULE.SCHEMA,
        )
        self.assertEqual(
            result["transition_label"],
            "T2",
        )
        self.assertEqual(
            result["transition_index"],
            2,
        )
        self.assertEqual(
            result["executed_transition_ordinal"],
            1,
        )
        self.assertEqual(
            result["expected_timeline_event_count"],
            3,
        )

        self.assertFalse(
            result["synthetic_prior_transition_events"]
        )
        self.assertFalse(
            result["skipped_transition_bindings_consumed"]
        )
        self.assertFalse(
            result["t3_handoff_present"]
        )
        self.assertFalse(
            result["t3_trigger_present"]
        )

        post = result["post_stationarity_command"]

        self.assertNotIn(
            "--stationarity-command",
            post,
        )
        self.assertNotIn(
            "prompt12-bounded-precontrol-handoff.py",
            post,
        )
        self.assertEqual(
            option_value(post, "--control-index"),
            "1",
        )
        self.assertEqual(
            option_value(
                post,
                "--expected-timeline-event-count",
            ),
            "3",
        )

        final = result["finalization_command"]

        self.assertEqual(
            option_value(
                final,
                "--expected-event-count",
            ),
            "3",
        )

    def test_source_objects_are_not_modified(self):
        source_binding = binding()
        source_resume = resume()

        before_binding = json.dumps(
            source_binding,
            sort_keys=True,
        )
        before_resume = json.dumps(
            source_resume,
            sort_keys=True,
        )

        MODULE.build_materialization(
            source_binding,
            source_resume,
            2,
        )

        self.assertEqual(
            json.dumps(
                source_binding,
                sort_keys=True,
            ),
            before_binding,
        )
        self.assertEqual(
            json.dumps(
                source_resume,
                sort_keys=True,
            ),
            before_resume,
        )

    def test_rejects_non_t2_transition(self):
        with self.assertRaises(
            MODULE.MaterializerError
        ):
            MODULE.build_materialization(
                binding(),
                resume(),
                3,
            )

    def test_rejects_resume_with_synthetic_prior_events(self):
        value = resume()
        value["synthetic_prior_transition_events"] = True

        with self.assertRaises(
            MODULE.MaterializerError
        ):
            MODULE.build_materialization(
                binding(),
                value,
                2,
            )

    def test_rejects_t2_post_without_handoff_marker(self):
        value = binding()
        value["transitions"][1][
            "post_stationarity_command"
        ] = stationarity_t2()

        with self.assertRaises(
            MODULE.MaterializerError
        ):
            MODULE.build_materialization(
                value,
                resume(),
                2,
            )

    def test_cli_writes_exclusive_nonexecuting_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)

            binding_path = root / "binding.json"
            resume_path = root / "resume.json"
            output_path = root / "single.json"

            binding_path.write_text(
                json.dumps(binding()),
                encoding="utf-8",
            )
            resume_path.write_text(
                json.dumps(resume()),
                encoding="utf-8",
            )

            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--binding-manifest",
                    str(binding_path),
                    "--resume-materialization",
                    str(resume_path),
                    "--initial-transition-index",
                    "2",
                    "--output",
                    str(output_path),
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
            self.assertIn(
                "MATERIALIZATION_GATE=PASS",
                proc.stdout,
            )
            self.assertIn(
                "CONTROL_EXECUTED=NO",
                proc.stdout,
            )
            self.assertIn(
                "TRAFFIC_EXECUTED=NO",
                proc.stdout,
            )

            report = json.loads(
                output_path.read_text(
                    encoding="utf-8"
                )
            )

            self.assertEqual(
                report["transition_label"],
                "T2",
            )
            self.assertEqual(
                report["expected_timeline_event_count"],
                3,
            )

            second = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--binding-manifest",
                    str(binding_path),
                    "--resume-materialization",
                    str(resume_path),
                    "--initial-transition-index",
                    "2",
                    "--output",
                    str(output_path),
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(
                second.returncode,
                0,
            )
            self.assertIn(
                "OUTPUT_ALREADY_EXISTS",
                second.stderr,
            )


if __name__ == "__main__":
    unittest.main()
