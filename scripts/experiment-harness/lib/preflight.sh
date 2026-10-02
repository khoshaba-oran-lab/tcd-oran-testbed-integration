#!/usr/bin/env bash

# Pre-run health and metadata snapshot helpers for Sci_O-RAN.

sci_oran_precheck() {
    local repo_root="$1"

    [[ -d "${repo_root}/.git" ]] || return 66

    command -v git >/dev/null || return 69
    command -v python3 >/dev/null || return 69
    command -v docker >/dev/null || return 69
    command -v sha256sum >/dev/null || return 69
    command -v ip >/dev/null || return 69
    command -v ss >/dev/null || return 69

    [[ -f "${repo_root}/scripts/tb3-resource-network-observer.py" ]] || return 66
    [[ -f "${repo_root}/scripts/tb3-native-metrics-receiver.sh" ]] || return 66

    docker info >/dev/null 2>&1 || return 69

    ip -br addr | grep -Fq '10.53.1.1' || return 69

    if ss -lun 2>/dev/null | grep -Eq \
        '(^|[[:space:]])10\.53\.1\.1:55555([[:space:]]|$)'
    then
        return 75
    fi

    local doctor_path
    local doctor_output
    local doctor_rc
    local readiness_gate
    local failure_reason

    doctor_path="${repo_root}/scripts/sci-oran-doctor.sh"

    [[ -x "$doctor_path" ]] || return 66

    if doctor_output="$("$doctor_path" 2>&1)"; then
        doctor_rc=0
    else
        doctor_rc=$?
    fi

    readiness_gate="$(
        printf '%s\n' "$doctor_output" |
        awk -F= '
            $1 == "SCI_ORAN_READY_GATE" {
                value = substr($0, index($0, "=") + 1)
            }
            END {
                if (value != "")
                    print value
            }
        '
    )"

    failure_reason="$(
        printf '%s\n' "$doctor_output" |
        awk -F= '
            $1 == "FAILURE_REASON" {
                value = substr($0, index($0, "=") + 1)
            }
            END {
                if (value != "")
                    print value
            }
        '
    )"

    if [[ "$doctor_rc" -ne 0 ]]; then
        printf '%s\n' \
            "SCI_ORAN_PREFLIGHT_READY_GATE=FAIL" \
            "SCI_ORAN_PREFLIGHT_DOCTOR_EXIT_CODE=${doctor_rc}" \
            "SCI_ORAN_PREFLIGHT_FAILURE_REASON=${failure_reason:-MISSING}" \
            >&2

        return "$doctor_rc"
    fi

    if [[ "$readiness_gate" != "PASS" ]] || \
       [[ "$failure_reason" != "NONE" ]]
    then
        printf '%s\n' \
            "SCI_ORAN_PREFLIGHT_READY_GATE=FAIL" \
            "SCI_ORAN_PREFLIGHT_DOCTOR_EXIT_CODE=${doctor_rc}" \
            "SCI_ORAN_PREFLIGHT_FAILURE_REASON=${failure_reason:-MISSING}" \
            >&2

        return 70
    fi

    local portable_path
    local portable_output
    local portable_rc
    local portable_gate
    local portable_qualification_gate

    portable_path="${repo_root}/scripts/experiment-harness/r6-f-portable-runtime-preflight.py"

    if [[ -z "${SCI_ORAN_PREFLIGHT_PYTHON_EXECUTABLE:-}" ]]; then
        printf '%s\n' \
            "SCI_ORAN_PREFLIGHT_READY_GATE=FAIL" \
            "SCI_ORAN_PREFLIGHT_DOCTOR_EXIT_CODE=0" \
            "SCI_ORAN_PREFLIGHT_PORTABLE_EXIT_CODE=NOT_EXECUTED" \
            "SCI_ORAN_PREFLIGHT_PORTABLE_GATE=NOT_EXECUTED" \
            "SCI_ORAN_PREFLIGHT_PORTABLE_ADMISSION_PATH=${SCI_ORAN_PREFLIGHT_PORTABLE_ADMISSION_OUTPUT:-MISSING}" \
            "SCI_ORAN_PREFLIGHT_FAILURE_REASON=MISSING_PREFLIGHT_PYTHON_EXECUTABLE" \
            >&2
        return 64
    fi

    if [[ "${SCI_ORAN_PREFLIGHT_PYTHON_EXECUTABLE}" != /* ]]; then
        printf '%s\n' \
            "SCI_ORAN_PREFLIGHT_READY_GATE=FAIL" \
            "SCI_ORAN_PREFLIGHT_DOCTOR_EXIT_CODE=0" \
            "SCI_ORAN_PREFLIGHT_PORTABLE_EXIT_CODE=NOT_EXECUTED" \
            "SCI_ORAN_PREFLIGHT_PORTABLE_GATE=NOT_EXECUTED" \
            "SCI_ORAN_PREFLIGHT_PORTABLE_ADMISSION_PATH=${SCI_ORAN_PREFLIGHT_PORTABLE_ADMISSION_OUTPUT:-MISSING}" \
            "SCI_ORAN_PREFLIGHT_FAILURE_REASON=PREFLIGHT_PYTHON_EXECUTABLE_NOT_ABSOLUTE" \
            >&2
        return 64
    fi

    if [[ ! -x "${SCI_ORAN_PREFLIGHT_PYTHON_EXECUTABLE}" ]]; then
        printf '%s\n' \
            "SCI_ORAN_PREFLIGHT_READY_GATE=FAIL" \
            "SCI_ORAN_PREFLIGHT_DOCTOR_EXIT_CODE=0" \
            "SCI_ORAN_PREFLIGHT_PORTABLE_EXIT_CODE=NOT_EXECUTED" \
            "SCI_ORAN_PREFLIGHT_PORTABLE_GATE=NOT_EXECUTED" \
            "SCI_ORAN_PREFLIGHT_PORTABLE_ADMISSION_PATH=${SCI_ORAN_PREFLIGHT_PORTABLE_ADMISSION_OUTPUT:-MISSING}" \
            "SCI_ORAN_PREFLIGHT_FAILURE_REASON=PREFLIGHT_PYTHON_EXECUTABLE_NOT_EXECUTABLE" \
            >&2
        return 69
    fi

    if [[ -z "${SCI_ORAN_PREFLIGHT_REQUIRE_JSONSCHEMA:-}" ]]; then
        printf '%s\n' \
            "SCI_ORAN_PREFLIGHT_READY_GATE=FAIL" \
            "SCI_ORAN_PREFLIGHT_DOCTOR_EXIT_CODE=0" \
            "SCI_ORAN_PREFLIGHT_PORTABLE_EXIT_CODE=NOT_EXECUTED" \
            "SCI_ORAN_PREFLIGHT_PORTABLE_GATE=NOT_EXECUTED" \
            "SCI_ORAN_PREFLIGHT_PORTABLE_ADMISSION_PATH=${SCI_ORAN_PREFLIGHT_PORTABLE_ADMISSION_OUTPUT:-MISSING}" \
            "SCI_ORAN_PREFLIGHT_FAILURE_REASON=MISSING_PREFLIGHT_REQUIRE_JSONSCHEMA" \
            >&2
        return 64
    fi

    if [[ "${SCI_ORAN_PREFLIGHT_REQUIRE_JSONSCHEMA}" != "yes" ]] && \
       [[ "${SCI_ORAN_PREFLIGHT_REQUIRE_JSONSCHEMA}" != "no" ]]
    then
        printf '%s\n' \
            "SCI_ORAN_PREFLIGHT_READY_GATE=FAIL" \
            "SCI_ORAN_PREFLIGHT_DOCTOR_EXIT_CODE=0" \
            "SCI_ORAN_PREFLIGHT_PORTABLE_EXIT_CODE=NOT_EXECUTED" \
            "SCI_ORAN_PREFLIGHT_PORTABLE_GATE=NOT_EXECUTED" \
            "SCI_ORAN_PREFLIGHT_PORTABLE_ADMISSION_PATH=${SCI_ORAN_PREFLIGHT_PORTABLE_ADMISSION_OUTPUT:-MISSING}" \
            "SCI_ORAN_PREFLIGHT_FAILURE_REASON=PREFLIGHT_REQUIRE_JSONSCHEMA_INVALID" \
            >&2
        return 64
    fi

    if [[ -z "${SCI_ORAN_PREFLIGHT_PORTABLE_ADMISSION_OUTPUT:-}" ]]; then
        printf '%s\n' \
            "SCI_ORAN_PREFLIGHT_READY_GATE=FAIL" \
            "SCI_ORAN_PREFLIGHT_DOCTOR_EXIT_CODE=0" \
            "SCI_ORAN_PREFLIGHT_PORTABLE_EXIT_CODE=NOT_EXECUTED" \
            "SCI_ORAN_PREFLIGHT_PORTABLE_GATE=NOT_EXECUTED" \
            "SCI_ORAN_PREFLIGHT_PORTABLE_ADMISSION_PATH=MISSING" \
            "SCI_ORAN_PREFLIGHT_FAILURE_REASON=MISSING_PREFLIGHT_PORTABLE_ADMISSION_OUTPUT" \
            >&2
        return 64
    fi

    if [[ "${SCI_ORAN_PREFLIGHT_PORTABLE_ADMISSION_OUTPUT}" != /* ]]; then
        printf '%s\n' \
            "SCI_ORAN_PREFLIGHT_READY_GATE=FAIL" \
            "SCI_ORAN_PREFLIGHT_DOCTOR_EXIT_CODE=0" \
            "SCI_ORAN_PREFLIGHT_PORTABLE_EXIT_CODE=NOT_EXECUTED" \
            "SCI_ORAN_PREFLIGHT_PORTABLE_GATE=NOT_EXECUTED" \
            "SCI_ORAN_PREFLIGHT_PORTABLE_ADMISSION_PATH=${SCI_ORAN_PREFLIGHT_PORTABLE_ADMISSION_OUTPUT}" \
            "SCI_ORAN_PREFLIGHT_FAILURE_REASON=PREFLIGHT_PORTABLE_ADMISSION_OUTPUT_NOT_ABSOLUTE" \
            >&2
        return 64
    fi

    if [[ ! -x "$portable_path" ]]; then
        printf '%s\n' \
            "SCI_ORAN_PREFLIGHT_READY_GATE=FAIL" \
            "SCI_ORAN_PREFLIGHT_DOCTOR_EXIT_CODE=0" \
            "SCI_ORAN_PREFLIGHT_PORTABLE_EXIT_CODE=NOT_EXECUTED" \
            "SCI_ORAN_PREFLIGHT_PORTABLE_GATE=NOT_EXECUTED" \
            "SCI_ORAN_PREFLIGHT_PORTABLE_ADMISSION_PATH=${SCI_ORAN_PREFLIGHT_PORTABLE_ADMISSION_OUTPUT}" \
            "SCI_ORAN_PREFLIGHT_FAILURE_REASON=PORTABLE_RUNTIME_PROVIDER_UNAVAILABLE" \
            >&2
        return 66
    fi

    if portable_output="$(
        "$portable_path" \
            --python-executable "${SCI_ORAN_PREFLIGHT_PYTHON_EXECUTABLE}" \
            --require-jsonschema "${SCI_ORAN_PREFLIGHT_REQUIRE_JSONSCHEMA}" \
            --output "${SCI_ORAN_PREFLIGHT_PORTABLE_ADMISSION_OUTPUT}" \
            2>&1
    )"
    then
        portable_rc=0
    else
        portable_rc=$?
    fi

    portable_gate="$(
        printf '%s\n' "$portable_output" |
        awk -F= '
            $1 == "R6_F_PORTABLE_RUNTIME_PREFLIGHT_GATE" {
                value = substr($0, index($0, "=") + 1)
            }
            END {
                if (value != "")
                    print value
            }
        '
    )"

    portable_qualification_gate="$(
        printf '%s\n' "$portable_output" |
        awk -F= '
            $1 == "ADMISSION_QUALIFICATION_GATE" {
                value = substr($0, index($0, "=") + 1)
            }
            END {
                if (value != "")
                    print value
            }
        '
    )"

    if [[ "$portable_rc" -ne 0 ]]; then
        printf '%s\n' \
            "SCI_ORAN_PREFLIGHT_READY_GATE=FAIL" \
            "SCI_ORAN_PREFLIGHT_DOCTOR_EXIT_CODE=0" \
            "SCI_ORAN_PREFLIGHT_PORTABLE_EXIT_CODE=${portable_rc}" \
            "SCI_ORAN_PREFLIGHT_PORTABLE_GATE=${portable_gate:-MISSING}" \
            "SCI_ORAN_PREFLIGHT_PORTABLE_QUALIFICATION_GATE=${portable_qualification_gate:-MISSING}" \
            "SCI_ORAN_PREFLIGHT_PORTABLE_ADMISSION_PATH=${SCI_ORAN_PREFLIGHT_PORTABLE_ADMISSION_OUTPUT}" \
            "SCI_ORAN_PREFLIGHT_FAILURE_REASON=PORTABLE_RUNTIME_PROVIDER_FAILED" \
            >&2

        return "$portable_rc"
    fi

    if [[ "$portable_gate" != "PASS" ]] || \
       [[ "$portable_qualification_gate" != "PASS" ]]
    then
        printf '%s\n' \
            "SCI_ORAN_PREFLIGHT_READY_GATE=FAIL" \
            "SCI_ORAN_PREFLIGHT_DOCTOR_EXIT_CODE=0" \
            "SCI_ORAN_PREFLIGHT_PORTABLE_EXIT_CODE=0" \
            "SCI_ORAN_PREFLIGHT_PORTABLE_GATE=${portable_gate:-MISSING}" \
            "SCI_ORAN_PREFLIGHT_PORTABLE_QUALIFICATION_GATE=${portable_qualification_gate:-MISSING}" \
            "SCI_ORAN_PREFLIGHT_PORTABLE_ADMISSION_PATH=${SCI_ORAN_PREFLIGHT_PORTABLE_ADMISSION_OUTPUT}" \
            "SCI_ORAN_PREFLIGHT_FAILURE_REASON=PORTABLE_RUNTIME_GATE_NOT_PASS" \
            >&2

        return 70
    fi

    if [[ ! -s "${SCI_ORAN_PREFLIGHT_PORTABLE_ADMISSION_OUTPUT}" ]]; then
        printf '%s\n' \
            "SCI_ORAN_PREFLIGHT_READY_GATE=FAIL" \
            "SCI_ORAN_PREFLIGHT_DOCTOR_EXIT_CODE=0" \
            "SCI_ORAN_PREFLIGHT_PORTABLE_EXIT_CODE=0" \
            "SCI_ORAN_PREFLIGHT_PORTABLE_GATE=PASS" \
            "SCI_ORAN_PREFLIGHT_PORTABLE_QUALIFICATION_GATE=PASS" \
            "SCI_ORAN_PREFLIGHT_PORTABLE_ADMISSION_PATH=${SCI_ORAN_PREFLIGHT_PORTABLE_ADMISSION_OUTPUT}" \
            "SCI_ORAN_PREFLIGHT_FAILURE_REASON=PORTABLE_RUNTIME_ADMISSION_ARTIFACT_MISSING" \
            >&2

        return 65
    fi

    echo "SCI_ORAN_PREFLIGHT_READY_GATE=PASS"
    echo "SCI_ORAN_PREFLIGHT_DOCTOR_EXIT_CODE=0"
    echo "SCI_ORAN_PREFLIGHT_PORTABLE_EXIT_CODE=0"
    echo "SCI_ORAN_PREFLIGHT_PORTABLE_GATE=PASS"
    echo "SCI_ORAN_PREFLIGHT_PORTABLE_QUALIFICATION_GATE=PASS"
    echo "SCI_ORAN_PREFLIGHT_PORTABLE_ADMISSION_PATH=${SCI_ORAN_PREFLIGHT_PORTABLE_ADMISSION_OUTPUT}"
    echo "SCI_ORAN_PREFLIGHT_FAILURE_REASON=NONE"

    return 0
}

sci_oran_metadata_snapshot() {
    local repo_root="$1"
    local output_path="$2"
    local snapshot_time_utc="$3"

    [[ "$snapshot_time_utc" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$ ]] || return 64
    [[ ! -e "$output_path" ]] || return 73

    mkdir -p -- "$(dirname -- "$output_path")" || return 73

    python3 - "$repo_root" "$output_path" "$snapshot_time_utc" <<'PY'
import hashlib
import json
import os
import subprocess
import sys

repo_root, output_path, snapshot_time_utc = sys.argv[1:]

def git(*args):
    return subprocess.check_output(
        ["git", "-C", repo_root, *args],
        text=True,
    ).strip()

def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

status = git("status", "--porcelain")

references = [
    "manifests/hosts/tb3-dell.yaml",
    "manifests/software.yaml",
    "manifests/docker-images.yaml",
]

files = []

for relative_path in references:
    absolute_path = os.path.join(repo_root, relative_path)

    if os.path.isfile(absolute_path):
        files.append(
            {
                "path": relative_path,
                "sha256": sha256_file(absolute_path),
            }
        )

document = {
    "git": {
        "branch": git("branch", "--show-current"),
        "head": git("rev-parse", "HEAD"),
        "working_tree_clean": status == "",
        "working_tree_status": status.splitlines(),
    },
    "host": {
        "hostname": os.uname().nodename,
    },
    "project_manifests": files,
    "snapshot_time_utc": snapshot_time_utc,
}

with open(output_path, "x", encoding="utf-8", newline="\n") as handle:
    json.dump(
        document,
        handle,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    handle.write("\n")
PY
}

sci_oran_postcheck() {
    local repo_root="$1"
    local run_dir="$2"
    local resource_pid="$3"
    local native_pid="$4"
    local rtt_pid="$5"
    local state

    [[ -d "${repo_root}/.git" ]] || return 66
    [[ "$resource_pid" =~ ^[0-9]+$ ]] || return 64
    [[ "$native_pid" =~ ^[0-9]+$ ]] || return 64
    [[ "$rtt_pid" =~ ^[0-9]+$ ]] || return 64

    docker info >/dev/null 2>&1 || return 69

    ip -br addr | grep -Fq '10.53.1.1' || return 69

    kill -0 "$resource_pid" 2>/dev/null || return 70
    state="$(ps -o stat= -p "$resource_pid" 2>/dev/null | awk 'NR == 1 {print $1}')"
    [[ -n "$state" && "$state" != Z* ]] || return 70

    kill -0 "$native_pid" 2>/dev/null || return 70
    state="$(ps -o stat= -p "$native_pid" 2>/dev/null | awk 'NR == 1 {print $1}')"
    [[ -n "$state" && "$state" != Z* ]] || return 70

    kill -0 "$rtt_pid" 2>/dev/null || return 70
    state="$(ps -o stat= -p "$rtt_pid" 2>/dev/null | awk 'NR == 1 {print $1}')"
    [[ -n "$state" && "$state" != Z* ]] || return 70

    [[ -s "${run_dir}/raw/resource/resource-network.jsonl" ]] || return 65
    [[ -s "${run_dir}/raw/rtt/ping.log" ]] || return 65

    grep -Fxq \
        'UDP_RECEIVER_READY=10.53.1.1:55555' \
        "${run_dir}/raw/native_gnb/native-gNB.log" || return 65

    grep -Eq \
        '^\[[0-9]+\.[0-9]+\].*icmp_seq=[0-9]+.*time=[0-9.]+ ms' \
        "${run_dir}/raw/rtt/ping.log" || return 65

    return 0
}
