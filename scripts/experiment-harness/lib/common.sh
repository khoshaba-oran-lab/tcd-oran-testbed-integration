#!/usr/bin/env bash

# Common helpers for the Sci_O-RAN reproducible experiment harness.

sci_oran_utc_now() {
    date -u '+%Y-%m-%dT%H:%M:%SZ'
}

sci_oran_log() {
    local level="$1"
    shift

    printf '%s level=%s %s\n' \
        "$(sci_oran_utc_now)" \
        "$level" \
        "$*"
}

sci_oran_error() {
    sci_oran_log "ERROR" "$@" >&2
}

sci_oran_die() {
    local exit_code="$1"
    shift

    sci_oran_error "$@"
    return "$exit_code"
}
