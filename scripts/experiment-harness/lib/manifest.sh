#!/usr/bin/env bash

# Operational manifest helpers for the Sci_O-RAN experiment harness.

sci_oran_manifest_init() {
    local manifest_path="$1"
    local experiment_id="$2"
    local run_id="$3"
    local created_time_utc="$4"
    local manifest_version="${5:-0.1.0}"
    local manifest_dir

    [[ -n "$manifest_path" ]] || return 64
    [[ -n "$experiment_id" ]] || return 64
    [[ -n "$run_id" ]] || return 64
    [[ "$created_time_utc" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$ ]] || return 64

    manifest_dir="$(dirname -- "$manifest_path")"
    mkdir -p -- "$manifest_dir" || return 73

    python3 - "$manifest_path" "$experiment_id" "$run_id" \
        "$created_time_utc" "$manifest_version" <<'PY'
import json
import os
import sys

path, experiment_id, run_id, created_time_utc, manifest_version = sys.argv[1:]

document = {
    "final_status": None,
    "identity": {
        "created_time_utc": created_time_utc,
        "experiment_id": experiment_id,
        "manifest_version": manifest_version,
        "run_id": run_id,
    },
    "lifecycle": {
        "state": "IDENTITY",
    },
}

try:
    with open(path, "x", encoding="utf-8", newline="\n") as handle:
        json.dump(
            document,
            handle,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        handle.write("\n")
except FileExistsError:
    raise SystemExit(73)
except OSError:
    raise SystemExit(74)
PY
}

sci_oran_manifest_set_lifecycle() {
    local manifest_path="$1"
    local lifecycle_state="$2"
    local transition_time_utc="$3"

    [[ -f "$manifest_path" ]] || return 66

    case "$lifecycle_state" in
        PRECHECK|IDENTITY|SNAPSHOT|LOGGER_START|LOGGER_READY|RUNNING|COOLDOWN|POSTCHECK|LOGGER_STOP|VALIDATION|FINALIZATION|COMPLETED|FAILED|INTERRUPTED|REJECTED)
            ;;
        *)
            return 64
            ;;
    esac

    [[ "$transition_time_utc" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$ ]] || return 64

    python3 - "$manifest_path" "$lifecycle_state" "$transition_time_utc" <<'PY'
import json
import os
import sys
import tempfile

path, state, transition_time_utc = sys.argv[1:]

try:
    with open(path, encoding="utf-8") as handle:
        document = json.load(handle)

    lifecycle = document.setdefault("lifecycle", {})
    history = lifecycle.setdefault("history", [])

    if not history:
        identity = document.get("identity", {})
        created_time = identity.get("created_time_utc")
        current_state = lifecycle.get("state")

        if current_state and created_time:
            history.append(
                {
                    "state": current_state,
                    "time_utc": created_time,
                }
            )

    lifecycle["state"] = state
    lifecycle["last_transition_time_utc"] = transition_time_utc
    history.append(
        {
            "state": state,
            "time_utc": transition_time_utc,
        }
    )

    directory = os.path.dirname(path) or "."
    original_mode = os.stat(path).st_mode & 0o777

    fd, temporary_path = tempfile.mkstemp(
        prefix=".sci-oran-manifest-",
        suffix=".tmp",
        dir=directory,
        text=True,
    )

    try:
        os.fchmod(fd, original_mode)

        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
            newline="\n",
        ) as handle:
            json.dump(
                document,
                handle,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(temporary_path, path)

        try:
            directory_fd = os.open(directory, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError:
            pass

    finally:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)

except FileNotFoundError:
    raise SystemExit(66)
except (OSError, json.JSONDecodeError):
    raise SystemExit(74)
PY
}
