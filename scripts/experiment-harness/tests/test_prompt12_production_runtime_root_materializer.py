import importlib.util
import json
import os
import pathlib
import stat
import subprocess
import sys
import tempfile
import unittest


SCRIPT = (
    pathlib.Path(__file__).resolve().parents[1]
    / "prompt12-production-runtime-root-materializer.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "runtime_root_materializer",
        SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RuntimeRootMaterializerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module()

    def make_parent(self):
        tmp = tempfile.TemporaryDirectory()
        root = pathlib.Path(tmp.name).resolve()
        return tmp, root

    def test_script_exists(self):
        self.assertTrue(SCRIPT.is_file())

    def test_schema_exact(self):
        self.assertEqual(
            self.mod.SCHEMA,
            "sci_oran_prompt12_v2_production_runtime_root_materializer_v1",
        )

    def test_prefix_exact(self):
        self.assertEqual(
            self.mod.PREFIX,
            "prompt12-runtime-",
        )

    def test_output_is_absolute(self):
        tmp, parent = self.make_parent()
        self.addCleanup(tmp.cleanup)

        value = self.mod.materialize_runtime_root(
            "exp-a",
            "run-a",
            str(parent),
        )

        self.assertTrue(pathlib.Path(value).is_absolute())

    def test_output_direct_child_of_parent(self):
        tmp, parent = self.make_parent()
        self.addCleanup(tmp.cleanup)

        value = pathlib.Path(
            self.mod.materialize_runtime_root(
                "exp-a",
                "run-a",
                str(parent),
            )
        )

        self.assertEqual(value.parent, parent)

    def test_output_deterministic(self):
        tmp, parent = self.make_parent()
        self.addCleanup(tmp.cleanup)

        a = self.mod.materialize_runtime_root(
            "exp-a",
            "run-a",
            str(parent),
        )
        b = self.mod.materialize_runtime_root(
            "exp-a",
            "run-a",
            str(parent),
        )

        self.assertEqual(a, b)

    def test_experiment_id_changes_output(self):
        tmp, parent = self.make_parent()
        self.addCleanup(tmp.cleanup)

        a = self.mod.materialize_runtime_root(
            "exp-a",
            "run-a",
            str(parent),
        )
        b = self.mod.materialize_runtime_root(
            "exp-b",
            "run-a",
            str(parent),
        )

        self.assertNotEqual(a, b)

    def test_run_id_changes_output(self):
        tmp, parent = self.make_parent()
        self.addCleanup(tmp.cleanup)

        a = self.mod.materialize_runtime_root(
            "exp-a",
            "run-a",
            str(parent),
        )
        b = self.mod.materialize_runtime_root(
            "exp-a",
            "run-b",
            str(parent),
        )

        self.assertNotEqual(a, b)

    def test_empty_experiment_id_rejected(self):
        tmp, parent = self.make_parent()
        self.addCleanup(tmp.cleanup)

        with self.assertRaisesRegex(
            self.mod.ContractError,
            "EXPERIMENT_ID_EMPTY",
        ):
            self.mod.materialize_runtime_root(
                "",
                "run-a",
                str(parent),
            )

    def test_whitespace_experiment_id_rejected(self):
        tmp, parent = self.make_parent()
        self.addCleanup(tmp.cleanup)

        with self.assertRaisesRegex(
            self.mod.ContractError,
            "EXPERIMENT_ID_EMPTY",
        ):
            self.mod.materialize_runtime_root(
                "   ",
                "run-a",
                str(parent),
            )

    def test_empty_run_id_rejected(self):
        tmp, parent = self.make_parent()
        self.addCleanup(tmp.cleanup)

        with self.assertRaisesRegex(
            self.mod.ContractError,
            "RUN_ID_EMPTY",
        ):
            self.mod.materialize_runtime_root(
                "exp-a",
                "",
                str(parent),
            )

    def test_whitespace_run_id_rejected(self):
        tmp, parent = self.make_parent()
        self.addCleanup(tmp.cleanup)

        with self.assertRaisesRegex(
            self.mod.ContractError,
            "RUN_ID_EMPTY",
        ):
            self.mod.materialize_runtime_root(
                "exp-a",
                "   ",
                str(parent),
            )

    def test_empty_parent_rejected(self):
        with self.assertRaisesRegex(
            self.mod.ContractError,
            "TRACKED_RUNTIME_PARENT_EMPTY",
        ):
            self.mod.materialize_runtime_root(
                "exp-a",
                "run-a",
                "",
            )

    def test_relative_parent_rejected(self):
        with self.assertRaisesRegex(
            self.mod.ContractError,
            "TRACKED_RUNTIME_PARENT_NOT_ABSOLUTE",
        ):
            self.mod.materialize_runtime_root(
                "exp-a",
                "run-a",
                "relative/path",
            )

    def test_missing_parent_rejected(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)

        missing = (
            pathlib.Path(tmp.name).resolve()
            / "missing"
        )

        with self.assertRaisesRegex(
            self.mod.ContractError,
            "TRACKED_RUNTIME_PARENT_UNAVAILABLE",
        ):
            self.mod.materialize_runtime_root(
                "exp-a",
                "run-a",
                str(missing),
            )

    def test_parent_must_be_directory(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)

        file_path = pathlib.Path(tmp.name).resolve() / "file"
        file_path.write_text("x", encoding="utf-8")

        with self.assertRaisesRegex(
            self.mod.ContractError,
            "TRACKED_RUNTIME_PARENT_NOT_DIRECTORY",
        ):
            self.mod.materialize_runtime_root(
                "exp-a",
                "run-a",
                str(file_path),
            )

    def test_noncanonical_parent_rejected(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)

        root = pathlib.Path(tmp.name).resolve()
        sub = root / "sub"
        sub.mkdir()

        noncanonical = str(sub / ".." / "sub")

        with self.assertRaisesRegex(
            self.mod.ContractError,
            "TRACKED_RUNTIME_PARENT_NOT_CANONICAL",
        ):
            self.mod.materialize_runtime_root(
                "exp-a",
                "run-a",
                noncanonical,
            )

    def test_existing_output_rejected(self):
        tmp, parent = self.make_parent()
        self.addCleanup(tmp.cleanup)

        value = pathlib.Path(
            self.mod.materialize_runtime_root(
                "exp-a",
                "run-a",
                str(parent),
            )
        )
        value.mkdir()

        with self.assertRaisesRegex(
            self.mod.ContractError,
            "RUNTIME_ROOT_ALREADY_EXISTS",
        ):
            self.mod.materialize_runtime_root(
                "exp-a",
                "run-a",
                str(parent),
            )

    def test_materializer_does_not_create_runtime_root(self):
        tmp, parent = self.make_parent()
        self.addCleanup(tmp.cleanup)

        value = pathlib.Path(
            self.mod.materialize_runtime_root(
                "exp-a",
                "run-a",
                str(parent),
            )
        )

        self.assertFalse(os.path.lexists(value))

    def test_materializer_does_not_create_fifo(self):
        tmp, parent = self.make_parent()
        self.addCleanup(tmp.cleanup)

        value = pathlib.Path(
            self.mod.materialize_runtime_root(
                "exp-a",
                "run-a",
                str(parent),
            )
        )

        self.assertFalse(
            os.path.lexists(value / "actuator.fifo")
        )

    def test_slashes_in_ids_cannot_escape_parent(self):
        tmp, parent = self.make_parent()
        self.addCleanup(tmp.cleanup)

        value = pathlib.Path(
            self.mod.materialize_runtime_root(
                "../../exp",
                "../run",
                str(parent),
            )
        )

        self.assertEqual(value.parent, parent)

    def test_unicode_ids_supported_deterministically(self):
        tmp, parent = self.make_parent()
        self.addCleanup(tmp.cleanup)

        a = self.mod.materialize_runtime_root(
            "експеримент",
            "запуск",
            str(parent),
        )
        b = self.mod.materialize_runtime_root(
            "експеримент",
            "запуск",
            str(parent),
        )

        self.assertEqual(a, b)

    def test_cli_missing_experiment_id_fails(self):
        tmp, parent = self.make_parent()
        self.addCleanup(tmp.cleanup)

        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--run-id",
                "run-a",
                "--tracked-runtime-parent",
                str(parent),
            ],
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(proc.returncode, 0)

    def test_cli_missing_run_id_fails(self):
        tmp, parent = self.make_parent()
        self.addCleanup(tmp.cleanup)

        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--experiment-id",
                "exp-a",
                "--tracked-runtime-parent",
                str(parent),
            ],
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(proc.returncode, 0)

    def test_cli_missing_parent_fails(self):
        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--experiment-id",
                "exp-a",
                "--run-id",
                "run-a",
            ],
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(proc.returncode, 0)

    def test_cli_unexpected_extra_input_fails(self):
        tmp, parent = self.make_parent()
        self.addCleanup(tmp.cleanup)

        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--experiment-id",
                "exp-a",
                "--run-id",
                "run-a",
                "--tracked-runtime-parent",
                str(parent),
                "--unexpected",
                "x",
            ],
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(proc.returncode, 0)

    def test_cli_success_returns_json(self):
        tmp, parent = self.make_parent()
        self.addCleanup(tmp.cleanup)

        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--experiment-id",
                "exp-a",
                "--run-id",
                "run-a",
                "--tracked-runtime-parent",
                str(parent),
            ],
            capture_output=True,
            text=True,
        )

        self.assertEqual(proc.returncode, 0)

        data = json.loads(proc.stdout)

        self.assertEqual(
            data["schema"],
            self.mod.SCHEMA,
        )
        self.assertTrue(
            pathlib.Path(data["runtime_root"]).is_absolute()
        )
        self.assertEqual(
            pathlib.Path(data["runtime_root"]).parent,
            parent,
        )

    def test_cli_success_does_not_create_output(self):
        tmp, parent = self.make_parent()
        self.addCleanup(tmp.cleanup)

        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--experiment-id",
                "exp-a",
                "--run-id",
                "run-a",
                "--tracked-runtime-parent",
                str(parent),
            ],
            capture_output=True,
            text=True,
        )

        self.assertEqual(proc.returncode, 0)

        value = pathlib.Path(
            json.loads(proc.stdout)["runtime_root"]
        )

        self.assertFalse(os.path.lexists(value))

    def test_source_has_no_process_execution_api(self):
        source = SCRIPT.read_text(encoding="utf-8")

        forbidden = [
            "subprocess.",
            "os.system(",
            "os.exec",
            "os.spawn",
            "Popen(",
            "docker ",
        ]

        for token in forbidden:
            self.assertNotIn(token, source)

    def test_source_has_no_directory_creation_api(self):
        source = SCRIPT.read_text(encoding="utf-8")

        forbidden = [
            ".mkdir(",
            "os.mkdir(",
            "os.makedirs(",
            "mkdtemp(",
            "TemporaryDirectory(",
        ]

        for token in forbidden:
            self.assertNotIn(token, source)

    def test_source_has_no_fifo_creation_api(self):
        source = SCRIPT.read_text(encoding="utf-8")

        self.assertNotIn(
            "mkfifo",
            source.lower(),
        )


if __name__ == "__main__":
    unittest.main()
