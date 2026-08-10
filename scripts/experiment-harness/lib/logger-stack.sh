#!/usr/bin/env bash

SCI_ORAN_LOGGER_LIB_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SCI_ORAN_LOGGER_HARNESS_DIR="$(cd -- "${SCI_ORAN_LOGGER_LIB_DIR}/.." && pwd)"

source "${SCI_ORAN_LOGGER_HARNESS_DIR}/adapters/resource-observer.sh"
source "${SCI_ORAN_LOGGER_HARNESS_DIR}/adapters/native-telemetry.sh"

SCI_ORAN_RESOURCE_PID=""
SCI_ORAN_NATIVE_PID=""

sci_oran_logger_stack_start() {
    local repo_root="$1"
    local run_dir="$2"

    mkdir -p "${run_dir}/raw/resource" "${run_dir}/raw/native_gnb" || return 73

    sci_oran_resource_observer_start \
        "$repo_root" \
        "${run_dir}/raw/resource/resource-network.jsonl" \
        "${run_dir}/raw/resource/resource-network.stderr.log" \
        "1" \
        "0" \
        "5" || return $?

    SCI_ORAN_RESOURCE_PID="$SCI_ORAN_LAST_PID"

    if ! sci_oran_native_telemetry_start \
        "$repo_root" \
        "${run_dir}/raw/native_gnb/native-gNB.log" \
        "${run_dir}/raw/native_gnb/native-gNB.stderr.log"
    then
        sci_oran_process_stop_graceful "$SCI_ORAN_RESOURCE_PID" 1 3 || true
        return 1
    fi

    SCI_ORAN_NATIVE_PID="$SCI_ORAN_LAST_PID"

    return 0
}

sci_oran_logger_stack_ready() {
    local run_dir="$1"
    local timeout_s="$2"

    sci_oran_resource_observer_ready \
        "${run_dir}/raw/resource/resource-network.jsonl" \
        "$SCI_ORAN_RESOURCE_PID" \
        "$timeout_s" || return $?

    sci_oran_native_telemetry_ready \
        "${run_dir}/raw/native_gnb/native-gNB.log" \
        "$SCI_ORAN_NATIVE_PID" \
        "$timeout_s" || return $?

    return 0
}

sci_oran_logger_stack_stop() {
    local rc=0

    if [[ -n "$SCI_ORAN_NATIVE_PID" ]]; then
        sci_oran_native_telemetry_stop "$SCI_ORAN_NATIVE_PID" 1 3 || rc=1
    fi

    if [[ -n "$SCI_ORAN_RESOURCE_PID" ]]; then
        sci_oran_process_stop_graceful "$SCI_ORAN_RESOURCE_PID" 1 3 || rc=1
    fi

    return "$rc"
}
