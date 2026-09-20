#!/usr/bin/env python3

import argparse
import json
import os
import pathlib
import subprocess
import sys
import time
import uuid


class AdapterError(Exception):
    def __init__(self, reason, rc=65):
        super().__init__(reason)
        self.reason = reason
        self.rc = rc


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Create a stable Prompt-12 receiver evidence snapshot, run the "
            "existing offline parser/canonicalizer/stationarity evaluator, "
            "and emit exactly one stationarity JSON object on stdout."
        )
    )
    parser.add_argument("--python-executable", required=True)
    parser.add_argument("--parser", required=True)
    parser.add_argument("--canonicalizer", required=True)
    parser.add_argument("--evaluator", required=True)
    parser.add_argument("--raw-input", required=True)
    parser.add_argument("--timestamp-input", required=True)
    parser.add_argument("--schema", required=True)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--mode",
        required=True,
        choices=("initial-pre-step", "post-step"),
    )
    parser.add_argument("--evidence-root", required=True)
    parser.add_argument("--actuator-timeline")
    parser.add_argument("--control-index", type=int)
    parser.add_argument("--stable-ms", type=int, default=40)
    parser.add_argument("--snapshot-timeout-ms", type=int, default=1000)
    return parser.parse_args()


def require_regular_file(value, label):
    path = pathlib.Path(value)
    if not path.is_file():
        raise AdapterError(f"{label}_MISSING", 66)
    return path


def validate_arguments(args):
    python_executable = require_regular_file(
        args.python_executable,
        "PYTHON_EXECUTABLE",
    )
    if not os.access(python_executable, os.X_OK):
        raise AdapterError("PYTHON_EXECUTABLE_NOT_EXECUTABLE", 77)

    paths = {
        "python": python_executable,
        "parser": require_regular_file(args.parser, "PARSER"),
        "canonicalizer": require_regular_file(
            args.canonicalizer,
            "CANONICALIZER",
        ),
        "evaluator": require_regular_file(args.evaluator, "EVALUATOR"),
        "raw": require_regular_file(args.raw_input, "RAW_INPUT"),
        "timestamps": require_regular_file(
            args.timestamp_input,
            "TIMESTAMP_INPUT",
        ),
        "schema": require_regular_file(args.schema, "SCHEMA"),
    }

    if args.stable_ms < 0:
        raise AdapterError("STABLE_MS_INVALID", 64)
    if args.snapshot_timeout_ms <= 0:
        raise AdapterError("SNAPSHOT_TIMEOUT_MS_INVALID", 64)

    if args.mode == "initial-pre-step":
        if args.actuator_timeline is not None or args.control_index is not None:
            raise AdapterError("INITIAL_MODE_POST_ARGUMENT_PRESENT", 64)
        paths["actuator_timeline"] = None
    else:
        if args.actuator_timeline is None or args.control_index is None:
            raise AdapterError("POST_MODE_ARGUMENT_MISSING", 64)
        if not 1 <= args.control_index <= 6:
            raise AdapterError("CONTROL_INDEX_INVALID", 64)
        paths["actuator_timeline"] = require_regular_file(
            args.actuator_timeline,
            "ACTUATOR_TIMELINE",
        )

    return paths


def create_attempt(evidence_root):
    root = pathlib.Path(evidence_root)
    root.mkdir(parents=True, exist_ok=True)
    name = f"attempt-{time.time_ns()}-{os.getpid()}-{uuid.uuid4().hex}"
    attempt = root / name
    attempt.mkdir(mode=0o750)
    for child in ("raw", "processed", "logs"):
        (attempt / child).mkdir(mode=0o750)
    return attempt


def read_exact(path, size):
    with path.open("rb") as handle:
        data = handle.read(size)
    if len(data) != size:
        raise AdapterError("SNAPSHOT_SHORT_READ", 75)
    return data


def write_bytes_exclusive(path, data):
    with path.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def stable_pair_snapshot(
    raw_source,
    timestamp_source,
    raw_destination,
    timestamp_destination,
    stable_ms,
    timeout_ms,
):
    deadline = time.monotonic() + timeout_ms / 1000
    stable_seconds = stable_ms / 1000
    previous = None
    stable_since = None

    while time.monotonic() < deadline:
        sizes = (raw_source.stat().st_size, timestamp_source.stat().st_size)
        now = time.monotonic()

        if sizes[0] > 0 and sizes[1] > 0:
            if sizes != previous:
                previous = sizes
                stable_since = now
            elif stable_since is not None and now - stable_since >= stable_seconds:
                raw_data = read_exact(raw_source, sizes[0])
                timestamp_data = read_exact(timestamp_source, sizes[1])
                after = (
                    raw_source.stat().st_size,
                    timestamp_source.stat().st_size,
                )
                if after != sizes:
                    previous = after
                    stable_since = time.monotonic()
                    continue
                if not raw_data.endswith(b"\n"):
                    raise AdapterError("RAW_SNAPSHOT_INCOMPLETE_LINE", 75)
                if not timestamp_data.endswith(b"\n"):
                    raise AdapterError("TIMESTAMP_SNAPSHOT_INCOMPLETE_LINE", 75)
                write_bytes_exclusive(raw_destination, raw_data)
                write_bytes_exclusive(timestamp_destination, timestamp_data)
                return

        time.sleep(0.01)

    raise AdapterError("SNAPSHOT_STABILITY_TIMEOUT", 75)


def stable_single_snapshot(source, destination):
    size = source.stat().st_size
    if size <= 0:
        raise AdapterError("ACTUATOR_TIMELINE_EMPTY", 75)
    data = read_exact(source, size)
    if source.stat().st_size != size:
        raise AdapterError("ACTUATOR_TIMELINE_CHANGED_DURING_SNAPSHOT", 75)
    if not data.endswith(b"\n"):
        raise AdapterError("ACTUATOR_TIMELINE_INCOMPLETE_LINE", 75)
    write_bytes_exclusive(destination, data)


def write_json_exclusive(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def run_tool(label, argv, logs_directory):
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.run(
        argv,
        text=True,
        capture_output=True,
        check=False,
        env=environment,
    )
    (logs_directory / f"{label}.stdout.log").write_text(
        proc.stdout,
        encoding="utf-8",
    )
    (logs_directory / f"{label}.stderr.log").write_text(
        proc.stderr,
        encoding="utf-8",
    )
    if proc.returncode != 0:
        raise AdapterError(f"{label.upper()}_FAILED_RC_{proc.returncode}", 70)


def build_commands(args, paths, attempt):
    raw_snapshot = attempt / "raw" / "iperf3-receiver.stdout.log"
    timestamp_snapshot = (
        attempt / "raw" / "iperf3-receiver.timestamps.jsonl"
    )
    staging = attempt / "processed" / "intervals.staging.jsonl"
    canonical = attempt / "processed" / "intervals.canonical.jsonl"
    report = attempt / "processed" / "stationarity.json"

    parser_command = [
        str(paths["python"]),
        str(paths["parser"]),
        "--raw-input",
        str(raw_snapshot),
        "--timestamp-input",
        str(timestamp_snapshot),
        "--output",
        str(staging),
    ]
    canonicalizer_command = [
        str(paths["python"]),
        str(paths["canonicalizer"]),
        "--input",
        str(staging),
        "--output",
        str(canonical),
        "--schema",
        str(paths["schema"]),
        "--experiment-id",
        args.experiment_id,
        "--run-id",
        args.run_id,
        "--classification-scope",
        (
            "no-actuator-transitions"
            if args.mode == "initial-pre-step"
            else "actuator-transitions"
        ),
    ]
    evaluator_command = [
        str(paths["python"]),
        str(paths["evaluator"]),
        "--input",
        str(canonical),
        "--schema",
        str(paths["schema"]),
        "--experiment-id",
        args.experiment_id,
        "--run-id",
        args.run_id,
        "--mode",
        args.mode,
        "--output",
        str(report),
    ]

    if args.mode == "post-step":
        timeline_snapshot = attempt / "raw" / "actuator-timeline.jsonl"
        canonicalizer_command.extend(
            ["--actuator-timeline", str(timeline_snapshot)]
        )
        evaluator_command.extend(
            [
                "--actuator-timeline",
                str(timeline_snapshot),
                "--control-index",
                str(args.control_index),
            ]
        )

    return {
        "parser": parser_command,
        "canonicalizer": canonicalizer_command,
        "evaluator": evaluator_command,
    }, report


def execute(args):
    paths = validate_arguments(args)
    attempt = create_attempt(args.evidence_root)

    stable_pair_snapshot(
        paths["raw"],
        paths["timestamps"],
        attempt / "raw" / "iperf3-receiver.stdout.log",
        attempt / "raw" / "iperf3-receiver.timestamps.jsonl",
        args.stable_ms,
        args.snapshot_timeout_ms,
    )
    if paths["actuator_timeline"] is not None:
        stable_single_snapshot(
            paths["actuator_timeline"],
            attempt / "raw" / "actuator-timeline.jsonl",
        )

    commands, report_path = build_commands(args, paths, attempt)
    write_json_exclusive(attempt / "commands.json", commands)

    for label in ("parser", "canonicalizer", "evaluator"):
        run_tool(label, commands[label], attempt / "logs")

    try:
        with report_path.open(encoding="utf-8") as handle:
            report = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise AdapterError("EVALUATOR_REPORT_INVALID", 65) from exc

    if not isinstance(report, dict):
        raise AdapterError("EVALUATOR_REPORT_NOT_OBJECT", 65)
    if report.get("output_stationarity_gate") not in ("PASS", "FAIL"):
        raise AdapterError("EVALUATOR_GATE_INVALID", 65)

    return report, attempt


def main():
    args = parse_args()
    attempt = None
    try:
        report, attempt = execute(args)
    except AdapterError as exc:
        print("STATIONARITY_COMMAND_ADAPTER_GATE=FAIL", file=sys.stderr)
        print(f"FAIL_REASON={exc.reason}", file=sys.stderr)
        if attempt is not None:
            print(f"ATTEMPT_DIR={attempt}", file=sys.stderr)
        return exc.rc
    except (OSError, ValueError) as exc:
        print("STATIONARITY_COMMAND_ADAPTER_GATE=FAIL", file=sys.stderr)
        print(f"FAIL_REASON=UNEXPECTED_LOCAL_ERROR:{type(exc).__name__}", file=sys.stderr)
        return 70

    sys.stdout.write(
        json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
