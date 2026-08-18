#!/usr/bin/env bash

SCI_ORAN_TRAFFIC_WINDOW_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SCI_ORAN_TRAFFIC_HARNESS_DIR="$(cd -- "${SCI_ORAN_TRAFFIC_WINDOW_DIR}/.." && pwd)"

source "${SCI_ORAN_TRAFFIC_HARNESS_DIR}/lib/common.sh"
source "${SCI_ORAN_TRAFFIC_HARNESS_DIR}/lib/manifest.sh"
source "${SCI_ORAN_TRAFFIC_HARNESS_DIR}/adapters/traffic.sh"

SCI_ORAN_TRAFFIC_START_UTC=""
SCI_ORAN_TRAFFIC_END_UTC=""
SCI_ORAN_TRAFFIC_EXIT_CODE=""
SCI_ORAN_TRAFFIC_PID=""

sci_oran_run_traffic_window() {
    local manifest_path="$1"
    local run_dir="$2"
    local cooldown_s="$3"
    local traffic_command="$4"
    local traffic_pid

    [[ "$cooldown_s" =~ ^[0-9]+$ ]] || return 64
    [[ -n "$traffic_command" ]] || return 64

    mkdir -p "${run_dir}/raw/traffic" || return 73

    SCI_ORAN_TRAFFIC_START_UTC="$(sci_oran_utc_now)"

    sci_oran_manifest_set_lifecycle \
        "$manifest_path" \
        "RUNNING" \
        "$SCI_ORAN_TRAFFIC_START_UTC" || return $?

    sci_oran_traffic_start \
        "${run_dir}/raw/traffic/traffic.stdout.log" \
        "${run_dir}/raw/traffic/traffic.stderr.log" \
        bash -lc "$traffic_command" || return $?

    traffic_pid="$SCI_ORAN_LAST_PID"
    SCI_ORAN_TRAFFIC_PID="$traffic_pid"

    sci_oran_traffic_wait "$traffic_pid" || return $?

    SCI_ORAN_TRAFFIC_EXIT_CODE="$SCI_ORAN_LAST_EXIT_CODE"
    SCI_ORAN_TRAFFIC_END_UTC="$(sci_oran_utc_now)"

    sci_oran_manifest_set_lifecycle \
        "$manifest_path" \
        "COOLDOWN" \
        "$SCI_ORAN_TRAFFIC_END_UTC" || return $?

    if (( cooldown_s > 0 )); then
        sleep "$cooldown_s"
    fi

    [[ "$SCI_ORAN_TRAFFIC_EXIT_CODE" -eq 0 ]] || return 70

    return 0
}
