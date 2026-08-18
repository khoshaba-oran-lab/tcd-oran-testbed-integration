#!/usr/bin/env bash

SCI_ORAN_KPM_ADAPTER_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SCI_ORAN_KPM_HARNESS_DIR="$(cd -- "${SCI_ORAN_KPM_ADAPTER_DIR}/.." && pwd)"

source "${SCI_ORAN_KPM_HARNESS_DIR}/lib/process-supervisor.sh"

SCI_ORAN_KPM_PID=""
SCI_ORAN_KPM_STATUS="disabled"

sci_oran_kpm_start() {
    local enabled="$1"
    local stdout_path="$2"
    local stderr_path="$3"
    local command="${4:-}"

    case "$enabled" in
        false|0)
            SCI_ORAN_KPM_PID=""
            SCI_ORAN_KPM_STATUS="disabled"
            return 0
            ;;
        true|1)
            ;;
        *)
            return 64
            ;;
    esac

    [[ -n "$command" ]] || return 64

    mkdir -p -- "$(dirname -- "$stdout_path")" || return 73
    mkdir -p -- "$(dirname -- "$stderr_path")" || return 73

    sci_oran_process_start \
        "$stdout_path" \
        "$stderr_path" \
        bash -lc "$command" || return $?

    SCI_ORAN_KPM_PID="$SCI_ORAN_LAST_PID"
    SCI_ORAN_KPM_STATUS="starting"

    return 0
}

sci_oran_kpm_ready() {
    local enabled="$1"
    local stdout_path="$2"
    local pid="$3"
    local timeout_s="$4"
    local ready_marker="$5"
    local deadline

    case "$enabled" in
        false|0)
            SCI_ORAN_KPM_STATUS="disabled"
            return 0
            ;;
        true|1)
            ;;
        *)
            return 64
            ;;
    esac

    [[ "$pid" =~ ^[0-9]+$ ]] || return 64
    [[ "$timeout_s" =~ ^[0-9]+$ ]] || return 64
    (( timeout_s > 0 )) || return 64
    [[ -n "$ready_marker" ]] || return 64

    deadline=$((SECONDS + timeout_s))

    while true; do
        if [[ -s "$stdout_path" ]] && \
           grep -Fxq "$ready_marker" "$stdout_path"
        then
            SCI_ORAN_KPM_STATUS="ready"
            return 0
        fi

        if ! sci_oran_process_is_running "$pid"; then
            SCI_ORAN_KPM_STATUS="failed"
            return 1
        fi

        if (( SECONDS >= deadline )); then
            SCI_ORAN_KPM_STATUS="failed"
            return 124
        fi

        sleep 0.1
    done
}

sci_oran_kpm_stop() {
    local enabled="$1"

    case "$enabled" in
        false|0)
            SCI_ORAN_KPM_STATUS="disabled"
            return 0
            ;;
        true|1)
            ;;
        *)
            return 64
            ;;
    esac

    [[ "$SCI_ORAN_KPM_PID" =~ ^[0-9]+$ ]] || return 64

    sci_oran_process_stop_graceful \
        "$SCI_ORAN_KPM_PID" \
        1 \
        3 || return $?

    SCI_ORAN_KPM_STATUS="stopped"

    return 0
}
