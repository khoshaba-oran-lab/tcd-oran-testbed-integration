"""Regression tests for the Prompt 12 production local FIFO reader.

All execution tests use only temporary FIFOs and harmless Python stubs.
No FlexRIC, Docker, traffic, PRB control, scientific trigger, or real
actuator is used by this module.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
READER = (
    REPO_ROOT
    / "scripts"
    / "experiment-harness"
    / "prompt12-production-local-fifo-reader.py"
)


def load_reader_module():
    spec = importlib.util.spec_from_file_location(
        "prompt12_production_local_fifo_reader",
        READER,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load production reader module")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


READER_MODULE = load_reader_module()


def wait_until(predicate, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)

    raise AssertionError("timed out waiting for expected reader state")


def wait_for_text(path: Path, expected: str, timeout: float = 5.0) -> None:
    def present() -> bool:
        if not path.exists():
            return False
        return expected in path.read_text(encoding="utf-8")

    wait_until(present, timeout=timeout)


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []

    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


class ProductionLocalFifoReaderTests(unittest.TestCase):
    def make_stub(self, tmp_path: Path) -> Path:
        stub = tmp_path / "safe_stub.py"

        stub.write_text(
            """
import json
import os
import sys

record = {
    "ratio": os.environ.get("SCI_ORAN_MAX_PRB_RATIO"),
    "argv": sys.argv[1:],
}

with open(
    os.environ["PROMPT12_TEST_STUB_LOG"],
    "a",
    encoding="utf-8",
) as f:
    f.write(json.dumps(record, sort_keys=True) + "\\n")
    f.flush()
    os.fsync(f.fileno())

raise SystemExit(
    int(os.environ.get("PROMPT12_TEST_STUB_EXIT_CODE", "0"))
)
""".lstrip(),
            encoding="utf-8",
        )

        return stub

    def start_reader(
        self,
        tmp_path: Path,
        *,
        ratio: str,
        stub_exit_code: int = 0,
        stub_args: list[str] | None = None,
    ) -> dict:
        fifo = tmp_path / "actuator.fifo"
        log = tmp_path / "stub.jsonl"
        stdout_path = tmp_path / "reader.out"
        stderr_path = tmp_path / "reader.err"
        stub = self.make_stub(tmp_path)

        os.mkfifo(fifo)
        log.write_text("", encoding="utf-8")

        actuator_argv = [sys.executable, str(stub)]
        actuator_argv.extend(stub_args or [])

        env = os.environ.copy()
        env["SCI_ORAN_MAX_PRB_RATIO"] = ratio
        env["PROMPT12_TEST_STUB_LOG"] = str(log)
        env["PROMPT12_TEST_STUB_EXIT_CODE"] = str(stub_exit_code)

        stdout_handle = stdout_path.open("w", encoding="utf-8")
        stderr_handle = stderr_path.open("w", encoding="utf-8")

        process = subprocess.Popen(
            [
                sys.executable,
                str(READER),
                "--fifo-path",
                str(fifo),
                "--actuator-argv-json",
                json.dumps(actuator_argv),
            ],
            env=env,
            stdout=stdout_handle,
            stderr=stderr_handle,
            text=True,
            shell=False,
        )

        wait_for_text(
            stdout_path,
            f"PROMPT12_V2_READER_PREARMED=YES ratio_pct={ratio}",
        )

        return {
            "process": process,
            "fifo": fifo,
            "log": log,
            "stdout": stdout_path,
            "stderr": stderr_path,
            "stdout_handle": stdout_handle,
            "stderr_handle": stderr_handle,
        }

    def close_reader_handles(self, state: dict) -> None:
        state["stdout_handle"].close()
        state["stderr_handle"].close()

    def test_static_production_boundary(self) -> None:
        source = READER.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(READER))

        subprocess_run_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "subprocess"
            and node.func.attr == "run"
        ]

        self.assertEqual(len(subprocess_run_calls), 1)
        self.assertIn("shell=False", source)
        self.assertNotIn("shell=True", source)
        self.assertNotIn("os.mkfifo", source)

        self.assertNotIn("U_CMD=", source)
        self.assertNotIn("U_ACK=", source)
        self.assertNotIn("PRB_ACTUATOR_APPLIED=", source)

    def test_invalid_actuator_argv_fails_closed(self) -> None:
        invalid_values = [
            "",
            "not-json",
            "{}",
            "[]",
            '[""]',
            '["ok", ""]',
        ]

        for raw in invalid_values:
            with self.subTest(raw=raw):
                with self.assertRaises(READER_MODULE.ReaderContractError):
                    READER_MODULE.parse_actuator_argv(raw)

    def test_missing_or_invalid_ratio_fails_closed(self) -> None:
        invalid_envs = [
            {},
            {"SCI_ORAN_MAX_PRB_RATIO": ""},
            {"SCI_ORAN_MAX_PRB_RATIO": "13"},
            {"SCI_ORAN_MAX_PRB_RATIO": "26"},
            {"SCI_ORAN_MAX_PRB_RATIO": "101"},
        ]

        for env in invalid_envs:
            with self.subTest(env=env):
                with self.assertRaises(READER_MODULE.ReaderContractError):
                    READER_MODULE.validate_prebound_ratio(env)

    def test_allowed_ratios_are_accepted(self) -> None:
        for ratio in ["25", "50", "75", "100"]:
            with self.subTest(ratio=ratio):
                actual = READER_MODULE.validate_prebound_ratio(
                    {"SCI_ORAN_MAX_PRB_RATIO": ratio}
                )
                self.assertEqual(actual, ratio)

    def test_non_fifo_path_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="prompt12-reader-unittest-"
        ) as tmp:
            tmp_path = Path(tmp)
            regular_file = tmp_path / "not-a-fifo"
            regular_file.write_text("not a fifo", encoding="utf-8")

            with self.assertRaises(READER_MODULE.ReaderContractError):
                READER_MODULE.validate_existing_fifo(str(regular_file))

    def test_missing_ratio_cli_fails_before_fifo_open(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="prompt12-reader-unittest-"
        ) as tmp:
            tmp_path = Path(tmp)

            env = os.environ.copy()
            env.pop("SCI_ORAN_MAX_PRB_RATIO", None)

            completed = subprocess.run(
                [
                    sys.executable,
                    str(READER),
                    "--fifo-path",
                    str(tmp_path / "does-not-exist.fifo"),
                    "--actuator-argv-json",
                    json.dumps(
                        [
                            sys.executable,
                            "-c",
                            "raise SystemExit(0)",
                        ]
                    ),
                ],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=False,
                check=False,
                timeout=5,
            )

            self.assertEqual(completed.returncode, 2)
            self.assertIn(
                "SCI_ORAN_MAX_PRB_RATIO must be pre-bound before reader start",
                completed.stderr,
            )

    def test_invalid_ratio_cli_fails_before_fifo_open(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="prompt12-reader-unittest-"
        ) as tmp:
            tmp_path = Path(tmp)

            env = os.environ.copy()
            env["SCI_ORAN_MAX_PRB_RATIO"] = "13"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(READER),
                    "--fifo-path",
                    str(tmp_path / "does-not-exist.fifo"),
                    "--actuator-argv-json",
                    json.dumps(
                        [
                            sys.executable,
                            "-c",
                            "raise SystemExit(0)",
                        ]
                    ),
                ],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=False,
                check=False,
                timeout=5,
            )

            self.assertEqual(completed.returncode, 2)
            self.assertIn(
                "invalid SCI_ORAN_MAX_PRB_RATIO='13'",
                completed.stderr,
            )

    def test_invalid_token_then_trigger_executes_stub_exactly_once(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(
            prefix="prompt12-reader-unittest-"
        ) as tmp:
            tmp_path = Path(tmp)

            state = self.start_reader(
                tmp_path,
                ratio="50",
                stub_exit_code=0,
                stub_args=["--probe", "alpha beta"],
            )

            process = state["process"]
            writer_fd = os.open(state["fifo"], os.O_WRONLY)

            try:
                os.write(writer_fd, b"INVALID\n")

                wait_for_text(
                    state["stderr"],
                    'PROMPT12_V2_READER_TOKEN_REJECTED="INVALID\\n"',
                )

                self.assertEqual(read_jsonl(state["log"]), [])

                os.write(writer_fd, b"TRIGGER\n")

                wait_until(
                    lambda: len(read_jsonl(state["log"])) == 1,
                )

                wait_for_text(
                    state["stdout"],
                    "PROMPT12_V2_READER_ACTUATOR_EXECUTION_COMPLETED=YES",
                )

                records = read_jsonl(state["log"])

                self.assertEqual(len(records), 1)
                self.assertEqual(records[0]["ratio"], "50")
                self.assertEqual(
                    records[0]["argv"],
                    ["--probe", "alpha beta"],
                )

            finally:
                os.close(writer_fd)

            self.assertEqual(process.wait(timeout=5), 2)
            self.close_reader_handles(state)

            self.assertEqual(len(read_jsonl(state["log"])), 1)
            self.assertIn(
                "FIFO reached EOF; automatic reader restart prohibited",
                state["stderr"].read_text(encoding="utf-8"),
            )

    def test_actuator_failure_has_no_retry_or_replay(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="prompt12-reader-unittest-"
        ) as tmp:
            tmp_path = Path(tmp)

            state = self.start_reader(
                tmp_path,
                ratio="75",
                stub_exit_code=17,
                stub_args=["--probe", "failure"],
            )

            process = state["process"]
            writer_fd = os.open(state["fifo"], os.O_WRONLY)

            try:
                os.write(writer_fd, b"TRIGGER\n")
                self.assertEqual(process.wait(timeout=5), 2)
            finally:
                os.close(writer_fd)

            self.close_reader_handles(state)

            records = read_jsonl(state["log"])

            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["ratio"], "75")
            self.assertEqual(records[0]["argv"], ["--probe", "failure"])

            stdout = state["stdout"].read_text(encoding="utf-8")
            stderr = state["stderr"].read_text(encoding="utf-8")

            self.assertIn(
                "PROMPT12_V2_READER_TRIGGER_ACCEPTED=YES",
                stdout,
            )
            self.assertNotIn(
                "PROMPT12_V2_READER_ACTUATOR_EXECUTION_COMPLETED=YES",
                stdout,
            )
            self.assertIn(
                "returncode=17; replay prohibited",
                stderr,
            )

    def test_fifo_eof_without_trigger_fails_closed_without_actuation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(
            prefix="prompt12-reader-unittest-"
        ) as tmp:
            tmp_path = Path(tmp)

            state = self.start_reader(
                tmp_path,
                ratio="25",
                stub_exit_code=0,
            )

            process = state["process"]

            writer_fd = os.open(state["fifo"], os.O_WRONLY)
            os.close(writer_fd)

            self.assertEqual(process.wait(timeout=5), 2)
            self.close_reader_handles(state)

            self.assertEqual(read_jsonl(state["log"]), [])
            self.assertIn(
                "FIFO reached EOF; automatic reader restart prohibited",
                state["stderr"].read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
