#!/usr/bin/env python3

import argparse
import json
import os
import pathlib
import sys


SCHEMA = "sci_oran_prompt12_v2_production_fifo_path_materializer_v1"
FIFO_NAME = "actuator.fifo"


class MaterializerError(ValueError):
    pass


def require_nonempty(value, name):
    if value is None:
        raise MaterializerError(f"{name}_MISSING")

    value = str(value)

    if not value.strip():
        raise MaterializerError(f"{name}_EMPTY")

    return value


def validate_runtime_root(value):
    raw = require_nonempty(
        value,
        "RUNTIME_ROOT",
    )

    runtime_root = pathlib.Path(raw)

    if not runtime_root.is_absolute():
        raise MaterializerError(
            "RUNTIME_ROOT_NOT_ABSOLUTE"
        )

    if runtime_root.parent == runtime_root:
        raise MaterializerError(
            "RUNTIME_ROOT_INVALID_STRUCTURE"
        )

    if (
        runtime_root.name in ("", ".", "..")
        or ".." in runtime_root.parts
    ):
        raise MaterializerError(
            "RUNTIME_ROOT_INVALID_STRUCTURE"
        )

    return runtime_root


def materialize_fifo_path(runtime_root):
    runtime_root = validate_runtime_root(
        runtime_root
    )

    fifo_path = runtime_root / FIFO_NAME

    if not fifo_path.is_absolute():
        raise MaterializerError(
            "FIFO_PATH_NOT_ABSOLUTE"
        )

    if fifo_path.parent != runtime_root:
        raise MaterializerError(
            "FIFO_PATH_NOT_DIRECT_CHILD"
        )

    if fifo_path.name != FIFO_NAME:
        raise MaterializerError(
            "FIFO_PATH_NOT_CANONICAL"
        )

    if os.path.lexists(str(fifo_path)):
        raise MaterializerError(
            "FIFO_PATH_ALREADY_EXISTS"
        )

    return str(fifo_path)


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Materialize the canonical Prompt 12 "
            "production FIFO path without creating it."
        )
    )

    parser.add_argument(
        "--runtime-root",
        required=True,
    )

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        fifo_path = materialize_fifo_path(
            args.runtime_root
        )
    except MaterializerError as exc:
        print(
            f"ERROR={exc}",
            file=sys.stderr,
        )
        return 2

    print(
        json.dumps(
            {
                "fifo_path": fifo_path,
            },
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
