#!/usr/bin/env bash

# Generic process supervision helpers for the Sci_O-RAN experiment harness.

SCI_ORAN_LAST_PID=""
SCI_ORAN_LAST_EXIT_CODE=""
SCI_ORAN_LAST_STOP_SIGNAL=""
SCI_ORAN_LAST_ESCALATED="NO"

sci_oran_process_start() {
    local stdout_path="$1"
    local stderr_path="$2"
    shift 2

    [[ "$#" -gt 0 ]] || return 64
    [[ ! -e "$stdout_path" ]] || return 73
    [[ ! -e "$stderr_path" ]] || return 73

    "$@" >"$stdout_path" 2>"$stderr_path" &
    SCI_ORAN_LAST_PID=$!

    [[ "$SCI_ORAN_LAST_PID" =~ ^[0-9]+$ ]]
}

sci_oran_process_is_running() {
    local pid="$1"
    local state

    [[ "$pid" =~ ^[0-9]+$ ]] || return 1

    kill -0 "$pid" 2>/dev/null || return 1

    state="$(ps -o stat= -p "$pid" 2>/dev/null | awk 'NR == 1 {print $1}')"

    [[ -n "$state" ]] || return 1
    [[ "$state" != Z* ]]
}

sci_oran_process_wait_stopped() {
    local pid="$1"
    local timeout_s="$2"
    local deadline

    [[ "$pid" =~ ^[0-9]+$ ]] || return 64
    [[ "$timeout_s" =~ ^[0-9]+$ ]] || return 64
    (( timeout_s > 0 )) || return 64

    deadline=$((SECONDS + timeout_s))

    while sci_oran_process_is_running "$pid"; do
        if (( SECONDS >= deadline )); then
            return 124
        fi

        sleep 0.1
    done

    return 0
}

sci_oran_process_capture_wait() {
    local pid="$1"
    local rc

    if wait "$pid"; then
        rc=0
    else
        rc=$?
    fi

    SCI_ORAN_LAST_EXIT_CODE="$rc"

    return 0
}

sci_oran_process_stop_graceful() {
    local pid="$1"
    local int_timeout_s="$2"
    local term_timeout_s="$3"

    [[ "$pid" =~ ^[0-9]+$ ]] || return 64
    [[ "$int_timeout_s" =~ ^[0-9]+$ ]] || return 64
    [[ "$term_timeout_s" =~ ^[0-9]+$ ]] || return 64
    (( int_timeout_s > 0 )) || return 64
    (( term_timeout_s > 0 )) || return 64

    SCI_ORAN_LAST_EXIT_CODE=""
    SCI_ORAN_LAST_STOP_SIGNAL=""
    SCI_ORAN_LAST_ESCALATED="NO"

    if ! sci_oran_process_is_running "$pid"; then
        sci_oran_process_capture_wait "$pid"
        return 0
    fi

    SCI_ORAN_LAST_STOP_SIGNAL="SIGINT"

    kill -INT "$pid" 2>/dev/null || return 1

    if sci_oran_process_wait_stopped "$pid" "$int_timeout_s"; then
        sci_oran_process_capture_wait "$pid"
        return 0
    fi

    if ! sci_oran_process_is_running "$pid"; then
        sci_oran_process_capture_wait "$pid"
        return 0
    fi

    SCI_ORAN_LAST_ESCALATED="YES"
    SCI_ORAN_LAST_STOP_SIGNAL="SIGTERM"

    kill -TERM "$pid" 2>/dev/null || return 1

    if ! sci_oran_process_wait_stopped "$pid" "$term_timeout_s"; then
        return 124
    fi

    sci_oran_process_capture_wait "$pid"

    return 0
}
