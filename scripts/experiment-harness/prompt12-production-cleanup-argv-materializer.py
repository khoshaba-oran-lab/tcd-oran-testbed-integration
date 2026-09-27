#!/usr/bin/env python3

"""Materialise Prompt 12 production cleanup argv."""

import argparse
import json
import pathlib
import sys


SCHEMA = (
    "sci_oran_prompt12_v2_production_"
    "cleanup_argv_materializer_v1"
)


class ContractError(Exception):
    pass


def validate_runtime_root(raw):
    if not isinstance(raw, str) or raw.strip() == "":
        raise ContractError("RUNTIME_ROOT_EMPTY")

    path = pathlib.PurePosixPath(raw)

    if not path.is_absolute():
        raise ContractError(
            "RUNTIME_ROOT_NOT_ABSOLUTE"
        )

    if ".." in path.parts or "." in path.parts:
        raise ContractError(
            "RUNTIME_ROOT_NOT_CANONICAL"
        )

    if str(path) == "/":
        raise ContractError(
            "RUNTIME_ROOT_IS_FILESYSTEM_ROOT"
        )

    return str(path)


def materialize_cleanup_argv(runtime_root):
    runtime_root = validate_runtime_root(
        runtime_root
    )

    cleanup = (
        pathlib.Path(__file__)
        .resolve()
        .parent
        / "prompt12-production-cleanup.py"
    )

    if not cleanup.is_file():
        raise ContractError(
            "CLEANUP_EXECUTABLE_MISSING"
        )

    if not cleanup.stat().st_mode & 0o111:
        raise ContractError(
            "CLEANUP_EXECUTABLE_NOT_EXECUTABLE"
        )

    return {
        "schema": SCHEMA,
        "cleanup_argv": [
            str(cleanup),
            "--runtime-root",
            runtime_root,
        ],
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--runtime-root",
        required=True,
    )

    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    try:
        result = materialize_cleanup_argv(
            args.runtime_root
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
