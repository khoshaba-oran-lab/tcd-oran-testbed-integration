#!/usr/bin/env python3
"""Materialize a resume-aware initial precontrol command for Prompt-12.

This tool does not execute traffic, stationarity, FIFO writes, actuator
control, Docker operations, or scientific transitions.  It transforms
the canonical initial-pre-step precontrol command from an existing
production binding manifest so that a resumed sequence can start at an
explicit transition index without synthesizing any skipped actuator
events.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from typing import Any, Sequence


SCHEMA = "sci_oran_prompt12_resume_precontrol_materialization_v1"
TRANSITION_LABELS = tuple(f"T{i}" for i in range(1, 7))


class ContractError(ValueError):
    pass


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def read_json(path: pathlib.Path) -> Any:
    if not path.is_file():
        raise ContractError(f"INPUT_NOT_REGULAR_FILE:{path}")

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ContractError(
            f"INPUT_JSON_INVALID:{path}:{exc.msg}"
        ) from exc


def require_command(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ContractError(f"{name}_NOT_NONEMPTY_ARGV")

    if any(not isinstance(item, str) or not item for item in value):
        raise ContractError(f"{name}_INVALID_ARGV_ITEM")

    return list(value)


def option_positions(argv: Sequence[str], option: str) -> list[int]:
    return [
        index
        for index, value in enumerate(argv[:-1])
        if value == option
    ]


def option_value(argv: Sequence[str], option: str) -> str:
    positions = option_positions(argv, option)

    if len(positions) != 1:
        raise ContractError(
            f"OPTION_CARDINALITY_INVALID:{option}:{len(positions)}"
        )

    return argv[positions[0] + 1]


def replace_option_value(
    argv: list[str],
    option: str,
    new_value: str,
) -> None:
    positions = option_positions(argv, option)

    if len(positions) != 1:
        raise ContractError(
            f"OPTION_CARDINALITY_INVALID:{option}:{len(positions)}"
        )

    argv[positions[0] + 1] = new_value


def require_absolute(value: str, name: str) -> pathlib.Path:
    path = pathlib.Path(value)

    if not path.is_absolute():
        raise ContractError(f"{name}_NOT_ABSOLUTE:{value}")

    return path


def replace_transition_file(
    value: str,
    *,
    expected_name: str,
    target_name: str,
    field: str,
) -> str:
    path = require_absolute(value, field)

    if path.name != expected_name:
        raise ContractError(
            f"{field}_EXPECTED_NAME_MISMATCH:"
            f"{path.name}:{expected_name}"
        )

    return str(path.with_name(target_name))


def replace_transition_directory(
    value: str,
    *,
    expected_name: str,
    target_name: str,
    field: str,
) -> str:
    path = require_absolute(value, field)

    if path.name != expected_name:
        raise ContractError(
            f"{field}_EXPECTED_NAME_MISMATCH:"
            f"{path.name}:{expected_name}"
        )

    return str(path.with_name(target_name))


def validate_manifest(manifest: Any) -> dict[str, Any]:
    if not isinstance(manifest, dict):
        raise ContractError("MANIFEST_NOT_OBJECT")

    initial = require_command(
        manifest.get("initial_stationarity_command"),
        "INITIAL_STATIONARITY_COMMAND",
    )

    transitions = manifest.get("transitions")

    if not isinstance(transitions, list) or len(transitions) != 6:
        raise ContractError("TRANSITIONS_CARDINALITY_NOT_SIX")

    labels = []

    for index, transition in enumerate(transitions, start=1):
        if not isinstance(transition, dict):
            raise ContractError(
                f"TRANSITION_NOT_OBJECT:{index}"
            )

        label = transition.get("label")
        labels.append(label)

        if label != f"T{index}":
            raise ContractError(
                f"TRANSITION_ORDER_MISMATCH:{index}:{label}"
            )

    if tuple(labels) != TRANSITION_LABELS:
        raise ContractError("TRANSITION_ORDER_INVALID")

    if option_value(initial, "--mode") != "initial-pre-step":
        raise ContractError(
            "INITIAL_STATIONARITY_MODE_NOT_INITIAL_PRE_STEP"
        )

    if "--control-index" in initial:
        raise ContractError(
            "INITIAL_STATIONARITY_HAS_CONTROL_INDEX"
        )

    if "--timeline-command-json" in initial:
        raise ContractError(
            "INITIAL_STATIONARITY_HAS_TIMELINE_COMMAND"
        )

    if "--expected-timeline-event-count" in initial:
        raise ContractError(
            "INITIAL_STATIONARITY_HAS_EXPECTED_TIMELINE_EVENT_COUNT"
        )

    return {
        "initial": initial,
        "transitions": transitions,
    }


def materialize(
    manifest_path: pathlib.Path,
    initial_transition_index: int,
) -> dict[str, Any]:
    if (
        isinstance(initial_transition_index, bool)
        or not isinstance(initial_transition_index, int)
        or not 1 <= initial_transition_index <= 6
    ):
        raise ContractError(
            "INITIAL_TRANSITION_INDEX_OUT_OF_RANGE"
        )

    manifest = read_json(manifest_path)
    validated = validate_manifest(manifest)

    source = validated["initial"]
    command = list(source)

    target_label = f"T{initial_transition_index}"

    if initial_transition_index == 1:
        if command != source:
            raise ContractError(
                "INDEX_ONE_COMMAND_CHANGED"
            )
    else:
        attempt_root = option_value(
            command,
            "--attempt-root",
        )
        precontrol_output = option_value(
            command,
            "--precontrol-output",
        )
        selected_output = option_value(
            command,
            "--selected-output",
        )
        stationarity_root = option_value(
            command,
            "--evidence-root",
        )

        replace_option_value(
            command,
            "--attempt-root",
            replace_transition_directory(
                attempt_root,
                expected_name="T1",
                target_name=target_label,
                field="ATTEMPT_ROOT",
            ),
        )

        replace_option_value(
            command,
            "--precontrol-output",
            replace_transition_file(
                precontrol_output,
                expected_name="T1.json",
                target_name=f"{target_label}.json",
                field="PRECONTROL_OUTPUT",
            ),
        )

        replace_option_value(
            command,
            "--selected-output",
            replace_transition_file(
                selected_output,
                expected_name="T1.selected.jsonl",
                target_name=f"{target_label}.selected.jsonl",
                field="SELECTED_OUTPUT",
            ),
        )

        replace_option_value(
            command,
            "--evidence-root",
            replace_transition_directory(
                stationarity_root,
                expected_name="initial",
                target_name=f"resume-{target_label}",
                field="STATIONARITY_EVIDENCE_ROOT",
            ),
        )

    if option_value(command, "--mode") != "initial-pre-step":
        raise ContractError(
            "MATERIALIZED_MODE_NOT_INITIAL_PRE_STEP"
        )

    forbidden_options = (
        "--control-index",
        "--timeline-command-json",
        "--expected-timeline-event-count",
        "--actuator-timeline",
    )

    for option in forbidden_options:
        if option in command:
            raise ContractError(
                f"RESUME_INITIAL_COMMAND_FORBIDDEN_OPTION:{option}"
            )

    expected_precontrol = f"{target_label}.json"

    if (
        pathlib.Path(
            option_value(command, "--precontrol-output")
        ).name
        != expected_precontrol
    ):
        raise ContractError(
            "TARGET_PRECONTROL_OUTPUT_MISMATCH"
        )

    if initial_transition_index > 1:
        forbidden_fragments = (
            "/precontrol/T1.json",
            "/precontrol/T1.selected.jsonl",
            "/precontrol-handoff/T1",
        )

        for item in command:
            for fragment in forbidden_fragments:
                if fragment in item:
                    raise ContractError(
                        "SKIPPED_T1_REFERENCE_REMAINS:"
                        + fragment
                    )

    return {
        "schema": SCHEMA,
        "source_manifest": str(manifest_path),
        "source_manifest_sha256": sha256(manifest_path),
        "initial_transition_index": initial_transition_index,
        "first_scientific_transition": target_label,
        "precontrol_semantics": "initial-pre-step",
        "synthetic_prior_transition_events": False,
        "skipped_transition_bindings_consumed": False,
        "command_executed": False,
        "traffic_executed": False,
        "fifo_trigger_executed": False,
        "actuator_request_executed": False,
        "control_executed": False,
        "command": command,
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser()

    value.add_argument(
        "--manifest",
        required=True,
    )
    value.add_argument(
        "--initial-transition-index",
        required=True,
        type=int,
        choices=range(1, 7),
    )
    value.add_argument(
        "--output",
        required=True,
    )

    return value


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)

    manifest_path = pathlib.Path(args.manifest)
    output_path = pathlib.Path(args.output)

    if not output_path.is_absolute():
        raise ContractError(
            "OUTPUT_PATH_NOT_ABSOLUTE"
        )

    if output_path.exists():
        raise ContractError(
            f"OUTPUT_ALREADY_EXISTS:{output_path}"
        )

    report = materialize(
        manifest_path,
        args.initial_transition_index,
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        with output_path.open(
            "x",
            encoding="utf-8",
        ) as stream:
            json.dump(
                report,
                stream,
                sort_keys=True,
                indent=2,
            )
            stream.write("\n")
    except FileExistsError as exc:
        raise ContractError(
            f"OUTPUT_ALREADY_EXISTS:{output_path}"
        ) from exc

    print(
        json.dumps(
            report,
            sort_keys=True,
            separators=(",", ":"),
        )
    )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as exc:
        print(
            "RESUME_PRECONTROL_MATERIALIZATION_GATE=FAIL:"
            + str(exc),
            file=sys.stderr,
        )
        raise SystemExit(2)
