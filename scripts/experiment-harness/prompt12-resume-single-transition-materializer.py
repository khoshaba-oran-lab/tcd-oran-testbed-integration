#!/usr/bin/env python3

"""Materialize one resumed Prompt-12 scientific transition.

This tool is deliberately non-executing.  It validates an existing
production binding plus an existing resume-precontrol materialization and
emits one immutable single-transition execution description.

It does not start traffic, Docker, FIFO control, actuator control, PRB
control, or any scientific transition.
"""

import argparse
import json
import os
import pathlib
import sys
from typing import Any


SCHEMA = "sci_oran_prompt12_resume_single_transition_materialization_v1"
RESUME_SCHEMA = "sci_oran_prompt12_resume_precontrol_materialization_v1"

HANDOFF_STATIONARITY_MARKER = "--stationarity-command"
FINALIZATION_TIMELINE_MARKER = "--timeline-command"

SPRINT_TRANSITION_INDEX = 2
SPRINT_TRANSITION_LABEL = "T2"
EXECUTED_TRANSITION_ORDINAL = 1
EXPECTED_TIMELINE_EVENT_COUNT = 3


class MaterializerError(Exception):
    pass


def load_object(path: pathlib.Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MaterializerError(
            f"{label}_READ_FAILED:{type(exc).__name__}"
        ) from exc

    if not isinstance(value, dict):
        raise MaterializerError(f"{label}_NOT_OBJECT")

    return value


def require_command(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise MaterializerError(f"{label}_INVALID")

    if not all(isinstance(item, str) and item for item in value):
        raise MaterializerError(f"{label}_INVALID")

    return list(value)


def require_bool(value: Any, expected: bool, label: str) -> None:
    if value is not expected:
        raise MaterializerError(f"{label}_INVALID")


def option_positions(command: list[str], option: str) -> list[int]:
    return [
        index
        for index, value in enumerate(command)
        if value == option
    ]


def replace_single_option(
    command: list[str],
    option: str,
    expected_old: str,
    new_value: str,
    label: str,
) -> list[str]:
    positions = option_positions(command, option)

    if len(positions) != 1:
        raise MaterializerError(
            f"{label}_{option}_CARDINALITY_INVALID:{len(positions)}"
        )

    index = positions[0]

    if index + 1 >= len(command):
        raise MaterializerError(
            f"{label}_{option}_VALUE_MISSING"
        )

    if command[index + 1] != expected_old:
        raise MaterializerError(
            f"{label}_{option}_SOURCE_VALUE_INVALID:"
            f"{command[index + 1]}"
        )

    result = list(command)
    result[index + 1] = new_value
    return result


def extract_pure_post_stationarity(
    wrapped_command: list[str],
    scientific_transition_index: int,
) -> list[str]:
    positions = option_positions(
        wrapped_command,
        HANDOFF_STATIONARITY_MARKER,
    )

    if len(positions) != 1:
        raise MaterializerError(
            "POST_HANDOFF_STATIONARITY_MARKER_CARDINALITY_INVALID:"
            + str(len(positions))
        )

    marker_index = positions[0]

    if marker_index + 1 >= len(wrapped_command):
        raise MaterializerError(
            "POST_HANDOFF_STATIONARITY_COMMAND_MISSING"
        )

    pure = require_command(
        wrapped_command[marker_index + 1:],
        "PURE_POST_STATIONARITY_COMMAND",
    )

    pure = replace_single_option(
        pure,
        "--control-index",
        str(scientific_transition_index),
        str(EXECUTED_TRANSITION_ORDINAL),
        "PURE_POST",
    )

    pure = replace_single_option(
        pure,
        "--expected-timeline-event-count",
        str(scientific_transition_index * 3),
        str(EXPECTED_TIMELINE_EVENT_COUNT),
        "PURE_POST",
    )

    if HANDOFF_STATIONARITY_MARKER in pure:
        raise MaterializerError(
            "PURE_POST_CONTAINS_HANDOFF_MARKER"
        )

    return pure


def materialize_resume_finalization(
    source_command: list[str],
) -> list[str]:
    timeline_positions = option_positions(
        source_command,
        FINALIZATION_TIMELINE_MARKER,
    )

    if len(timeline_positions) != 1:
        raise MaterializerError(
            "FINALIZATION_TIMELINE_MARKER_CARDINALITY_INVALID:"
            + str(len(timeline_positions))
        )

    timeline_index = timeline_positions[0]

    common = list(source_command[:timeline_index])
    tail = list(source_command[timeline_index:])

    common = replace_single_option(
        common,
        "--expected-event-count",
        "18",
        str(EXPECTED_TIMELINE_EVENT_COUNT),
        "FINALIZATION",
    )

    return common + tail


def validate_binding(binding: dict[str, Any]) -> None:
    require_command(
        binding.get("traffic_command"),
        "TRAFFIC_COMMAND",
    )
    require_command(
        binding.get("initial_stationarity_command"),
        "INITIAL_STATIONARITY_COMMAND",
    )
    require_command(
        binding.get("finalization_command"),
        "FINALIZATION_COMMAND",
    )

    transitions = binding.get("transitions")

    if not isinstance(transitions, list) or len(transitions) != 6:
        raise MaterializerError(
            "TRANSITION_COUNT_INVALID"
        )

    for index, transition in enumerate(transitions, start=1):
        if not isinstance(transition, dict):
            raise MaterializerError(
                f"TRANSITION_{index}_NOT_OBJECT"
            )

        if transition.get("label") != f"T{index}":
            raise MaterializerError(
                f"TRANSITION_{index}_LABEL_INVALID"
            )

        require_command(
            transition.get("ratio_bind_command"),
            f"T{index}_RATIO_BIND_COMMAND",
        )
        require_command(
            transition.get("trigger_command"),
            f"T{index}_TRIGGER_COMMAND",
        )
        require_command(
            transition.get("post_stationarity_command"),
            f"T{index}_POST_STATIONARITY_COMMAND",
        )


def validate_resume(
    resume: dict[str, Any],
    transition_index: int,
) -> list[str]:
    if resume.get("schema") != RESUME_SCHEMA:
        raise MaterializerError(
            "RESUME_SCHEMA_INVALID"
        )

    if resume.get("initial_transition_index") != transition_index:
        raise MaterializerError(
            "RESUME_TRANSITION_INDEX_INVALID"
        )

    expected_label = f"T{transition_index}"

    if resume.get("first_scientific_transition") != expected_label:
        raise MaterializerError(
            "RESUME_FIRST_SCIENTIFIC_TRANSITION_INVALID"
        )

    if resume.get("precontrol_semantics") != "initial-pre-step":
        raise MaterializerError(
            "RESUME_PRECONTROL_SEMANTICS_INVALID"
        )

    require_bool(
        resume.get("synthetic_prior_transition_events"),
        False,
        "SYNTHETIC_PRIOR_TRANSITION_EVENTS",
    )

    require_bool(
        resume.get("skipped_transition_bindings_consumed"),
        False,
        "SKIPPED_TRANSITION_BINDINGS_CONSUMED",
    )

    require_bool(
        resume.get("command_executed"),
        False,
        "RESUME_COMMAND_EXECUTED",
    )

    return require_command(
        resume.get("command"),
        "RESUME_INITIAL_PRECONTROL_COMMAND",
    )


def build_materialization(
    binding: dict[str, Any],
    resume: dict[str, Any],
    transition_index: int,
) -> dict[str, Any]:
    if transition_index != SPRINT_TRANSITION_INDEX:
        raise MaterializerError(
            "SPRINT01_REQUIRES_TRANSITION_INDEX_2"
        )

    validate_binding(binding)

    initial_precontrol = validate_resume(
        resume,
        transition_index,
    )

    transitions = binding["transitions"]
    transition = transitions[transition_index - 1]

    label = transition["label"]

    if label != SPRINT_TRANSITION_LABEL:
        raise MaterializerError(
            "SPRINT01_TRANSITION_LABEL_INVALID"
        )

    ratio_bind = require_command(
        transition["ratio_bind_command"],
        "T2_RATIO_BIND_COMMAND",
    )

    trigger = require_command(
        transition["trigger_command"],
        "T2_TRIGGER_COMMAND",
    )

    wrapped_post = require_command(
        transition["post_stationarity_command"],
        "T2_WRAPPED_POST_STATIONARITY_COMMAND",
    )

    pure_post = extract_pure_post_stationarity(
        wrapped_post,
        transition_index,
    )

    finalization = materialize_resume_finalization(
        require_command(
            binding["finalization_command"],
            "FINALIZATION_COMMAND",
        )
    )

    return {
        "schema": SCHEMA,
        "transition_label": label,
        "transition_index": transition_index,
        "first_scientific_transition": label,
        "executed_transition_ordinal":
            EXECUTED_TRANSITION_ORDINAL,
        "expected_actuator_transaction_count": 1,
        "expected_timeline_event_count":
            EXPECTED_TIMELINE_EVENT_COUNT,
        "traffic_command": require_command(
            binding["traffic_command"],
            "TRAFFIC_COMMAND",
        ),
        "initial_precontrol_command": initial_precontrol,
        "ratio_bind_command": ratio_bind,
        "trigger_command": trigger,
        "post_stationarity_command": pure_post,
        "finalization_command": finalization,
        "synthetic_prior_transition_events": False,
        "skipped_transition_bindings_consumed": False,
        "t3_handoff_present": False,
        "t3_trigger_present": False,
        "command_executed": False,
        "control_executed": False,
        "traffic_executed": False,
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description=(
            "Materialize a non-executing resumed single-transition "
            "Prompt-12 execution description."
        )
    )

    value.add_argument(
        "--binding-manifest",
        required=True,
    )
    value.add_argument(
        "--resume-materialization",
        required=True,
    )
    value.add_argument(
        "--initial-transition-index",
        required=True,
        type=int,
    )
    value.add_argument(
        "--output",
        required=True,
    )

    return value


def write_exclusive(
    path: pathlib.Path,
    value: dict[str, Any],
) -> None:
    if not path.is_absolute():
        raise MaterializerError(
            "OUTPUT_PATH_NOT_ABSOLUTE"
        )

    if os.path.lexists(path):
        raise MaterializerError(
            "OUTPUT_ALREADY_EXISTS"
        )

    if not path.parent.is_dir():
        raise MaterializerError(
            "OUTPUT_PARENT_NOT_DIRECTORY"
        )

    payload = (
        json.dumps(
            value,
            sort_keys=True,
            indent=2,
        )
        + "\n"
    )

    with path.open(
        "x",
        encoding="utf-8",
    ) as handle:
        handle.write(payload)


def main() -> int:
    args = parser().parse_args()

    try:
        binding_path = pathlib.Path(
            args.binding_manifest
        )
        resume_path = pathlib.Path(
            args.resume_materialization
        )
        output_path = pathlib.Path(
            args.output
        )

        binding = load_object(
            binding_path,
            "BINDING",
        )
        resume = load_object(
            resume_path,
            "RESUME",
        )

        report = build_materialization(
            binding,
            resume,
            args.initial_transition_index,
        )

        write_exclusive(
            output_path,
            report,
        )

    except MaterializerError as exc:
        print(
            f"MATERIALIZATION_GATE=FAIL",
            file=sys.stderr,
        )
        print(
            f"FAIL_REASON={exc}",
            file=sys.stderr,
        )
        return 65

    print("MATERIALIZATION_GATE=PASS")
    print(
        "FIRST_SCIENTIFIC_TRANSITION="
        + report["first_scientific_transition"]
    )
    print(
        "INITIAL_TRANSITION_INDEX="
        + str(report["transition_index"])
    )
    print(
        "EXECUTED_TRANSITION_ORDINAL="
        + str(report["executed_transition_ordinal"])
    )
    print(
        "EXPECTED_TIMELINE_EVENT_COUNT="
        + str(report["expected_timeline_event_count"])
    )
    print("T3_HANDOFF_PRESENT=NO")
    print("T3_TRIGGER_PRESENT=NO")
    print("COMMAND_EXECUTED=NO")
    print("CONTROL_EXECUTED=NO")
    print("TRAFFIC_EXECUTED=NO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
