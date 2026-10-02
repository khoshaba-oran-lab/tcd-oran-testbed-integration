#!/usr/bin/env python3

import argparse
import json
import os
import pathlib
import socket
import subprocess
import sys


SCHEMA = "sci_oran_r6_f_portable_runtime_admission_v1"


def fail(message):
    raise ValueError(message)


def parser():
    value = argparse.ArgumentParser(
        description=(
            "Read-only R6-F portable-runtime capability preflight. "
            "The tool validates one explicit Python interpreter and writes "
            "one admission record. It performs no package installation, "
            "venv creation, lifecycle action, traffic generation, PRB "
            "control, or Prompt-12 scientific trigger."
        )
    )

    value.add_argument("--python-executable", required=True)
    value.add_argument(
        "--require-jsonschema",
        required=True,
        choices=("yes", "no"),
    )
    value.add_argument("--output", required=True)

    return value


def require_interpreter(value):
    raw = str(value).strip()

    if not raw:
        fail("PYTHON_EXECUTABLE_EMPTY")

    path = pathlib.Path(raw)

    if not path.is_absolute():
        fail("PYTHON_EXECUTABLE_NOT_ABSOLUTE")

    if not path.is_file():
        fail("PYTHON_EXECUTABLE_MISSING")

    if not os.access(path, os.X_OK):
        fail("PYTHON_EXECUTABLE_NOT_EXECUTABLE")

    return path


def require_output(value):
    raw = str(value).strip()

    if not raw:
        fail("OUTPUT_EMPTY")

    path = pathlib.Path(raw)

    if not path.is_absolute():
        fail("OUTPUT_NOT_ABSOLUTE")

    if not path.parent.is_dir():
        fail("OUTPUT_PARENT_MISSING")

    if os.path.lexists(str(path)):
        fail("OUTPUT_ALREADY_EXISTS")

    return path


PROBE = r'''
import importlib.metadata
import json
import sys

required = sys.argv[1] == "yes"

result = {
    "python_version": sys.version.split()[0],
    "jsonschema_version": None,
    "draft202012_capability": False,
}

if required:
    try:
        from jsonschema import Draft202012Validator
        from jsonschema.exceptions import ValidationError
    except Exception as exc:
        print(
            json.dumps(
                {
                    "probe_gate": "FAIL",
                    "reason": "JSONSCHEMA_IMPORT_FAILED",
                    "detail": type(exc).__name__ + ":" + str(exc),
                },
                sort_keys=True,
            )
        )
        raise SystemExit(20)

    try:
        version = importlib.metadata.version("jsonschema")

        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "value": {"type": "integer"},
            },
            "required": ["value"],
            "additionalProperties": False,
        }

        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        validator.validate({"value": 1})

        try:
            validator.validate({"value": "invalid"})
        except ValidationError:
            rejected = True
        else:
            rejected = False

        if not rejected:
            raise RuntimeError("INVALID_INSTANCE_NOT_REJECTED")

        result["jsonschema_version"] = version
        result["draft202012_capability"] = True

    except Exception as exc:
        print(
            json.dumps(
                {
                    "probe_gate": "FAIL",
                    "reason": "DRAFT202012_CAPABILITY_FAILED",
                    "detail": type(exc).__name__ + ":" + str(exc),
                },
                sort_keys=True,
            )
        )
        raise SystemExit(21)

print(
    json.dumps(
        {
            "probe_gate": "PASS",
            **result,
        },
        sort_keys=True,
    )
)
'''


def probe(interpreter, require_jsonschema):
    proc = subprocess.run(
        [
            str(interpreter),
            "-c",
            PROBE,
            "yes" if require_jsonschema else "no",
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    if proc.returncode != 0:
        fail(
            "INTERPRETER_CAPABILITY_PROBE_FAILED:"
            + str(proc.returncode)
            + ":"
            + proc.stdout.strip()
            + ":"
            + proc.stderr.strip()
        )

    lines = [
        line
        for line in proc.stdout.splitlines()
        if line.strip()
    ]

    if len(lines) != 1:
        fail("INTERPRETER_CAPABILITY_PROBE_OUTPUT_INVALID")

    try:
        value = json.loads(lines[0])
    except json.JSONDecodeError as exc:
        fail("INTERPRETER_CAPABILITY_PROBE_JSON_INVALID:" + str(exc))

    if value.get("probe_gate") != "PASS":
        fail("INTERPRETER_CAPABILITY_PROBE_GATE_NOT_PASS")

    if not isinstance(value.get("python_version"), str):
        fail("PYTHON_VERSION_INVALID")

    if require_jsonschema:
        if not isinstance(value.get("jsonschema_version"), str):
            fail("JSONSCHEMA_VERSION_INVALID")

        if value.get("draft202012_capability") is not True:
            fail("DRAFT202012_CAPABILITY_NOT_PASS")

    return value


def write_exclusive(path, value):
    data = (
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")

    fd = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )

    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
    except Exception:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise


def main():
    args = parser().parse_args()

    try:
        interpreter = require_interpreter(
            args.python_executable
        )

        output = require_output(args.output)

        require_jsonschema = (
            args.require_jsonschema == "yes"
        )

        result = probe(
            interpreter,
            require_jsonschema,
        )

        record = {
            "schema": SCHEMA,
            "host": socket.getfqdn(),
            "python_executable": str(interpreter),
            "python_version": result["python_version"],
            "jsonschema_required": require_jsonschema,
            "jsonschema_version": result[
                "jsonschema_version"
            ],
            "draft202012_capability": result[
                "draft202012_capability"
            ],
            "qualification_gate": "PASS",
        }

        write_exclusive(output, record)

    except Exception as exc:
        print(
            "R6_F_PORTABLE_RUNTIME_PREFLIGHT_GATE=FAIL",
            file=sys.stderr,
        )
        print(
            "ERROR="
            + type(exc).__name__
            + ":"
            + str(exc),
            file=sys.stderr,
        )
        print(
            "PACKAGE_INSTALL_PERFORMED=NO",
            file=sys.stderr,
        )
        print(
            "VENV_CREATION_PERFORMED=NO",
            file=sys.stderr,
        )
        print(
            "SCIENTIFIC_OPERATION_PERFORMED=NO",
            file=sys.stderr,
        )
        return 1

    print("R6_F_PORTABLE_RUNTIME_PREFLIGHT_GATE=PASS")
    print("ADMISSION_SCHEMA=" + SCHEMA)
    print("ADMISSION_HOST=" + record["host"])
    print(
        "ADMISSION_PYTHON_EXECUTABLE="
        + record["python_executable"]
    )
    print(
        "ADMISSION_PYTHON_VERSION="
        + record["python_version"]
    )
    print(
        "ADMISSION_JSONSCHEMA_REQUIRED="
        + (
            "YES"
            if record["jsonschema_required"]
            else "NO"
        )
    )
    print(
        "ADMISSION_JSONSCHEMA_VERSION="
        + str(record["jsonschema_version"])
    )
    print(
        "ADMISSION_DRAFT202012_CAPABILITY="
        + (
            "PASS"
            if record["draft202012_capability"]
            else "NOT_REQUIRED"
        )
    )
    print("ADMISSION_QUALIFICATION_GATE=PASS")
    print("PACKAGE_INSTALL_PERFORMED=NO")
    print("VENV_CREATION_PERFORMED=NO")
    print("SCIENTIFIC_OPERATION_PERFORMED=NO")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
