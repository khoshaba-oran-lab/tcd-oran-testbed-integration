#!/usr/bin/env bash

# Controlled traffic adapter for the Sci_O-RAN experiment harness.

SCI_ORAN_TRAFFIC_ADAPTER_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SCI_ORAN_TRAFFIC_HARNESS_DIR="$(cd -- "${SCI_ORAN_TRAFFIC_ADAPTER_DIR}/.." && pwd)"

source "${SCI_ORAN_TRAFFIC_HARNESS_DIR}/lib/process-supervisor.sh"

sci_oran_traffic_start() {
    local stdout_path="$1"
    local stderr_path="$2"
    shift 2

    [[ "$#" -gt 0 ]] || return 64

    mkdir -p -- "$(dirname -- "$stdout_path")" || return 73
    mkdir -p -- "$(dirname -- "$stderr_path")" || return 73

    sci_oran_process_start \
        "$stdout_path" \
        "$stderr_path" \
        "$@"
}

sci_oran_traffic_wait() {
    local pid="$1"

    [[ "$pid" =~ ^[0-9]+$ ]] || return 64

    sci_oran_process_capture_wait "$pid"
}
