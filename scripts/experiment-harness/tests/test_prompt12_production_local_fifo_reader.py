#!/usr/bin/env python3

import datetime
import importlib.util
import json
import os
import pathlib
import stat
import subprocess
import sys
import tempfile
import time
import unittest
import uuid


HERE = pathlib.Path(__file__).resolve().parent
HARNESS = HERE.parent
READER = HARNESS / "prompt12-production-local-fifo-reader.py"

spec = importlib.util.spec_from_file_location(
    "prompt12_production_local_fifo_reader",
    READER,
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ProductionLocalFifoReaderTests(unittest.TestCase):

    def setUp(self):
        self.experiment_id = "EXP-001"
        self.run_id = "RUN-001"

    def create_stub(self, root):
        stub = root / "actuator-stub.py"

        stub.write_text(
            """#!/usr/bin/env python3
import json
import os
import pathlib
import sys

log = pathlib.Path(sys.argv[1])
rc = int(sys.argv[2])

record = {
    "ratio": os.environ.get("SCI_ORAN_MAX_PRB_RATIO"),
}

with log.open("a", encoding="utf-8") as handle:
    handle.write(json.dumps(record) + "\\n")

raise SystemExit(rc)
""",
            encoding="utf-8",
        )

        return stub

    def binding_paths(self, root):
        directory = root / "ratio-bindings"
        directory.mkdir(mode=0o700)

        return [
            directory / f"T{index}.binding.json"
            for index in range(1, 7)
        ]

    def binding_value(
        self,
        *,
        transition_index,
        ratio,
        experiment_id=None,
        run_id=None,
        schema=None,
        created_utc=None,
        binding_id=None,
    ):
        if created_utc is None:
            created_utc = (
                datetime.datetime.now(
                    datetime.timezone.utc
                )
                .replace(microsecond=0)
                .isoformat()
                .replace("+00:00", "Z")
            )

        return {
            "schema": schema or module.BINDING_SCHEMA,
            "binding_id": binding_id or uuid.uuid4().hex,
            "experiment_id": (
                experiment_id
                if experiment_id is not None
                else self.experiment_id
            ),
            "run_id": (
                run_id
                if run_id is not None
                else self.run_id
            ),
            "transition_label": f"T{transition_index}",
            "transition_index": transition_index,
            "requested_ratio_pct": ratio,
            "created_utc": created_utc,
        }

    def write_binding(
        self,
        path,
        *,
        transition_index,
        ratio,
        **overrides,
    ):
        value = self.binding_value(
            transition_index=transition_index,
            ratio=ratio,
            **overrides,
        )

        path.write_text(
            json.dumps(
                value,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        path.chmod(0o600)

        return value

    def start_reader(
        self,
        root,
        *,
        stub_rc=0,
    ):
        fifo = root / "actuator.fifo"
        os.mkfifo(fifo, 0o600)

        paths = self.binding_paths(root)

        log = root / "actuator.jsonl"
        stub = self.create_stub(root)

        actuator_argv = [
            sys.executable,
            str(stub),
            str(log),
            str(stub_rc),
        ]

        env = os.environ.copy()
        env.pop("SCI_ORAN_MAX_PRB_RATIO", None)

        process = subprocess.Popen(
            [
                sys.executable,
                str(READER),
                "--fifo-path",
                str(fifo),
                "--actuator-argv-json",
                json.dumps(actuator_argv),
                "--experiment-id",
                self.experiment_id,
                "--run-id",
                self.run_id,
                "--ratio-binding-paths-json",
                json.dumps(
                    [str(path) for path in paths]
                ),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )

        prearmed = process.stdout.readline()

        self.assertIn(
            "PROMPT12_V2_READER_PREARMED=YES",
            prearmed,
        )
        self.assertIn(
            "ratio_binding_count=6",
            prearmed,
        )

        writer_fd = os.open(
            fifo,
            os.O_WRONLY,
        )

        return {
            "fifo": fifo,
            "paths": paths,
            "log": log,
            "process": process,
            "writer_fd": writer_fd,
        }

    def stop_reader(self, state):
        try:
            os.close(state["writer_fd"])
        except OSError:
            pass

        try:
            return state["process"].communicate(timeout=5)
        except subprocess.TimeoutExpired:
            state["process"].terminate()
            return state["process"].communicate(timeout=5)

    def records(self, log):
        if not log.exists():
            return []

        return [
            json.loads(line)
            for line in log.read_text(
                encoding="utf-8"
            ).splitlines()
            if line.strip()
        ]

    def wait_for_record_count(
        self,
        log,
        expected,
        timeout=5,
    ):
        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            records = self.records(log)

            if len(records) >= expected:
                return records

            time.sleep(0.02)

        self.fail(
            f"actuator record count did not reach {expected}; "
            f"actual={len(self.records(log))}"
        )

    def trigger(self, state):
        os.write(
            state["writer_fd"],
            b"TRIGGER\n",
        )

    def test_static_production_boundary(self):
        source = READER.read_text(encoding="utf-8")

        self.assertNotIn("os.mkfifo", source)
        self.assertNotIn("docker", source.lower())
        self.assertNotIn("flexric", source.lower())
        self.assertEqual(
            source.count("subprocess.run("),
            1,
        )
        self.assertIn(
            'TRIGGER_TOKEN = "TRIGGER\\n"',
            source,
        )
        self.assertNotIn(
            'TRIGGER_TOKEN = "TRIGGER:',
            source,
        )

    def test_binding_path_contract_is_exact_six_absolute_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)

            paths = [
                str(
                    root
                    / f"T{index}.binding.json"
                )
                for index in range(1, 7)
            ]

            parsed = module.parse_ratio_binding_paths(
                json.dumps(paths)
            )

            self.assertEqual(
                [path.name for path in parsed],
                [
                    "T1.binding.json",
                    "T2.binding.json",
                    "T3.binding.json",
                    "T4.binding.json",
                    "T5.binding.json",
                    "T6.binding.json",
                ],
            )

    def test_one_persistent_reader_executes_full_six_ratio_sequence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            state = self.start_reader(root)

            expected_ratios = [
                50,
                75,
                100,
                75,
                50,
                25,
            ]

            try:
                pid = state["process"].pid

                for index, ratio in enumerate(
                    expected_ratios,
                    start=1,
                ):
                    self.write_binding(
                        state["paths"][index - 1],
                        transition_index=index,
                        ratio=ratio,
                    )

                    self.trigger(state)

                    records = self.wait_for_record_count(
                        state["log"],
                        index,
                    )

                    self.assertEqual(
                        records[-1]["ratio"],
                        str(ratio),
                    )
                    self.assertEqual(
                        state["process"].pid,
                        pid,
                    )

                    original = state["paths"][index - 1]
                    consumed = module.consumed_path_for(
                        original
                    )

                    self.assertFalse(original.exists())
                    self.assertTrue(consumed.is_file())

                self.assertEqual(
                    [row["ratio"] for row in self.records(state["log"])],
                    ["50", "75", "100", "75", "50", "25"],
                )

            finally:
                stdout, stderr = self.stop_reader(state)

            self.assertIn(
                "FIFO reached EOF; automatic reader restart prohibited",
                stderr,
            )

    def test_missing_binding_fails_closed_without_actuation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            state = self.start_reader(root)

            self.trigger(state)

            stdout, stderr = self.stop_reader(state)

            self.assertEqual(
                state["process"].returncode,
                2,
            )
            self.assertIn(
                "BINDING_MISSING",
                stderr,
            )
            self.assertEqual(
                self.records(state["log"]),
                [],
            )

    def test_malformed_binding_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            state = self.start_reader(root)

            state["paths"][0].write_text(
                "{invalid",
                encoding="utf-8",
            )

            self.trigger(state)

            stdout, stderr = self.stop_reader(state)

            self.assertEqual(
                state["process"].returncode,
                2,
            )
            self.assertIn(
                "BINDING_JSON_INVALID",
                stderr,
            )
            self.assertEqual(
                self.records(state["log"]),
                [],
            )

    def test_invalid_schema_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            state = self.start_reader(root)

            self.write_binding(
                state["paths"][0],
                transition_index=1,
                ratio=50,
                schema="invalid-schema",
            )

            self.trigger(state)

            stdout, stderr = self.stop_reader(state)

            self.assertIn(
                "BINDING_SCHEMA_INVALID",
                stderr,
            )
            self.assertEqual(
                self.records(state["log"]),
                [],
            )

    def test_invalid_ratio_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            state = self.start_reader(root)

            self.write_binding(
                state["paths"][0],
                transition_index=1,
                ratio=13,
            )

            self.trigger(state)

            stdout, stderr = self.stop_reader(state)

            self.assertIn(
                "BINDING_RATIO_INVALID",
                stderr,
            )
            self.assertEqual(
                self.records(state["log"]),
                [],
            )

    def test_experiment_identity_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            state = self.start_reader(root)

            self.write_binding(
                state["paths"][0],
                transition_index=1,
                ratio=50,
                experiment_id="EXP-OTHER",
            )

            self.trigger(state)

            stdout, stderr = self.stop_reader(state)

            self.assertIn(
                "BINDING_EXPERIMENT_ID_MISMATCH",
                stderr,
            )
            self.assertEqual(
                self.records(state["log"]),
                [],
            )

    def test_transition_identity_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            state = self.start_reader(root)

            value = self.binding_value(
                transition_index=2,
                ratio=50,
            )

            state["paths"][0].write_text(
                json.dumps(value) + "\n",
                encoding="utf-8",
            )

            self.trigger(state)

            stdout, stderr = self.stop_reader(state)

            self.assertIn(
                "BINDING_TRANSITION_LABEL_MISMATCH",
                stderr,
            )
            self.assertEqual(
                self.records(state["log"]),
                [],
            )

    def test_stale_binding_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            state = self.start_reader(root)

            self.write_binding(
                state["paths"][0],
                transition_index=1,
                ratio=50,
                created_utc="2000-01-01T00:00:00Z",
            )

            self.trigger(state)

            stdout, stderr = self.stop_reader(state)

            self.assertIn(
                "BINDING_STALE",
                stderr,
            )
            self.assertEqual(
                self.records(state["log"]),
                [],
            )

    def test_preexisting_consumed_binding_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            state = self.start_reader(root)

            path = state["paths"][0]
            consumed = module.consumed_path_for(path)

            consumed.write_text(
                "{}\n",
                encoding="utf-8",
            )

            self.trigger(state)

            stdout, stderr = self.stop_reader(state)

            self.assertIn(
                "BINDING_ALREADY_CONSUMED",
                stderr,
            )
            self.assertEqual(
                self.records(state["log"]),
                [],
            )

    def test_binding_is_consumed_before_actuator_failure_and_not_replayed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            state = self.start_reader(
                root,
                stub_rc=17,
            )

            path = state["paths"][0]

            self.write_binding(
                path,
                transition_index=1,
                ratio=75,
            )

            self.trigger(state)

            stdout, stderr = self.stop_reader(state)

            records = self.records(state["log"])

            self.assertEqual(
                len(records),
                1,
            )
            self.assertEqual(
                records[0]["ratio"],
                "75",
            )

            self.assertFalse(path.exists())
            self.assertTrue(
                module.consumed_path_for(path).exists()
            )

            self.assertIn(
                "returncode=17; replay prohibited",
                stderr,
            )

    def test_invalid_token_never_consumes_binding_or_executes_actuator(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            state = self.start_reader(root)

            path = state["paths"][0]

            self.write_binding(
                path,
                transition_index=1,
                ratio=50,
            )

            os.write(
                state["writer_fd"],
                b"INVALID\n",
            )

            time.sleep(0.1)

            self.assertTrue(path.exists())
            self.assertFalse(
                module.consumed_path_for(path).exists()
            )
            self.assertEqual(
                self.records(state["log"]),
                [],
            )

            self.trigger(state)

            self.wait_for_record_count(
                state["log"],
                1,
            )

            stdout, stderr = self.stop_reader(state)

            self.assertIn(
                "PROMPT12_V2_READER_TOKEN_REJECTED",
                stderr,
            )

    def test_fifo_eof_without_trigger_fails_closed_without_actuation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            state = self.start_reader(root)

            stdout, stderr = self.stop_reader(state)

            self.assertEqual(
                state["process"].returncode,
                2,
            )
            self.assertIn(
                "FIFO reached EOF; automatic reader restart prohibited",
                stderr,
            )
            self.assertEqual(
                self.records(state["log"]),
                [],
            )


if __name__ == "__main__":
    unittest.main()
