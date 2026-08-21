#!/usr/bin/env python3

import argparse
import json
import os
import re
import sys
from decimal import Decimal

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError


STAGING_SCHEMA = "sci_oran_iperf_receiver_interval_parse_v1"

EXPERIMENT_RE = re.compile(
    r"^EXP-[0-9]{8}-DL-18000K-R0[1-4]$"
)

RUN_RE = re.compile(
    r"^RUN-[0-9]{8}T[0-9]{6}Z-[0-9]{3}$"
)

PRIMARY_TS = Decimal("0.2")
STARTUP_GUARD_S = Decimal("1.0")
EPSILON = Decimal("0.000001")
NS_PER_SECOND = Decimal("1000000000")

RATIO_TO_PRBS = {
    25: 13,
    50: 26,
    75: 39,
    100: 52,
}


class CanonicalizationError(Exception):
    pass


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Convert verified Prompt-12 iperf staging intervals into "
            "schema-valid canonical iperfInterval records."
        )
    )

    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--schema", required=True)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--run-id", required=True)

    parser.add_argument(
        "--classification-scope",
        required=True,
        choices=[
            "no-actuator-transitions",
            "actuator-transitions",
        ],
    )

    parser.add_argument(
        "--actuator-timeline",
        help=(
            "Schema-valid actuatorEvent JSONL. Required only for "
            "classification-scope=actuator-transitions."
        ),
    )

    return parser.parse_args()


def load_root_schema(schema_path):
    with open(schema_path, encoding="utf-8") as handle:
        root_schema = json.load(handle)

    Draft202012Validator.check_schema(root_schema)

    return root_schema


def validator_for(root_schema, definition):
    return Draft202012Validator(
        {
            "$schema": root_schema["$schema"],
            "$defs": root_schema["$defs"],
            "$ref": f"#/$defs/{definition}",
        }
    )


def validate_identity(experiment_id, run_id):
    if not EXPERIMENT_RE.fullmatch(experiment_id):
        raise CanonicalizationError(
            "invalid Prompt-12 experiment_id"
        )

    if not RUN_RE.fullmatch(run_id):
        raise CanonicalizationError(
            "invalid Prompt-12 run_id"
        )


def exact_duration_ns(value):
    decimal_value = Decimal(str(value))

    if decimal_value <= 0:
        raise CanonicalizationError(
            "interval duration must be positive"
        )

    scaled = decimal_value * NS_PER_SECOND
    integral = scaled.to_integral_value()

    if scaled != integral:
        raise CanonicalizationError(
            "interval duration cannot be represented exactly "
            "at nanosecond resolution"
        )

    return int(integral)


def base_interval_class(row):
    shape = row["interval_shape"]

    duration = Decimal(
        str(row["interval_duration_s"])
    )

    interval_end = Decimal(
        str(row["interval_end_s"])
    )

    if shape == "partial_terminal_candidate":
        if not (
            Decimal("0")
            < duration
            < PRIMARY_TS
        ):
            raise CanonicalizationError(
                "partial terminal candidate has invalid duration"
            )

        return "partial_terminal"

    if shape != "complete_0p2":
        raise CanonicalizationError(
            f"unsupported staging interval shape: {shape}"
        )

    if abs(
        duration - PRIMARY_TS
    ) > EPSILON:
        raise CanonicalizationError(
            "complete_0p2 staging record is not 0.2 seconds"
        )

    if interval_end <= STARTUP_GUARD_S + EPSILON:
        return "startup_guard"

    return "complete"


def load_actuator_timeline(
    path,
    validator,
    experiment_id,
    run_id,
):
    with open(path, encoding="utf-8") as handle:
        rows = [
            json.loads(line)
            for line in handle
            if line.strip()
        ]

    if not rows:
        raise CanonicalizationError(
            "actuator timeline is empty"
        )

    if len(rows) % 3 != 0:
        raise CanonicalizationError(
            "actuator timeline must contain complete "
            "command/applied_readback/acknowledgement triplets"
        )

    control_count = len(rows) // 3

    if not 1 <= control_count <= 6:
        raise CanonicalizationError(
            "actuator timeline control count must be between 1 and 6"
        )

    seen_record_ids = set()
    previous_timestamp = None
    previous_ack_timestamp = None
    applied_timestamps = []

    for row_index, row in enumerate(rows):
        validator.validate(row)

        if row["experiment_id"] != experiment_id:
            raise CanonicalizationError(
                "actuator timeline experiment_id mismatch"
            )

        if row["run_id"] != run_id:
            raise CanonicalizationError(
                "actuator timeline run_id mismatch"
            )

        record_id = row["record_id"]

        if record_id in seen_record_ids:
            raise CanonicalizationError(
                "duplicate actuator timeline record_id"
            )

        seen_record_ids.add(record_id)

        timestamp = row["timestamp_utc_ns"]

        if previous_timestamp is not None:
            if timestamp <= previous_timestamp:
                raise CanonicalizationError(
                    "actuator timeline timestamp ordering violation"
                )

        previous_timestamp = timestamp

    for control_index in range(control_count):
        offset = control_index * 3

        command = rows[offset]
        applied = rows[offset + 1]
        acknowledgement = rows[offset + 2]

        event_types = [
            command["event_type"],
            applied["event_type"],
            acknowledgement["event_type"],
        ]

        if event_types != [
            "command",
            "applied_readback",
            "acknowledgement",
        ]:
            raise CanonicalizationError(
                f"control {control_index + 1}: invalid actuator event order"
            )

        ratio = command.get(
            "requested_max_prb_ratio_pct"
        )

        if ratio not in RATIO_TO_PRBS:
            raise CanonicalizationError(
                f"control {control_index + 1}: "
                "requested ratio outside Prompt-12 domain"
            )

        if applied.get("applied_min_prbs") != 0:
            raise CanonicalizationError(
                f"control {control_index + 1}: "
                "applied_min_prbs must be 0"
            )

        expected_max = RATIO_TO_PRBS[ratio]

        if applied.get("applied_max_prbs") != expected_max:
            raise CanonicalizationError(
                f"control {control_index + 1}: "
                "ratio/readback mismatch"
            )

        if acknowledgement.get(
            "acknowledgement_status"
        ) != "PASS":
            raise CanonicalizationError(
                f"control {control_index + 1}: "
                "acknowledgement must be PASS"
            )

        command_ts = command["timestamp_utc_ns"]
        applied_ts = applied["timestamp_utc_ns"]
        ack_ts = acknowledgement[
            "timestamp_utc_ns"
        ]

        if not (
            command_ts
            < applied_ts
            < ack_ts
        ):
            raise CanonicalizationError(
                f"control {control_index + 1}: "
                "command < applied_readback < acknowledgement "
                "ordering violation"
            )

        if (
            previous_ack_timestamp is not None
            and command_ts <= previous_ack_timestamp
        ):
            raise CanonicalizationError(
                f"control {control_index + 1}: "
                "command is not later than previous acknowledgement"
            )

        previous_ack_timestamp = ack_ts
        applied_timestamps.append(applied_ts)

    return rows, applied_timestamps


def classify_interval(
    row,
    applied_timestamps,
):
    base_class = base_interval_class(row)

    if not applied_timestamps:
        return base_class

    rx_wall_ns = row["rx_wall_ns"]

    if (
        not isinstance(rx_wall_ns, int)
        or rx_wall_ns <= 0
    ):
        raise CanonicalizationError(
            "invalid rx_wall_ns"
        )

    duration_ns = exact_duration_ns(
        row["interval_duration_s"]
    )

    observed_end_ns = rx_wall_ns
    observed_start_ns = (
        observed_end_ns - duration_ns
    )

    if observed_start_ns < 0:
        raise CanonicalizationError(
            "derived observed interval start is negative"
        )

    strict_hits = [
        timestamp
        for timestamp in applied_timestamps
        if (
            observed_start_ns
            < timestamp
            < observed_end_ns
        )
    ]

    if len(strict_hits) > 1:
        raise CanonicalizationError(
            "multiple applied_readback events lie strictly "
            "inside one receiver interval"
        )

    if not strict_hits:
        return base_class

    if base_class == "startup_guard":
        raise CanonicalizationError(
            "applied_readback lies inside startup_guard interval"
        )

    if base_class == "partial_terminal":
        raise CanonicalizationError(
            "applied_readback lies inside partial_terminal interval"
        )

    if base_class != "complete":
        raise CanonicalizationError(
            "transition crossing requires a complete interval"
        )

    return "transition_crossing"


def canonical_record(
    experiment_id,
    run_id,
    row,
    applied_timestamps,
):
    source_sequence = row["source_sequence"]

    if (
        not isinstance(source_sequence, int)
        or source_sequence < 0
    ):
        raise CanonicalizationError(
            "invalid source_sequence"
        )

    rx_wall_ns = row["rx_wall_ns"]
    rx_mono_ns = row["rx_mono_ns"]

    if (
        not isinstance(rx_wall_ns, int)
        or rx_wall_ns <= 0
    ):
        raise CanonicalizationError(
            "invalid rx_wall_ns"
        )

    if (
        not isinstance(rx_mono_ns, int)
        or rx_mono_ns <= 0
    ):
        raise CanonicalizationError(
            "invalid rx_mono_ns"
        )

    interval_class = classify_interval(
        row,
        applied_timestamps,
    )

    timestamp_utc_ns = rx_wall_ns

    return {
        "experiment_id": experiment_id,
        "run_id": run_id,
        "record_id": (
            f"IPERF-RX-LINE-{source_sequence:09d}"
        ),
        "timestamp_utc_ns": timestamp_utc_ns,
        "rx_wall_ns": rx_wall_ns,
        "rx_mono_ns": rx_mono_ns,
        "interval_start_s": row[
            "interval_start_s"
        ],
        "interval_end_s": row[
            "interval_end_s"
        ],
        "interval_duration_s": row[
            "interval_duration_s"
        ],
        "throughput_kbit_s": row[
            "throughput_kbit_s"
        ],
        "loss_pct": row.get("loss_pct"),
        "jitter_ms": row.get("jitter_ms"),
        "bytes_transferred": row.get(
            "bytes_transferred"
        ),
        "interval_class": interval_class,
    }


def main():
    args = parse_args()

    validate_identity(
        args.experiment_id,
        args.run_id,
    )

    if os.path.exists(args.output):
        raise CanonicalizationError(
            "output already exists"
        )

    if (
        args.classification_scope
        == "no-actuator-transitions"
    ):
        if args.actuator_timeline is not None:
            raise CanonicalizationError(
                "actuator timeline is forbidden for "
                "no-actuator-transitions scope"
            )

    elif (
        args.classification_scope
        == "actuator-transitions"
    ):
        if args.actuator_timeline is None:
            raise CanonicalizationError(
                "actuator timeline is required for "
                "actuator-transitions scope"
            )

    else:
        raise CanonicalizationError(
            "unsupported classification scope"
        )

    root_schema = load_root_schema(
        args.schema
    )

    interval_validator = validator_for(
        root_schema,
        "iperfInterval",
    )

    actuator_validator = validator_for(
        root_schema,
        "actuatorEvent",
    )

    applied_timestamps = []

    if (
        args.classification_scope
        == "actuator-transitions"
    ):
        _, applied_timestamps = (
            load_actuator_timeline(
                args.actuator_timeline,
                actuator_validator,
                args.experiment_id,
                args.run_id,
            )
        )

    with open(args.input, encoding="utf-8") as handle:
        staging_rows = [
            json.loads(line)
            for line in handle
            if line.strip()
        ]

    canonical_rows = []

    previous_wall_ns = None
    previous_mono_ns = None

    for row in staging_rows:
        if row.get("schema") != STAGING_SCHEMA:
            raise CanonicalizationError(
                "unexpected staging schema"
            )

        wall_ns = row["rx_wall_ns"]
        mono_ns = row["rx_mono_ns"]

        if previous_wall_ns is not None:
            if wall_ns < previous_wall_ns:
                raise CanonicalizationError(
                    "rx_wall_ns ordering violation"
                )

            if mono_ns <= previous_mono_ns:
                raise CanonicalizationError(
                    "rx_mono_ns ordering violation"
                )

        record = canonical_record(
            args.experiment_id,
            args.run_id,
            row,
            applied_timestamps,
        )

        interval_validator.validate(
            record
        )

        canonical_rows.append(record)

        previous_wall_ns = wall_ns
        previous_mono_ns = mono_ns

    with open(
        args.output,
        "x",
        encoding="utf-8",
        newline="\n",
    ) as output_handle:
        for record in canonical_rows:
            output_handle.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                + "\n"
            )

    counts = {
        "startup_guard": 0,
        "complete": 0,
        "partial_terminal": 0,
        "transition_crossing": 0,
    }

    for record in canonical_rows:
        counts[record["interval_class"]] += 1

    print(
        f"CANONICAL_RECORD_COUNT={len(canonical_rows)}"
    )
    print(
        f"STARTUP_GUARD_COUNT={counts['startup_guard']}"
    )
    print(
        f"COMPLETE_COUNT={counts['complete']}"
    )
    print(
        f"PARTIAL_TERMINAL_COUNT={counts['partial_terminal']}"
    )
    print(
        f"TRANSITION_CROSSING_COUNT={counts['transition_crossing']}"
    )

    if (
        args.classification_scope
        == "actuator-transitions"
    ):
        print(
            "APPLIED_READBACK_EVENT_COUNT="
            f"{len(applied_timestamps)}"
        )

    print(
        "TIMESTAMP_UTC_NS_SOURCE=RX_WALL_NS"
    )
    print(
        "OBSERVED_INTERVAL_END_SOURCE=RX_WALL_NS"
    )
    print(
        "OBSERVED_INTERVAL_START_FORMULA="
        "RX_WALL_NS_MINUS_EXACT_DURATION_NS"
    )
    print(
        "TRANSITION_ORIGIN_EVENT=APPLIED_READBACK"
    )
    print(
        "ACK_USED_FOR_TRANSITION_CROSSING=NO"
    )
    print(
        "SYNTHETIC_TIMESTAMP_GENERATION=NO"
    )
    print(
        "SCHEMA_VALIDATION=PASS"
    )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())

    except CanonicalizationError as exc:
        print(
            f"ERROR={exc}",
            file=sys.stderr,
        )
        raise SystemExit(64)

    except ValidationError as exc:
        print(
            "ERROR=schema validation failure: "
            f"{exc.message}",
            file=sys.stderr,
        )
        raise SystemExit(65)
