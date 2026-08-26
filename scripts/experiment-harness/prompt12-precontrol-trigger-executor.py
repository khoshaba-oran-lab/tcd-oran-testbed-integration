#!/usr/bin/env python3

import argparse
import json
import os
import stat
import sys
import time
from decimal import Decimal
from pathlib import Path


CONTROL_AUTHORIZATION_TOKEN = (
    "PROMPT12_T2_EXPLICIT_FIFO_CONTROL"
)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Prompt-12 atomic precontrol-to-trigger executor"
        )
    )

    parser.add_argument(
        "--precontrol-json",
        required=True,
    )

    parser.add_argument(
        "--mode",
        required=True,
        choices=(
            "no-control",
            "fifo",
        ),
    )

    parser.add_argument(
        "--max-age-ms",
        required=True,
    )

    parser.add_argument(
        "--output",
        required=True,
    )

    parser.add_argument(
        "--fifo-path",
    )

    parser.add_argument(
        "--trigger-token",
        default="TRIGGER",
    )

    parser.add_argument(
        "--control-authorization-token",
    )

    return parser.parse_args()


def write_result(path, result):
    destination = Path(path)

    if destination.exists():
        raise RuntimeError(
            f"output already exists: {destination}"
        )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination.write_text(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    for key in sorted(result):
        print(
            f"{key}={result[key]}"
        )


def fail_closed(
    args,
    result,
    reason,
    rc,
):
    result.update({
        "EXECUTOR_GATE":
            "FAIL_CLOSED",

        "FAIL_CLOSED_REASON":
            reason,

        "CONTROL_EXECUTED":
            "NO",

        "TRIGGER_WRITE_ATTEMPT_COUNT":
            0,

        "TRIGGER_WRITE_SUCCESS_COUNT":
            0,

        "SCIENTIFIC_TRIGGER_CONSUMED":
            "NO",

        "SCIENTIFIC_TRIGGER_REPLAY_DECISION":
            "NOT_APPLICABLE_NO_WRITE_ATTEMPT",
    })

    write_result(
        args.output,
        result,
    )

    return rc


def main():
    args = parse_args()

    result = {
        "SCHEMA":
            "sci_oran_prompt12_atomic_executor_v1",

        "MODE":
            args.mode,

        "MAX_AGE_MS_ARGUMENT":
            args.max_age_ms,

        "FINAL_RUNTIME_PROBE_AFTER_AGE_GATE":
            "NO",

        "DOCKER_EXECUTION_BY_EXECUTOR":
            "NO",

        "GNB_LOG_SCAN_BY_EXECUTOR":
            "NO",
    }

    source_path = Path(
        args.precontrol_json
    )

    if not source_path.is_file():
        return fail_closed(
            args,
            result,
            "PRECONTROL_JSON_MISSING",
            20,
        )

    try:
        source = json.loads(
            source_path.read_text(
                encoding="utf-8"
            )
        )
    except Exception:
        return fail_closed(
            args,
            result,
            "PRECONTROL_JSON_INVALID",
            21,
        )

    result.update({
        "SOURCE_SELECTION":
            source.get("selection"),

        "SOURCE_SELECTED_COMPLETE_COUNT":
            source.get(
                "selected_complete_count"
            ),

        "SOURCE_WINDOW_BINDING_GATE":
            source.get(
                "stationarity_window_binding_gate"
            ),

        "SOURCE_OUTPUT_STATIONARITY_GATE":
            source.get(
                "output_stationarity_gate"
            ),

        "SOURCE_FRESHNESS_GATE":
            source.get(
                "freshness_gate"
            ),

        "SOURCE_PRECONTROL_ADMISSION_GATE":
            source.get(
                "precontrol_admission_gate"
            ),
    })

    required_source_pass = all([
        source.get("selection")
            == "latest_50_complete_contiguous_samples",

        source.get(
            "selected_complete_count"
        ) == 50,

        source.get(
            "stationarity_window_binding_gate"
        ) == "PASS",

        source.get(
            "output_stationarity_gate"
        ) == "PASS",

        source.get(
            "freshness_gate"
        ) == "PASS",

        source.get(
            "precontrol_admission_gate"
        ) == "PASS",
    ])

    if not required_source_pass:
        return fail_closed(
            args,
            result,
            "SOURCE_PRECONTROL_GATE_NOT_PASS",
            22,
        )

    try:
        latest_sample_ns = int(
            source[
                "latest_sample_timestamp_utc_ns"
            ]
        )

        decision_ns = int(
            source[
                "decision_utc_ns"
            ]
        )

        source_max_age_ms = Decimal(
            str(
                source[
                    "maximum_allowed_age_ms"
                ]
            )
        )

        requested_max_age_ms = Decimal(
            str(args.max_age_ms)
        )

    except Exception:
        return fail_closed(
            args,
            result,
            "SOURCE_TIMING_FIELDS_INVALID",
            23,
        )

    if source_max_age_ms != requested_max_age_ms:
        return fail_closed(
            args,
            result,
            "MAX_AGE_POLICY_MISMATCH",
            24,
        )

    if requested_max_age_ms != Decimal("800"):
        return fail_closed(
            args,
            result,
            "NON_FROZEN_MAX_AGE_NOT_ALLOWED",
            25,
        )

    fifo_path = None

    if args.mode == "no-control":
        if (
            args.fifo_path is not None
            or args.control_authorization_token
            is not None
        ):
            return fail_closed(
                args,
                result,
                "NO_CONTROL_MODE_REJECTS_CONTROL_ARGUMENTS",
                26,
            )

    elif args.mode == "fifo":
        if (
            args.control_authorization_token
            != CONTROL_AUTHORIZATION_TOKEN
        ):
            return fail_closed(
                args,
                result,
                "CONTROL_AUTHORIZATION_TOKEN_INVALID",
                27,
            )

        if not args.fifo_path:
            return fail_closed(
                args,
                result,
                "FIFO_PATH_REQUIRED",
                28,
            )

        fifo_path = Path(
            args.fifo_path
        )

        try:
            fifo_stat = fifo_path.stat()
        except OSError:
            return fail_closed(
                args,
                result,
                "FIFO_PATH_UNAVAILABLE",
                29,
            )

        if not stat.S_ISFIFO(
            fifo_stat.st_mode
        ):
            return fail_closed(
                args,
                result,
                "CONTROL_PATH_IS_NOT_FIFO",
                30,
            )

        if "\n" in args.trigger_token:
            return fail_closed(
                args,
                result,
                "TRIGGER_TOKEN_CONTAINS_NEWLINE",
                31,
            )

    result.update({
        "SOURCE_LATEST_SAMPLE_UTC_NS":
            latest_sample_ns,

        "SOURCE_DECISION_UTC_NS":
            decision_ns,

        "SOURCE_MAXIMUM_ALLOWED_AGE_MS":
            str(source_max_age_ms),
    })

    #
    # All validation and optional FIFO metadata checks
    # occur above this point.
    #
    # After executor_start_ns the scientific control
    # path is intentionally bounded:
    #
    #   time.time_ns()
    #   age comparison
    #   [fifo mode only]
    #     time.time_ns()
    #     os.open(O_NONBLOCK)
    #     os.write()
    #     os.close()
    #
    # No runtime inspection or external process is used.
    #

    executor_start_ns = time.time_ns()

    age_ns = (
        executor_start_ns
        - latest_sample_ns
    )

    max_age_ns = int(
        requested_max_age_ms
        * Decimal("1000000")
    )

    age_ms = (
        Decimal(age_ns)
        / Decimal("1000000")
    )

    result.update({
        "EXECUTOR_START_UTC_NS":
            executor_start_ns,

        "EXECUTOR_START_SAMPLE_AGE_MS":
            str(age_ms),

        "EXECUTOR_START_MAX_ALLOWED_AGE_MS":
            str(requested_max_age_ms),
    })

    if (
        age_ns < 0
        or age_ns > max_age_ns
    ):
        result[
            "EXECUTOR_START_SAMPLE_AGE_GATE"
        ] = "FAIL"

        return fail_closed(
            args,
            result,
            "EXECUTOR_START_SAMPLE_AGE_OUT_OF_BOUNDS",
            32,
        )

    result[
        "EXECUTOR_START_SAMPLE_AGE_GATE"
    ] = "PASS"

    if args.mode == "no-control":
        result.update({
            "EXECUTOR_GATE":
                "PASS",

            "CONTROL_EXECUTED":
                "NO",

            "TRIGGER_WRITE_ATTEMPT_COUNT":
                0,

            "TRIGGER_WRITE_SUCCESS_COUNT":
                0,

            "SCIENTIFIC_TRIGGER_CONSUMED":
                "NO",

            "NO_CONTROL_DRY_RUN_GATE":
                "PASS",
        })

        write_result(
            args.output,
            result,
        )

        return 0

    trigger_start_ns = time.time_ns()

    result[
        "TRIGGER_EXECUTOR_START_UTC_NS"
    ] = trigger_start_ns

    fd = None
    write_attempt_count = 0
    write_success_count = 0

    try:
        fd = os.open(
            fifo_path,
            os.O_WRONLY
            | os.O_NONBLOCK,
        )

        payload = (
            args.trigger_token
            + "\n"
        ).encode("utf-8")

        write_attempt_count = 1

        written = os.write(
            fd,
            payload,
        )

        if written != len(payload):
            raise RuntimeError(
                "partial FIFO trigger write"
            )

        write_success_count = 1

    except Exception as exc:
        result.update({
            "EXECUTOR_GATE":
                "FAIL_AFTER_AGE_GATE",

            "FAIL_CLOSED_REASON":
                (
                    "FIFO_EXECUTION_FAILED:"
                    + type(exc).__name__
                ),

            "CONTROL_EXECUTED":
                (
                    "UNKNOWN_AFTER_WRITE_ATTEMPT"
                    if write_attempt_count
                    else "NO"
                ),

            "TRIGGER_WRITE_ATTEMPT_COUNT":
                write_attempt_count,

            "TRIGGER_WRITE_SUCCESS_COUNT":
                write_success_count,

            "SCIENTIFIC_TRIGGER_CONSUMED":
                (
                    "UNKNOWN"
                    if write_attempt_count
                    else "NO"
                ),

            "SCIENTIFIC_TRIGGER_REPLAY_DECISION":
                (
                    "NEVER_AUTOMATICALLY_REPLAY"
                    if write_attempt_count
                    else
                    "NOT_APPLICABLE_NO_WRITE_ATTEMPT"
                ),
        })

        write_result(
            args.output,
            result,
        )

        return 40

    finally:
        if fd is not None:
            os.close(fd)

    trigger_end_ns = time.time_ns()

    result.update({
        "TRIGGER_EXECUTOR_END_UTC_NS":
            trigger_end_ns,

        "EXECUTOR_GATE":
            "PASS",

        "CONTROL_EXECUTED":
            "YES",

        "TRIGGER_WRITE_ATTEMPT_COUNT":
            1,

        "TRIGGER_WRITE_SUCCESS_COUNT":
            1,

        "SCIENTIFIC_TRIGGER_CONSUMED":
            "YES",

        "SCIENTIFIC_TRIGGER_REPLAY_DECISION":
            "NEVER_REPEAT",
    })

    write_result(
        args.output,
        result,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
