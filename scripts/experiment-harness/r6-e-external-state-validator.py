#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator


EX_DATAERR = 65
VALIDATOR_VERSION = "1.0.0"

STALE_CLASSES = {
    "STALE_OR_HISTORICAL_REFERENCE_TARGET_ABSENT",
    "STALE_PRESERVED_RUNTIME_RESIDUE",
}

IDENTITY_REQUIRED_RETENTION_STATES = {
    "RETAINED",
    "RELEASED",
}


class SemanticError(Exception):
    pass


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Read-only Sci_O-RAN R6-E external-state reference validator. "
            "The validator performs no transfer, migration, deletion, "
            "lifecycle, provider, FIFO, traffic, PRB, or Prompt-12 action."
        )
    )
    parser.add_argument(
        "--schema",
        required=True,
        help="R6-E JSON Schema path",
    )
    parser.add_argument(
        "--record",
        required=True,
        help="External-state reference JSON record",
    )
    parser.add_argument(
        "--expected-host",
        help="Optional exact host binding to require",
    )
    return parser.parse_args()


def require(condition, reason):
    if not condition:
        raise SemanticError(reason)


def load_json(path_value, label):
    path = Path(path_value)

    if not path.is_file():
        raise SemanticError(f"{label}_FILE_MISSING")

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SemanticError(
            f"{label}_JSON_INVALID:{type(exc).__name__}"
        ) from exc


def build_validator(schema):
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as exc:
        raise SemanticError(
            "SCHEMA_SELF_CHECK_FAILED:"
            + type(exc).__name__
        ) from exc

    return Draft202012Validator(schema)


def validate_record_schema(validator, record):
    errors = sorted(
        validator.iter_errors(record),
        key=lambda error: (
            list(error.absolute_path),
            error.message,
        ),
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
        "SCHEMA_VALIDATION_FAILED:"
        + path
        + ":"
        + first.message
    )


def validate_semantics(record, expected_host):
    require(
        record["host"].strip() == record["host"]
        and bool(record["host"].strip()),
        "HOST_INVALID",
    )

    path = Path(record["absolute_path"])

    require(
        path.is_absolute(),
        "ABSOLUTE_PATH_REQUIRED",
    )

    if expected_host is not None:
        require(
            record["host"] == expected_host,
            "HOST_BINDING_MISMATCH",
        )

    historical_path = record.get(
        "original_historical_path"
    )

    if historical_path is not None:
        require(
            Path(historical_path).is_absolute(),
            "ORIGINAL_HISTORICAL_PATH_MUST_BE_ABSOLUTE",
        )

    manifest_path = record.get("manifest_path")
    manifest_sha = record.get("manifest_sha256")

    require(
        (manifest_path is None) == (manifest_sha is None),
        "MANIFEST_PATH_SHA256_PAIR_REQUIRED",
    )

    if manifest_path is not None:
        require(
            Path(manifest_path).is_absolute(),
            "MANIFEST_PATH_MUST_BE_ABSOLUTE",
        )

    if record["retention_state"] in IDENTITY_REQUIRED_RETENTION_STATES:
        require(
            bool(record.get("manifest_sha256"))
            or bool(record.get("object_sha256")),
            "DETERMINISTIC_IDENTITY_REQUIRED_FOR_RETAINED_OR_RELEASED_STATE",
        )

    liveness_state = record["liveness_state"]
    liveness_expectation = record["liveness_expectation"]
    evidence = record.get("liveness_evidence", {})

    strong_liveness = any(
        evidence.get(field) is True
        for field in (
            "live_process_confirmed",
            "open_file_or_fifo_confirmed",
            "current_control_plane_evidence",
        )
    )

    if liveness_state == "LIVE":
        require(
            strong_liveness,
            "LIVE_STATE_REQUIRES_CURRENT_STRONG_LIVENESS_EVIDENCE",
        )

    if (
        liveness_expectation == "REQUIRED"
        and liveness_state == "NOT_APPLICABLE"
    ):
        raise SemanticError(
            "REQUIRED_LIVENESS_CANNOT_BE_NOT_APPLICABLE"
        )

    if record["artifact_class"] in STALE_CLASSES:
        require(
            liveness_state != "LIVE",
            "STALE_CLASS_CANNOT_BE_LIVE",
        )

    if (
        record["artifact_class"]
        == "STALE_OR_HISTORICAL_REFERENCE_TARGET_ABSENT"
    ):
        require(
            record["existence_expectation"]
            in {"ABSENT", "HISTORICAL_ONLY"},
            "ABSENT_REFERENCE_CLASS_REQUIRES_ABSENT_OR_HISTORICAL_EXPECTATION",
        )

    if (
        evidence.get("path_present") is True
        or evidence.get("admission_metadata_present") is True
    ) and not strong_liveness:
        require(
            liveness_state != "LIVE",
            "PATH_OR_ADMISSION_METADATA_ALONE_DOES_NOT_PROVE_LIVENESS",
        )


def main():
    args = parse_args()

    try:
        schema = load_json(args.schema, "SCHEMA")
        record = load_json(args.record, "RECORD")

        validator = build_validator(schema)
        validate_record_schema(validator, record)
        validate_semantics(record, args.expected_host)

    except SemanticError as exc:
        print("R6_E_EXTERNAL_STATE_VALIDATION=FAIL")
        print(f"REASON={exc}")
        return EX_DATAERR

    print("R6_E_EXTERNAL_STATE_VALIDATION=PASS")
    print(f"VALIDATOR_VERSION={VALIDATOR_VERSION}")
    print(f"RECORD_ID={record['record_id']}")
    print(f"HOST={record['host']}")
    print(f"ABSOLUTE_PATH={record['absolute_path']}")
    print(f"ARTIFACT_CLASS={record['artifact_class']}")
    print(f"LIVENESS_STATE={record['liveness_state']}")
    print("EXTERNAL_STATE_MUTATION_PERFORMED=NO")
    print("SCIENTIFIC_OPERATION_PERFORMED=NO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
