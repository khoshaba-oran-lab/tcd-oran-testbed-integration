#!/usr/bin/env python3

import argparse
import json
import os
import pathlib
import subprocess
import sys
import time
import uuid


STATIONARITY_MARKER = "--stationarity-command"
FRESHNESS_MARKER = "--freshness-command"

STATIONARITY_JSON_TOKEN = "@PROMPT12_STATIONARITY_JSON@"
PRECONTROL_JSON_TOKEN = "@PROMPT12_PRECONTROL_JSON@"
DECISION_UTC_NS_TOKEN = "@PROMPT12_DECISION_UTC_NS@"
CANONICAL_INTERVALS_TOKEN = "@PROMPT12_CANONICAL_INTERVALS@"

SHELL_NAMES = {
    "bash",
    "dash",
    "sh",
    "zsh",
    "ksh",
}


class HandoffError(Exception):
    def __init__(self, reason, rc=70):
        super().__init__(reason)
        self.reason = reason
        self.rc = rc


class HandoffParser(argparse.ArgumentParser):
    def error(self, message):
        raise HandoffError(
            "ARGUMENTS_INVALID:" + message.replace(" ", "_"),
            64,
        )



def show_contract():
    print("PROMPT12_BOUNDED_PRECONTROL_HANDOFF_CONTRACT=1")
    print("COMMAND_FORM=ARGV_ONLY")
    print("STATIONARITY_STDOUT_FORM=EXACTLY_ONE_JSON_OBJECT")
    print("CANONICAL_INTERVALS_TOKEN=@PROMPT12_CANONICAL_INTERVALS@")
    print("PRECONTROL_CREATED_ONLY_AFTER_STATIONARITY_PASS=YES")
    print("PRECONTROL_OUTPUT_OVERWRITE_ALLOWED=NO")
    print("SHELL_STRING_EXECUTION_ALLOWED=NO")
    print("TRIGGER_WRITE_CAPABILITY=ABSENT")
    print("CONTROL_EXECUTED=NO")



def parse_invocation(argv):
    if argv.count(STATIONARITY_MARKER) != 1:
        raise HandoffError(
            "STATIONARITY_COMMAND_MARKER_COUNT_INVALID",
            64,
        )

    if argv.count(FRESHNESS_MARKER) != 1:
        raise HandoffError(
            "FRESHNESS_COMMAND_MARKER_COUNT_INVALID",
            64,
        )

    stationarity_index = argv.index(STATIONARITY_MARKER)
    freshness_index = argv.index(FRESHNESS_MARKER)

    if stationarity_index >= freshness_index:
        raise HandoffError("COMMAND_MARKER_ORDER_INVALID", 64)

    parser = HandoffParser(
        description=(
            "Run a bounded stationarity argv command, create a "
            "precontrol JSON through the existing freshness tool only "
            "after stationarity PASS, and preserve stationarity JSON "
            "as the sole stdout record."
        ),
        allow_abbrev=False,
    )
    parser.add_argument("--attempt-root", required=True)
    parser.add_argument("--precontrol-output", required=True)

    common = parser.parse_args(argv[:stationarity_index])
    stationarity = argv[
        stationarity_index + 1:freshness_index
    ]
    freshness = argv[freshness_index + 1:]

    validate_command(stationarity, "STATIONARITY")
    validate_command(freshness, "FRESHNESS")
    validate_freshness_template(freshness)

    return common, stationarity, freshness


def command_uses_shell_string(command):
    for index, value in enumerate(command[:-1]):
        name = pathlib.Path(value).name
        if (
            name in SHELL_NAMES
            and command[index + 1] in ("-c", "-lc")
        ):
            return True
    return False


def validate_command(command, label):
    if not isinstance(command, list) or not command:
        raise HandoffError(f"{label}_COMMAND_EMPTY", 64)

    for value in command:
        if (
            not isinstance(value, str)
            or not value
            or "\x00" in value
        ):
            raise HandoffError(
                f"{label}_COMMAND_ARGUMENT_INVALID",
                64,
            )

    if command_uses_shell_string(command):
        raise HandoffError(
            f"{label}_SHELL_STRING_PROHIBITED",
            64,
        )



def validate_freshness_template(command):
    if command.count(STATIONARITY_JSON_TOKEN) != 1:
        raise HandoffError(
            "FRESHNESS_STATIONARITY_TOKEN_COUNT_INVALID",
            64,
        )

    if command.count(PRECONTROL_JSON_TOKEN) != 1:
        raise HandoffError(
            "FRESHNESS_PRECONTROL_TOKEN_COUNT_INVALID",
            64,
        )

    if command.count(CANONICAL_INTERVALS_TOKEN) != 1:
        raise HandoffError(
            "FRESHNESS_CANONICAL_INTERVALS_TOKEN_COUNT_INVALID",
            64,
        )

    if command.count(DECISION_UTC_NS_TOKEN) > 1:
        raise HandoffError(
            "FRESHNESS_DECISION_TIME_TOKEN_COUNT_INVALID",
            64,
        )



def create_attempt(root):
    root.mkdir(parents=True, exist_ok=True)
    name = (
        f"attempt-{time.time_ns()}-"
        f"{os.getpid()}-{uuid.uuid4().hex}"
    )
    attempt = root / name
    attempt.mkdir(mode=0o750)
    (attempt / "logs").mkdir(mode=0o750)
    return attempt


def write_text_exclusive(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open(
        "x",
        encoding="utf-8",
        newline="\n",
    ) as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())


def write_json_exclusive(path, value):
    write_text_exclusive(
        path,
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )


def run_tool(label, command, attempt):
    try:
        proc = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="strict",
            check=False,
        )
    except OSError as exc:
        raise HandoffError(
            f"{label}_EXECUTION_FAILED:{type(exc).__name__}",
            70,
        ) from exc

    write_text_exclusive(
        attempt / "logs" / f"{label.lower()}.stdout.log",
        proc.stdout,
    )
    write_text_exclusive(
        attempt / "logs" / f"{label.lower()}.stderr.log",
        proc.stderr,
    )

    return proc


def parse_stationarity(stdout):
    try:
        record = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise HandoffError(
            "STATIONARITY_STDOUT_INVALID_JSON",
            65,
        ) from exc

    if not isinstance(record, dict):
        raise HandoffError(
            "STATIONARITY_STDOUT_NOT_OBJECT",
            65,
        )

    gate = record.get("output_stationarity_gate")
    if gate not in ("PASS", "FAIL"):
        raise HandoffError(
            "STATIONARITY_GATE_INVALID",
            65,
        )

    return record, gate


def resolve_freshness_command(
    template,
    stationarity_path,
    candidate_path,
    decision_utc_ns,
):
    replacements = {
        STATIONARITY_JSON_TOKEN: str(stationarity_path),
        PRECONTROL_JSON_TOKEN: str(candidate_path),
        DECISION_UTC_NS_TOKEN: str(decision_utc_ns),
    }

    return [
        replacements.get(value, value)
        for value in template
    ]


def validate_precontrol(path):
    if not path.is_file():
        raise HandoffError(
            "PRECONTROL_CANDIDATE_MISSING",
            65,
        )

    try:
        with path.open(encoding="utf-8") as handle:
            record = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoffError(
            "PRECONTROL_CANDIDATE_INVALID",
            65,
        ) from exc

    if not isinstance(record, dict):
        raise HandoffError(
            "PRECONTROL_CANDIDATE_NOT_OBJECT",
            65,
        )

    required = (
        record.get("selection")
            == "latest_50_complete_contiguous_samples",
        record.get("stationarity_window_binding_gate")
            == "PASS",
        record.get("output_stationarity_gate")
            == "PASS",
        record.get("freshness_gate")
            == "PASS",
        record.get("precontrol_admission_gate")
            == "PASS",
    )

    if not all(required):
        raise HandoffError(
            "PRECONTROL_CANDIDATE_GATE_NOT_PASS",
            65,
        )

    return record


def publish_exclusive(candidate, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)

    try:
        with candidate.open("rb") as source:
            payload = source.read()

        with destination.open("xb") as target:
            target.write(payload)
            target.flush()
            os.fsync(target.fileno())
    except FileExistsError as exc:
        raise HandoffError(
            "PRECONTROL_OUTPUT_ALREADY_EXISTS",
            65,
        ) from exc
    except OSError as exc:
        raise HandoffError(
            f"PRECONTROL_PUBLISH_FAILED:{type(exc).__name__}",
            70,
        ) from exc



def validate_canonical_snapshot(stationarity_record):
    value = stationarity_record.get(
        "canonical_interval_snapshot_path"
    )

    if not isinstance(value, str) or not value:
        raise HandoffError(
            "CANONICAL_INTERVAL_SNAPSHOT_PATH_MISSING",
            65,
        )

    path = pathlib.Path(value)

    if not path.is_absolute():
        raise HandoffError(
            "CANONICAL_INTERVAL_SNAPSHOT_PATH_NOT_ABSOLUTE",
            65,
        )

    try:
        resolved = path.resolve(strict=True)
        data = resolved.read_bytes()
    except OSError as exc:
        raise HandoffError(
            "CANONICAL_INTERVAL_SNAPSHOT_UNAVAILABLE",
            65,
        ) from exc

    if str(resolved) != value:
        raise HandoffError(
            "CANONICAL_INTERVAL_SNAPSHOT_PATH_NOT_CANONICAL",
            65,
        )

    if (
        resolved.name != "intervals.canonical.jsonl"
        or resolved.parent.name != "processed"
        or not resolved.parent.parent.name.startswith(
            "attempt-"
        )
    ):
        raise HandoffError(
            "CANONICAL_INTERVAL_SNAPSHOT_LAYOUT_INVALID",
            65,
        )

    if not data or not data.endswith(b"\n"):
        raise HandoffError(
            "CANONICAL_INTERVAL_SNAPSHOT_CONTENT_INVALID",
            65,
        )

    return value


def bind_canonical_snapshot(
    freshness_template,
    canonical_snapshot,
):
    resolved = [
        canonical_snapshot
        if value == CANONICAL_INTERVALS_TOKEN
        else value
        for value in freshness_template
    ]

    if CANONICAL_INTERVALS_TOKEN in resolved:
        raise HandoffError(
            "CANONICAL_INTERVALS_TOKEN_UNRESOLVED",
            64,
        )

    return resolved



def execute(
    args,
    stationarity_command,
    freshness_template,
):
    attempt_root = pathlib.Path(args.attempt_root)
    precontrol_output = pathlib.Path(
        args.precontrol_output
    )

    if os.path.lexists(str(precontrol_output)):
        raise HandoffError(
            "PRECONTROL_OUTPUT_ALREADY_EXISTS",
            65,
        )

    if (
        attempt_root.absolute()
        == precontrol_output.absolute()
    ):
        raise HandoffError(
            "ATTEMPT_ROOT_EQUALS_PRECONTROL_OUTPUT",
            64,
        )

    attempt = create_attempt(attempt_root)

    write_json_exclusive(
        attempt / "commands.json",
        {
            "stationarity_command":
                stationarity_command,
            "freshness_command_template":
                freshness_template,
            "precontrol_output":
                str(precontrol_output),
        },
    )

    stationarity_proc = run_tool(
        "STATIONARITY",
        stationarity_command,
        attempt,
    )

    if stationarity_proc.returncode != 0:
        raise HandoffError(
            "STATIONARITY_COMMAND_FAILED_RC_"
            + str(stationarity_proc.returncode),
            stationarity_proc.returncode or 70,
        )

    stationarity_record, gate = parse_stationarity(
        stationarity_proc.stdout
    )

    stationarity_path = (
        attempt / "stationarity.json"
    )
    write_text_exclusive(
        stationarity_path,
        stationarity_proc.stdout,
    )

    if gate == "FAIL":
        return stationarity_proc.stdout, attempt

    canonical_snapshot = validate_canonical_snapshot(
        stationarity_record
    )

    candidate_path = (
        attempt / "precontrol.candidate.json"
    )
    decision_utc_ns = time.time_ns()

    bound_template = bind_canonical_snapshot(
        freshness_template,
        canonical_snapshot,
    )

    freshness_command = resolve_freshness_command(
        bound_template,
        stationarity_path,
        candidate_path,
        decision_utc_ns,
    )

    write_json_exclusive(
        attempt
        / "freshness-command.resolved.json",
        freshness_command,
    )

    freshness_proc = run_tool(
        "FRESHNESS",
        freshness_command,
        attempt,
    )

    if freshness_proc.returncode != 0:
        raise HandoffError(
            "FRESHNESS_COMMAND_FAILED_RC_"
            + str(freshness_proc.returncode),
            freshness_proc.returncode or 70,
        )

    validate_precontrol(candidate_path)
    publish_exclusive(
        candidate_path,
        precontrol_output,
    )

    return stationarity_proc.stdout, attempt



def emit_stationarity(stdout):
    sys.stdout.write(stdout)
    if not stdout.endswith("\n"):
        sys.stdout.write("\n")
    sys.stdout.flush()


def main():
    if sys.argv[1:] == ["contract"]:
        show_contract()
        return 0

    attempt = None

    try:
        args, stationarity, freshness = parse_invocation(
            sys.argv[1:]
        )
        stdout, attempt = execute(
            args,
            stationarity,
            freshness,
        )
    except HandoffError as exc:
        print(
            "PROMPT12_PRECONTROL_HANDOFF_GATE=FAIL",
            file=sys.stderr,
        )
        print(
            f"FAIL_REASON={exc.reason}",
            file=sys.stderr,
        )
        if attempt is not None:
            print(
                f"ATTEMPT_DIR={attempt}",
                file=sys.stderr,
            )
        return exc.rc
    except (OSError, ValueError) as exc:
        print(
            "PROMPT12_PRECONTROL_HANDOFF_GATE=FAIL",
            file=sys.stderr,
        )
        print(
            "FAIL_REASON=UNEXPECTED_LOCAL_ERROR:"
            + type(exc).__name__,
            file=sys.stderr,
        )
        if attempt is not None:
            print(
                f"ATTEMPT_DIR={attempt}",
                file=sys.stderr,
            )
        return 70

    emit_stationarity(stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
