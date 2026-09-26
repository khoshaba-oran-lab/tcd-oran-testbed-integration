#!/usr/bin/env python3

import hashlib
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest


HERE = pathlib.Path(__file__).resolve().parent
HARNESS = HERE.parent
WRITER = HARNESS / "prompt12-pretrigger-ratio-binding-writer.py"

spec = importlib.util.spec_from_file_location(
    "prompt12_ratio_binding_writer",
    WRITER,
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class RatioBindingWriterTests(unittest.TestCase):

    def run_writer(
        self,
        output,
        *,
        experiment_id="EXP-001",
        run_id="RUN-001",
        transition_label="T1",
        transition_index=1,
        ratio=50,
    ):
        return subprocess.run(
            [
                sys.executable,
                str(WRITER),
                "--experiment-id",
                experiment_id,
                "--run-id",
                run_id,
                "--transition-label",
                transition_label,
                "--transition-index",
                str(transition_index),
                "--requested-ratio-pct",
                str(ratio),
                "--output",
                str(output),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

    def test_static_safety_boundary(self):
        source = WRITER.read_text(encoding="utf-8")

        self.assertNotIn("subprocess.Popen", source)
        self.assertNotIn("subprocess.run", source)
        self.assertNotIn("os.mkfifo", source)
        self.assertNotIn("docker", source.lower())
        self.assertNotIn("flexric", source.lower())
        self.assertNotIn("TRIGGER\\n", source)

    def test_all_allowed_ratios_materialize_valid_binding(self):
        for index, ratio in enumerate(
            [25, 50, 75, 100],
            start=1,
        ):
            with self.subTest(ratio=ratio):
                with tempfile.TemporaryDirectory() as temporary:
                    root = pathlib.Path(temporary)
                    output = root / f"T{index}.binding.json"

                    proc = self.run_writer(
                        output,
                        transition_label=f"T{index}",
                        transition_index=index,
                        ratio=ratio,
                    )

                    self.assertEqual(
                        proc.returncode,
                        0,
                        proc.stderr,
                    )
                    self.assertIn(
                        "RATIO_BOUND=PASS",
                        proc.stdout,
                    )
                    self.assertTrue(output.is_file())

                    value = json.loads(
                        output.read_text(encoding="utf-8")
                    )

                    self.assertEqual(
                        value["schema"],
                        module.SCHEMA,
                    )
                    self.assertEqual(
                        value["requested_ratio_pct"],
                        ratio,
                    )
                    self.assertEqual(
                        value["transition_label"],
                        f"T{index}",
                    )
                    self.assertEqual(
                        value["transition_index"],
                        index,
                    )

                    self.assertEqual(
                        set(value),
                        {
                            "schema",
                            "binding_id",
                            "experiment_id",
                            "run_id",
                            "transition_label",
                            "transition_index",
                            "requested_ratio_pct",
                            "created_utc",
                        },
                    )

                    self.assertEqual(
                        output.stat().st_mode & 0o777,
                        0o600,
                    )

    def test_sha256_evidence_matches_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = pathlib.Path(temporary) / "binding.json"

            proc = self.run_writer(output)

            self.assertEqual(proc.returncode, 0)

            reported = None
            for line in proc.stdout.splitlines():
                if line.startswith("BINDING_SHA256="):
                    reported = line.split("=", 1)[1]

            self.assertIsNotNone(reported)

            actual = hashlib.sha256(
                output.read_bytes()
            ).hexdigest()

            self.assertEqual(reported, actual)

    def test_binding_id_is_unique(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)

            first = root / "first.json"
            second = root / "second.json"

            p1 = self.run_writer(first)
            p2 = self.run_writer(second)

            self.assertEqual(p1.returncode, 0)
            self.assertEqual(p2.returncode, 0)

            first_value = json.loads(
                first.read_text(encoding="utf-8")
            )
            second_value = json.loads(
                second.read_text(encoding="utf-8")
            )

            self.assertNotEqual(
                first_value["binding_id"],
                second_value["binding_id"],
            )

    def test_existing_output_fails_closed_without_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = pathlib.Path(temporary) / "binding.json"

            output.write_text(
                "sentinel\n",
                encoding="utf-8",
            )

            proc = self.run_writer(output)

            self.assertEqual(proc.returncode, 2)
            self.assertIn(
                "OUTPUT_ALREADY_EXISTS",
                proc.stderr,
            )
            self.assertNotIn(
                "RATIO_BOUND=PASS",
                proc.stdout,
            )
            self.assertEqual(
                output.read_text(encoding="utf-8"),
                "sentinel\n",
            )

    def test_invalid_ratios_fail_closed_without_output(self):
        for ratio in [0, 13, 26, 101]:
            with self.subTest(ratio=ratio):
                with tempfile.TemporaryDirectory() as temporary:
                    output = (
                        pathlib.Path(temporary)
                        / "binding.json"
                    )

                    proc = self.run_writer(
                        output,
                        ratio=ratio,
                    )

                    self.assertEqual(proc.returncode, 2)
                    self.assertIn(
                        "REQUESTED_RATIO_INVALID",
                        proc.stderr,
                    )
                    self.assertFalse(output.exists())

    def test_transition_label_index_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = pathlib.Path(temporary) / "binding.json"

            proc = self.run_writer(
                output,
                transition_label="T2",
                transition_index=1,
            )

            self.assertEqual(proc.returncode, 2)
            self.assertIn(
                "TRANSITION_LABEL_INDEX_MISMATCH",
                proc.stderr,
            )
            self.assertFalse(output.exists())

    def test_invalid_transition_index_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = pathlib.Path(temporary) / "binding.json"

            proc = self.run_writer(
                output,
                transition_label="T7",
                transition_index=7,
            )

            self.assertEqual(proc.returncode, 2)
            self.assertIn(
                "TRANSITION_INDEX_INVALID",
                proc.stderr,
            )
            self.assertFalse(output.exists())

    def test_invalid_identity_fails_closed(self):
        invalid_values = [
            "",
            "../escape",
            "contains space",
        ]

        for value in invalid_values:
            with self.subTest(value=value):
                with tempfile.TemporaryDirectory() as temporary:
                    output = (
                        pathlib.Path(temporary)
                        / "binding.json"
                    )

                    proc = self.run_writer(
                        output,
                        experiment_id=value,
                    )

                    self.assertEqual(proc.returncode, 2)
                    self.assertIn(
                        "EXPERIMENT_ID_INVALID",
                        proc.stderr,
                    )
                    self.assertFalse(output.exists())

    def test_relative_output_path_fails_closed(self):
        proc = self.run_writer(
            pathlib.Path("relative-binding.json")
        )

        self.assertEqual(proc.returncode, 2)
        self.assertIn(
            "OUTPUT_PATH_NOT_ABSOLUTE",
            proc.stderr,
        )
        self.assertFalse(
            pathlib.Path("relative-binding.json").exists()
        )


if __name__ == "__main__":
    unittest.main()
