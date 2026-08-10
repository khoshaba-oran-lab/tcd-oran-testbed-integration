#!/usr/bin/env bash

# Resource/network observer adapter for the Sci_O-RAN experiment harness.

SCI_ORAN_RESOURCE_ADAPTER_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SCI_ORAN_RESOURCE_HARNESS_DIR="$(cd -- "${SCI_ORAN_RESOURCE_ADAPTER_DIR}/.." && pwd)"

source "${SCI_ORAN_RESOURCE_HARNESS_DIR}/lib/process-supervisor.sh"

sci_oran_resource_observer_start() {
    local repo_root="$1"
    local stdout_path="$2"
    local stderr_path="$3"
    local interval_s="$4"
    local count="$5"
    local qdisc_every="$6"
    local collector

    collector="${repo_root}/scripts/tb3-resource-network-observer.py"

    [[ -f "$collector" ]] || return 66
    [[ "$interval_s" =~ ^[0-9]+([.][0-9]+)?$ ]] || return 64
    [[ "$count" =~ ^[0-9]+$ ]] || return 64
    [[ "$qdisc_every" =~ ^[0-9]+$ ]] || return 64

    mkdir -p -- "$(dirname -- "$stdout_path")" || return 73
    mkdir -p -- "$(dirname -- "$stderr_path")" || return 73

    sci_oran_process_start \
        "$stdout_path" \
        "$stderr_path" \
        python3 -u "$collector" \
        --interval "$interval_s" \
        --count "$count" \
        --qdisc-every "$qdisc_every"
}

sci_oran_resource_observer_ready() {
    local stdout_path="$1"
    local pid="$2"
    local timeout_s="$3"
    local deadline

    [[ "$pid" =~ ^[0-9]+$ ]] || return 64
    [[ "$timeout_s" =~ ^[0-9]+$ ]] || return 64
    (( timeout_s > 0 )) || return 64

    deadline=$((SECONDS + timeout_s))

    while true; do
        if [[ -s "$stdout_path" ]]; then
            if python3 - "$stdout_path" <<'PY'
import json
import sys

path = sys.argv[1]

try:
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue

            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue

            if (
                row.get("schema")
                == "sci_oran_resource_network_observability_v1"
                and "timestamp_utc" in row
                and "host" in row
                and "containers" in row
            ):
                raise SystemExit(0)

except OSError:
    pass

raise SystemExit(1)
PY
            then
                return 0
            fi
        fi

        if ! kill -0 "$pid" 2>/dev/null; then
            return 1
        fi

        if (( SECONDS >= deadline )); then
            return 124
        fi

        sleep 0.1
    done
}
