#!/usr/bin/env python3

import argparse
import json
import os
import pathlib
import re
import sys


PROFILE_SCHEMA = "sci_oran_prompt12_bounded_sequence_runtime_profile_v1"
BINDING_SCHEMA = "sci_oran_prompt12_bounded_sequence_bindings_v1"
TRANSITION_LABELS = tuple(f"T{index}" for index in range(1, 7))
REQUESTED_RATIOS = (50, 75, 100, 75, 50, 25)

STATIONARITY_JSON_TOKEN = "@PROMPT12_STATIONARITY_JSON@"
CANONICAL_INTERVALS_TOKEN = "@PROMPT12_CANONICAL_INTERVALS@"
PRECONTROL_JSON_TOKEN = "@PROMPT12_PRECONTROL_JSON@"
DECISION_UTC_NS_TOKEN = "@PROMPT12_DECISION_UTC_NS@"
ACTUATOR_TIMELINE_TOKEN = "@PROMPT12_ACTUATOR_TIMELINE@"

TOOL_KEYS = {
    "traffic_adapter",
    "stationarity_adapter",
    "precontrol_handoff",
    "finalization_adapter",
    "parser",
    "canonicalizer",
    "stationarity_evaluator",
    "freshness_evaluator",
    "trigger_executor",
    "timeline_builder",
    "receiver_pipeline",
    "schema",
    "freshness_policy",
}
DATA_KEYS = {
    "actuator_command_input",
    "actuator_applied_input",
    "actuator_ack_input",
}
PROFILE_KEYS = {
    "schema",
    "python_executable",
    "experiment_id",
    "run_id",
    "run_directory",
    "receiver_container_name",
    "traffic_duration_s",
    "actuator_fifo_path",
    "control_authorization_token",
    "trigger_token",
    "max_age_ms",
    "stable_ms",
    "snapshot_timeout_ms",
    "timeline_readiness_timeout_ms",
    "timeline_readiness_poll_ms",
    "tool_paths",
    "data_paths",
    "incremental_timeline_command_json",
}


class BuilderError(Exception):
    pass


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Build one validated Prompt-12 production binding manifest "
            "without executing any bound command."
        )
    )
    parser.add_argument("--profile", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def read_object(path, label):
    try:
        with path.open(encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise BuilderError(
            f"{label}_READ_FAILED:{type(exc).__name__}"
        ) from exc
    if not isinstance(value, dict):
        raise BuilderError(f"{label}_NOT_OBJECT")
    return value


def require_exact_keys(value, expected, label):
    actual = set(value)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing:
        raise BuilderError(f"{label}_MISSING_KEYS:{','.join(missing)}")
    if extra:
        raise BuilderError(f"{label}_UNKNOWN_KEYS:{','.join(extra)}")


def require_string(value, label):
    if (
        not isinstance(value, str)
        or not value
        or "\0" in value
        or "\n" in value
        or "\r" in value
    ):
        raise BuilderError(f"{label}_INVALID")
    return value


def require_int(value, minimum, maximum, label):
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not minimum <= value <= maximum
    ):
        raise BuilderError(f"{label}_INVALID")
    return value


def require_absolute_path(value, label, must_exist=False):
    raw = require_string(value, label)
    path = pathlib.Path(raw)
    if not path.is_absolute():
        raise BuilderError(f"{label}_NOT_ABSOLUTE")
    if must_exist and not path.is_file():
        raise BuilderError(f"{label}_NOT_FILE")
    return path


def validate_profile(root):
    require_exact_keys(root, PROFILE_KEYS, "PROFILE")
    if root["schema"] != PROFILE_SCHEMA:
        raise BuilderError("PROFILE_SCHEMA_INVALID")

    python = require_absolute_path(
        root["python_executable"],
        "PYTHON_EXECUTABLE",
        must_exist=True,
    )
    experiment_id = require_string(root["experiment_id"], "EXPERIMENT_ID")
    run_id = require_string(root["run_id"], "RUN_ID")
    if not re.fullmatch(r"EXP-\d{8}-DL-\d+K-R0[1-4]", experiment_id):
        raise BuilderError("EXPERIMENT_ID_FORMAT_INVALID")
    if not re.fullmatch(r"RUN-\d{8}T\d{6}Z-\d{3}", run_id):
        raise BuilderError("RUN_ID_FORMAT_INVALID")

    run_directory = require_absolute_path(
        root["run_directory"], "RUN_DIRECTORY"
    )
    receiver = require_string(
        root["receiver_container_name"], "RECEIVER_CONTAINER_NAME"
    )
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", receiver):
        raise BuilderError("RECEIVER_CONTAINER_NAME_FORMAT_INVALID")

    fifo = require_absolute_path(
        root["actuator_fifo_path"], "ACTUATOR_FIFO_PATH"
    )
    authorization = require_string(
        root["control_authorization_token"],
        "CONTROL_AUTHORIZATION_TOKEN",
    )
    trigger_token = require_string(root["trigger_token"], "TRIGGER_TOKEN")

    tool_paths = root["tool_paths"]
    data_paths = root["data_paths"]
    if not isinstance(tool_paths, dict):
        raise BuilderError("TOOL_PATHS_NOT_OBJECT")
    if not isinstance(data_paths, dict):
        raise BuilderError("DATA_PATHS_NOT_OBJECT")
    require_exact_keys(tool_paths, TOOL_KEYS, "TOOL_PATHS")
    require_exact_keys(data_paths, DATA_KEYS, "DATA_PATHS")

    tools = {
        key: require_absolute_path(
            tool_paths[key], f"TOOL_{key.upper()}", must_exist=True
        )
        for key in sorted(TOOL_KEYS)
    }
    for key in ("traffic_adapter", "receiver_pipeline"):
        if not os.access(tools[key], os.X_OK):
            raise BuilderError(f"TOOL_{key.upper()}_NOT_EXECUTABLE")

    data = {
        key: require_absolute_path(
            data_paths[key], f"DATA_{key.upper()}"
        )
        for key in sorted(DATA_KEYS)
    }

    timeline_json = root["incremental_timeline_command_json"]
    if not isinstance(timeline_json, list) or len(timeline_json) != 6:
        raise BuilderError("INCREMENTAL_TIMELINE_COMMAND_JSON_COUNT_INVALID")
    timeline_paths = [
        require_absolute_path(
            item,
            f"INCREMENTAL_TIMELINE_COMMAND_JSON_{index}",
            must_exist=True,
        )
        for index, item in enumerate(timeline_json, start=1)
    ]
    if len(set(timeline_paths)) != 6:
        raise BuilderError("INCREMENTAL_TIMELINE_COMMAND_JSON_NOT_DISTINCT")

    return {
        "python": python,
        "experiment_id": experiment_id,
        "run_id": run_id,
        "run_directory": run_directory,
        "receiver": receiver,
        "traffic_duration_s": require_int(
            root["traffic_duration_s"], 141, 180, "TRAFFIC_DURATION_S"
        ),
        "fifo": fifo,
        "authorization": authorization,
        "trigger_token": trigger_token,
        "max_age_ms": require_int(root["max_age_ms"], 1, 10000, "MAX_AGE_MS"),
        "stable_ms": require_int(root["stable_ms"], 0, 5000, "STABLE_MS"),
        "snapshot_timeout_ms": require_int(
            root["snapshot_timeout_ms"], 1, 60000, "SNAPSHOT_TIMEOUT_MS"
        ),
        "timeline_readiness_timeout_ms": require_int(
            root["timeline_readiness_timeout_ms"],
            1,
            60000,
            "TIMELINE_READINESS_TIMEOUT_MS",
        ),
        "timeline_readiness_poll_ms": require_int(
            root["timeline_readiness_poll_ms"],
            1,
            5000,
            "TIMELINE_READINESS_POLL_MS",
        ),
        "tools": tools,
        "data": data,
        "timeline_json": timeline_paths,
    }


def stationarity_command(profile, mode, control_index=None):
    py = str(profile["python"])
    tools = profile["tools"]
    run = profile["run_directory"]
    raw = run / "raw" / "iperf3-receiver.stdout.log"
    timestamps = run / "raw" / "iperf3-receiver.timestamps.jsonl"
    role = "initial" if control_index is None else f"T{control_index}"
    command = [
        py,
        str(tools["stationarity_adapter"]),
        "--python-executable",
        py,
        "--parser",
        str(tools["parser"]),
        "--canonicalizer",
        str(tools["canonicalizer"]),
        "--evaluator",
        str(tools["stationarity_evaluator"]),
        "--raw-input",
        str(raw),
        "--timestamp-input",
        str(timestamps),
        "--schema",
        str(tools["schema"]),
        "--experiment-id",
        profile["experiment_id"],
        "--run-id",
        profile["run_id"],
        "--mode",
        mode,
        "--evidence-root",
        str(run / "evidence" / "stationarity" / role),
        "--stable-ms",
        str(profile["stable_ms"]),
        "--snapshot-timeout-ms",
        str(profile["snapshot_timeout_ms"]),
    ]
    if control_index is not None:
        command.extend([
            "--control-index",
            str(control_index),
            "--timeline-command-json",
            str(profile["timeline_json"][control_index - 1]),
            "--expected-timeline-event-count",
            str(control_index * 3),
            "--timeline-readiness-timeout-ms",
            str(profile["timeline_readiness_timeout_ms"]),
            "--timeline-readiness-poll-ms",
            str(profile["timeline_readiness_poll_ms"]),
        ])
    return command


def freshness_command(profile, transition_index):
    py = str(profile["python"])
    tools = profile["tools"]
    run = profile["run_directory"]
    label = f"T{transition_index}"
    return [
        py,
        str(tools["freshness_evaluator"]),
        "--input",
        CANONICAL_INTERVALS_TOKEN,
        "--schema",
        str(tools["schema"]),
        "--policy",
        str(tools["freshness_policy"]),
        "--evaluator",
        str(tools["stationarity_evaluator"]),
        "--experiment-id",
        profile["experiment_id"],
        "--run-id",
        profile["run_id"],
        "--decision-utc-ns",
        DECISION_UTC_NS_TOKEN,
        "--selected-output",
        str(run / "precontrol" / f"{label}.selected.jsonl"),
        "--stationarity-output",
        STATIONARITY_JSON_TOKEN,
        "--output",
        PRECONTROL_JSON_TOKEN,
    ]


def handoff_command(profile, transition_index, stationarity):
    py = str(profile["python"])
    run = profile["run_directory"]
    label = f"T{transition_index}"
    return [
        py,
        str(profile["tools"]["precontrol_handoff"]),
        "--attempt-root",
        str(run / "evidence" / "precontrol-handoff" / label),
        "--precontrol-output",
        str(run / "precontrol" / f"{label}.json"),
        "--stationarity-command",
        *stationarity,
        "--freshness-command",
        *freshness_command(profile, transition_index),
    ]


def trigger_command(profile, transition_index):
    py = str(profile["python"])
    run = profile["run_directory"]
    label = f"T{transition_index}"
    return [
        py,
        str(profile["tools"]["trigger_executor"]),
        "--precontrol-json",
        str(run / "precontrol" / f"{label}.json"),
        "--mode",
        "fifo",
        "--max-age-ms",
        str(profile["max_age_ms"]),
        "--output",
        str(run / "control" / f"{label}.executor.json"),
        "--fifo-path",
        str(profile["fifo"]),
        "--trigger-token",
        profile["trigger_token"],
        "--control-authorization-token",
        profile["authorization"],
    ]


def finalization_command(profile):
    py = str(profile["python"])
    tools = profile["tools"]
    data = profile["data"]
    run = profile["run_directory"]
    timeline = run / "processed" / "actuator-timeline.jsonl"
    staging = run / "processed" / "iperf3-receiver.intervals.staging.jsonl"
    canonical = run / "processed" / "iperf3-receiver.intervals.canonical.jsonl"
    timeline_command = [
        py,
        str(tools["timeline_builder"]),
        "--schema",
        str(tools["schema"]),
        "--experiment-id",
        profile["experiment_id"],
        "--run-id",
        profile["run_id"],
        "--requested-ratios",
        ",".join(str(value) for value in REQUESTED_RATIOS),
        "--command-input",
        str(data["actuator_command_input"]),
        "--applied-input",
        str(data["actuator_applied_input"]),
        "--ack-input",
        str(data["actuator_ack_input"]),
        "--output",
        ACTUATOR_TIMELINE_TOKEN,
    ]
    pipeline_command = [
        str(tools["receiver_pipeline"]),
        "process-actuator-transitions",
        profile["experiment_id"],
        profile["run_id"],
        str(run),
        ACTUATOR_TIMELINE_TOKEN,
    ]
    return [
        py,
        str(tools["finalization_adapter"]),
        "--attempt-root",
        str(run / "evidence" / "finalization"),
        "--python-executable",
        py,
        "--timeline-output",
        str(timeline),
        "--staging-output",
        str(staging),
        "--canonical-output",
        str(canonical),
        "--expected-event-count",
        "18",
        "--timeline-command",
        *timeline_command,
        "--pipeline-command",
        *pipeline_command,
    ]


def build_binding(profile):
    run = profile["run_directory"]
    traffic = [
        str(profile["tools"]["traffic_adapter"]),
        "run",
        profile["receiver"],
        str(profile["traffic_duration_s"]),
        str(run / "raw" / "iperf3-receiver.stdout.log"),
        str(run / "raw" / "iperf3-receiver.timestamps.jsonl"),
        str(run / "raw" / "iperf3-receiver.stderr.log"),
    ]
    initial = handoff_command(
        profile,
        1,
        stationarity_command(profile, "initial-pre-step"),
    )
    transitions = []
    for index, label in enumerate(TRANSITION_LABELS, start=1):
        post = stationarity_command(profile, "post-step", index)
        if index < 6:
            post = handoff_command(profile, index + 1, post)
        transitions.append({
            "label": label,
            "trigger_command": trigger_command(profile, index),
            "post_stationarity_command": post,
        })
    return {
        "schema": BINDING_SCHEMA,
        "traffic_command": traffic,
        "initial_stationarity_command": initial,
        "finalization_command": finalization_command(profile),
        "transitions": transitions,
    }


def write_exclusive(path, value):
    if os.path.lexists(str(path)):
        raise BuilderError("OUTPUT_ALREADY_EXISTS")
    if not path.parent.is_dir():
        raise BuilderError("OUTPUT_PARENT_NOT_DIRECTORY")
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise BuilderError(f"OUTPUT_WRITE_FAILED:{type(exc).__name__}") from exc


def main():
    args = parse_args()
    try:
        profile_path = pathlib.Path(args.profile)
        output_path = pathlib.Path(args.output)
        root = read_object(profile_path, "PROFILE")
        profile = validate_profile(root)
        binding = build_binding(profile)
        write_exclusive(output_path, binding)
    except BuilderError as exc:
        print("PRODUCTION_BINDING_BUILDER_GATE=FAIL", file=sys.stderr)
        print(f"FAIL_REASON={exc}", file=sys.stderr)
        print("COMMAND_EXECUTED=NO", file=sys.stderr)
        print("CONTROL_EXECUTED=NO", file=sys.stderr)
        return 65

    print("PRODUCTION_BINDING_BUILDER_GATE=PASS")
    print(f"OUTPUT={args.output}")
    print("TRANSITION_COUNT=6")
    print("COMMAND_EXECUTED=NO")
    print("CONTROL_EXECUTED=NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
