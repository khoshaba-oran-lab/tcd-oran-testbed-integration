#!/usr/bin/env bash

# Identity validation helpers for the Sci_O-RAN experiment harness.

sci_oran_validate_experiment_id() {
    local experiment_id="$1"

    [[ "$experiment_id" =~ ^EXP-[0-9]{8}-[A-Z0-9]+-[A-Z0-9-]+-R[0-9]{2}$ ]]
}

sci_oran_validate_run_id() {
    local run_id="$1"

    [[ "$run_id" =~ ^RUN-[0-9]{8}T[0-9]{6}Z-[0-9]{3}$ ]]
}

sci_oran_generate_run_id() {
    local experiment_id="$1"
    local raw_root="$2"
    local manifest_root="$3"
    local timestamp="${4:-}"
    local sequence
    local candidate
    local raw_path
    local manifest_path

    sci_oran_validate_experiment_id "$experiment_id" || return 1

    if [[ -z "$timestamp" ]]; then
        timestamp="$(date -u '+%Y%m%dT%H%M%SZ')"
    fi

    [[ "$timestamp" =~ ^[0-9]{8}T[0-9]{6}Z$ ]] || return 1

    for ((sequence = 1; sequence <= 999; sequence++)); do
        printf -v candidate 'RUN-%s-%03d' "$timestamp" "$sequence"

        raw_path="${raw_root}/${experiment_id}/${candidate}"
        manifest_path="${manifest_root}/${experiment_id}/${candidate}.json"

        if [[ ! -e "$raw_path" && ! -e "$manifest_path" ]]; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done

    return 1
}
