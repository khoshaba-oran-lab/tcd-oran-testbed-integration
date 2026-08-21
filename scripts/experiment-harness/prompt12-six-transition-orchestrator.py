#!/usr/bin/env python3

import argparse
import json
import pathlib
import re
import sys


BLOCKED_RC = 20

EXPERIMENT_RE = re.compile(
    r"^EXP-[0-9]{8}-DL-18000K-(R0[1-4])$"
)

RUN_RE = re.compile(
    r"^RUN-[0-9]{8}T[0-9]{6}Z-[0-9]{3}$"
)

EXPECTED_TRANSITIONS = [
    {
        "transition_label": "T1",
        "from_ratio_pct": 25,
        "to_ratio_pct": 50,
        "from_prbs": 13,
        "to_prbs": 26,
    },
    {
        "transition_label": "T2",
        "from_ratio_pct": 50,
        "to_ratio_pct": 75,
        "from_prbs": 26,
        "to_prbs": 39,
    },
    {
        "transition_label": "T3",
        "from_ratio_pct": 75,
        "to_ratio_pct": 100,
        "from_prbs": 39,
        "to_prbs": 52,
    },
    {
        "transition_label": "T4",
        "from_ratio_pct": 100,
        "to_ratio_pct": 75,
        "from_prbs": 52,
        "to_prbs": 39,
    },
    {
        "transition_label": "T5",
        "from_ratio_pct": 75,
        "to_ratio_pct": 50,
        "from_prbs": 39,
        "to_prbs": 26,
    },
    {
        "transition_label": "T6",
        "from_ratio_pct": 50,
        "to_ratio_pct": 25,
        "from_prbs": 26,
        "to_prbs": 13,
    },
]

REPEAT_TO_MODEL_USE = {
    "R01": "estimation",
    "R02": "estimation",
    "R03": "estimation",
    "R04": "holdout_validation",
}

VALID_GATE_VALUES = {
    "PASS",
    "FAIL",
}


class OrchestrationError(Exception):
    pass


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Prompt-12 six-transition orchestration state machine. "
            "This implementation supports dry-run planning only and "
            "contains no live execution mechanism."
        )
    )

    parser.add_argument(
        "--mode",
        required=True,
        choices=["dry-run"],
    )

    parser.add_argument(
        "--schema",
        required=True,
    )

    parser.add_argument(
        "--experiment-id",
        required=True,
    )

    parser.add_argument(
        "--run-id",
        required=True,
    )

    parser.add_argument(
        "--repeat-id",
        required=True,
        choices=[
            "R01",
            "R02",
            "R03",
            "R04",
        ],
    )

    parser.add_argument(
        "--initial-stationarity-gate",
        required=True,
        choices=[
            "PASS",
            "FAIL",
        ],
    )

    parser.add_argument(
        "--post-stationarity-gates",
        required=True,
        help=(
            "Exactly six comma-separated gate values for "
            "post-T1 through post-T6, each PASS or FAIL."
        ),
    )

    parser.add_argument(
        "--output",
        required=True,
    )

    return parser.parse_args()


def validate_identity(
    experiment_id,
    run_id,
    repeat_id,
):
    match = EXPERIMENT_RE.fullmatch(
        experiment_id
    )

    if match is None:
        raise OrchestrationError(
            "invalid Prompt-12 experiment_id"
        )

    experiment_repeat = match.group(1)

    if experiment_repeat != repeat_id:
        raise OrchestrationError(
            "experiment_id repeat does not match repeat-id"
        )

    if RUN_RE.fullmatch(run_id) is None:
        raise OrchestrationError(
            "invalid Prompt-12 run_id"
        )


def load_schema_transition_plan(
    schema_path,
):
    path = pathlib.Path(schema_path)

    root = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    try:
        transition_plan = (
            root["$defs"]
            ["transitionPlan"]
            ["const"]
        )

    except KeyError as exc:
        raise OrchestrationError(
            "schema transitionPlan contract missing"
        ) from exc

    if transition_plan != EXPECTED_TRANSITIONS:
        raise OrchestrationError(
            "schema transitionPlan differs from frozen T1-T6 contract"
        )

    return transition_plan


def parse_post_gates(text):
    values = [
        item.strip().upper()
        for item in text.split(",")
    ]

    if len(values) != 6:
        raise OrchestrationError(
            "post-stationarity-gates must contain exactly six values"
        )

    for index, value in enumerate(
        values,
        start=1,
    ):
        if value not in VALID_GATE_VALUES:
            raise OrchestrationError(
                "invalid post-stationarity gate "
                f"at index {index}"
            )

    return values


def make_control_plan(
    transition,
    control_index,
    admission_source,
    admission_gate,
):
    return {
        "control_index": control_index,
        "transition_label": transition[
            "transition_label"
        ],
        "from_ratio_pct": transition[
            "from_ratio_pct"
        ],
        "to_ratio_pct": transition[
            "to_ratio_pct"
        ],
        "from_prbs": transition[
            "from_prbs"
        ],
        "to_prbs": transition[
            "to_prbs"
        ],
        "admission_source": (
            admission_source
        ),
        "admission_gate": (
            admission_gate
        ),
        "control_time_origin": (
            "applied_readback"
        ),
        "ack_as_time_origin": False,
        "execution_mode": (
            "DRY_RUN_NO_CONTROL_EXECUTION"
        ),
    }


def evaluate_sequence(
    transition_plan,
    initial_gate,
    post_gates,
):
    admitted_controls = []

    for index, transition in enumerate(
        transition_plan
    ):
        control_number = index + 1

        if index == 0:
            admission_source = (
                "initial_pre_step_stationarity"
            )

            admission_gate = initial_gate

        else:
            admission_source = (
                "post_"
                + transition_plan[
                    index - 1
                ]["transition_label"]
                + "_stationarity"
            )

            admission_gate = (
                post_gates[index - 1]
            )

        if admission_gate != "PASS":
            return {
                "sequence_gate": "BLOCKED",
                "sequence_complete": False,
                "admitted_control_count": len(
                    admitted_controls
                ),
                "blocked_before_control": (
                    transition[
                        "transition_label"
                    ]
                ),
                "blocked_completion_point": None,
                "blocking_gate_source": (
                    admission_source
                ),
                "blocking_gate_value": (
                    admission_gate
                ),
                "controls": (
                    admitted_controls
                ),
            }

        admitted_controls.append(
            make_control_plan(
                transition,
                control_number,
                admission_source,
                admission_gate,
            )
        )

    final_gate = post_gates[5]

    if final_gate != "PASS":
        return {
            "sequence_gate": "BLOCKED",
            "sequence_complete": False,
            "admitted_control_count": 6,
            "blocked_before_control": None,
            "blocked_completion_point": (
                "POST_T6_COMPLETION"
            ),
            "blocking_gate_source": (
                "post_T6_stationarity"
            ),
            "blocking_gate_value": (
                final_gate
            ),
            "controls": admitted_controls,
        }

    return {
        "sequence_gate": "PASS",
        "sequence_complete": True,
        "admitted_control_count": 6,
        "blocked_before_control": None,
        "blocked_completion_point": None,
        "blocking_gate_source": None,
        "blocking_gate_value": None,
        "controls": admitted_controls,
    }


def build_report(
    args,
    transition_plan,
    post_gates,
):
    sequence = evaluate_sequence(
        transition_plan,
        args.initial_stationarity_gate,
        post_gates,
    )

    report = {
        "schema": (
            "sci_oran_prompt12_six_transition_"
            "dry_run_orchestration_v1"
        ),
        "mode": "dry-run",
        "experiment_id": args.experiment_id,
        "run_id": args.run_id,
        "repeat_id": args.repeat_id,
        "model_use_class": (
            REPEAT_TO_MODEL_USE[
                args.repeat_id
            ]
        ),
        "initial_ratio_pct": 25,
        "initial_prbs": 13,
        "expected_control_count": 6,
        "transition_labels": [
            item["transition_label"]
            for item in transition_plan
        ],
        "control_target_ratios": [
            item["to_ratio_pct"]
            for item in transition_plan
        ],
        "control_target_prbs": [
            item["to_prbs"]
            for item in transition_plan
        ],
        "traffic_stream_count": 1,
        "traffic_continuity_required": True,
        "receiver_continuity_required": True,
        "initial_admission": (
            "STARTUP_GUARD_PLUS_"
            "OUTPUT_STATIONARITY_PASS"
        ),
        "intermediate_admission": (
            "PREVIOUS_POST_STEP_"
            "STATIONARITY_PASS"
        ),
        "additional_startup_guard_between_transitions": False,
        "next_control_without_stationarity_pass": False,
        "control_time_origin": "applied_readback",
        "ack_as_time_origin": False,
        "live_control_allowed": False,
        "live_traffic_allowed": False,
        "docker_mutation_allowed": False,
        "initial_stationarity_gate": (
            args.initial_stationarity_gate
        ),
        "post_stationarity_gates": (
            post_gates
        ),
    }

    report.update(sequence)

    return report


def write_report(
    output_path,
    report,
):
    path = pathlib.Path(output_path)

    if path.exists():
        raise OrchestrationError(
            "output already exists"
        )

    path.write_text(
        json.dumps(
            report,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )


def main():
    args = parse_args()

    validate_identity(
        args.experiment_id,
        args.run_id,
        args.repeat_id,
    )

    transition_plan = (
        load_schema_transition_plan(
            args.schema
        )
    )

    post_gates = parse_post_gates(
        args.post_stationarity_gates
    )

    report = build_report(
        args,
        transition_plan,
        post_gates,
    )

    write_report(
        args.output,
        report,
    )

    print("ORCHESTRATION_MODE=DRY_RUN")
    print(
        "TRANSITION_SEQUENCE="
        "T1,T2,T3,T4,T5,T6"
    )
    print(
        "CONTROL_TARGET_RATIOS="
        "50,75,100,75,50,25"
    )
    print(
        "CONTROL_TARGET_PRBS="
        "26,39,52,39,26,13"
    )
    print(
        "EXPECTED_CONTROL_COUNT=6"
    )
    print(
        "ADMITTED_CONTROL_COUNT="
        f"{report['admitted_control_count']}"
    )
    print(
        "SEQUENCE_GATE="
        f"{report['sequence_gate']}"
    )
    print(
        "SEQUENCE_COMPLETE="
        + (
            "YES"
            if report["sequence_complete"]
            else "NO"
        )
    )
    print(
        "BLOCKED_BEFORE_CONTROL="
        + (
            "NONE"
            if report[
                "blocked_before_control"
            ] is None
            else report[
                "blocked_before_control"
            ]
        )
    )
    print(
        "BLOCKED_COMPLETION_POINT="
        + (
            "NONE"
            if report[
                "blocked_completion_point"
            ] is None
            else report[
                "blocked_completion_point"
            ]
        )
    )
    print(
        "LIVE_CONTROL_ALLOWED=NO"
    )
    print(
        "LIVE_TRAFFIC_ALLOWED=NO"
    )
    print(
        "DOCKER_MUTATION_ALLOWED=NO"
    )
    print(
        "CONTROL_TIME_ORIGIN="
        "APPLIED_READBACK"
    )
    print(
        "ACK_AS_TIME_ORIGIN=NO"
    )

    if report["sequence_gate"] != "PASS":
        return BLOCKED_RC

    print(
        "SIX_TRANSITION_DRY_RUN_ORCHESTRATION=PASS"
    )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())

    except OrchestrationError as exc:
        print(
            f"ERROR={exc}",
            file=sys.stderr,
        )

        raise SystemExit(64)
