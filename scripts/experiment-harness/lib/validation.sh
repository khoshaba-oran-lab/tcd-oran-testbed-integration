#!/usr/bin/env bash

# Generic validation helpers for the Sci_O-RAN experiment harness.

sci_oran_validate_file_exists() {
    local path="$1"

    [[ -f "$path" ]]
}

sci_oran_validate_file_nonempty() {
    local path="$1"

    [[ -f "$path" && -s "$path" ]]
}

sci_oran_file_size_bytes() {
    local path="$1"

    [[ -f "$path" ]] || return 66

    wc -c < "$path" | tr -d '[:space:]'
}

sci_oran_file_sha256() {
    local path="$1"
    local digest

    [[ -f "$path" ]] || return 66

    digest="$(sha256sum -- "$path" | awk '{print $1}')" || return 74

    [[ "$digest" =~ ^[0-9a-f]{64}$ ]] || return 74

    printf '%s\n' "$digest"
}
