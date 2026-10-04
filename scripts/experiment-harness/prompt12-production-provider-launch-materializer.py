#!/usr/bin/env python3
"""Prompt 12 V2 production provider launch argv materializer.

This component only validates explicit inputs and constructs the production
reader argv.  It does not execute the reader, actuator, Docker, traffic, or
any scientific control operation.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Sequence


CONTRACT_SCHEMA = (
    "sci_oran_prompt12_v2_production_provider_launch_materializer_contract_v1"
)

SCRIPT_DIR = Path(__file__).resolve().parent

READER_PATH = SCRIPT_DIR / "prompt12-production-local-fifo-reader.py"
WRAPPER_PATH = SCRIPT_DIR / "prompt12-production-actuator-wrapper.py"
FIFO_TOKEN = "@PROMPT12_ACTUATOR_FIFO@"


class ContractError(ValueError):
    """Raised when the materializer contract is not satisfied."""


def _require_nonempty(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{name} missing or empty")
    return value


def _require_absolute_path(value: str, name: str) -> str:
    value = _require_nonempty(value, name)
    if not os.path.isabs(value):
        raise ContractError(f"{name} must be absolute")
    return value


def _require_executable(path: Path, name: str) -> Path:
    if not path.is_file():
        raise ContractError(f"{name} executable missing: {path}")
    if not os.access(path, os.X_OK):
        raise ContractError(f"{name} executable not executable: {path}")
    return path


def validate_ratio_binding_paths(value: object) -> list[str]:
    if not isinstance(value, list):
        raise ContractError("ratio_binding_paths must be a JSON list")

    if len(value) != 6:
        raise ContractError("ratio_binding_paths cardinality must equal six")

    validated: list[str] = []

    for index, path in enumerate(value):
        if not isinstance(path, str) or not path.strip():
            raise ContractError(
                f"ratio_binding_paths[{index}] missing or empty"
            )

        if not os.path.isabs(path):
            raise ContractError(
                f"ratio_binding_paths[{index}] must be absolute"
            )

        validated.append(path)

    return validated


def build_provider_launch_argv(
    *,
    experiment_id: str,
    run_id: str,
    fifo_path: str,
    ratio_binding_paths: object,
    initial_transition_index: int,
) -> list[str]:
    experiment_id = _require_nonempty(experiment_id, "experiment_id")
    run_id = _require_nonempty(run_id, "run_id")
    fifo_path = _require_absolute_path(fifo_path, "fifo_path")
    paths = validate_ratio_binding_paths(ratio_binding_paths)

    if (
        isinstance(initial_transition_index, bool)
        or not isinstance(initial_transition_index, int)
        or not 1 <= initial_transition_index <= 6
    ):
        raise ContractError(
            "INITIAL_TRANSITION_INDEX_INVALID"
        )

    reader = _require_executable(READER_PATH, "reader")
    wrapper = _require_executable(WRAPPER_PATH, "wrapper")

    actuator_argv_json = json.dumps(
        [str(wrapper)],
        separators=(",", ":"),
    )

    ratio_binding_paths_json = json.dumps(
        paths,
        separators=(",", ":"),
    )

    return [
        str(reader),
        "--fifo-path",
        FIFO_TOKEN,
        "--actuator-argv-json",
        actuator_argv_json,
        "--experiment-id",
        experiment_id,
        "--run-id",
        run_id,
        "--initial-transition-index",
        str(initial_transition_index),
        "--ratio-binding-paths-json",
        ratio_binding_paths_json,
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Construct the Prompt 12 V2 production provider launch argv. "
            "No command is executed."
        )
    )

    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--fifo-path", required=True)
    parser.add_argument("--ratio-binding-paths-json", required=True)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    parser.add_argument(
        "--initial-transition-index",
        required=True,
        type=int,
        choices=range(1, 7),
    )

    args = parser.parse_args(argv)

    try:
        ratio_binding_paths = json.loads(args.ratio_binding_paths_json)

        provider_launch_argv = build_provider_launch_argv(
            experiment_id=args.experiment_id,
            run_id=args.run_id,
            fifo_path=args.fifo_path,
            ratio_binding_paths=ratio_binding_paths,
            initial_transition_index=args.initial_transition_index,
        )
    except (ContractError, json.JSONDecodeError) as exc:
        print(f"ERROR={exc}", file=sys.stderr)
        return 2

    print(
        json.dumps(
            provider_launch_argv,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
