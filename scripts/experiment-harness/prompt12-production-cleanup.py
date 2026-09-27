#!/usr/bin/env python3

"""Evidence-preserving Prompt 12 production process cleanup."""

import argparse
import json
import os
import pathlib
import signal
import sys
import time


SCHEMA = "sci_oran_prompt12_v2_production_cleanup_v1"
ADMISSION_SCHEMA = (
    "sci_oran_prompt12_persistent_prearmed_"
    "actuator_provider_admission_v1"
)

TERM_TIMEOUT_MS = 5000
POLL_MS = 50


class CleanupError(Exception):
    pass


def canonical_existing_directory(raw):
    if not isinstance(raw, str) or raw.strip() == "":
        raise CleanupError("RUNTIME_ROOT_EMPTY")

    path = pathlib.Path(raw)

    if not path.is_absolute():
        raise CleanupError("RUNTIME_ROOT_NOT_ABSOLUTE")

    try:
        resolved = path.resolve(strict=True)
    except OSError:
        raise CleanupError("RUNTIME_ROOT_UNAVAILABLE")

    if resolved != path:
        raise CleanupError("RUNTIME_ROOT_NOT_CANONICAL")

    if not path.is_dir():
        raise CleanupError("RUNTIME_ROOT_NOT_DIRECTORY")

    return path


def read_process_snapshot(pid):
    try:
        boot_id = pathlib.Path(
            "/proc/sys/kernel/random/boot_id"
        ).read_text(encoding="utf-8").strip()

        stat_text = pathlib.Path(
            f"/proc/{pid}/stat"
        ).read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise CleanupError(
            "PROCESS_IDENTITY_READ_FAILED:"
            + str(exc.errno)
        )

    right = stat_text.rfind(")")

    if right < 0:
        raise CleanupError("PROCESS_STAT_INVALID")

    fields = stat_text[right + 2:].split()

    # fields[0] is proc stat field 3 (state);
    # fields[19] is proc stat field 22 (starttime).
    if len(fields) <= 19:
        raise CleanupError("PROCESS_STAT_TOO_SHORT")

    state = fields[0]
    start_ticks = fields[19]

    return {
        "identity": f"{boot_id}:{pid}:{start_ticks}",
        "state": state,
    }


def process_start_identity(pid):
    snapshot = read_process_snapshot(pid)

    if snapshot is None:
        return None

    return snapshot["identity"]


def load_admission(runtime_root):
    path = runtime_root / "provider-admission.json"

    try:
        if path.resolve(strict=True) != path:
            raise CleanupError(
                "PROVIDER_ADMISSION_NOT_CANONICAL"
            )

        data = json.loads(
            path.read_text(encoding="utf-8")
        )
    except CleanupError:
        raise
    except (OSError, json.JSONDecodeError):
        raise CleanupError(
            "PROVIDER_ADMISSION_UNAVAILABLE_OR_INVALID"
        )

    if data.get("schema") != ADMISSION_SCHEMA:
        raise CleanupError(
            "PROVIDER_ADMISSION_SCHEMA_INVALID"
        )

    pid = data.get("provider_pid")
    identity = data.get(
        "provider_process_start_identity"
    )

    if (
        not isinstance(pid, int)
        or isinstance(pid, bool)
        or pid <= 1
    ):
        raise CleanupError("PROVIDER_PID_INVALID")

    if (
        not isinstance(identity, str)
        or identity.strip() == ""
    ):
        raise CleanupError(
            "PROVIDER_PROCESS_START_IDENTITY_INVALID"
        )

    return pid, identity


def assert_exact_process(pid, expected_identity):
    snapshot = read_process_snapshot(pid)

    if snapshot is None:
        raise CleanupError(
            "TARGET_PROCESS_NOT_RUNNING"
        )

    if snapshot["identity"] != expected_identity:
        raise CleanupError(
            "TARGET_PROCESS_IDENTITY_MISMATCH"
        )

    if snapshot["state"] == "Z":
        raise CleanupError(
            "TARGET_PROCESS_ALREADY_TERMINATED"
        )

    try:
        pgid = os.getpgid(pid)
    except ProcessLookupError:
        raise CleanupError(
            "TARGET_PROCESS_NOT_RUNNING"
        )
    except OSError as exc:
        raise CleanupError(
            "TARGET_PGID_READ_FAILED:"
            + str(exc.errno)
        )

    if pgid != pid:
        raise CleanupError(
            "TARGET_PROCESS_GROUP_NOT_EXACT"
        )


def wait_until_gone(pid, expected_identity, timeout_ms):
    deadline = time.monotonic() + timeout_ms / 1000.0

    while time.monotonic() < deadline:
        snapshot = read_process_snapshot(pid)

        if snapshot is None:
            return True

        if snapshot["identity"] != expected_identity:
            raise CleanupError(
                "PROCESS_IDENTITY_CHANGED_DURING_CLEANUP"
            )

        # A child in zombie state has already terminated.
        # /proc/<pid> remains visible only until its parent reaps it.
        if snapshot["state"] == "Z":
            return True

        time.sleep(POLL_MS / 1000.0)

    return False


def cleanup(runtime_root_raw):
    runtime_root = canonical_existing_directory(
        runtime_root_raw
    )

    pid, expected_identity = load_admission(
        runtime_root
    )

    assert_exact_process(
        pid,
        expected_identity,
    )

    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        raise CleanupError(
            "TARGET_PROCESS_DISAPPEARED_BEFORE_SIGTERM"
        )

    if wait_until_gone(
        pid,
        expected_identity,
        TERM_TIMEOUT_MS,
    ):
        return {
            "schema": SCHEMA,
            "provider_pid": pid,
            "termination": "SIGTERM",
            "runtime_root_preserved": True,
            "fifo_preserved": True,
            "evidence_preserved": True,
        }

    # Revalidate strong identity before escalation.
    assert_exact_process(
        pid,
        expected_identity,
    )

    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        return {
            "schema": SCHEMA,
            "provider_pid": pid,
            "termination": "SIGTERM",
            "runtime_root_preserved": True,
            "fifo_preserved": True,
            "evidence_preserved": True,
        }

    if not wait_until_gone(
        pid,
        expected_identity,
        TERM_TIMEOUT_MS,
    ):
        raise CleanupError(
            "TARGET_PROCESS_SURVIVED_SIGKILL"
        )

    return {
        "schema": SCHEMA,
        "provider_pid": pid,
        "termination": "SIGKILL",
        "runtime_root_preserved": True,
        "fifo_preserved": True,
        "evidence_preserved": True,
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
        result = cleanup(args.runtime_root)
    except CleanupError as exc:
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
