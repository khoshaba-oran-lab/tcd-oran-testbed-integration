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
