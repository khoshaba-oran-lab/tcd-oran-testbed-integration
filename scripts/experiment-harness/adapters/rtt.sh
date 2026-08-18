#!/usr/bin/env bash

# User-plane RTT measurement adapter for the Sci_O-RAN experiment harness.
#
# Scientific semantics:
#   source container   : srsUE
#   source interface   : tun_srsue
#   source address     : UE PDU address
#   destination        : UPF-side user-plane address
#   measurement        : ICMP round-trip time
#
# Native gNB cell_avg_latency is not interpreted as network RTT.

SCI_ORAN_RTT_ADAPTER_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SCI_ORAN_RTT_HARNESS_DIR="$(cd -- "${SCI_ORAN_RTT_ADAPTER_DIR}/.." && pwd)"

source "${SCI_ORAN_RTT_HARNESS_DIR}/lib/process-supervisor.sh"

SCI_ORAN_RTT_CONTAINER=""
SCI_ORAN_RTT_CONTAINER_PIDFILE="/tmp/sci-oran-rtt-collector.pid"

sci_oran_rtt_start() {
    local stdout_path="$1"
    local stderr_path="$2"
    local container="$3"
    local interface="$4"
    local target_ip="$5"
    local interval_s="$6"
    local payload_bytes="$7"
    local reply_timeout_s="$8"

    [[ -n "$stdout_path" ]] || return 64
    [[ -n "$stderr_path" ]] || return 64
    [[ -n "$container" ]] || return 64
    [[ -n "$interface" ]] || return 64
    [[ -n "$target_ip" ]] || return 64

    [[ "$interval_s" =~ ^[0-9]+([.][0-9]+)?$ ]] || return 64
    [[ "$payload_bytes" =~ ^[0-9]+$ ]] || return 64
    [[ "$reply_timeout_s" =~ ^[0-9]+$ ]] || return 64

    docker inspect "$container" >/dev/null 2>&1 || return 66

    docker exec "$container" sh -lc '
        pidfile="$1"

        if [ -f "$pidfile" ]; then
            old_pid="$(cat "$pidfile" 2>/dev/null || true)"

            case "$old_pid" in
                ""|*[!0-9]*)
                    rm -f "$pidfile"
                    ;;
                *)
                    if kill -0 "$old_pid" 2>/dev/null; then
                        exit 75
                    fi

                    rm -f "$pidfile"
                    ;;
            esac
        fi
    ' _ "$SCI_ORAN_RTT_CONTAINER_PIDFILE" || return $?

    mkdir -p -- "$(dirname -- "$stdout_path")" || return 73
    mkdir -p -- "$(dirname -- "$stderr_path")" || return 73

    SCI_ORAN_RTT_CONTAINER="$container"

    sci_oran_process_start \
        "$stdout_path" \
        "$stderr_path" \
        docker exec "$container" sh -lc '
            pidfile="$1"
            interface="$2"
            target_ip="$3"
            interval_s="$4"
            payload_bytes="$5"
            reply_timeout_s="$6"

            printf "%s\n" "$$" > "$pidfile"

            exec ping \
                -n \
                -D \
                -I "$interface" \
                -i "$interval_s" \
                -s "$payload_bytes" \
                -W "$reply_timeout_s" \
                "$target_ip"
        ' _ \
        "$SCI_ORAN_RTT_CONTAINER_PIDFILE" \
        "$interface" \
        "$target_ip" \
        "$interval_s" \
        "$payload_bytes" \
        "$reply_timeout_s"
}

sci_oran_rtt_ready() {
    local stdout_path="$1"
    local pid="$2"
    local timeout_s="$3"
    local deadline

    [[ -f "$stdout_path" ]] || return 66
    [[ "$pid" =~ ^[0-9]+$ ]] || return 64
    [[ "$timeout_s" =~ ^[0-9]+$ ]] || return 64
    (( timeout_s > 0 )) || return 64

    deadline=$((SECONDS + timeout_s))

    while true; do
        if [[ -s "$stdout_path" ]] &&
           grep -Eq 'icmp_seq=[0-9]+' "$stdout_path"
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

sci_oran_rtt_stop() {
    local host_pid="$1"
    local int_timeout_s="${2:-1}"
    local term_timeout_s="${3:-3}"
    local container="$SCI_ORAN_RTT_CONTAINER"
    local pidfile="$SCI_ORAN_RTT_CONTAINER_PIDFILE"

    [[ "$host_pid" =~ ^[0-9]+$ ]] || return 64
    [[ -n "$container" ]] || return 64

    docker exec "$container" sh -lc '
        pidfile="$1"

        if [ ! -f "$pidfile" ]; then
            exit 0
        fi

        pid="$(cat "$pidfile" 2>/dev/null || true)"

        case "$pid" in
            ""|*[!0-9]*)
                rm -f "$pidfile"
                exit 0
                ;;
        esac

        if kill -0 "$pid" 2>/dev/null; then
            kill -INT "$pid" 2>/dev/null || true
        fi

        i=0

        while kill -0 "$pid" 2>/dev/null; do
            if [ "$i" -ge 30 ]; then
                kill -TERM "$pid" 2>/dev/null || true
            fi

            if [ "$i" -ge 60 ]; then
                kill -KILL "$pid" 2>/dev/null || true
                break
            fi

            sleep 0.1
            i=$((i + 1))
        done

        rm -f "$pidfile"
    ' _ "$pidfile" || return $?

    sleep 0.2

    if sci_oran_process_is_running "$host_pid"; then
        sci_oran_process_stop_graceful \
            "$host_pid" \
            "$int_timeout_s" \
            "$term_timeout_s"
    fi

    return 0
}
