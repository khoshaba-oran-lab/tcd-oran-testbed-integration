#!/usr/bin/env python3

import argparse
import datetime
import json
import os
import pathlib
import re
import stat
import sys


PROFILE_SCHEMA = "sci_oran_prompt12_bounded_sequence_runtime_profile_v1"
TIMELINE_TOKEN = "@PROMPT12_ACTUATOR_TIMELINE@"
RATIOS = (50, 75, 100, 75, 50, 25)

FROZEN_KEYS = {
    "python_executable",
    "tool_paths",
    "traffic_duration_s",
    "trigger_token",
    "stable_ms",
    "snapshot_timeout_ms",
    "timeline_readiness_poll_ms",
    "timeline_readiness_timeout_ms",
}

TOOL_KEYS = {
    "canonicalizer",
    "finalization_adapter",
    "freshness_evaluator",
    "freshness_policy",
    "parser",
    "precontrol_handoff",
    "receiver_pipeline",
    "schema",
    "stationarity_adapter",
    "stationarity_evaluator",
    "timeline_builder",
    "traffic_adapter",
    "trigger_executor",
}

DATA_KEYS = {
    "actuator_ack_input",
    "actuator_applied_input",
    "actuator_command_input",
}

PROFILE_KEYS = {
    "schema",
    "experiment_id",
    "run_id",
    "run_directory",
    "receiver_container_name",
    "actuator_fifo_path",
    "python_executable",
    "tool_paths",
    "data_paths",
    "traffic_duration_s",
    "max_age_ms",
    "trigger_token",
    "control_authorization_token",
    "stable_ms",
    "snapshot_timeout_ms",
    "timeline_readiness_timeout_ms",
    "timeline_readiness_poll_ms",
    "incremental_timeline_command_json",
    "ratio_binding_paths",
}

EXPERIMENT_RE = re.compile(
    r"^EXP-(\d{8})-DL-18000K-(R0[1-4])$"
)
RUN_RE = re.compile(
    r"^RUN-(\d{8})T(\d{6})Z-(\d{3})$"
)


class MaterializerError(Exception):
    def __init__(self, reason, rc=65):
        super().__init__(reason)
        self.reason = reason
        self.rc = rc


def show_contract():
    print("PROMPT12_RUNTIME_PROFILE_MATERIALIZER_CONTRACT=1")
    print("PROFILE_SCHEMA=" + PROFILE_SCHEMA)
    print("OUTPUT_SCOPE=EXTERNAL_EVIDENCE_ROOT")
    print("RUN_DIRECTORY_CREATION=EXCLUSIVE")
    print("PROFILE_OUTPUT_CREATION=EXCLUSIVE")
    print("IDENTITY_REPLAY_ALLOWED=NO")
    print("ACTUATOR_FIFO_DISCOVERY=BROAD_SCAN_FORBIDDEN")
    print("ACTUATOR_FIFO_VALIDATION=EXPLICIT_PATH_AND_FIFO_TYPE")
    print("AUTHORIZATION_DEFAULTS_ALLOWED=NO")
    print("COMMAND_EXECUTION_CAPABILITY=ABSENT")
    print("DOCKER_EXECUTION_CAPABILITY=ABSENT")
    print("TRAFFIC_EXECUTION_CAPABILITY=ABSENT")
    print("CONTROL_EXECUTED=NO")


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Allocate one fresh Prompt-12 run directory and materialize "
            "one concrete, non-executed bounded-sequence runtime profile."
        ),
        allow_abbrev=False,
    )
    parser.add_argument("--evidence-root", required=True)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--frozen-config", required=True)
    parser.add_argument("--actuator-fifo-path", required=True)
    parser.add_argument("--max-age-ms", required=True, type=int)
    parser.add_argument("--control-authorization-token", required=True)
    return parser.parse_args()


def load_object(path, label):
    try:
        with path.open(encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise MaterializerError(
            f"{label}_READ_FAILED:{type(exc).__name__}"
        ) from exc
    if not isinstance(value, dict):
        raise MaterializerError(f"{label}_NOT_OBJECT")
    return value


def require_exact_keys(value, expected, label):
    actual = set(value)
    if actual != expected:
        missing = ",".join(sorted(expected - actual)) or "NONE"
        extra = ",".join(sorted(actual - expected)) or "NONE"
        raise MaterializerError(
            f"{label}_KEYS_INVALID:MISSING_{missing}:EXTRA_{extra}"
        )


def positive_int(value, label):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise MaterializerError(f"{label}_INVALID")
    return value


def nonnegative_int(value, label):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise MaterializerError(f"{label}_INVALID")
    return value


def nonempty_string(value, label):
    if not isinstance(value, str) or not value or "\0" in value:
        raise MaterializerError(f"{label}_INVALID")
    return value


def absolute_file(value, label, executable=False):
    text = nonempty_string(value, label)
    path = pathlib.Path(text)
    if not path.is_absolute() or not path.is_file():
        raise MaterializerError(f"{label}_NOT_ABSOLUTE_FILE")
    if executable and not os.access(path, os.X_OK):
        raise MaterializerError(f"{label}_NOT_EXECUTABLE")
    return path


def validate_identity(experiment_id, run_id):
    experiment_match = EXPERIMENT_RE.fullmatch(experiment_id)
    if experiment_match is None:
        raise MaterializerError("EXPERIMENT_ID_INVALID")
    run_match = RUN_RE.fullmatch(run_id)
    if run_match is None:
        raise MaterializerError("RUN_ID_INVALID")
    try:
        datetime.datetime.strptime(experiment_match.group(1), "%Y%m%d")
        datetime.datetime.strptime(
            run_match.group(1) + run_match.group(2),
            "%Y%m%d%H%M%S",
        )
    except ValueError as exc:
        raise MaterializerError("IDENTITY_TIMESTAMP_INVALID") from exc
    if experiment_match.group(1) != run_match.group(1):
        raise MaterializerError("IDENTITY_DATE_MISMATCH")


def validate_fifo(value):
    path = pathlib.Path(nonempty_string(value, "ACTUATOR_FIFO_PATH"))
    if not path.is_absolute():
        raise MaterializerError("ACTUATOR_FIFO_PATH_NOT_ABSOLUTE")
    try:
        mode = path.stat().st_mode
    except OSError as exc:
        raise MaterializerError("ACTUATOR_FIFO_PATH_UNAVAILABLE") from exc
    if not stat.S_ISFIFO(mode):
        raise MaterializerError("ACTUATOR_FIFO_PATH_NOT_FIFO")
    return path


def validate_frozen(path):
    frozen = load_object(path, "FROZEN_CONFIG")
    require_exact_keys(frozen, FROZEN_KEYS, "FROZEN_CONFIG")
    python_path = absolute_file(
        frozen["python_executable"],
        "PYTHON_EXECUTABLE",
        executable=True,
    )
    tools = frozen["tool_paths"]
    if not isinstance(tools, dict):
        raise MaterializerError("TOOL_PATHS_NOT_OBJECT")
    require_exact_keys(tools, TOOL_KEYS, "TOOL_PATHS")
    validated_tools = {}
    for name in sorted(TOOL_KEYS):
        validated_tools[name] = str(
            absolute_file(tools[name], f"TOOL_PATH_{name.upper()}")
        )
    return {
        "python_executable": str(python_path),
        "tool_paths": validated_tools,
        "traffic_duration_s": positive_int(
            frozen["traffic_duration_s"], "TRAFFIC_DURATION_S"
        ),
        "trigger_token": nonempty_string(
            frozen["trigger_token"], "TRIGGER_TOKEN"
        ),
        "stable_ms": nonnegative_int(frozen["stable_ms"], "STABLE_MS"),
        "snapshot_timeout_ms": positive_int(
            frozen["snapshot_timeout_ms"], "SNAPSHOT_TIMEOUT_MS"
        ),
        "timeline_readiness_poll_ms": positive_int(
            frozen["timeline_readiness_poll_ms"],
            "TIMELINE_READINESS_POLL_MS",
        ),
        "timeline_readiness_timeout_ms": positive_int(
            frozen["timeline_readiness_timeout_ms"],
            "TIMELINE_READINESS_TIMEOUT_MS",
        ),
    }


def write_json_exclusive(path, value, mode=0o600):
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, mode)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def receiver_name(run_id):
    value = "prompt12-" + run_id.lower() + "-receiver"
    if len(value) > 63 or re.fullmatch(r"[a-z0-9][a-z0-9_.-]*", value) is None:
        raise MaterializerError("RECEIVER_CONTAINER_NAME_INVALID")
    return value


def timeline_command(frozen, experiment_id, run_id, data_paths, ratios):
    tools = frozen["tool_paths"]
    return [
        frozen["python_executable"],
        tools["timeline_builder"],
        "--schema",
        tools["schema"],
        "--experiment-id",
        experiment_id,
        "--run-id",
        run_id,
        "--requested-ratios",
        ",".join(str(value) for value in ratios),
        "--command-input",
        data_paths["actuator_command_input"],
        "--applied-input",
        data_paths["actuator_applied_input"],
        "--ack-input",
        data_paths["actuator_ack_input"],
        "--output",
        TIMELINE_TOKEN,
    ]


def execute(args):
    validate_identity(args.experiment_id, args.run_id)
    frozen_path = absolute_file(args.frozen_config, "FROZEN_CONFIG")
    frozen = validate_frozen(frozen_path)
    fifo_path = validate_fifo(args.actuator_fifo_path)
    max_age_ms = positive_int(args.max_age_ms, "MAX_AGE_MS")
    authorization = nonempty_string(
        args.control_authorization_token,
        "CONTROL_AUTHORIZATION_TOKEN",
    )

    evidence_root = pathlib.Path(args.evidence_root)
    if not evidence_root.is_absolute() or not evidence_root.is_dir():
        raise MaterializerError("EVIDENCE_ROOT_NOT_ABSOLUTE_DIRECTORY")

    experiment_directory = evidence_root / args.experiment_id
    run_directory = experiment_directory / args.run_id
    if os.path.lexists(str(run_directory)):
        raise MaterializerError("RUN_DIRECTORY_ALREADY_EXISTS")

    experiment_directory.mkdir(mode=0o750, exist_ok=True)
    if not experiment_directory.is_dir():
        raise MaterializerError("EXPERIMENT_DIRECTORY_INVALID")
    run_directory.mkdir(mode=0o750)

    directories = (
        run_directory / "raw",
        run_directory / "raw" / "actuator",
        run_directory / "processed",
        run_directory / "logs",
        run_directory / "runtime",
        run_directory / "runtime" / "incremental-timeline",
    )
    for directory in directories:
        directory.mkdir(mode=0o750)

    data_paths = {
        "actuator_command_input": str(
            run_directory / "raw" / "actuator" / "command.jsonl"
        ),
        "actuator_applied_input": str(
            run_directory / "raw" / "actuator" / "applied.jsonl"
        ),
        "actuator_ack_input": str(
            run_directory / "raw" / "actuator" / "ack.jsonl"
        ),
    }
    require_exact_keys(data_paths, DATA_KEYS, "DATA_PATHS")

    ratio_binding_directory = (
        run_directory / "runtime" / "ratio-bindings"
    )
    ratio_binding_directory.mkdir(
        mode=0o700,
        exist_ok=False,
    )

    ratio_binding_paths = [
        str(
            ratio_binding_directory
            / f"T{index}.binding.json"
        )
        for index in range(1, 7)
    ]

    timeline_paths = []
    for index in range(1, 7):
        path = (
            run_directory
            / "runtime"
            / "incremental-timeline"
            / f"T{index}-timeline-command.json"
        )
        write_json_exclusive(
            path,
            timeline_command(
                frozen,
                args.experiment_id,
                args.run_id,
                data_paths,
                RATIOS[:index],
            ),
        )
        timeline_paths.append(str(path))

    profile = {
        "schema": PROFILE_SCHEMA,
        "experiment_id": args.experiment_id,
        "run_id": args.run_id,
        "run_directory": str(run_directory),
        "receiver_container_name": receiver_name(args.run_id),
        "actuator_fifo_path": str(fifo_path),
        "ratio_binding_paths": ratio_binding_paths,
        "python_executable": frozen["python_executable"],
        "tool_paths": frozen["tool_paths"],
        "data_paths": data_paths,
        "traffic_duration_s": frozen["traffic_duration_s"],
        "max_age_ms": max_age_ms,
        "trigger_token": frozen["trigger_token"],
        "control_authorization_token": authorization,
        "stable_ms": frozen["stable_ms"],
        "snapshot_timeout_ms": frozen["snapshot_timeout_ms"],
        "timeline_readiness_timeout_ms": frozen[
            "timeline_readiness_timeout_ms"
        ],
        "timeline_readiness_poll_ms": frozen[
            "timeline_readiness_poll_ms"
        ],
        "incremental_timeline_command_json": timeline_paths,
    }
    require_exact_keys(profile, PROFILE_KEYS, "RUNTIME_PROFILE")

    profile_path = run_directory / "runtime" / "runtime-profile.json"
    write_json_exclusive(profile_path, profile)

    allocation_path = run_directory / "runtime" / "allocation.json"
    allocation = {
        "schema": "sci_oran_prompt12_bounded_run_allocation_v1",
        "experiment_id": args.experiment_id,
        "run_id": args.run_id,
        "run_directory": str(run_directory),
        "runtime_profile": str(profile_path),
        "receiver_container_name": profile["receiver_container_name"],
        "actuator_fifo_path": str(fifo_path),
        "authorization_value_recorded": False,
        "command_executed": False,
        "control_executed": False,
    }
    write_json_exclusive(allocation_path, allocation)

    return {
        "schema": "sci_oran_prompt12_bounded_runtime_profile_materialization_v1",
        "materialization_gate": "PASS",
        "experiment_id": args.experiment_id,
        "run_id": args.run_id,
        "run_directory": str(run_directory),
        "runtime_profile": str(profile_path),
        "allocation_record": str(allocation_path),
        "incremental_timeline_command_count": len(timeline_paths),
        "command_executed": False,
        "control_executed": False,
    }, run_directory


def main():
    if sys.argv[1:] == ["contract"]:
        show_contract()
        return 0

    run_directory = None
    try:
        args = parse_args()
        report, run_directory = execute(args)
    except MaterializerError as exc:
        print("PROMPT12_RUNTIME_PROFILE_MATERIALIZER_GATE=FAIL", file=sys.stderr)
        print(f"FAIL_REASON={exc.reason}", file=sys.stderr)
        if run_directory is not None:
            print(f"RUN_DIRECTORY={run_directory}", file=sys.stderr)
        return exc.rc
    except (OSError, ValueError) as exc:
        print("PROMPT12_RUNTIME_PROFILE_MATERIALIZER_GATE=FAIL", file=sys.stderr)
        print(
            "FAIL_REASON=UNEXPECTED_LOCAL_ERROR:" + type(exc).__name__,
            file=sys.stderr,
        )
        if run_directory is not None:
            print(f"RUN_DIRECTORY={run_directory}", file=sys.stderr)
        return 70

    sys.stdout.write(
        json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
