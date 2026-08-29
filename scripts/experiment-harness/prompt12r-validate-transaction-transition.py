#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator


EX_DATAERR = 65

VALIDATOR_VERSION = "1.0.0"

PRETRIGGER_STATES = {
    "NEW",
    "DEPLOYED",
    "PLATFORM_QUALIFIED",
    "INITIAL_STATE_VERIFIED",
    "ACTUATOR_ARMED",
    "WORKLOAD_READY",
    "PRESTEP_ADMITTED",
    "ABORTED_PRETRIGGER",
}

FAILURE_STATES = {
    "ABORTED_PRETRIGGER",
    "INVALID_POSTTRIGGER",
}

LEGAL_TRANSITIONS = {
    "NEW": {
        "DEPLOYED",
        "ABORTED_PRETRIGGER",
    },
    "DEPLOYED": {
        "PLATFORM_QUALIFIED",
        "ABORTED_PRETRIGGER",
    },
    "PLATFORM_QUALIFIED": {
        "INITIAL_STATE_VERIFIED",
        "ABORTED_PRETRIGGER",
    },
    "INITIAL_STATE_VERIFIED": {
        "ACTUATOR_ARMED",
        "ABORTED_PRETRIGGER",
    },
    "ACTUATOR_ARMED": {
        "WORKLOAD_READY",
        "ABORTED_PRETRIGGER",
    },
    "WORKLOAD_READY": {
        "PRESTEP_ADMITTED",
        "ABORTED_PRETRIGGER",
    },
    "PRESTEP_ADMITTED": {
        "TRIGGERED_EXACTLY_ONCE",
        "ABORTED_PRETRIGGER",
        "INVALID_POSTTRIGGER",
    },
    "TRIGGERED_EXACTLY_ONCE": {
        "APPLIED_VERIFIED",
        "INVALID_POSTTRIGGER",
    },
    "APPLIED_VERIFIED": {
        "POSTSTEP_COMPLETE",
        "INVALID_POSTTRIGGER",
    },
    "POSTSTEP_COMPLETE": {
        "SCIENTIFICALLY_ADJUDICATED",
        "INVALID_POSTTRIGGER",
    },
    "INVALID_POSTTRIGGER": {
        "SCIENTIFICALLY_ADJUDICATED",
    },
    "SCIENTIFICALLY_ADJUDICATED": {
        "CLOSED",
    },
    "ABORTED_PRETRIGGER": {
        "CLOSED",
    },
    "CLOSED": {
        "DESTROYED",
    },
    "DESTROYED": set(),
}

IMMUTABLE_FIELDS = (
    "transaction_id",
    "experiment_id",
    "run_id",
    "transition_label",
    "repository_head",
    "protocol_identity",
    "initial_prb_required",
)

WRITE_ONCE_FIELDS = (
    "platform_qualification_identity",
    "runtime_incarnation_identity",
    "initial_prb_observed",
    "receiver_workload_identity",
    "actuator_identity",
    "applied_readback_identity",
    "closeout_checksum_identity",
)

TRIGGER_FIELDS = (
    "trigger_write_attempt_count",
    "trigger_write_success_count",
    "scientific_trigger_consumed",
    "replay_decision",
)


class SemanticError(Exception):
    pass


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Offline Prompt 12R transaction state-transition validator. "
            "The tool performs no Docker, workload, lifecycle or control "
            "operation."
        )
    )

    parser.add_argument(
        "--schema",
        required=True,
        help="Prompt 12R transaction JSON Schema",
    )

    parser.add_argument(
        "--current",
        required=True,
        help="Current transaction-state JSON record",
    )

    parser.add_argument(
        "--previous",
        help=(
            "Previous transaction-state JSON record. Required for every "
            "current state except NEW."
        ),
    )

    return parser.parse_args()


def load_json(path_value, label):
    path = Path(path_value)

    if not path.is_file():
        raise SemanticError(
            f"{label}_FILE_MISSING"
        )

    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise SemanticError(
            f"{label}_JSON_INVALID:{type(exc).__name__}"
        ) from exc


def schema_errors(validator, record):
    return sorted(
        validator.iter_errors(record),
        key=lambda error: (
            list(error.absolute_path),
            error.message,
        ),
    )


def require(condition, reason):
    if not condition:
        raise SemanticError(reason)


def require_nonempty(value, reason):
    require(
        isinstance(value, str) and bool(value),
        reason,
    )


def validate_schema(schema):
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as exc:
        raise SemanticError(
            "SCHEMA_SELF_CHECK_FAILED:"
            + type(exc).__name__
        ) from exc

    return Draft202012Validator(schema)


def validate_record_schema(
    validator,
    record,
    label,
):
    errors = schema_errors(
        validator,
        record,
    )

    if not errors:
        return

    first = errors[0]

    path = ".".join(
        str(item)
        for item in first.absolute_path
    )

    if not path:
        path = "<root>"

    raise SemanticError(
        f"{label}_SCHEMA_INVALID:"
        f"{path}:{first.message}"
    )


def validate_record_state_invariants(record):
    state = record["transaction_state"]

    if state in {
        "NEW",
        "DEPLOYED",
        "PLATFORM_QUALIFIED",
        "INITIAL_STATE_VERIFIED",
        "ACTUATOR_ARMED",
        "WORKLOAD_READY",
        "PRESTEP_ADMITTED",
        "TRIGGERED_EXACTLY_ONCE",
        "APPLIED_VERIFIED",
        "POSTSTEP_COMPLETE",
    }:
        require(
            record["failure_class"] == "NONE",
            "ACTIVE_STATE_FAILURE_CLASS_NOT_NONE",
        )
        require(
            record["failure_reason"] == "NONE",
            "ACTIVE_STATE_FAILURE_REASON_NOT_NONE",
        )

    if state in FAILURE_STATES:
        require(
            record["failure_class"]
            in {
                "PLATFORM_FAILURE",
                "TOOLING_FAILURE",
            },
            "FAILURE_STATE_CLASS_INVALID",
        )
        require(
            record["failure_reason"] != "NONE",
            "FAILURE_STATE_REASON_MISSING",
        )

    if state in PRETRIGGER_STATES:
        require(
            record["trigger_write_attempt_count"] == 0,
            "PRETRIGGER_WRITE_ATTEMPT_NOT_ZERO",
        )
        require(
            record["trigger_write_success_count"] == 0,
            "PRETRIGGER_WRITE_SUCCESS_NOT_ZERO",
        )
        require(
            record["scientific_trigger_consumed"] == "NO",
            "PRETRIGGER_CONSUMPTION_NOT_NO",
        )
        require(
            record["replay_decision"] == "NOT_APPLICABLE",
            "PRETRIGGER_REPLAY_DECISION_INVALID",
        )

    if state == "TRIGGERED_EXACTLY_ONCE":
        require(
            record["trigger_write_attempt_count"] == 1,
            "EXACTLY_ONCE_ATTEMPT_COUNT_INVALID",
        )
        require(
            record["trigger_write_success_count"] == 1,
            "EXACTLY_ONCE_SUCCESS_COUNT_INVALID",
        )
        require(
            record["scientific_trigger_consumed"] == "YES",
            "EXACTLY_ONCE_CONSUMPTION_INVALID",
        )
        require(
            record["replay_decision"] == "NEVER_REPEAT",
            "EXACTLY_ONCE_REPLAY_DECISION_INVALID",
        )

    if state in {
        "PLATFORM_QUALIFIED",
        "INITIAL_STATE_VERIFIED",
        "ACTUATOR_ARMED",
        "WORKLOAD_READY",
        "PRESTEP_ADMITTED",
        "TRIGGERED_EXACTLY_ONCE",
        "APPLIED_VERIFIED",
        "POSTSTEP_COMPLETE",
    }:
        require_nonempty(
            record["platform_qualification_identity"],
            "PLATFORM_QUALIFICATION_IDENTITY_MISSING",
        )
        require_nonempty(
            record["runtime_incarnation_identity"],
            "RUNTIME_INCARNATION_IDENTITY_MISSING",
        )

    if state in {
        "INITIAL_STATE_VERIFIED",
        "ACTUATOR_ARMED",
        "WORKLOAD_READY",
        "PRESTEP_ADMITTED",
        "TRIGGERED_EXACTLY_ONCE",
        "APPLIED_VERIFIED",
        "POSTSTEP_COMPLETE",
    }:
        require(
            record["initial_prb_observed"]
            == record["initial_prb_required"],
            "INITIAL_PRB_STATE_MISMATCH",
        )

    if state in {
        "ACTUATOR_ARMED",
        "WORKLOAD_READY",
        "PRESTEP_ADMITTED",
        "TRIGGERED_EXACTLY_ONCE",
        "APPLIED_VERIFIED",
        "POSTSTEP_COMPLETE",
    }:
        require_nonempty(
            record["actuator_identity"],
            "ACTUATOR_IDENTITY_MISSING",
        )

    if state in {
        "WORKLOAD_READY",
        "PRESTEP_ADMITTED",
        "TRIGGERED_EXACTLY_ONCE",
        "APPLIED_VERIFIED",
        "POSTSTEP_COMPLETE",
    }:
        require_nonempty(
            record["receiver_workload_identity"],
            "RECEIVER_WORKLOAD_IDENTITY_MISSING",
        )

    if state in {
        "PRESTEP_ADMITTED",
        "TRIGGERED_EXACTLY_ONCE",
        "APPLIED_VERIFIED",
        "POSTSTEP_COMPLETE",
    }:
        require(
            record["precontrol_admission_result"] == "PASS",
            "PRECONTROL_ADMISSION_NOT_PASS",
        )

    if state in {
        "APPLIED_VERIFIED",
        "POSTSTEP_COMPLETE",
    }:
        require_nonempty(
            record["applied_readback_identity"],
            "APPLIED_READBACK_IDENTITY_MISSING",
        )

    if state == "POSTSTEP_COMPLETE":
        require(
            record["poststep_completion_result"] == "PASS",
            "POSTSTEP_COMPLETION_NOT_PASS",
        )

    if state == "SCIENTIFICALLY_ADJUDICATED":
        require(
            record["scientific_adjudication_result"]
            in {
                "VALID",
                "INVALID",
            },
            "SCIENTIFIC_ADJUDICATION_MISSING",
        )

    if state in {
        "CLOSED",
        "DESTROYED",
    }:
        require_nonempty(
            record["closeout_checksum_identity"],
            "CLOSEOUT_CHECKSUM_IDENTITY_MISSING",
        )


def validate_new_record(current, previous):
    require(
        current["transaction_state"] == "NEW",
        "PREVIOUS_RECORD_REQUIRED_FOR_NON_NEW_STATE",
    )

    require(
        previous is None,
        "PREVIOUS_RECORD_FORBIDDEN_FOR_NEW_STATE",
    )

    require(
        current["previous_transaction_state"] is None,
        "NEW_PREVIOUS_STATE_MUST_BE_NULL",
    )

    validate_record_state_invariants(
        current
    )


def validate_identity_continuity(
    previous,
    current,
):
    for field in IMMUTABLE_FIELDS:
        require(
            previous[field] == current[field],
            f"IMMUTABLE_FIELD_CHANGED:{field}",
        )

    for field in WRITE_ONCE_FIELDS:
        previous_value = previous[field]
        current_value = current[field]

        if previous_value is not None:
            require(
                current_value == previous_value,
                f"WRITE_ONCE_FIELD_CHANGED:{field}",
            )


def validate_failure_continuity(
    previous,
    current,
):
    current_state = current[
        "transaction_state"
    ]

    entering_failure = (
        current_state in FAILURE_STATES
        and previous["transaction_state"]
        not in FAILURE_STATES
    )

    if entering_failure:
        require(
            previous["failure_class"] == "NONE",
            "FAILURE_ENTERED_FROM_ALREADY_FAILED_RECORD",
        )
        return

    require(
        current["failure_class"]
        == previous["failure_class"],
        "FAILURE_CLASS_CHANGED_OUTSIDE_FAILURE_ENTRY",
    )

    require(
        current["failure_reason"]
        == previous["failure_reason"],
        "FAILURE_REASON_CHANGED_OUTSIDE_FAILURE_ENTRY",
    )


def trigger_tuple(record):
    return tuple(
        record[field]
        for field in TRIGGER_FIELDS
    )


def validate_trigger_transition(
    previous,
    current,
):
    previous_state = previous[
        "transaction_state"
    ]
    current_state = current[
        "transaction_state"
    ]

    if (
        previous_state == "PRESTEP_ADMITTED"
        and current_state
        == "TRIGGERED_EXACTLY_ONCE"
    ):
        expected = (
            1,
            1,
            "YES",
            "NEVER_REPEAT",
        )

        require(
            trigger_tuple(current) == expected,
            "CONFIRMED_TRIGGER_TUPLE_INVALID",
        )
        return

    if (
        previous_state == "PRESTEP_ADMITTED"
        and current_state
        == "INVALID_POSTTRIGGER"
    ):
        expected = (
            1,
            0,
            "UNKNOWN",
            "NEVER_AUTOMATICALLY_REPLAY",
        )

        require(
            trigger_tuple(current) == expected,
            "AMBIGUOUS_TRIGGER_TUPLE_INVALID",
        )
        return

    require(
        trigger_tuple(current)
        == trigger_tuple(previous),
        "TRIGGER_TUPLE_CHANGED_OUTSIDE_TRIGGER_BOUNDARY",
    )


def validate_adjudication_transition(
    previous,
    current,
):
    if (
        current["transaction_state"]
        != "SCIENTIFICALLY_ADJUDICATED"
    ):
        return

    require(
        current["scientific_adjudication_result"]
        in {
            "VALID",
            "INVALID",
        },
        "SCIENTIFIC_ADJUDICATION_MISSING",
    )

    if (
        previous["transaction_state"]
        == "INVALID_POSTTRIGGER"
    ):
        require(
            current[
                "scientific_adjudication_result"
            ] == "INVALID",
            "INVALID_POSTTRIGGER_ADJUDICATED_AS_VALID",
        )


def validate_transition(
    previous,
    current,
):
    previous_state = previous[
        "transaction_state"
    ]
    current_state = current[
        "transaction_state"
    ]

    require(
        current["previous_transaction_state"]
        == previous_state,
        "PREVIOUS_TRANSACTION_STATE_MISMATCH",
    )

    require(
        current_state
        in LEGAL_TRANSITIONS[previous_state],
        (
            "ILLEGAL_STATE_TRANSITION:"
            f"{previous_state}->{current_state}"
        ),
    )

    require(
        current["transition_decision_utc_ns"]
        > previous["transition_decision_utc_ns"],
        "TRANSITION_DECISION_TIME_NOT_STRICTLY_INCREASING",
    )

    validate_identity_continuity(
        previous,
        current,
    )

    validate_failure_continuity(
        previous,
        current,
    )

    validate_trigger_transition(
        previous,
        current,
    )

    validate_record_state_invariants(
        current
    )

    validate_adjudication_transition(
        previous,
        current,
    )


def emit_failure(reason):
    print(
        "PROMPT12R_TRANSACTION_VALIDATOR_VERSION="
        + VALIDATOR_VERSION
    )
    print("VALIDATOR_GATE=FAIL_CLOSED")
    print(f"FAIL_CLOSED_REASON={reason}")
    print("DOCKER_EXECUTION=NO")
    print("WORKLOAD_EXECUTION=NO")
    print("SCIENTIFIC_TRIGGER_EXECUTION=NO")


def main():
    args = parse_args()

    try:
        schema = load_json(
            args.schema,
            "SCHEMA",
        )

        validator = validate_schema(
            schema
        )

        print(
            "PROMPT12R_TRANSACTION_VALIDATOR_VERSION="
            + VALIDATOR_VERSION
        )
        print("SCHEMA_SELF_CHECK_GATE=PASS")

        current = load_json(
            args.current,
            "CURRENT",
        )

        validate_record_schema(
            validator,
            current,
            "CURRENT",
        )

        print("CURRENT_SCHEMA_GATE=PASS")

        previous = None

        if args.previous is not None:
            previous = load_json(
                args.previous,
                "PREVIOUS",
            )

            validate_record_schema(
                validator,
                previous,
                "PREVIOUS",
            )

            print(
                "PREVIOUS_SCHEMA_GATE=PASS"
            )

            validate_record_state_invariants(
                previous
            )

            print(
                "PREVIOUS_SEMANTIC_GATE=PASS"
            )
        else:
            print(
                "PREVIOUS_SCHEMA_GATE="
                "NOT_APPLICABLE"
            )

        if previous is None:
            validate_new_record(
                current,
                previous,
            )
        else:
            require(
                current["transaction_state"]
                != "NEW",
                "NEW_STATE_CANNOT_HAVE_PREVIOUS_RECORD",
            )

            validate_transition(
                previous,
                current,
            )

        print(
            "TRANSACTION_ID="
            + current["transaction_id"]
        )
        print(
            "PREVIOUS_TRANSACTION_STATE="
            + (
                str(
                    current[
                        "previous_transaction_state"
                    ]
                )
                if current[
                    "previous_transaction_state"
                ] is not None
                else "NONE"
            )
        )
        print(
            "CURRENT_TRANSACTION_STATE="
            + current["transaction_state"]
        )
        print(
            "SCIENTIFIC_TRIGGER_CONSUMED="
            + current[
                "scientific_trigger_consumed"
            ]
        )
        print(
            "REPLAY_DECISION="
            + current["replay_decision"]
        )
        print("TRANSITION_LEGALITY_GATE=PASS")
        print("TRANSACTION_SEMANTIC_GATE=PASS")
        print("VALIDATOR_GATE=PASS")
        print("FAIL_CLOSED_REASON=NONE")
        print("DOCKER_EXECUTION=NO")
        print("WORKLOAD_EXECUTION=NO")
        print("SCIENTIFIC_TRIGGER_EXECUTION=NO")

        return 0

    except SemanticError as exc:
        emit_failure(
            str(exc)
        )
        return EX_DATAERR

    except Exception as exc:
        emit_failure(
            "UNEXPECTED_VALIDATOR_ERROR:"
            + type(exc).__name__
        )
        return EX_DATAERR


if __name__ == "__main__":
    sys.exit(main())
