#!/usr/bin/env python3

import argparse
import json
import os
import sys
from decimal import Decimal, getcontext

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError


getcontext().prec = 40

PRIMARY_TS_S = Decimal("0.2")
WINDOW_S = Decimal("5")
WINDOW_SAMPLES = 25

CV_MAX_PCT = Decimal("5")
MEAN_SHIFT_MAX_PCT = Decimal("5")

INITIAL_PRE_MINIMUM_S = Decimal("11")
POST_MINIMUM_NS = 10_000_000_000

NS_PER_SECOND = Decimal("1000000000")
CONTIGUITY_TOLERANCE_S = Decimal("0.000001")

ALLOWED_INTERVAL_CLASSES = {
    "startup_guard",
    "complete",
    "partial_terminal",
    "transition_crossing",
}


class StationarityError(Exception):
    pass


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate the frozen Prompt-12 OUTPUT_STATIONARITY_GATE "
            "from canonical receiver-side iperfInterval records."
        )
    )

    parser.add_argument("--input", required=True)
    parser.add_argument("--schema", required=True)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--run-id", required=True)

    parser.add_argument(
        "--mode",
        required=True,
        choices=[
            "initial-pre-step",
            "post-step",
        ],
    )

    parser.add_argument(
        "--actuator-timeline",
        help=(
            "Required only for post-step mode. "
            "t0 is derived only from applied_readback."
        ),
    )

    parser.add_argument(
        "--control-index",
        type=int,
        help=(
            "1-based actuator control index. "
            "Required only for post-step mode."
        ),
    )

    parser.add_argument("--output", required=True)

    return parser.parse_args()


def load_root_schema(path):
    with open(path, encoding="utf-8") as handle:
        root = json.load(handle)

    Draft202012Validator.check_schema(root)

    return root


def validator_for(root, definition):
    return Draft202012Validator(
        {
            "$schema": root["$schema"],
            "$defs": root["$defs"],
            "$ref": f"#/$defs/{definition}",
        }
    )


def decimal_value(value):
    result = Decimal(str(value))

    if not result.is_finite():
        raise StationarityError(
            "non-finite decimal input"
        )

    return result


def exact_duration_ns(value):
    seconds = decimal_value(value)

    if seconds <= 0:
        raise StationarityError(
            "interval duration must be positive"
        )

    scaled = seconds * NS_PER_SECOND
    integral = scaled.to_integral_value()

    if scaled != integral:
        raise StationarityError(
            "interval duration is not exactly representable in nanoseconds"
        )

    return int(integral)


def validate_identity(row, experiment_id, run_id):
    if row["experiment_id"] != experiment_id:
        raise StationarityError(
            "experiment_id mismatch"
        )

    if row["run_id"] != run_id:
        raise StationarityError(
            "run_id mismatch"
        )


def load_intervals(
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
        raise StationarityError(
            "canonical iperf input is empty"
        )

    seen_ids = set()

    previous_wall = None
    previous_mono = None

    for row in rows:
        validator.validate(row)

        validate_identity(
            row,
            experiment_id,
            run_id,
        )

        record_id = row["record_id"]

        if record_id in seen_ids:
            raise StationarityError(
                "duplicate iperfInterval record_id"
            )

        seen_ids.add(record_id)

        interval_class = row["interval_class"]

        if interval_class not in ALLOWED_INTERVAL_CLASSES:
            raise StationarityError(
                "unsupported interval_class"
            )

        wall = row["rx_wall_ns"]
        mono = row["rx_mono_ns"]

        if previous_wall is not None:
            if wall < previous_wall:
                raise StationarityError(
                    "rx_wall_ns ordering violation"
                )

            if mono <= previous_mono:
                raise StationarityError(
                    "rx_mono_ns ordering violation"
                )

        previous_wall = wall
        previous_mono = mono

    return rows


def load_post_t0(
    path,
    validator,
    experiment_id,
    run_id,
    control_index,
):
    with open(path, encoding="utf-8") as handle:
        rows = [
            json.loads(line)
            for line in handle
            if line.strip()
        ]

    if not rows:
        raise StationarityError(
            "actuator timeline is empty"
        )

    if len(rows) % 3 != 0:
        raise StationarityError(
            "actuator timeline is not complete triplets"
        )

    controls = len(rows) // 3

    if control_index < 1 or control_index > controls:
        raise StationarityError(
            "control-index outside actuator timeline"
        )

    previous_timestamp = None

    for row in rows:
        validator.validate(row)

        validate_identity(
            row,
            experiment_id,
            run_id,
        )

        timestamp = row["timestamp_utc_ns"]

        if previous_timestamp is not None:
            if timestamp <= previous_timestamp:
                raise StationarityError(
                    "actuator timeline timestamp ordering violation"
                )

        previous_timestamp = timestamp

    offset = (control_index - 1) * 3
    triplet = rows[offset:offset + 3]

    event_types = [
        row["event_type"]
        for row in triplet
    ]

    if event_types != [
        "command",
        "applied_readback",
        "acknowledgement",
    ]:
        raise StationarityError(
            "selected actuator control is not "
            "command/applied_readback/acknowledgement"
        )

    command = triplet[0]
    applied = triplet[1]
    acknowledgement = triplet[2]

    if acknowledgement.get(
        "acknowledgement_status"
    ) != "PASS":
        raise StationarityError(
            "selected actuator acknowledgement is not PASS"
        )

    if not (
        command["timestamp_utc_ns"]
        < applied["timestamp_utc_ns"]
        < acknowledgement["timestamp_utc_ns"]
    ):
        raise StationarityError(
            "selected actuator event ordering violation"
        )

    return applied["timestamp_utc_ns"]


def is_complete(row):
    if row["interval_class"] != "complete":
        return False

    duration = decimal_value(
        row["interval_duration_s"]
    )

    return (
        abs(duration - PRIMARY_TS_S)
        <= CONTIGUITY_TOLERANCE_S
    )


def observed_bounds(row):
    end_ns = row["rx_wall_ns"]

    duration_ns = exact_duration_ns(
        row["interval_duration_s"]
    )

    start_ns = end_ns - duration_ns

    if start_ns < 0:
        raise StationarityError(
            "derived observed interval start is negative"
        )

    return start_ns, end_ns


def eligible(
    row,
    mode,
    t0_ns,
):
    if not is_complete(row):
        return False

    if mode == "initial-pre-step":
        return True

    start_ns, _ = observed_bounds(row)

    return start_ns >= t0_ns


def contiguous(previous, current):
    previous_end = decimal_value(
        previous["interval_end_s"]
    )

    current_start = decimal_value(
        current["interval_start_s"]
    )

    return (
        abs(current_start - previous_end)
        <= CONTIGUITY_TOLERANCE_S
    )


def latest_eligible_run(
    rows,
    mode,
    t0_ns,
):
    runs = []
    current = []

    for row in rows:
        if not eligible(
            row,
            mode,
            t0_ns,
        ):
            if current:
                runs.append(current)
                current = []

            continue

        if current:
            if not contiguous(
                current[-1],
                row,
            ):
                runs.append(current)
                current = []

        current.append(row)

    if current:
        runs.append(current)

    if not runs:
        return []

    return runs[-1]


def validate_window_geometry(window):
    if len(window) != WINDOW_SAMPLES:
        raise StationarityError(
            "stationarity window does not contain 25 samples"
        )

    for row in window:
        if not is_complete(row):
            raise StationarityError(
                "non-complete interval inside stationarity window"
            )

    for previous, current in zip(
        window,
        window[1:],
    ):
        if not contiguous(
            previous,
            current,
        ):
            raise StationarityError(
                "stationarity window contains a timing gap"
            )

    start = decimal_value(
        window[0]["interval_start_s"]
    )

    end = decimal_value(
        window[-1]["interval_end_s"]
    )

    span = end - start

    if abs(
        span - WINDOW_S
    ) > CONTIGUITY_TOLERANCE_S:
        raise StationarityError(
            "stationarity window does not span 5 seconds"
        )


def window_metrics(window):
    validate_window_geometry(window)

    values = [
        decimal_value(
            row["throughput_kbit_s"]
        )
        for row in window
    ]

    n = Decimal(len(values))

    mean = sum(
        values,
        Decimal("0"),
    ) / n

    if mean <= 0:
        raise StationarityError(
            "window mean throughput is zero or negative"
        )

    variance = sum(
        (
            value - mean
        ) * (
            value - mean
        )
        for value in values
    ) / n

    std = variance.sqrt()

    cv = (
        Decimal("100")
        * std
        / mean
    )

    return {
        "mean_kbit_s": mean,
        "population_std_kbit_s": std,
        "cv_pct": cv,
        "record_id_first": window[0]["record_id"],
        "record_id_last": window[-1]["record_id"],
        "interval_start_s": decimal_value(
            window[0]["interval_start_s"]
        ),
        "interval_end_s": decimal_value(
            window[-1]["interval_end_s"]
        ),
    }


def decimal_text(value):
    return format(
        value,
        "f",
    )


def json_metrics(metrics):
    return {
        "mean_kbit_s": decimal_text(
            metrics["mean_kbit_s"]
        ),
        "population_std_kbit_s": decimal_text(
            metrics["population_std_kbit_s"]
        ),
        "cv_pct": decimal_text(
            metrics["cv_pct"]
        ),
        "record_id_first": metrics[
            "record_id_first"
        ],
        "record_id_last": metrics[
            "record_id_last"
        ],
        "interval_start_s": decimal_text(
            metrics["interval_start_s"]
        ),
        "interval_end_s": decimal_text(
            metrics["interval_end_s"]
        ),
    }


def evaluate(
    rows,
    mode,
    t0_ns,
):
    run = latest_eligible_run(
        rows,
        mode,
        t0_ns,
    )

    full_windows = (
        len(run) // WINDOW_SAMPLES
    )

    trailing_samples = (
        len(run) % WINDOW_SAMPLES
    )

    report = {
        "schema": (
            "sci_oran_prompt12_output_stationarity_v1"
        ),
        "mode": mode,
        "standard_deviation_kind": "population",
        "standard_deviation_denominator": "N",
        "window_duration_s": 5,
        "samples_per_window": 25,
        "cv_max_pct": 5,
        "mean_shift_max_pct": 5,
        "eligible_run_sample_count": len(run),
        "full_window_count": full_windows,
        "trailing_eligible_sample_count": trailing_samples,
        "transition_origin_event": (
            "applied_readback"
            if mode == "post-step"
            else None
        ),
        "t_applied_readback_utc_ns": (
            t0_ns
            if mode == "post-step"
            else None
        ),
    }

    if full_windows < 2:
        report.update(
            {
                "window_pair_index": None,
                "w1": None,
                "w2": None,
                "mean_shift_pct": None,
                "cv_w1_gate": "NOT_EVALUATED",
                "cv_w2_gate": "NOT_EVALUATED",
                "mean_shift_gate": "NOT_EVALUATED",
                "output_stationarity_gate": "FAIL",
                "minimum_phase_duration_gate": "FAIL",
                "statistical_phase_candidate": "FAIL",
                "reason": (
                    "INSUFFICIENT_TWO_COMPLETE_WINDOWS"
                ),
            }
        )

        return report

    w1_index = full_windows - 1
    w2_index = full_windows

    w1_start = (
        (w1_index - 1)
        * WINDOW_SAMPLES
    )

    w1_end = (
        w1_index
        * WINDOW_SAMPLES
    )

    w2_start = w1_end
    w2_end = (
        w2_index
        * WINDOW_SAMPLES
    )

    w1 = run[w1_start:w1_end]
    w2 = run[w2_start:w2_end]

    m1 = window_metrics(w1)
    m2 = window_metrics(w2)

    if m1["mean_kbit_s"] <= 0:
        raise StationarityError(
            "W1 mean throughput is zero or negative"
        )

    mean_shift = (
        Decimal("100")
        * abs(
            m2["mean_kbit_s"]
            - m1["mean_kbit_s"]
        )
        / m1["mean_kbit_s"]
    )

    cv_w1_pass = (
        m1["cv_pct"]
        <= CV_MAX_PCT
    )

    cv_w2_pass = (
        m2["cv_pct"]
        <= CV_MAX_PCT
    )

    mean_shift_pass = (
        mean_shift
        <= MEAN_SHIFT_MAX_PCT
    )

    stationarity_pass = (
        cv_w1_pass
        and cv_w2_pass
        and mean_shift_pass
    )

    if mode == "initial-pre-step":
        final_end_s = decimal_value(
            w2[-1]["interval_end_s"]
        )

        duration_pass = (
            final_end_s
            >= INITIAL_PRE_MINIMUM_S
        )

    else:
        _, final_end_ns = observed_bounds(
            w2[-1]
        )

        duration_pass = (
            final_end_ns - t0_ns
            >= POST_MINIMUM_NS
        )

    phase_candidate = (
        stationarity_pass
        and duration_pass
    )

    report.update(
        {
            "window_pair_index": [
                w1_index,
                w2_index,
            ],
            "w1": json_metrics(m1),
            "w2": json_metrics(m2),
            "mean_shift_pct": decimal_text(
                mean_shift
            ),
            "cv_w1_gate": (
                "PASS"
                if cv_w1_pass
                else "FAIL"
            ),
            "cv_w2_gate": (
                "PASS"
                if cv_w2_pass
                else "FAIL"
            ),
            "mean_shift_gate": (
                "PASS"
                if mean_shift_pass
                else "FAIL"
            ),
            "output_stationarity_gate": (
                "PASS"
                if stationarity_pass
                else "FAIL"
            ),
            "minimum_phase_duration_gate": (
                "PASS"
                if duration_pass
                else "FAIL"
            ),
            "statistical_phase_candidate": (
                "PASS"
                if phase_candidate
                else "FAIL"
            ),
            "reason": (
                "PASS"
                if phase_candidate
                else "STATIONARITY_OR_DURATION_GATE_FAIL"
            ),
        }
    )

    return report


def main():
    args = parse_args()

    if os.path.exists(args.output):
        raise StationarityError(
            "output already exists"
        )

    if args.mode == "initial-pre-step":
        if args.actuator_timeline is not None:
            raise StationarityError(
                "actuator timeline forbidden for initial-pre-step"
            )

        if args.control_index is not None:
            raise StationarityError(
                "control-index forbidden for initial-pre-step"
            )

    if args.mode == "post-step":
        if args.actuator_timeline is None:
            raise StationarityError(
                "actuator timeline required for post-step"
            )

        if args.control_index is None:
            raise StationarityError(
                "control-index required for post-step"
            )

    root = load_root_schema(
        args.schema
    )

    interval_validator = validator_for(
        root,
        "iperfInterval",
    )

    actuator_validator = validator_for(
        root,
        "actuatorEvent",
    )

    rows = load_intervals(
        args.input,
        interval_validator,
        args.experiment_id,
        args.run_id,
    )

    t0_ns = None

    if args.mode == "post-step":
        t0_ns = load_post_t0(
            args.actuator_timeline,
            actuator_validator,
            args.experiment_id,
            args.run_id,
            args.control_index,
        )

    report = evaluate(
        rows,
        args.mode,
        t0_ns,
    )

    with open(
        args.output,
        "x",
        encoding="utf-8",
        newline="\n",
    ) as handle:
        json.dump(
            report,
            handle,
            sort_keys=True,
            separators=(",", ":"),
        )

        handle.write("\n")

    print(
        "STANDARD_DEVIATION_KIND="
        "POPULATION"
    )

    print(
        "STANDARD_DEVIATION_DENOMINATOR=N"
    )

    print(
        "WINDOW_DURATION_S=5"
    )

    print(
        "SAMPLES_PER_WINDOW=25"
    )

    print(
        "WINDOW_PAIR_INDEX="
        + (
            "NONE"
            if report["window_pair_index"] is None
            else (
                f"{report['window_pair_index'][0]},"
                f"{report['window_pair_index'][1]}"
            )
        )
    )

    print(
        "CV_W1_GATE="
        f"{report['cv_w1_gate']}"
    )

    print(
        "CV_W2_GATE="
        f"{report['cv_w2_gate']}"
    )

    print(
        "MEAN_SHIFT_GATE="
        f"{report['mean_shift_gate']}"
    )

    print(
        "OUTPUT_STATIONARITY_GATE="
        f"{report['output_stationarity_gate']}"
    )

    print(
        "MINIMUM_PHASE_DURATION_GATE="
        f"{report['minimum_phase_duration_gate']}"
    )

    print(
        "STATISTICAL_PHASE_CANDIDATE="
        f"{report['statistical_phase_candidate']}"
    )

    print(
        "TRANSITION_TIME_ORIGIN="
        + (
            "NONE"
            if args.mode == "initial-pre-step"
            else "APPLIED_READBACK"
        )
    )

    print(
        "ACK_USED_AS_STATIONARITY_TIME_ORIGIN=NO"
    )

    print(
        "OUTPUT_STATIONARITY_EVALUATION=PASS"
    )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())

    except StationarityError as exc:
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
