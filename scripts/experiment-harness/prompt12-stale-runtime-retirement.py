#!/usr/bin/env python3
"""Fail-closed retirement of a stale Prompt-12 runtime root."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import stat
import sys


SCHEMA = "sci_oran_prompt12_v2_stale_runtime_retirement_v1"
ADMISSION_SCHEMA = (
    "sci_oran_prompt12_persistent_prearmed_"
    "actuator_provider_admission_v1"
)

STRONG_IDENTITY_RE = re.compile(
    r"^([^:]+):([0-9]+):([0-9]+)$"
)


class RetirementError(Exception):
    """Fail-closed retirement contract violation."""


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)

    return digest.hexdigest()


def canonical_existing_directory(
    value: str,
    label: str,
) -> pathlib.Path:
    if not isinstance(value, str) or not value:
        raise RetirementError(f"{label}_INVALID")

    path = pathlib.Path(value)

    if not path.is_absolute():
        raise RetirementError(f"{label}_NOT_ABSOLUTE")

    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise RetirementError(
            f"{label}_UNAVAILABLE:{exc.errno}"
        ) from exc

    if resolved != path:
        raise RetirementError(
            f"{label}_NOT_CANONICAL"
        )

    if not path.is_dir():
        raise RetirementError(
            f"{label}_NOT_DIRECTORY"
        )

    return path


def validate_retirement_root(
    value: str,
    runtime_root: pathlib.Path,
) -> pathlib.Path:
    if not isinstance(value, str) or not value:
        raise RetirementError(
            "RETIREMENT_ROOT_INVALID"
        )

    path = pathlib.Path(value)

    if not path.is_absolute():
        raise RetirementError(
            "RETIREMENT_ROOT_NOT_ABSOLUTE"
        )

    if path.exists() or path.is_symlink():
        raise RetirementError(
            "RETIREMENT_ROOT_ALREADY_EXISTS"
        )

    parent = path.parent

    try:
        resolved_parent = parent.resolve(strict=True)
    except OSError as exc:
        raise RetirementError(
            "RETIREMENT_PARENT_UNAVAILABLE:"
            + str(exc.errno)
        ) from exc

    if resolved_parent != parent:
        raise RetirementError(
            "RETIREMENT_PARENT_NOT_CANONICAL"
        )

    if parent != runtime_root.parent:
        raise RetirementError(
            "RETIREMENT_ROOT_NOT_SIBLING"
        )

    if path == runtime_root:
        raise RetirementError(
            "RETIREMENT_ROOT_EQUALS_RUNTIME_ROOT"
        )

    return path


def load_admission(
    runtime_root: pathlib.Path,
) -> tuple[dict, pathlib.Path]:
    path = runtime_root / "provider-admission.json"

    try:
        if path.resolve(strict=True) != path:
            raise RetirementError(
                "PROVIDER_ADMISSION_NOT_CANONICAL"
            )

        if not path.is_file():
            raise RetirementError(
                "PROVIDER_ADMISSION_NOT_REGULAR_FILE"
            )

        data = json.loads(
            path.read_text(encoding="utf-8")
        )

    except RetirementError:
        raise
    except (OSError, json.JSONDecodeError) as exc:
        raise RetirementError(
            "PROVIDER_ADMISSION_UNAVAILABLE_OR_INVALID"
        ) from exc

    if data.get("schema") != ADMISSION_SCHEMA:
        raise RetirementError(
            "PROVIDER_ADMISSION_SCHEMA_INVALID"
        )

    if data.get("state") != "ADMITTED":
        raise RetirementError(
            "PROVIDER_ADMISSION_STATE_INVALID"
        )

    if data.get("runtime_root") != str(runtime_root):
        raise RetirementError(
            "PROVIDER_ADMISSION_RUNTIME_ROOT_MISMATCH"
        )

    expected_fifo = runtime_root / "actuator.fifo"

    if data.get("fifo_path") != str(expected_fifo):
        raise RetirementError(
            "PROVIDER_ADMISSION_FIFO_PATH_MISMATCH"
        )

    pid = data.get("provider_pid")

    if (
        not isinstance(pid, int)
        or isinstance(pid, bool)
        or pid <= 1
    ):
        raise RetirementError(
            "PROVIDER_PID_INVALID"
        )

    identity = data.get(
        "provider_process_start_identity"
    )

    if not isinstance(identity, str):
        raise RetirementError(
            "PROVIDER_PROCESS_START_IDENTITY_INVALID"
        )

    match = STRONG_IDENTITY_RE.fullmatch(identity)

    if match is None:
        raise RetirementError(
            "PROVIDER_PROCESS_START_IDENTITY_INVALID"
        )

    if int(match.group(2)) != pid:
        raise RetirementError(
            "PROVIDER_PROCESS_IDENTITY_PID_MISMATCH"
        )

    provider_identity = data.get(
        "provider_identity"
    )

    if (
        not isinstance(provider_identity, str)
        or not provider_identity
    ):
        raise RetirementError(
            "PROVIDER_IDENTITY_INVALID"
        )

    try:
        fifo_stat = expected_fifo.stat()
    except OSError as exc:
        raise RetirementError(
            "ACTUATOR_FIFO_UNAVAILABLE:"
            + str(exc.errno)
        ) from exc

    if not stat.S_ISFIFO(fifo_stat.st_mode):
        raise RetirementError(
            "ACTUATOR_FIFO_NOT_FIFO"
        )

    return data, path


def read_cmdline(
    proc: pathlib.Path,
) -> list[str]:
    try:
        return [
            item.decode(
                "utf-8",
                errors="replace",
            )
            for item in
            (proc / "cmdline").read_bytes().split(b"\0")
            if item
        ]
    except (OSError, PermissionError):
        return []


def assert_recorded_pid_absent(
    pid: int,
) -> None:
    if pathlib.Path(f"/proc/{pid}").exists():
        raise RetirementError(
            "RECORDED_PROVIDER_PID_STILL_EXISTS"
        )


def find_live_runtime_references(
    runtime_root: pathlib.Path,
    fifo_path: pathlib.Path,
) -> list[dict]:
    runtime_token = str(runtime_root)
    fifo_token = str(fifo_path)
    own_pid = os.getpid()

    matches = []

    for proc in pathlib.Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue

        pid = int(proc.name)

        if pid == own_pid:
            continue

        argv = read_cmdline(proc)

        if not argv:
            continue

        if (
            runtime_token in argv
            or fifo_token in argv
        ):
            matches.append(
                {
                    "pid": pid,
                    "argv": argv,
                }
            )

    return matches


def fsync_directory(
    path: pathlib.Path,
) -> None:
    flags = os.O_RDONLY

    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY

    fd = os.open(str(path), flags)

    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def retire(
    runtime_root_raw: str,
    retirement_root_raw: str,
) -> dict:
    runtime_root = canonical_existing_directory(
        runtime_root_raw,
        "RUNTIME_ROOT",
    )

    retirement_root = validate_retirement_root(
        retirement_root_raw,
        runtime_root,
    )

    admission, admission_path = load_admission(
        runtime_root
    )

    provider_pid = admission["provider_pid"]
    fifo_path = runtime_root / "actuator.fifo"

    assert_recorded_pid_absent(
        provider_pid
    )

    references = find_live_runtime_references(
        runtime_root,
        fifo_path,
    )

    if references:
        raise RetirementError(
            "LIVE_RUNTIME_REFERENCE_PRESENT:"
            + ",".join(
                str(item["pid"])
                for item in references
            )
        )

    admission_sha_before = sha256_file(
        admission_path
    )

    destination = (
        retirement_root
        / runtime_root.name
    )

    try:
        retirement_root.mkdir(
            mode=0o700,
            parents=False,
            exist_ok=False,
        )
    except FileExistsError as exc:
        raise RetirementError(
            "RETIREMENT_ROOT_ALREADY_EXISTS"
        ) from exc
    except OSError as exc:
        raise RetirementError(
            "RETIREMENT_ROOT_CREATION_FAILED:"
            + str(exc.errno)
        ) from exc

    try:
        os.rename(
            str(runtime_root),
            str(destination),
        )
    except OSError as exc:
        raise RetirementError(
            "ATOMIC_RUNTIME_ROOT_RENAME_FAILED:"
            + str(exc.errno)
        ) from exc

    fsync_directory(
        retirement_root
    )
    fsync_directory(
        retirement_root.parent
    )

    if runtime_root.exists():
        raise RetirementError(
            "SOURCE_RUNTIME_ROOT_STILL_PRESENT"
        )

    if not destination.is_dir():
        raise RetirementError(
            "RETIRED_RUNTIME_ROOT_MISSING"
        )

    retired_admission = (
        destination
        / "provider-admission.json"
    )

    if not retired_admission.is_file():
        raise RetirementError(
            "RETIRED_ADMISSION_MISSING"
        )

    admission_sha_after = sha256_file(
        retired_admission
    )

    if admission_sha_after != admission_sha_before:
        raise RetirementError(
            "RETIRED_ADMISSION_SHA_MISMATCH"
        )

    retired_fifo = (
        destination
        / "actuator.fifo"
    )

    try:
        retired_fifo_stat = retired_fifo.stat()
    except OSError as exc:
        raise RetirementError(
            "RETIRED_FIFO_MISSING:"
            + str(exc.errno)
        ) from exc

    if not stat.S_ISFIFO(
        retired_fifo_stat.st_mode
    ):
        raise RetirementError(
            "RETIRED_FIFO_NOT_FIFO"
        )

    return {
        "schema": SCHEMA,
        "source_runtime_root": str(
            runtime_root
        ),
        "retirement_root": str(
            retirement_root
        ),
        "retired_runtime_root": str(
            destination
        ),
        "provider_pid": provider_pid,
        "recorded_provider_pid_absent": True,
        "live_runtime_reference_count": 0,
        "admission_sha256_before":
            admission_sha_before,
        "admission_sha256_after":
            admission_sha_after,
        "fifo_preserved": True,
        "evidence_preserved": True,
        "source_path_released": True,
        "retirement_method":
            "ATOMIC_RENAME_WITH_EXCLUSIVE_CONTAINER",
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--runtime-root",
        required=True,
    )

    parser.add_argument(
        "--retirement-root",
        required=True,
    )

    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    try:
        result = retire(
            args.runtime_root,
            args.retirement_root,
        )
    except RetirementError as exc:
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
