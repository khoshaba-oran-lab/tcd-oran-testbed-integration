#!/usr/bin/env python3

import argparse
import hashlib
import json
import os
import pathlib
import sys


SCHEMA = "sci_oran_prompt12_v2_production_runtime_root_materializer_v1"
PREFIX = "prompt12-runtime-"


class ContractError(Exception):
    pass


def require_nonempty(value, name):
    if not isinstance(value, str):
        raise ContractError(f"{name}_NOT_STRING")
    if value.strip() == "":
        raise ContractError(f"{name}_EMPTY")
    return value


def validate_tracked_runtime_parent(value):
    raw = require_nonempty(value, "TRACKED_RUNTIME_PARENT")
    parent = pathlib.Path(raw)

    if not parent.is_absolute():
        raise ContractError("TRACKED_RUNTIME_PARENT_NOT_ABSOLUTE")

    try:
        resolved = parent.resolve(strict=True)
    except OSError:
        raise ContractError("TRACKED_RUNTIME_PARENT_UNAVAILABLE")

    if resolved != parent:
        raise ContractError("TRACKED_RUNTIME_PARENT_NOT_CANONICAL")

    if not parent.is_dir():
        raise ContractError("TRACKED_RUNTIME_PARENT_NOT_DIRECTORY")

    return parent


def deterministic_leaf(experiment_id, run_id):
    experiment_id = require_nonempty(experiment_id, "EXPERIMENT_ID")
    run_id = require_nonempty(run_id, "RUN_ID")

    payload = (
        experiment_id.encode("utf-8")
        + b"\x00"
        + run_id.encode("utf-8")
    )
    digest = hashlib.sha256(payload).hexdigest()
    return PREFIX + digest[:32]


def materialize_runtime_root(
    experiment_id,
    run_id,
    tracked_runtime_parent,
):
    parent = validate_tracked_runtime_parent(
        tracked_runtime_parent
    )

    leaf = deterministic_leaf(
        experiment_id,
        run_id,
    )

    runtime_root = parent / leaf

    if not runtime_root.is_absolute():
        raise ContractError("RUNTIME_ROOT_NOT_ABSOLUTE")

    if runtime_root.parent != parent:
        raise ContractError("RUNTIME_ROOT_ESCAPES_TRACKED_PARENT")

    if os.path.lexists(str(runtime_root)):
        raise ContractError("RUNTIME_ROOT_ALREADY_EXISTS")

    return str(runtime_root)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--experiment-id",
        required=True,
    )
    parser.add_argument(
        "--run-id",
        required=True,
    )
    parser.add_argument(
        "--tracked-runtime-parent",
        required=True,
    )
    return parser.parse_args()


def main():
    args = parse_args()

    try:
        runtime_root = materialize_runtime_root(
            args.experiment_id,
            args.run_id,
            args.tracked_runtime_parent,
        )
    except ContractError as exc:
        print(
            f"ERROR={exc}",
            file=sys.stderr,
        )
        return 2

    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "runtime_root": runtime_root,
            },
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
