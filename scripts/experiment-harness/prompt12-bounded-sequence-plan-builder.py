#!/usr/bin/env python3
import argparse
import json
import pathlib
import sys


BINDING_SCHEMA = "sci_oran_prompt12_bounded_sequence_bindings_v1"
PLAN_SCHEMA = "sci_oran_prompt12_bounded_sequence_v1"
TRANSITION_LABELS = tuple(f"T{index}" for index in range(1, 7))


class PlanBuilderError(Exception):
    pass


def require_exact_keys(record, expected, role):
    if not isinstance(record, dict):
        raise PlanBuilderError(f"{role} must be an object")

    expected = set(expected)
    actual = set(record)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)

    if missing:
        raise PlanBuilderError(
            f"{role} missing keys: {','.join(missing)}"
        )
    if extra:
        raise PlanBuilderError(
            f"{role} has unexpected keys: {','.join(extra)}"
        )


def validate_command(value, role):
    if not isinstance(value, list) or not value:
        raise PlanBuilderError(
            f"{role} must be a non-empty argv array"
        )

    command = []

    for index, item in enumerate(value):
        if not isinstance(item, str) or not item or "\0" in item:
            raise PlanBuilderError(
                f"{role}[{index}] must be a non-empty string without NUL"
            )
        command.append(item)

    return command


def load_bindings(path):
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise PlanBuilderError(
            f"binding manifest cannot be read: {exc}"
        ) from exc

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise PlanBuilderError(
            f"binding manifest is not valid JSON: {exc}"
        ) from exc


def build_plan(root):
    require_exact_keys(
        root,
        (
            "schema",
            "traffic_command",
            "initial_stationarity_command",
            "finalization_command",
            "transitions",
        ),
        "binding manifest",
    )

    if root["schema"] != BINDING_SCHEMA:
        raise PlanBuilderError("binding manifest schema is invalid")

    transitions = root["transitions"]

    if not isinstance(transitions, list):
        raise PlanBuilderError("transitions must be an array")
    if len(transitions) != len(TRANSITION_LABELS):
        raise PlanBuilderError("exactly six transitions are required")

    built_transitions = []

    for index, expected_label in enumerate(TRANSITION_LABELS):
        transition = transitions[index]
        role = f"transitions[{index}]"

        require_exact_keys(
            transition,
            (
                "label",
                "ratio_bind_command",
                "trigger_command",
                "post_stationarity_command",
            ),
            role,
        )

        if transition["label"] != expected_label:
            raise PlanBuilderError(
                f"{role}.label must be {expected_label}"
            )

        built_transitions.append(
            {
                "label": expected_label,
                "ratio_bind_command": validate_command(
                    transition["ratio_bind_command"],
                    f"{role}.ratio_bind_command",
                ),
                "trigger_command": validate_command(
                    transition["trigger_command"],
                    f"{role}.trigger_command",
                ),
                "post_stationarity_command": validate_command(
                    transition["post_stationarity_command"],
                    f"{role}.post_stationarity_command",
                ),
            }
        )

    return {
        "schema": PLAN_SCHEMA,
        "traffic_command": validate_command(
            root["traffic_command"],
            "traffic_command",
        ),
        "initial_stationarity_command": validate_command(
            root["initial_stationarity_command"],
            "initial_stationarity_command",
        ),
        "finalization_command": validate_command(
            root["finalization_command"],
            "finalization_command",
        ),
        "transitions": built_transitions,
    }


def write_plan(path, plan):
    if path.exists():
        raise PlanBuilderError("output path already exists")
    if not path.parent.is_dir():
        raise PlanBuilderError("output parent directory does not exist")

    try:
        with path.open("x", encoding="utf-8") as handle:
            json.dump(
                plan,
                handle,
                indent=2,
                sort_keys=True,
            )
            handle.write("\n")
    except FileExistsError as exc:
        raise PlanBuilderError("output path already exists") from exc
    except OSError as exc:
        raise PlanBuilderError(
            f"output plan cannot be written: {exc}"
        ) from exc


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Build a validated Prompt-12 bounded-sequence supervisor "
            "plan without executing any command."
        )
    )
    parser.add_argument("--binding", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def main():
    args = parse_args()

    try:
        bindings = load_bindings(pathlib.Path(args.binding))
        plan = build_plan(bindings)
        write_plan(pathlib.Path(args.output), plan)
    except PlanBuilderError as exc:
        print("PLAN_BUILDER_GATE=FAIL", file=sys.stderr)
        print(f"FAIL_REASON={exc}", file=sys.stderr)
        print("CONTROL_EXECUTED=NO", file=sys.stderr)
        return 65

    print("PLAN_BUILDER_GATE=PASS")
    print(f"OUTPUT={args.output}")
    print("TRANSITION_COUNT=6")
    print("CONTROL_EXECUTED=NO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
