#!/usr/bin/env python3

import argparse
import json
import os
import pathlib
import subprocess
import sys
import time
from decimal import Decimal


class PrestartError(RuntimeError):
    pass


LIVE_INTERLOCK_ENV = (
    "SCI_ORAN_PROMPT12_LIVE_CONTROL_ENABLE"
)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Fail-closed Prompt-12 atomic prestart executor. "
            "Evaluate the final precontrol gate, revalidate "
            "freshness immediately before start, and permit "
            "at most one docker start invocation."
        )
    )

    parser.add_argument(
        "--mode",
        choices=("simulate", "live-start"),
        required=True,
    )

    parser.add_argument("--gate", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--schema", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--evaluator", required=True)

    parser.add_argument(
        "--experiment-id",
        required=True,
    )

    parser.add_argument(
        "--run-id",
        required=True,
    )

    parser.add_argument(
        "--cutoff-utc-ns",
        type=int,
        default=None,
    )

    parser.add_argument(
        "--gate-decision-utc-ns",
        type=int,
        default=None,
    )

    parser.add_argument(
        "--prestart-utc-ns",
        type=int,
        default=None,
    )

    parser.add_argument(
        "--actuator-container",
        default=None,
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
        "--gate-output",
        required=True,
    )

    parser.add_argument(
        "--output",
        required=True,
    )

    return parser.parse_args()


def require_file(path):
    if not pathlib.Path(path).is_file():
        raise PrestartError(
            f"required input missing: {path}"
        )


def require_absent(path):
    if pathlib.Path(path).exists():
        raise PrestartError(
            f"output already exists: {path}"
        )


def load_policy(path):
    values = {}

    for raw in pathlib.Path(
        path
    ).read_text().splitlines():

        line = raw.strip()

        if (
            not line
            or line.startswith("#")
        ):
            continue

        if "=" not in line:
            raise PrestartError(
                f"invalid policy line: {line!r}"
            )

        key, value = line.split(
            "=",
            1,
        )

        if key in values:
            raise PrestartError(
                f"duplicate policy key: {key}"
            )

        values[key] = value

    required = {
        "FINAL_GATE_SELECTION",
        "FINAL_GATE_MAX_AGE_AT_DOCKER_START_MS",
        "FINAL_GATE_OUTPUT_STATIONARITY_PASS_REQUIRED",
        "FINAL_GATE_FRESHNESS_PASS_REQUIRED",
    }

    missing = sorted(
        required - values.keys()
    )

    if missing:
        raise PrestartError(
            "missing policy keys: "
            + ",".join(missing)
        )

    if (
        values["FINAL_GATE_SELECTION"]
        != "LATEST_50_COMPLETE_CONTIGUOUS_SAMPLES"
    ):
        raise PrestartError(
            "unexpected final-gate selection policy"
        )

    if (
        values[
            "FINAL_GATE_OUTPUT_STATIONARITY_PASS_REQUIRED"
        ]
        != "YES"
    ):
        raise PrestartError(
            "stationarity PASS is not mandatory"
        )

    if (
        values[
            "FINAL_GATE_FRESHNESS_PASS_REQUIRED"
        ]
        != "YES"
    ):
        raise PrestartError(
            "freshness PASS is not mandatory"
        )

    return values


def write_result(path, result):
    pathlib.Path(path).write_text(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def inspect_live_container(name):
    if not name:
        raise PrestartError(
            "live-start requires actuator container"
        )

    if not name.startswith(
        "prompt12-siso-actuator-"
    ):
        raise PrestartError(
            "unexpected actuator container name"
        )

    process = subprocess.run(
        [
            "docker",
            "inspect",
            name,
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    if process.returncode != 0:
        raise PrestartError(
            "actuator container inspect failed"
        )

    objects = json.loads(
        process.stdout
    )

    if len(objects) != 1:
        raise PrestartError(
            "unexpected docker inspect cardinality"
        )

    item = objects[0]
    state = item["State"]

    if state["Status"] != "created":
        raise PrestartError(
            "actuator container is not in created state"
        )

    if state["Running"]:
        raise PrestartError(
            "actuator container is already running"
        )

    if int(
        item["RestartCount"]
    ) != 0:
        raise PrestartError(
            "actuator restart count is not zero"
        )

    restart_policy = (
        item["HostConfig"]
        ["RestartPolicy"]
        ["Name"]
    )

    if restart_policy != "no":
        raise PrestartError(
            "actuator restart policy is not no"
        )


def main():
    args = parse_args()

    for path in (
        args.gate,
        args.input,
        args.schema,
        args.policy,
        args.evaluator,
    ):
        require_file(path)

    for path in (
        args.selected_output,
        args.stationarity_output,
        args.gate_output,
        args.output,
    ):
        require_absent(path)

    pathlib.Path(
        args.output
    ).parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    policy = load_policy(
        args.policy
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

    if args.mode == "simulate":

        if args.gate_decision_utc_ns is None:
            raise PrestartError(
                "simulate mode requires "
                "--gate-decision-utc-ns"
            )

        if args.prestart_utc_ns is None:
            raise PrestartError(
                "simulate mode requires "
                "--prestart-utc-ns"
            )

        if args.actuator_container is not None:
            raise PrestartError(
                "simulate mode forbids actuator container"
            )

    else:

        if args.gate_decision_utc_ns is not None:
            raise PrestartError(
                "live-start forbids synthetic gate time"
            )

        if args.prestart_utc_ns is not None:
            raise PrestartError(
                "live-start forbids synthetic prestart time"
            )

        if os.environ.get(
            LIVE_INTERLOCK_ENV
        ) != "YES":
            print(
                "PROMPT12_LIVE_CONTROL_INTERLOCK=BLOCKED"
            )

            print(
                "REQUIRED_ENV="
                + LIVE_INTERLOCK_ENV
                + "=YES"
            )

            return 77

        # Any potentially expensive Docker inspection
        # happens BEFORE the final gate.
        inspect_live_container(
            args.actuator_container
        )

    gate_command = [
        sys.executable,
        args.gate,

        "--input",
        args.input,

        "--schema",
        args.schema,

        "--policy",
        args.policy,

        "--evaluator",
        args.evaluator,

        "--experiment-id",
        args.experiment_id,

        "--run-id",
        args.run_id,

        "--selected-output",
        args.selected_output,

        "--stationarity-output",
        args.stationarity_output,

        "--output",
        args.gate_output,
    ]

    if args.cutoff_utc_ns is not None:
        gate_command.extend([
            "--cutoff-utc-ns",
            str(
                args.cutoff_utc_ns
            ),
        ])

    if args.gate_decision_utc_ns is not None:
        gate_command.extend([
            "--decision-utc-ns",
            str(
                args.gate_decision_utc_ns
            ),
        ])

    gate_process = subprocess.run(
        gate_command,
        text=True,
        capture_output=True,
        check=False,
    )

    print(
        "FINAL_GATE_PROCESS_RC="
        f"{gate_process.returncode}"
    )

    if gate_process.stdout:
        print(
            gate_process.stdout,
            end="",
        )

    if gate_process.stderr:
        print(
            gate_process.stderr,
            end="",
            file=sys.stderr,
        )

    if gate_process.returncode not in (
        0,
        10,
    ):
        raise PrestartError(
            "precontrol gate execution failed"
        )

    gate_path = pathlib.Path(
        args.gate_output
    )

    if not gate_path.is_file():
        raise PrestartError(
            "precontrol gate output missing"
        )

    gate_report = json.loads(
        gate_path.read_text()
    )

    latest_sample_ns = int(
        gate_report[
            "latest_sample_timestamp_utc_ns"
        ]
    )

    gate_decision_ns = int(
        gate_report[
            "decision_utc_ns"
        ]
    )

    gate_admission = (
        gate_report[
            "precontrol_admission_gate"
        ]
    )

    result = {
        "schema":
            "sci_oran_prompt12_atomic_prestart_v1",

        "mode":
            args.mode,

        "experiment_id":
            args.experiment_id,

        "run_id":
            args.run_id,

        "live_interlock_env":
            LIVE_INTERLOCK_ENV,

        "final_gate_process_rc":
            gate_process.returncode,

        "final_gate_admission":
            gate_admission,

        "latest_sample_timestamp_utc_ns":
            latest_sample_ns,

        "gate_decision_utc_ns":
            gate_decision_ns,

        "maximum_allowed_sample_age_ms":
            str(max_age_ms),

        "prestart_freshness_gate":
            "NOT_EVALUATED",

        "atomic_prestart_gate":
            "FAIL",

        "docker_start_invocation_count":
            0,

        "docker_start_executed":
            False,

        "would_start":
            False,

        "do_not_retry_same_actuator_after_start":
            True,
    }

    if (
        gate_process.returncode != 0
        or gate_admission != "PASS"
    ):
        result[
            "blocking_reason"
        ] = "FINAL_PRECONTROL_GATE_FAIL"

        write_result(
            args.output,
            result,
        )

        print(
            "ATOMIC_PRESTART_FINAL_GATE=FAIL"
        )

        print(
            "ATOMIC_PRESTART_START_EXECUTED=NO"
        )

        return 10

    prestart_ns = (
        args.prestart_utc_ns
        if args.mode == "simulate"
        else time.time_ns()
    )

    sample_age_ns = (
        prestart_ns
        - latest_sample_ns
    )

    decision_to_prestart_ns = (
        prestart_ns
        - gate_decision_ns
    )

    prestart_fresh = (
        sample_age_ns >= 0
        and sample_age_ns <= max_age_ns
    )

    result.update({
        "prestart_utc_ns":
            prestart_ns,

        "sample_age_at_prestart_ms":
            str(
                Decimal(sample_age_ns)
                / Decimal("1000000")
            ),

        "gate_decision_to_prestart_ms":
            str(
                Decimal(
                    decision_to_prestart_ns
                )
                / Decimal("1000000")
            ),

        "prestart_freshness_gate":
            (
                "PASS"
                if prestart_fresh
                else "FAIL"
            ),
    })

    print(
        "ATOMIC_PRESTART_SAMPLE_AGE_MS="
        + result[
            "sample_age_at_prestart_ms"
        ]
    )

    print(
        "ATOMIC_PRESTART_MAX_ALLOWED_AGE_MS="
        + str(max_age_ms)
    )

    if not prestart_fresh:

        result[
            "blocking_reason"
        ] = "STALE_AT_PRESTART"

        write_result(
            args.output,
            result,
        )

        print(
            "ATOMIC_PRESTART_FRESHNESS_GATE=FAIL"
        )

        print(
            "ATOMIC_PRESTART_START_EXECUTED=NO"
        )

        return 10

    result[
        "prestart_freshness_gate"
    ] = "PASS"

    result[
        "atomic_prestart_gate"
    ] = "PASS"

    if args.mode == "simulate":

        result[
            "would_start"
        ] = True

        result[
            "blocking_reason"
        ] = None

        write_result(
            args.output,
            result,
        )

        print(
            "ATOMIC_PRESTART_FRESHNESS_GATE=PASS"
        )

        print(
            "ATOMIC_PRESTART_GATE=PASS"
        )

        print(
            "ATOMIC_PRESTART_WOULD_START=YES"
        )

        print(
            "ATOMIC_PRESTART_START_EXECUTED=NO"
        )

        return 0

    # This is the final causal boundary.
    #
    # No Docker inspect, file processing, stationarity
    # evaluation or other long-running operation may
    # occur between this timestamp and docker start.

    docker_start_invoke_ns = (
        time.time_ns()
    )

    actual_age_ns = (
        docker_start_invoke_ns
        - latest_sample_ns
    )

    if (
        actual_age_ns < 0
        or actual_age_ns > max_age_ns
    ):
        result[
            "prestart_freshness_gate"
        ] = "FAIL"

        result[
            "atomic_prestart_gate"
        ] = "FAIL"

        result[
            "blocking_reason"
        ] = (
            "STALE_AT_DOCKER_START_INVOCATION"
        )

        result[
            "docker_start_invoke_utc_ns"
        ] = docker_start_invoke_ns

        result[
            "sample_age_at_docker_start_invoke_ms"
        ] = str(
            Decimal(actual_age_ns)
            / Decimal("1000000")
        )

        write_result(
            args.output,
            result,
        )

        print(
            "ATOMIC_PRESTART_DOCKER_START_AGE_GATE=FAIL"
        )

        print(
            "ATOMIC_PRESTART_START_EXECUTED=NO"
        )

        return 10

    result[
        "docker_start_invoke_utc_ns"
    ] = docker_start_invoke_ns

    result[
        "sample_age_at_docker_start_invoke_ms"
    ] = str(
        Decimal(actual_age_ns)
        / Decimal("1000000")
    )

    start_process = subprocess.run(
        [
            "docker",
            "start",
            args.actuator_container,
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    # Once subprocess.run above has been invoked,
    # this executor must never invoke docker start
    # for this actuator again.

    result[
        "docker_start_invocation_count"
    ] = 1

    result[
        "docker_start_executed"
    ] = True

    result[
        "docker_start_rc"
    ] = start_process.returncode

    result[
        "docker_start_stdout"
    ] = start_process.stdout

    result[
        "docker_start_stderr"
    ] = start_process.stderr

    if start_process.returncode == 0:
        result[
            "blocking_reason"
        ] = None
    else:
        result[
            "blocking_reason"
        ] = (
            "DOCKER_START_FAILED_AFTER_SINGLE_INVOCATION"
        )

    write_result(
        args.output,
        result,
    )

    print(
        "ATOMIC_PRESTART_DOCKER_START_AGE_GATE=PASS"
    )

    print(
        "ATOMIC_PRESTART_DOCKER_START_INVOCATION_COUNT=1"
    )

    print(
        "ATOMIC_PRESTART_DOCKER_START_RC="
        f"{start_process.returncode}"
    )

    print(
        "ATOMIC_PRESTART_REPEAT_POLICY="
        "NEVER_REPEAT_AFTER_START_INVOCATION"
    )

    return (
        0
        if start_process.returncode == 0
        else 11
    )


if __name__ == "__main__":
    try:
        raise SystemExit(
            main()
        )

    except PrestartError as exc:
        print(
            f"ERROR={exc}",
            file=sys.stderr,
        )

        raise SystemExit(64)
