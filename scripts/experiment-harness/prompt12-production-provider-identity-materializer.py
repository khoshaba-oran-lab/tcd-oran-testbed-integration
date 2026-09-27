#!/usr/bin/env python3

"""Materialise the Prompt 12 V2 logical provider identity.

The identity is a deterministic pre-start logical binding.  It is derived
only from experiment_id and run_id and is intentionally independent of PID,
process start identity, host runtime state, wall-clock time, and randomness.
"""

import argparse
import hashlib
import json
import sys


SCHEMA = (
    "sci_oran_prompt12_v2_production_"
    "provider_identity_materializer_v1"
)
PREFIX = "prompt12-provider-"


class ContractError(Exception):
    pass


def require_nonempty(value, name):
    if not isinstance(value, str):
        raise ContractError(f"{name}_NOT_STRING")

    if value.strip() == "":
        raise ContractError(f"{name}_EMPTY")

    return value


def deterministic_provider_identity(
    experiment_id,
    run_id,
):
    experiment_id = require_nonempty(
        experiment_id,
        "EXPERIMENT_ID",
    )
    run_id = require_nonempty(
        run_id,
        "RUN_ID",
    )

    payload = (
        experiment_id.encode("utf-8")
        + b"\x00"
        + run_id.encode("utf-8")
    )

    digest = hashlib.sha256(payload).hexdigest()

    return PREFIX + digest[:32]


def materialize_provider_identity(
    experiment_id,
    run_id,
):
    provider_identity = deterministic_provider_identity(
        experiment_id,
        run_id,
    )

    return {
        "schema": SCHEMA,
        "provider_identity": provider_identity,
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--experiment-id",
        required=True,
    )
    parser.add_argument(
        "--run-id",
        required=True,
    )

    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    try:
        result = materialize_provider_identity(
            args.experiment_id,
            args.run_id,
        )
    except ContractError as exc:
        print(
            f"ERROR={exc}",
            file=sys.stderr,
        )
        return 2

    print(
        json.dumps(
            result,
            sort_keys=True,
            separators=(",", ":"),
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
