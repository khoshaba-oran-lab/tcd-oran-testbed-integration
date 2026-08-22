#!/usr/bin/env python3

import argparse
import json
import subprocess
import sys
import time
from decimal import Decimal
from pathlib import Path


class FreshnessError(RuntimeError):
    pass


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate the Prompt-12 final pre-control "
            "stationarity/freshness gate from the two "
            "most recent complete contiguous 5 s windows."
        )
    )

    parser.add_argument("--input", required=True)
    parser.add_argument("--schema", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--evaluator", required=True)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--run-id", required=True)

    parser.add_argument(
        "--cutoff-utc-ns",
        type=int,
        default=None,
        help=(
            "Optional offline cutoff. Only complete intervals "
            "whose end timestamp is <= cutoff are eligible."
        ),
    )

    parser.add_argument(
        "--decision-utc-ns",
        type=int,
        default=None,
        help=(
            "Optional deterministic gate-decision timestamp. "
            "If omitted, time.time_ns() is sampled after the "
            "official stationarity evaluator completes."
        ),
    )

    parser.add_argument(
        "--selected-output",
        required=True,
    )

    parser.add_argument(
        "--stationarity-output",
        required=True,
    )

    parser.add_argument(
        "--output",
        required=True,
    )

    return parser.parse_args()


def load_policy(path):
    values = {}

    for raw in Path(path).read_text().splitlines():
        line = raw.strip()

        if not line or line.startswith("#"):
            continue

        if "=" not in line:
            raise FreshnessError(
                f"invalid policy line: {line!r}"
            )

        key, value = line.split("=", 1)

        if key in values:
            raise FreshnessError(
                f"duplicate policy key: {key}"
            )

        values[key] = value

    required = {
        "PRIMARY_OUTPUT_TS_MS",
        "STATIONARITY_WINDOW_S",
        "STATIONARITY_SAMPLES_PER_WINDOW",
        "STATIONARITY_WINDOW_COUNT",
        "FINAL_GATE_SELECTION",
        "FINAL_GATE_MAX_AGE_AT_DOCKER_START_MS",
    }

    missing = sorted(required - values.keys())

    if missing:
        raise FreshnessError(
            "missing policy keys: "
            + ",".join(missing)
        )

    if values["FINAL_GATE_SELECTION"] != (
        "LATEST_50_COMPLETE_CONTIGUOUS_SAMPLES"
    ):
        raise FreshnessError(
            "unexpected FINAL_GATE_SELECTION"
        )

    if int(values["STATIONARITY_SAMPLES_PER_WINDOW"]) != 25:
        raise FreshnessError(
            "stationarity samples/window is not 25"
        )

    if int(values["STATIONARITY_WINDOW_COUNT"]) != 2:
        raise FreshnessError(
            "stationarity window count is not 2"
        )

    if Decimal(values["STATIONARITY_WINDOW_S"]) != Decimal("5"):
        raise FreshnessError(
            "stationarity window is not 5 s"
        )

    if Decimal(values["PRIMARY_OUTPUT_TS_MS"]) != Decimal("200"):
        raise FreshnessError(
            "primary sample period is not 200 ms"
        )

    return values


def load_rows(path, experiment_id, run_id, cutoff):
    all_rows = []

    for lineno, raw in enumerate(
        Path(path).read_text().splitlines(),
        start=1,
    ):
        if not raw.strip():
            continue

        try:
            row = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise FreshnessError(
                f"invalid JSON at line {lineno}: {exc}"
            ) from exc

        if row.get("experiment_id") != experiment_id:
            raise FreshnessError(
                f"experiment_id mismatch at line {lineno}"
            )

        if row.get("run_id") != run_id:
            raise FreshnessError(
                f"run_id mismatch at line {lineno}"
            )

        all_rows.append(row)

    complete = []

    previous_ts = None

    for row in all_rows:
        ts = int(row["timestamp_utc_ns"])

        if previous_ts is not None and ts <= previous_ts:
            raise FreshnessError(
                "canonical timestamp order is not strictly increasing"
            )

        previous_ts = ts

        if row.get("interval_class") != "complete":
            continue

        if cutoff is not None and ts > cutoff:
            continue

        duration = Decimal(
            str(row["interval_duration_s"])
        )

        if duration != Decimal("0.2"):
            raise FreshnessError(
                "eligible complete interval duration is not 0.2 s"
            )

        complete.append(row)

    return all_rows, complete


def validate_window(window):
    if len(window) != 25:
        raise FreshnessError(
            "stationarity window does not contain 25 samples"
        )

    for left, right in zip(
        window,
        window[1:],
    ):
        left_end = Decimal(
            str(left["interval_end_s"])
        )

        right_start = Decimal(
            str(right["interval_start_s"])
        )

        if left_end != right_start:
            raise FreshnessError(
                "selected stationarity window contains "
                "a logical timing gap"
            )

    start = Decimal(
        str(window[0]["interval_start_s"])
    )

    end = Decimal(
        str(window[-1]["interval_end_s"])
    )

    if end - start != Decimal("5.0"):
        raise FreshnessError(
            "selected stationarity window does not span 5 s"
        )


def ensure_output_absent(path):
    if Path(path).exists():
        raise FreshnessError(
            f"output already exists: {path}"
        )


def main():
    args = parse_args()

    for path in (
        args.input,
        args.schema,
        args.policy,
        args.evaluator,
    ):
        if not Path(path).is_file():
            raise FreshnessError(
                f"required input missing: {path}"
            )

    for path in (
        args.selected_output,
        args.stationarity_output,
        args.output,
    ):
        ensure_output_absent(path)

    policy = load_policy(
        args.policy
    )

    all_rows, complete = load_rows(
        args.input,
        args.experiment_id,
        args.run_id,
        args.cutoff_utc_ns,
    )

    required_samples = (
        int(
            policy[
                "STATIONARITY_SAMPLES_PER_WINDOW"
            ]
        )
        *
        int(
            policy[
                "STATIONARITY_WINDOW_COUNT"
            ]
        )
    )

    if required_samples != 50:
        raise FreshnessError(
            "policy does not resolve to exactly 50 samples"
        )

    if len(complete) < required_samples:
        raise FreshnessError(
            "fewer than 50 complete eligible samples"
        )

    selected = complete[
        -required_samples:
    ]

    w1 = selected[:25]
    w2 = selected[25:]

    validate_window(w1)
    validate_window(w2)

    if Decimal(
        str(w1[-1]["interval_end_s"])
    ) != Decimal(
        str(w2[0]["interval_start_s"])
    ):
        raise FreshnessError(
            "W1 and W2 are not consecutive"
        )

    selected_path = Path(
        args.selected_output
    )

    selected_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with selected_path.open("w") as handle:
        for row in selected:
            handle.write(
                json.dumps(
                    row,
                    separators=(",", ":"),
                    ensure_ascii=False,
                )
                + "\n"
            )

    command = [
        sys.executable,
        args.evaluator,
        "--input",
        args.selected_output,
        "--schema",
        args.schema,
        "--experiment-id",
        args.experiment_id,
        "--run-id",
        args.run_id,
        "--mode",
        "initial-pre-step",
        "--output",
        args.stationarity_output,
    ]

    process = subprocess.run(
        command,
        text=True,
        capture_output=True,
        check=False,
    )

    print(
        f"OFFICIAL_STATIONARITY_EVALUATOR_RC="
        f"{process.returncode}"
    )

    if process.stdout:
        print(
            process.stdout,
            end="",
        )

    if process.stderr:
        print(
            process.stderr,
            end="",
            file=sys.stderr,
        )

    if process.returncode != 0:
        raise FreshnessError(
            "official stationarity evaluator failed"
        )

    report = json.loads(
        Path(
            args.stationarity_output
        ).read_text()
    )

    expected_binding = {
        "w1_first": w1[0]["record_id"],
        "w1_last": w1[-1]["record_id"],
        "w2_first": w2[0]["record_id"],
        "w2_last": w2[-1]["record_id"],
    }

    actual_binding = {
        "w1_first":
            report["w1"]["record_id_first"],
        "w1_last":
            report["w1"]["record_id_last"],
        "w2_first":
            report["w2"]["record_id_first"],
        "w2_last":
            report["w2"]["record_id_last"],
    }

    binding_pass = (
        actual_binding
        == expected_binding
    )

    stationarity_pass = all([
        binding_pass,
        report.get(
            "cv_w1_gate"
        ) == "PASS",
        report.get(
            "cv_w2_gate"
        ) == "PASS",
        report.get(
            "mean_shift_gate"
        ) == "PASS",
        report.get(
            "output_stationarity_gate"
        ) == "PASS",
        report.get(
            "minimum_phase_duration_gate"
        ) == "PASS",
    ])

    decision_utc_ns = (
        args.decision_utc_ns
        if args.decision_utc_ns is not None
        else time.time_ns()
    )

    latest_sample_utc_ns = int(
        selected[-1][
            "timestamp_utc_ns"
        ]
    )

    age_ns = (
        decision_utc_ns
        - latest_sample_utc_ns
    )

    max_age_ms = Decimal(
        policy[
            "FINAL_GATE_MAX_AGE_AT_DOCKER_START_MS"
        ]
    )

    max_age_ns = int(
        max_age_ms
        * Decimal("1000000")
    )

    freshness_pass = (
        age_ns >= 0
        and age_ns <= max_age_ns
    )

    admission_pass = (
        stationarity_pass
        and freshness_pass
    )

    result = {
        "schema":
            "sci_oran_prompt12_precontrol_freshness_v1",

        "experiment_id":
            args.experiment_id,

        "run_id":
            args.run_id,

        "selection":
            "latest_50_complete_contiguous_samples",

        "canonical_record_count":
            len(all_rows),

        "eligible_complete_count":
            len(complete),

        "selected_complete_count":
            len(selected),

        "cutoff_utc_ns":
            args.cutoff_utc_ns,

        "decision_utc_ns":
            decision_utc_ns,

        "latest_sample_timestamp_utc_ns":
            latest_sample_utc_ns,

        "latest_sample_age_ms":
            str(
                Decimal(age_ns)
                / Decimal("1000000")
            ),

        "maximum_allowed_age_ms":
            str(max_age_ms),

        "w1": {
            "record_id_first":
                w1[0]["record_id"],
            "record_id_last":
                w1[-1]["record_id"],
            "interval_start_s":
                w1[0]["interval_start_s"],
            "interval_end_s":
                w1[-1]["interval_end_s"],
        },

        "w2": {
            "record_id_first":
                w2[0]["record_id"],
            "record_id_last":
                w2[-1]["record_id"],
            "interval_start_s":
                w2[0]["interval_start_s"],
            "interval_end_s":
                w2[-1]["interval_end_s"],
        },

        "stationarity_window_binding_gate":
            (
                "PASS"
                if binding_pass
                else "FAIL"
            ),

        "output_stationarity_gate":
            (
                "PASS"
                if stationarity_pass
                else "FAIL"
            ),

        "freshness_gate":
            (
                "PASS"
                if freshness_pass
                else "FAIL"
            ),

        "precontrol_admission_gate":
            (
                "PASS"
                if admission_pass
                else "FAIL"
            ),

        "official_stationarity_report":
            report,
    }

    output_path = Path(
        args.output
    )

    output_path.write_text(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

    print(
        "PRECONTROL_SELECTED_COMPLETE_COUNT="
        f"{len(selected)}"
    )

    print(
        "PRECONTROL_W1="
        f"{w1[0]['interval_start_s']},"
        f"{w1[-1]['interval_end_s']}"
    )

    print(
        "PRECONTROL_W2="
        f"{w2[0]['interval_start_s']},"
        f"{w2[-1]['interval_end_s']}"
    )

    print(
        "PRECONTROL_LATEST_SAMPLE_UTC_NS="
        f"{latest_sample_utc_ns}"
    )

    print(
        "PRECONTROL_DECISION_UTC_NS="
        f"{decision_utc_ns}"
    )

    print(
        "PRECONTROL_LATEST_SAMPLE_AGE_MS="
        f"{Decimal(age_ns) / Decimal('1000000')}"
    )

    print(
        "PRECONTROL_MAX_ALLOWED_AGE_MS="
        f"{max_age_ms}"
    )

    print(
        "PRECONTROL_WINDOW_BINDING_GATE="
        + (
            "PASS"
            if binding_pass
            else "FAIL"
        )
    )

    print(
        "PRECONTROL_OUTPUT_STATIONARITY_GATE="
        + (
            "PASS"
            if stationarity_pass
            else "FAIL"
        )
    )

    print(
        "PRECONTROL_FRESHNESS_GATE="
        + (
            "PASS"
            if freshness_pass
            else "FAIL"
        )
    )

    print(
        "PRECONTROL_ADMISSION_GATE="
        + (
            "PASS"
            if admission_pass
            else "FAIL"
        )
    )

    return (
        0
        if admission_pass
        else 10
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())

    except FreshnessError as exc:
        print(
            f"ERROR={exc}",
            file=sys.stderr,
        )

        raise SystemExit(64)
