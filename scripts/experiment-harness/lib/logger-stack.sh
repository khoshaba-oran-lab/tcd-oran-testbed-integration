#!/usr/bin/env bash

SCI_ORAN_LOGGER_LIB_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SCI_ORAN_LOGGER_HARNESS_DIR="$(cd -- "${SCI_ORAN_LOGGER_LIB_DIR}/.." && pwd)"

source "${SCI_ORAN_LOGGER_HARNESS_DIR}/adapters/resource-observer.sh"
source "${SCI_ORAN_LOGGER_HARNESS_DIR}/adapters/native-telemetry.sh"
source "${SCI_ORAN_LOGGER_HARNESS_DIR}/adapters/rtt.sh"

SCI_ORAN_RESOURCE_PID=""
SCI_ORAN_NATIVE_PID=""
SCI_ORAN_RTT_PID=""

SCI_ORAN_RTT_CONTAINER_NAME="base05_srsran_srsue"
SCI_ORAN_RTT_INTERFACE="tun_srsue"
SCI_ORAN_RTT_TARGET_IP="10.45.1.1"
SCI_ORAN_RTT_INTERVAL_S="0.2"
SCI_ORAN_RTT_PAYLOAD_BYTES="64"
SCI_ORAN_RTT_REPLY_TIMEOUT_S="2"

sci_oran_logger_stack_start() {
    local repo_root="$1"
    local run_dir="$2"

    mkdir -p \
        "${run_dir}/raw/resource" \
        "${run_dir}/raw/native_gnb" \
        "${run_dir}/raw/rtt" || return 73

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
        sci_oran_process_stop_graceful \
            "$SCI_ORAN_RESOURCE_PID" \
            1 \
            3 || true
        return 1
    fi

    SCI_ORAN_NATIVE_PID="$SCI_ORAN_LAST_PID"

    if ! sci_oran_rtt_start \
        "${run_dir}/raw/rtt/ping.log" \
        "${run_dir}/raw/rtt/ping.stderr.log" \
        "$SCI_ORAN_RTT_CONTAINER_NAME" \
        "$SCI_ORAN_RTT_INTERFACE" \
        "$SCI_ORAN_RTT_TARGET_IP" \
        "$SCI_ORAN_RTT_INTERVAL_S" \
        "$SCI_ORAN_RTT_PAYLOAD_BYTES" \
        "$SCI_ORAN_RTT_REPLY_TIMEOUT_S"
    then
        sci_oran_native_telemetry_stop \
            "$SCI_ORAN_NATIVE_PID" \
            1 \
            3 || true

        sci_oran_process_stop_graceful \
            "$SCI_ORAN_RESOURCE_PID" \
            1 \
            3 || true

        return 1
    fi

    SCI_ORAN_RTT_PID="$SCI_ORAN_LAST_PID"

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

    sci_oran_rtt_ready \
        "${run_dir}/raw/rtt/ping.log" \
        "$SCI_ORAN_RTT_PID" \
        "$timeout_s" || return $?

    return 0
}

sci_oran_logger_stack_stop() {
    local rc=0

    if [[ -n "$SCI_ORAN_RTT_PID" ]]; then
        sci_oran_rtt_stop \
            "$SCI_ORAN_RTT_PID" \
            1 \
            3 || rc=1
    fi

    if [[ -n "$SCI_ORAN_NATIVE_PID" ]]; then
        sci_oran_native_telemetry_stop \
            "$SCI_ORAN_NATIVE_PID" \
            1 \
            3 || rc=1
    fi

    if [[ -n "$SCI_ORAN_RESOURCE_PID" ]]; then
        sci_oran_process_stop_graceful \
            "$SCI_ORAN_RESOURCE_PID" \
            1 \
            3 || rc=1
    fi

    return "$rc"
}
