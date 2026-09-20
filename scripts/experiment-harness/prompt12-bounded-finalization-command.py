#!/usr/bin/env python3

import argparse
import json
import os
import pathlib
import subprocess
import sys
import time
import uuid


TIMELINE_MARKER = "--timeline-command"
PIPELINE_MARKER = "--pipeline-command"
TIMELINE_TOKEN = "@PROMPT12_ACTUATOR_TIMELINE@"

SHELL_NAMES = {
    "bash",
    "dash",
    "sh",
    "zsh",
    "ksh",
}


class FinalizationError(Exception):
    def __init__(self, reason, rc=70):
        super().__init__(reason)
        self.reason = reason
        self.rc = rc


class FinalizationParser(argparse.ArgumentParser):
    def error(self, message):
        raise FinalizationError(
            "ARGUMENTS_INVALID:" + message.replace(" ", "_"),
            64,
        )


def show_contract():
    print("PROMPT12_BOUNDED_FINALIZATION_COMMAND_CONTRACT=1")
    print("COMMAND_FORM=ARGV_ONLY")
    print("EXECUTION_ORDER=ACTUATOR_TIMELINE_THEN_RECEIVER_PIPELINE")
    print("PIPELINE_WITHOUT_TIMELINE_PASS_ALLOWED=NO")
    print("OUTPUT_OVERWRITE_ALLOWED=NO")
    print("CHILD_PYTHON_BINDING=PYTHON_EXECUTABLE_PARENT_PREPENDED_TO_PATH")
    print("SHELL_STRING_EXECUTION_ALLOWED=NO")
    print("DOCKER_EXECUTION_CAPABILITY=ABSENT")
    print("TRAFFIC_EXECUTION_CAPABILITY=ABSENT")
    print("CONTROL_EXECUTED=NO")


def parse_invocation(argv):
    if argv.count(TIMELINE_MARKER) != 1:
        raise FinalizationError(
            "TIMELINE_COMMAND_MARKER_COUNT_INVALID",
            64,
        )

    if argv.count(PIPELINE_MARKER) != 1:
        raise FinalizationError(
            "PIPELINE_COMMAND_MARKER_COUNT_INVALID",
            64,
        )

    timeline_index = argv.index(TIMELINE_MARKER)
    pipeline_index = argv.index(PIPELINE_MARKER)

    if timeline_index >= pipeline_index:
        raise FinalizationError(
            "COMMAND_MARKER_ORDER_INVALID",
            64,
        )

    parser = FinalizationParser(
        description=(
            "Build the Prompt-12 actuator timeline first and run "
            "transition-aware receiver processing only after the "
            "timeline command and timeline evidence pass."
        ),
        allow_abbrev=False,
    )
    parser.add_argument("--attempt-root", required=True)
    parser.add_argument("--python-executable", required=True)
    parser.add_argument("--timeline-output", required=True)
    parser.add_argument("--staging-output", required=True)
    parser.add_argument("--canonical-output", required=True)
    parser.add_argument(
        "--expected-event-count",
        type=int,
        default=6,
    )

    common = parser.parse_args(argv[:timeline_index])
    timeline = argv[timeline_index + 1:pipeline_index]
    pipeline = argv[pipeline_index + 1:]

    validate_command(timeline, "TIMELINE")
    validate_command(pipeline, "PIPELINE")
    validate_templates(timeline, pipeline)

    if common.expected_event_count <= 0:
        raise FinalizationError(
            "EXPECTED_EVENT_COUNT_INVALID",
            64,
        )

    return common, timeline, pipeline


def command_uses_shell_string(command):
    for index, value in enumerate(command[:-1]):
        if (
            pathlib.Path(value).name in SHELL_NAMES
            and command[index + 1] in ("-c", "-lc")
        ):
            return True
    return False


def validate_command(command, label):
    if not isinstance(command, list) or not command:
        raise FinalizationError(
            f"{label}_COMMAND_EMPTY",
            64,
        )

    for value in command:
        if (
            not isinstance(value, str)
            or not value
            or "\x00" in value
        ):
            raise FinalizationError(
                f"{label}_COMMAND_ARGUMENT_INVALID",
                64,
            )

    if command_uses_shell_string(command):
        raise FinalizationError(
            f"{label}_SHELL_STRING_PROHIBITED",
            64,
        )


def validate_templates(timeline, pipeline):
    if timeline.count(TIMELINE_TOKEN) != 1:
        raise FinalizationError(
            "TIMELINE_OUTPUT_TOKEN_COUNT_INVALID",
            64,
        )

    if pipeline.count(TIMELINE_TOKEN) != 1:
        raise FinalizationError(
            "PIPELINE_TIMELINE_TOKEN_COUNT_INVALID",
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


def child_environment(python_executable):
    executable = pathlib.Path(python_executable)

    if (
        not executable.is_file()
        or not os.access(executable, os.X_OK)
    ):
        raise FinalizationError(
            "PYTHON_EXECUTABLE_INVALID",
            66,
        )

    environment = os.environ.copy()
    current_path = environment.get("PATH", "")
    python_directory = str(
        executable.resolve().parent
    )

    environment["PATH"] = (
        python_directory
        if not current_path
        else python_directory + os.pathsep + current_path
    )
    environment["PYTHONDONTWRITEBYTECODE"] = "1"

    return environment


def run_tool(label, command, attempt, environment):
    try:
        proc = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="strict",
            env=environment,
            check=False,
        )
    except OSError as exc:
        raise FinalizationError(
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


def load_jsonl(path, label):
    if not path.is_file():
        raise FinalizationError(
            f"{label}_MISSING",
            65,
        )

    rows = []

    try:
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue

                value = json.loads(line)

                if not isinstance(value, dict):
                    raise FinalizationError(
                        f"{label}_ROW_NOT_OBJECT:"
                        f"{line_number}",
                        65,
                    )

                rows.append(value)
    except json.JSONDecodeError as exc:
        raise FinalizationError(
            f"{label}_INVALID_JSONL",
            65,
        ) from exc
    except OSError as exc:
        raise FinalizationError(
            f"{label}_READ_FAILED:"
            f"{type(exc).__name__}",
            70,
        ) from exc

    if not rows:
        raise FinalizationError(
            f"{label}_EMPTY",
            65,
        )

    return rows


def reject_existing_outputs(paths):
    for label, path in paths:
        if os.path.lexists(str(path)):
            raise FinalizationError(
                f"{label}_ALREADY_EXISTS",
                65,
            )


def ensure_distinct_outputs(paths):
    normalized = [
        str(path.absolute())
        for path in paths
    ]

    if len(set(normalized)) != len(normalized):
        raise FinalizationError(
            "OUTPUT_PATHS_NOT_DISTINCT",
            64,
        )


def resolve_command(template, timeline_output):
    return [
        str(timeline_output)
        if value == TIMELINE_TOKEN
        else value
        for value in template
    ]


def execute(args, timeline_template, pipeline_template):
    attempt_root = pathlib.Path(args.attempt_root)
    timeline_output = pathlib.Path(args.timeline_output)
    staging_output = pathlib.Path(args.staging_output)
    canonical_output = pathlib.Path(args.canonical_output)

    outputs = [
        ("TIMELINE_OUTPUT", timeline_output),
        ("STAGING_OUTPUT", staging_output),
        ("CANONICAL_OUTPUT", canonical_output),
    ]

    ensure_distinct_outputs(
        [path for _, path in outputs]
    )
    reject_existing_outputs(outputs)

    environment = child_environment(
        args.python_executable
    )

    for _, path in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)

    attempt = create_attempt(attempt_root)

    timeline_command = resolve_command(
        timeline_template,
        timeline_output,
    )
    pipeline_command = resolve_command(
        pipeline_template,
        timeline_output,
    )

    write_json_exclusive(
        attempt / "commands.json",
        {
            "timeline_command": timeline_command,
            "pipeline_command": pipeline_command,
            "python_executable": args.python_executable,
            "expected_event_count":
                args.expected_event_count,
            "timeline_output": str(timeline_output),
            "staging_output": str(staging_output),
            "canonical_output": str(canonical_output),
        },
    )

    timeline_proc = run_tool(
        "TIMELINE",
        timeline_command,
        attempt,
        environment,
    )

    if timeline_proc.returncode != 0:
        raise FinalizationError(
            "TIMELINE_COMMAND_FAILED_RC_"
            + str(timeline_proc.returncode),
            timeline_proc.returncode or 70,
        )

    timeline_rows = load_jsonl(
        timeline_output,
        "TIMELINE_OUTPUT",
    )

    if len(timeline_rows) != args.expected_event_count:
        raise FinalizationError(
            "TIMELINE_EVENT_COUNT_INVALID:"
            + str(len(timeline_rows)),
            65,
        )

    pipeline_proc = run_tool(
        "PIPELINE",
        pipeline_command,
        attempt,
        environment,
    )

    if pipeline_proc.returncode != 0:
        raise FinalizationError(
            "PIPELINE_COMMAND_FAILED_RC_"
            + str(pipeline_proc.returncode),
            pipeline_proc.returncode or 70,
        )

    staging_rows = load_jsonl(
        staging_output,
        "STAGING_OUTPUT",
    )
    canonical_rows = load_jsonl(
        canonical_output,
        "CANONICAL_OUTPUT",
    )

    return {
        "schema":
            "sci_oran_prompt12_bounded_finalization_v1",
        "finalization_gate": "PASS",
        "execution_order": [
            "actuator_timeline",
            "receiver_pipeline",
        ],
        "timeline_event_count": len(timeline_rows),
        "staging_record_count": len(staging_rows),
        "canonical_record_count": len(canonical_rows),
        "timeline_output": str(timeline_output),
        "staging_output": str(staging_output),
        "canonical_output": str(canonical_output),
        "attempt_directory": str(attempt),
        "control_executed": False,
    }, attempt


def main():
    if sys.argv[1:] == ["contract"]:
        show_contract()
        return 0

    attempt = None

    try:
        args, timeline, pipeline = parse_invocation(
            sys.argv[1:]
        )
        report, attempt = execute(
            args,
            timeline,
            pipeline,
        )
    except FinalizationError as exc:
        print(
            "PROMPT12_BOUNDED_FINALIZATION_GATE=FAIL",
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
            "PROMPT12_BOUNDED_FINALIZATION_GATE=FAIL",
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

    sys.stdout.write(
        json.dumps(
            report,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
