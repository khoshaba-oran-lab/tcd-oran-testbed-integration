#!/usr/bin/env python3

import argparse
import calendar
import datetime as dt
import json
import os
import pathlib
import re
import sys

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError


PROMPT12_RATIO_TO_PRBS = {
    25: 13,
    50: 26,
    75: 39,
    100: 52,
}

COMMAND_MARKER = "E42_RIC_CONTROL_REQUEST rx"
APPLIED_MARKER = "PRB_ACTUATOR_APPLIED"
ACK_MARKER = "CONTROL ACKNOWLEDGE rx"

TIMESTAMP_RE = re.compile(
    r"^(?P<year>[0-9]{4})-"
    r"(?P<month>[0-9]{2})-"
    r"(?P<day>[0-9]{2})T"
    r"(?P<hour>[0-9]{2}):"
    r"(?P<minute>[0-9]{2}):"
    r"(?P<second>[0-9]{2})"
    r"(?:[.](?P<fraction>[0-9]+))?"
    r"(?P<z>Z)?"
)

APPLIED_RE = re.compile(
    r"PRB_ACTUATOR_APPLIED"
    r".*applied_min_prbs=(?P<minimum>[0-9]+)"
    r".*applied_max_prbs=(?P<maximum>[0-9]+)"
)


class TimelineError(Exception):
    pass


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Build schema-valid Prompt-12 actuatorEvent JSONL from "
            "authoritative RIC command/acknowledgement and native gNB "
            "applied-readback evidence."
        )
    )

    parser.add_argument("--schema", required=True)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--run-id", required=True)

    parser.add_argument(
        "--requested-ratios",
        required=True,
        help=(
            "Comma-separated Prompt-12 Max PRB Policy Ratios. "
            "Allowed values: 25,50,75,100."
        ),
    )

    parser.add_argument("--command-input", required=True)
    parser.add_argument("--applied-input", required=True)
    parser.add_argument("--ack-input", required=True)
    parser.add_argument("--output", required=True)

    return parser.parse_args()


def read_lines(path_text):
    path = pathlib.Path(path_text)

    if not path.is_file():
        raise TimelineError(
            f"input file missing: {path}"
        )

    return path.read_text(
        encoding="utf-8",
        errors="strict",
    ).splitlines()


def matching_lines(path_text, marker):
    return [
        line
        for line in read_lines(path_text)
        if marker in line
    ]


def exact_timestamp_utc_ns(line):
    match = TIMESTAMP_RE.match(line)

    if not match:
        raise TimelineError(
            f"cannot parse leading UTC timestamp: {line}"
        )

    fraction = match.group("fraction") or ""

    if len(fraction) > 9:
        raise TimelineError(
            "timestamp precision exceeds nanoseconds"
        )

    year = int(match.group("year"))
    month = int(match.group("month"))
    day = int(match.group("day"))
    hour = int(match.group("hour"))
    minute = int(match.group("minute"))
    second = int(match.group("second"))

    try:
        value = dt.datetime(
            year,
            month,
            day,
            hour,
            minute,
            second,
            tzinfo=dt.timezone.utc,
        )
    except ValueError as exc:
        raise TimelineError(
            f"invalid UTC timestamp: {exc}"
        ) from exc

    epoch_seconds = calendar.timegm(
        value.utctimetuple()
    )

    fractional_ns = (
        int(fraction.ljust(9, "0"))
        if fraction
        else 0
    )

    return (
        epoch_seconds * 1_000_000_000
        + fractional_ns
    )


def parse_requested_ratios(text):
    pieces = text.split(",")

    if not pieces or any(not item for item in pieces):
        raise TimelineError(
            "requested-ratios must be a non-empty comma-separated list"
        )

    values = []

    for item in pieces:
        if not re.fullmatch(r"[0-9]+", item):
            raise TimelineError(
                f"invalid requested ratio token: {item}"
            )

        value = int(item)

        if value not in PROMPT12_RATIO_TO_PRBS:
            raise TimelineError(
                f"ratio outside Prompt-12 identification domain: {value}"
            )

        values.append(value)

    if len(values) > 6:
        raise TimelineError(
            "more than six Prompt-12 controls in one run are not allowed"
        )

    return values


def load_schema(schema_path):
    path = pathlib.Path(schema_path)

    if not path.is_file():
        raise TimelineError(
            f"schema missing: {path}"
        )

    root = json.loads(
        path.read_text(encoding="utf-8")
    )

    Draft202012Validator.check_schema(root)

    defs = root.get("$defs", {})

    for required_name in (
        "actuatorEvent",
        "prompt12ExperimentId",
        "runId",
    ):
        if required_name not in defs:
            raise TimelineError(
                f"schema definition missing: {required_name}"
            )

    event_schema = {
        "$schema": root["$schema"],
        "$defs": defs,
        "$ref": "#/$defs/actuatorEvent",
    }

    validator = Draft202012Validator(
        event_schema
    )

    return root, validator


def validate_identity(root, experiment_id, run_id):
    defs = root["$defs"]

    experiment_pattern = defs[
        "prompt12ExperimentId"
    ]["pattern"]

    run_pattern = defs["runId"]["pattern"]

    if re.fullmatch(
        experiment_pattern,
        experiment_id,
    ) is None:
        raise TimelineError(
            "invalid Prompt-12 experiment_id"
        )

    if re.fullmatch(
        run_pattern,
        run_id,
    ) is None:
        raise TimelineError(
            "invalid Prompt-12 run_id"
        )


def build_events(
    experiment_id,
    run_id,
    ratios,
    command_lines,
    applied_lines,
    ack_lines,
):
    expected_count = len(ratios)

    counts = {
        "command": len(command_lines),
        "applied_readback": len(applied_lines),
        "acknowledgement": len(ack_lines),
    }

    for event_type, count in counts.items():
        if count != expected_count:
            raise TimelineError(
                f"{event_type} event count {count} "
                f"does not match requested ratio count {expected_count}"
            )

    events = []
    previous_ack_ns = None

    for index, ratio in enumerate(ratios, start=1):
        command_line = command_lines[index - 1]
        applied_line = applied_lines[index - 1]
        ack_line = ack_lines[index - 1]

        command_ns = exact_timestamp_utc_ns(
            command_line
        )

        applied_ns = exact_timestamp_utc_ns(
            applied_line
        )

        ack_ns = exact_timestamp_utc_ns(
            ack_line
        )

        applied_match = APPLIED_RE.search(
            applied_line
        )

        if not applied_match:
            raise TimelineError(
                f"control {index}: malformed PRB_ACTUATOR_APPLIED line"
            )

        applied_min = int(
            applied_match.group("minimum")
        )

        applied_max = int(
            applied_match.group("maximum")
        )

        expected_max = PROMPT12_RATIO_TO_PRBS[
            ratio
        ]

        if applied_min != 0:
            raise TimelineError(
                f"control {index}: applied_min_prbs "
                f"{applied_min} != 0"
            )

        if applied_max != expected_max:
            raise TimelineError(
                f"control {index}: requested ratio {ratio}% "
                f"requires {expected_max} PRB but "
                f"readback reports {applied_max}"
            )

        if not (
            command_ns
            < applied_ns
            < ack_ns
        ):
            raise TimelineError(
                f"control {index}: event order must be "
                "command < applied_readback < acknowledgement"
            )

        if (
            previous_ack_ns is not None
            and command_ns <= previous_ack_ns
        ):
            raise TimelineError(
                f"control {index}: command is not later "
                "than previous acknowledgement"
            )

        prefix = f"ACTUATOR-{index:03d}"

        command_event = {
            "experiment_id": experiment_id,
            "run_id": run_id,
            "record_id": (
                f"{prefix}-COMMAND"
            ),
            "timestamp_utc_ns": command_ns,
            "event_type": "command",
            "requested_max_prb_ratio_pct": ratio,
        }

        applied_event = {
            "experiment_id": experiment_id,
            "run_id": run_id,
            "record_id": (
                f"{prefix}-APPLIED-READBACK"
            ),
            "timestamp_utc_ns": applied_ns,
            "event_type": "applied_readback",
            "applied_min_prbs": applied_min,
            "applied_max_prbs": applied_max,
        }

        ack_event = {
            "experiment_id": experiment_id,
            "run_id": run_id,
            "record_id": (
                f"{prefix}-ACKNOWLEDGEMENT"
            ),
            "timestamp_utc_ns": ack_ns,
            "event_type": "acknowledgement",
            "acknowledgement_status": "PASS",
        }

        events.extend(
            (
                command_event,
                applied_event,
                ack_event,
            )
        )

        previous_ack_ns = ack_ns

    return events


def main():
    args = parse_args()

    if os.path.exists(args.output):
        raise TimelineError(
            "output already exists"
        )

    root, validator = load_schema(
        args.schema
    )

    validate_identity(
        root,
        args.experiment_id,
        args.run_id,
    )

    ratios = parse_requested_ratios(
        args.requested_ratios
    )

    command_lines = matching_lines(
        args.command_input,
        COMMAND_MARKER,
    )

    applied_lines = matching_lines(
        args.applied_input,
        APPLIED_MARKER,
    )

    ack_lines = matching_lines(
        args.ack_input,
        ACK_MARKER,
    )

    events = build_events(
        args.experiment_id,
        args.run_id,
        ratios,
        command_lines,
        applied_lines,
        ack_lines,
    )

    record_ids = [
        event["record_id"]
        for event in events
    ]

    if len(record_ids) != len(set(record_ids)):
        raise TimelineError(
            "duplicate actuatorEvent record_id"
        )

    timestamps = [
        event["timestamp_utc_ns"]
        for event in events
    ]

    if timestamps != sorted(timestamps):
        raise TimelineError(
            "global actuator timeline ordering violation"
        )

    for event in events:
        validator.validate(event)

    output_path = pathlib.Path(
        args.output
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "x",
        encoding="utf-8",
    ) as handle:
        for event in events:
            handle.write(
                json.dumps(
                    event,
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )

            handle.write("\n")

    applied_events = [
        event
        for event in events
        if event["event_type"]
        == "applied_readback"
    ]

    print(
        f"ACTUATOR_CONTROL_SEQUENCE_COUNT={len(ratios)}"
    )

    print(
        f"ACTUATOR_EVENT_COUNT={len(events)}"
    )

    print(
        "ACTUATOR_EVENT_ORDER_PER_CONTROL="
        "command<applied_readback<acknowledgement"
    )

    print(
        "PLANT_STEP_TIME_ORIGIN_EVENT_TYPE="
        "applied_readback"
    )

    print(
        "ACK_SUBSTITUTES_FOR_APPLIED_READBACK=NO"
    )

    print(
        "TIMESTAMP_UTC_NS_CONVERSION=EXACT_INTEGER"
    )

    for index, event in enumerate(
        applied_events,
        start=1,
    ):
        print(
            f"CONTROL_{index:03d}_PLANT_STEP_UTC_NS="
            f"{event['timestamp_utc_ns']}"
        )

    print(
        "ACTUATOR_TIMELINE_SCHEMA_VALIDATION=PASS"
    )

    print(
        "ACTUATOR_TIMELINE_BUILD=PASS"
    )


if __name__ == "__main__":
    try:
        main()

    except TimelineError as exc:
        print(
            f"ERROR={exc}",
            file=sys.stderr,
        )
        raise SystemExit(64)

    except ValidationError as exc:
        print(
            f"ERROR=schema validation failure: {exc.message}",
            file=sys.stderr,
        )
        raise SystemExit(65)
