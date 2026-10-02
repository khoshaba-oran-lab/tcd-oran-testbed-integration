#!/usr/bin/env python3

import json
import os
import pathlib
import shlex
import socket
import subprocess
import sys
import tempfile
import unittest


HARNESS = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = HARNESS / "r6-f-portable-runtime-preflight.py"


class PortableRuntimePreflightTests(unittest.TestCase):

    def run_preflight(
        self,
        interpreter,
        require_jsonschema="yes",
    ):
        root = pathlib.Path(
            tempfile.mkdtemp(
                prefix="r6f-preflight-test-"
            )
        )

        self.addCleanup(
            lambda: subprocess.run(
                ["rm", "-rf", str(root)],
                check=False,
            )
        )

        output = root / "admission.json"

        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--python-executable",
                str(interpreter),
                "--require-jsonschema",
                require_jsonschema,
                "--output",
                str(output),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

        return proc, output

    def test_accepts_qualified_controller_interpreter(self):
        proc, output = self.run_preflight(
            sys.executable
        )

        self.assertEqual(
            proc.returncode,
            0,
            proc.stderr,
        )

        value = json.loads(
            output.read_text(encoding="utf-8")
        )

        self.assertEqual(
            value["schema"],
            "sci_oran_r6_f_portable_runtime_admission_v1",
        )
        self.assertEqual(
            value["python_executable"],
            sys.executable,
        )
        self.assertEqual(
            value["host"],
            socket.getfqdn(),
        )
        self.assertIs(
            value["jsonschema_required"],
            True,
        )
        self.assertIs(
            value["draft202012_capability"],
            True,
        )
        self.assertEqual(
            value["qualification_gate"],
            "PASS",
        )

    def test_accepts_explicit_absolute_interpreter_when_jsonschema_not_required(self):
        proc, output = self.run_preflight(
            sys.executable,
            require_jsonschema="no",
        )

        self.assertEqual(
            proc.returncode,
            0,
            proc.stderr,
        )

        value = json.loads(
            output.read_text(encoding="utf-8")
        )

        self.assertEqual(
            value["python_executable"],
            sys.executable,
        )

        self.assertIs(
            value["jsonschema_required"],
            False,
        )

        self.assertIsNone(
            value["jsonschema_version"],
        )

        self.assertIs(
            value["draft202012_capability"],
            False,
        )

        self.assertEqual(
            value["qualification_gate"],
            "PASS",
        )

    def test_rejects_missing_interpreter(self):
        proc, output = self.run_preflight(
            "/definitely/missing/r6f-python"
        )

        self.assertNotEqual(proc.returncode, 0)
        self.assertFalse(output.exists())
        self.assertIn(
            "PYTHON_EXECUTABLE_MISSING",
            proc.stderr,
        )

    def test_rejects_non_absolute_interpreter(self):
        proc, output = self.run_preflight(
            "python3"
        )

        self.assertNotEqual(proc.returncode, 0)
        self.assertFalse(output.exists())
        self.assertIn(
            "PYTHON_EXECUTABLE_NOT_ABSOLUTE",
            proc.stderr,
        )

    def test_rejects_non_executable_interpreter(self):
        with tempfile.TemporaryDirectory(
            prefix="r6f-nonexec-"
        ) as tmp:
            path = pathlib.Path(tmp) / "python"
            path.write_text(
                "#!/bin/sh\nexit 0\n",
                encoding="utf-8",
            )
            path.chmod(0o600)

            proc, output = self.run_preflight(path)

            self.assertNotEqual(proc.returncode, 0)
            self.assertFalse(output.exists())
            self.assertIn(
                "PYTHON_EXECUTABLE_NOT_EXECUTABLE",
                proc.stderr,
            )

    def test_rejects_missing_required_jsonschema_capability(self):
        with tempfile.TemporaryDirectory(
            prefix="r6f-no-site-"
        ) as tmp:
            wrapper = pathlib.Path(tmp) / "python3"
            wrapper.write_text(
                "#!/bin/sh\n"
                "exec "
                + shlex.quote(sys.executable)
                + ' -S "$@"\n',
                encoding="utf-8",
            )
            wrapper.chmod(0o700)

            proc, output = self.run_preflight(wrapper)

            self.assertNotEqual(proc.returncode, 0)
            self.assertFalse(output.exists())
            self.assertIn(
                "INTERPRETER_CAPABILITY_PROBE_FAILED",
                proc.stderr,
            )

    def test_source_contains_no_install_or_venv_creation_path(self):
        source = SCRIPT.read_text(encoding="utf-8")

        forbidden = (
            "pip install",
            "-m pip",
            "python -m venv",
            "virtualenv",
            "apt install",
        )

        for value in forbidden:
            self.assertNotIn(value, source)

    def test_admission_has_exact_required_field_set(self):
        proc, output = self.run_preflight(
            sys.executable
        )

        self.assertEqual(
            proc.returncode,
            0,
            proc.stderr,
        )

        value = json.loads(
            output.read_text(encoding="utf-8")
        )

        self.assertEqual(
            set(value),
            {
                "schema",
                "host",
                "python_executable",
                "python_version",
                "jsonschema_required",
                "jsonschema_version",
                "draft202012_capability",
                "qualification_gate",
            },
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
