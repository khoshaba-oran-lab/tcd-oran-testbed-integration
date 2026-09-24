#!/usr/bin/env python3
"""Prompt 12 production local FIFO actuator reader.

This reader implements the frozen production V2 boundary:

* it runs locally on tb3-dell;
* it consumes an already-created FIFO;
* it accepts only the exact ``TRIGGER\n`` token;
* the PRB ratio is pre-bound through SCI_ORAN_MAX_PRB_RATIO;
* one accepted trigger causes exactly one actuator process execution;
* actuator stdout/stderr are inherited unchanged;
* shell execution, automatic retry and automatic replay are prohibited.

The reader does not create the FIFO, does not select/change the PRB ratio,
does not emit U_CMD/U_ACK/PRB_ACTUATOR_APPLIED evidence and does not contain
Docker, SSH or Ansible lifecycle logic.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
import sys
from typing import NoReturn, Sequence


RATIO_ENV_KEY = "SCI_ORAN_MAX_PRB_RATIO"
ALLOWED_RATIOS = frozenset({"25", "50", "75", "100"})
TRIGGER_TOKEN = "TRIGGER\n"


class ReaderContractError(RuntimeError):
    """Fail-closed production reader contract violation."""


def fail(message: str, exit_code: int = 2) -> NoReturn:
    print(
        f"PROMPT12_V2_READER_FAIL_CLOSED={message}",
        file=sys.stderr,
        flush=True,
    )
    raise SystemExit(exit_code)


def parse_actuator_argv(raw: str) -> list[str]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ReaderContractError(
            f"actuator argv JSON is invalid: {exc}"
        ) from exc

    if not isinstance(value, list) or not value:
        raise ReaderContractError(
            "actuator argv must be a non-empty JSON array"
        )

    if not all(isinstance(item, str) and item for item in value):
        raise ReaderContractError(
            "every actuator argv element must be a non-empty string"
        )

    return list(value)


def validate_prebound_ratio(env: dict[str, str]) -> str:
    ratio = env.get(RATIO_ENV_KEY)

    if ratio is None or ratio == "":
        raise ReaderContractError(
            f"{RATIO_ENV_KEY} must be pre-bound before reader start"
        )

    if ratio not in ALLOWED_RATIOS:
        allowed = ",".join(sorted(ALLOWED_RATIOS, key=int))
        raise ReaderContractError(
            f"invalid {RATIO_ENV_KEY}={ratio!r}; allowed={allowed}"
        )

    return ratio


def validate_existing_fifo(path: str) -> None:
    try:
        info = os.stat(path)
    except OSError as exc:
        raise ReaderContractError(
            f"FIFO path is unavailable: {path}: {exc}"
        ) from exc

    if not stat.S_ISFIFO(info.st_mode):
        raise ReaderContractError(
            f"path is not a FIFO: {path}"
        )


def execute_actuator_once(
    actuator_argv: Sequence[str],
    actuator_env: dict[str, str],
) -> None:
    """Execute exactly one actuator process for one accepted trigger."""

    try:
        completed = subprocess.run(
            list(actuator_argv),
            env=actuator_env,
            shell=False,
            check=False,
        )
    except OSError as exc:
        raise ReaderContractError(
            f"actuator execution could not be started: {exc}"
        ) from exc

    if completed.returncode != 0:
        raise ReaderContractError(
            "actuator execution failed with "
            f"returncode={completed.returncode}; replay prohibited"
        )


def run_reader(
    fifo_path: str,
    actuator_argv: Sequence[str],
) -> int:
    # Freeze the actuator environment before any scientific trigger.
    actuator_env = os.environ.copy()
    ratio = validate_prebound_ratio(actuator_env)

    validate_existing_fifo(fifo_path)

    print(
        "PROMPT12_V2_READER_PREARMED=YES "
        f"ratio_pct={ratio}",
        flush=True,
    )

    # FIFO is deliberately opened, not created. The provider owns FIFO
    # creation/lifecycle and uses writer-side open as the readiness proof.
    try:
        fifo_fd = os.open(fifo_path, os.O_RDONLY)
    except OSError as exc:
        raise ReaderContractError(
            f"cannot open FIFO for reading: {fifo_path}: {exc}"
        ) from exc

    with os.fdopen(
        fifo_fd,
        mode="r",
        encoding="utf-8",
        errors="strict",
        newline="",
    ) as fifo:
        while True:
            token = fifo.readline()

            if token == "":
                raise ReaderContractError(
                    "FIFO reached EOF; automatic reader restart prohibited"
                )

            if token != TRIGGER_TOKEN:
                # Invalid tokens fail closed with respect to actuation:
                # they never cause an actuator process to be started.
                print(
                    "PROMPT12_V2_READER_TOKEN_REJECTED="
                    + json.dumps(token),
                    file=sys.stderr,
                    flush=True,
                )
                continue

            print(
                "PROMPT12_V2_READER_TRIGGER_ACCEPTED=YES",
                flush=True,
            )

            # Exactly one call site and exactly one actuator execution for
            # this accepted trigger. There is intentionally no retry loop.
            execute_actuator_once(
                actuator_argv=actuator_argv,
                actuator_env=actuator_env,
            )

            print(
                "PROMPT12_V2_READER_ACTUATOR_EXECUTION_COMPLETED=YES",
                flush=True,
            )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Prompt 12 production persistent FIFO reader. "
            "The FIFO must already exist and SCI_ORAN_MAX_PRB_RATIO "
            "must already be bound."
        )
    )
    parser.add_argument(
        "--fifo-path",
        required=True,
        help="Existing provider-owned FIFO path.",
    )
    parser.add_argument(
        "--actuator-argv-json",
        required=True,
        help=(
            "Exact actuator argv encoded as a JSON array. "
            "Execution always uses shell=False."
        ),
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    try:
        actuator_argv = parse_actuator_argv(args.actuator_argv_json)
        return run_reader(
            fifo_path=args.fifo_path,
            actuator_argv=actuator_argv,
        )
    except ReaderContractError as exc:
        fail(str(exc))

    raise AssertionError("unreachable")


if __name__ == "__main__":
    sys.exit(main())
