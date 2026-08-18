#!/usr/bin/env bash

# Native gNB telemetry adapter for the Sci_O-RAN experiment harness.

SCI_ORAN_NATIVE_ADAPTER_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SCI_ORAN_NATIVE_HARNESS_DIR="$(cd -- "${SCI_ORAN_NATIVE_ADAPTER_DIR}/.." && pwd)"

source "${SCI_ORAN_NATIVE_HARNESS_DIR}/lib/process-supervisor.sh"

sci_oran_native_telemetry_start() {
    local repo_root="$1"
    local stdout_path="$2"
    local stderr_path="$3"
    local receiver

    receiver="${repo_root}/scripts/tb3-native-metrics-receiver.sh"

    [[ -f "$receiver" ]] || return 66

    mkdir -p -- "$(dirname -- "$stdout_path")" || return 73
    mkdir -p -- "$(dirname -- "$stderr_path")" || return 73

    sci_oran_process_start \
        "$stdout_path" \
        "$stderr_path" \
        bash "$receiver"
}

sci_oran_native_telemetry_ready() {
    local stdout_path="$1"
    local pid="$2"
    local timeout_s="$3"
    local deadline

    [[ "$pid" =~ ^[0-9]+$ ]] || return 64
    [[ "$timeout_s" =~ ^[0-9]+$ ]] || return 64
    (( timeout_s > 0 )) || return 64

    deadline=$((SECONDS + timeout_s))

    while true; do
        if [[ -s "$stdout_path" ]] && \
           grep -Fxq 'UDP_RECEIVER_READY=10.53.1.1:55555' "$stdout_path"
        then
            return 0
        fi

        if ! sci_oran_process_is_running "$pid"; then
            return 1
        fi

        if (( SECONDS >= deadline )); then
            return 124
        fi

        sleep 0.1
    done
}

sci_oran_native_telemetry_stop() {
    local pid="$1"
    local int_timeout_s="${2:-1}"
    local term_timeout_s="${3:-3}"

    sci_oran_process_stop_graceful \
        "$pid" \
        "$int_timeout_s" \
        "$term_timeout_s"
}
