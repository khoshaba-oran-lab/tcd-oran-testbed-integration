#!/usr/bin/env bash
set -Eeuo pipefail

HARNESS_VERSION="0.1.0"
EX_USAGE=64

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"

source "${SCRIPT_DIR}/lib/common.sh"
source "${SCRIPT_DIR}/lib/identity.sh"
source "${SCRIPT_DIR}/lib/manifest.sh"
source "${SCRIPT_DIR}/lib/preflight.sh"
source "${SCRIPT_DIR}/lib/logger-stack.sh"
source "${SCRIPT_DIR}/lib/traffic-window.sh"
source "${SCRIPT_DIR}/lib/finalization.sh"
source "${SCRIPT_DIR}/adapters/kpm.sh"

LOGGER_STACK_ACTIVE=0
KPM_ACTIVE=0
RUN_COMPLETED=0
TERMINAL_OVERRIDE=""
MANIFEST_PATH=""

cleanup_on_exit() {
    local terminal_state
    local terminal_time

    if [[ -n "${SCI_ORAN_TRAFFIC_PID:-}" ]] && \
       sci_oran_process_is_running "$SCI_ORAN_TRAFFIC_PID"
    then
        sci_oran_process_stop_graceful \
            "$SCI_ORAN_TRAFFIC_PID" \
            1 \
            3 >/dev/null 2>&1 || true
    fi

    if [[ "$KPM_ACTIVE" -eq 1 ]]; then
        sci_oran_kpm_stop true >/dev/null 2>&1 || true
        KPM_ACTIVE=0
    fi

    if [[ "$LOGGER_STACK_ACTIVE" -eq 1 ]]; then
        sci_oran_logger_stack_stop >/dev/null 2>&1 || true
        LOGGER_STACK_ACTIVE=0
    fi

    if [[ "$RUN_COMPLETED" -eq 0 ]] && \
       [[ -n "$MANIFEST_PATH" ]] && \
       [[ -f "$MANIFEST_PATH" ]]
    then
        terminal_state="${TERMINAL_OVERRIDE:-FAILED}"
        terminal_time="$(sci_oran_utc_now)"

        sci_oran_manifest_set_lifecycle \
            "$MANIFEST_PATH" \
            "$terminal_state" \
            "$terminal_time" >/dev/null 2>&1 || true

        sci_oran_manifest_set_final_status \
            "$MANIFEST_PATH" \
            "$terminal_state" \
            "$terminal_time" >/dev/null 2>&1 || true
    fi

    return 0
}

handle_signal() {
    local signal_name="$1"

    TERMINAL_OVERRIDE="INTERRUPTED"

    case "$signal_name" in
        INT)
            exit 130
            ;;
        TERM)
            exit 143
            ;;
        *)
            exit 1
            ;;
    esac
}

trap 'handle_signal INT' INT
trap 'handle_signal TERM' TERM
trap 'rc=$?; trap - EXIT INT TERM; cleanup_on_exit; exit "$rc"' EXIT

usage() {
    echo "Usage: $(basename "$0") --experiment-id ID --workspace-root PATH --traffic-command COMMAND [--cooldown-s N] [--kpm-command COMMAND] [--kpm-ready-marker MARKER]"
}

if [[ "${1:-}" == "--version" ]]; then
    echo "sci-oran-experiment-harness ${HARNESS_VERSION}"
    exit 0
fi

EXPERIMENT_ID=""
WORKSPACE_ROOT=""
TRAFFIC_COMMAND=""
COOLDOWN_S="1"
KPM_ENABLED="false"
KPM_COMMAND=""
KPM_READY_MARKER="KPM_READY"

while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --experiment-id)
            [[ "$#" -ge 2 ]] || exit "$EX_USAGE"
            EXPERIMENT_ID="$2"
            shift 2
            ;;
        --workspace-root)
            [[ "$#" -ge 2 ]] || exit "$EX_USAGE"
            WORKSPACE_ROOT="$2"
            shift 2
            ;;
        --traffic-command)
            [[ "$#" -ge 2 ]] || exit "$EX_USAGE"
            TRAFFIC_COMMAND="$2"
            shift 2
            ;;
        --cooldown-s)
            [[ "$#" -ge 2 ]] || exit "$EX_USAGE"
            COOLDOWN_S="$2"
            shift 2
            ;;
        --kpm-command)
            [[ "$#" -ge 2 ]] || exit "$EX_USAGE"
            KPM_COMMAND="$2"
            KPM_ENABLED="true"
            shift 2
            ;;
        --kpm-ready-marker)
            [[ "$#" -ge 2 ]] || exit "$EX_USAGE"
            KPM_READY_MARKER="$2"
            shift 2
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            echo "Unsupported argument: $1" >&2
            exit "$EX_USAGE"
            ;;
    esac
done

[[ -n "$EXPERIMENT_ID" ]] || exit "$EX_USAGE"
[[ -n "$WORKSPACE_ROOT" ]] || exit "$EX_USAGE"
[[ -n "$TRAFFIC_COMMAND" ]] || exit "$EX_USAGE"
[[ "$COOLDOWN_S" =~ ^[0-9]+$ ]] || exit "$EX_USAGE"

sci_oran_validate_experiment_id "$EXPERIMENT_ID" || exit "$EX_USAGE"

sci_oran_log INFO "lifecycle=PRECHECK"

sci_oran_precheck "$REPO_ROOT" || {
    rc=$?
    sci_oran_error "precheck failed rc=${rc}"
    exit "$rc"
}

RUNS_ROOT="${WORKSPACE_ROOT}/runs"
MANIFEST_ROOT="${WORKSPACE_ROOT}/manifests"

mkdir -p "$RUNS_ROOT" "$MANIFEST_ROOT"

RUN_ID="$(
    sci_oran_generate_run_id \
        "$EXPERIMENT_ID" \
        "$RUNS_ROOT" \
        "$MANIFEST_ROOT"
)" || exit 73

RUN_DIR="${RUNS_ROOT}/${EXPERIMENT_ID}/${RUN_ID}"
MANIFEST_PATH="${MANIFEST_ROOT}/${EXPERIMENT_ID}/${RUN_ID}.json"
SNAPSHOT_PATH="${RUN_DIR}/metadata-snapshot.json"

mkdir -p "$RUN_DIR"

IDENTITY_TIME="$(sci_oran_utc_now)"

sci_oran_manifest_init \
    "$MANIFEST_PATH" \
    "$EXPERIMENT_ID" \
    "$RUN_ID" \
    "$IDENTITY_TIME" \
    "$HARNESS_VERSION"

SNAPSHOT_TIME="$(sci_oran_utc_now)"

sci_oran_metadata_snapshot \
    "$REPO_ROOT" \
    "$SNAPSHOT_PATH" \
    "$SNAPSHOT_TIME"

sci_oran_manifest_set_lifecycle \
    "$MANIFEST_PATH" \
    "SNAPSHOT" \
    "$SNAPSHOT_TIME"

LOGGER_START_TIME="$(sci_oran_utc_now)"

sci_oran_manifest_set_lifecycle \
    "$MANIFEST_PATH" \
    "LOGGER_START" \
    "$LOGGER_START_TIME"

sci_oran_log INFO "lifecycle=LOGGER_START"

if sci_oran_logger_stack_start "$REPO_ROOT" "$RUN_DIR"; then
    LOGGER_STACK_ACTIVE=1
else
    rc=$?
    sci_oran_error "logger start failed rc=${rc}"
    exit "$rc"
fi

RESOURCE_PID="$SCI_ORAN_RESOURCE_PID"
NATIVE_PID="$SCI_ORAN_NATIVE_PID"
RTT_PID="$SCI_ORAN_RTT_PID"

if [[ "$KPM_ENABLED" == "true" ]]; then
    if sci_oran_kpm_start         true         "${RUN_DIR}/raw/oran_kpm/oran-kpm.log"         "${RUN_DIR}/raw/oran_kpm/oran-kpm.stderr.log"         "$KPM_COMMAND"
    then
        KPM_ACTIVE=1
    else
        rc=$?
        sci_oran_error "KPM start failed rc=${rc}"
        exit "$rc"
    fi
fi

if ! sci_oran_logger_stack_ready "$RUN_DIR" 5; then
    rc=$?
    sci_oran_error "logger readiness failed rc=${rc}"
    exit "$rc"
fi

if [[ "$KPM_ENABLED" == "true" ]]; then
    if sci_oran_kpm_ready         true         "${RUN_DIR}/raw/oran_kpm/oran-kpm.log"         "$SCI_ORAN_KPM_PID"         5         "$KPM_READY_MARKER"
    then
        :
    else
        rc=$?
        sci_oran_error "KPM readiness failed rc=${rc}"
        exit "$rc"
    fi
fi

LOGGER_READY_TIME="$(sci_oran_utc_now)"

sci_oran_manifest_set_lifecycle \
    "$MANIFEST_PATH" \
    "LOGGER_READY" \
    "$LOGGER_READY_TIME"

sci_oran_log INFO "lifecycle=LOGGER_READY"
sci_oran_log INFO "lifecycle=RUNNING"

if sci_oran_run_traffic_window     "$MANIFEST_PATH"     "$RUN_DIR"     "$COOLDOWN_S"     "$TRAFFIC_COMMAND"
then
    :
else
    rc=$?
    sci_oran_error "traffic window failed rc=${rc}"
    exit "$rc"
fi

sci_oran_log INFO     "lifecycle=COOLDOWN traffic_start_utc=${SCI_ORAN_TRAFFIC_START_UTC} traffic_end_utc=${SCI_ORAN_TRAFFIC_END_UTC}"

POSTCHECK_TIME="$(sci_oran_utc_now)"

sci_oran_manifest_set_lifecycle \
    "$MANIFEST_PATH" \
    "POSTCHECK" \
    "$POSTCHECK_TIME"

sci_oran_log INFO "lifecycle=POSTCHECK"

if sci_oran_postcheck \
    "$REPO_ROOT" \
    "$RUN_DIR" \
    "$RESOURCE_PID" \
    "$NATIVE_PID" \
    "$RTT_PID"
then
    :
else
    rc=$?
    sci_oran_error "postcheck failed rc=${rc}"
    exit "$rc"
fi

if [[ "$KPM_ENABLED" == "true" ]]; then
    if sci_oran_process_is_running "$SCI_ORAN_KPM_PID"; then
        :
    else
        sci_oran_error "KPM process not alive during postcheck"
        exit 70
    fi
fi

LOGGER_STOP_TIME="$(sci_oran_utc_now)"

sci_oran_manifest_set_lifecycle \
    "$MANIFEST_PATH" \
    "LOGGER_STOP" \
    "$LOGGER_STOP_TIME"

sci_oran_log INFO "lifecycle=LOGGER_STOP"

if [[ "$KPM_ACTIVE" -eq 1 ]]; then
    if sci_oran_kpm_stop true; then
        KPM_ACTIVE=0
    else
        rc=$?
        sci_oran_error "KPM stop failed rc=${rc}"
        exit "$rc"
    fi
fi

if sci_oran_logger_stack_stop
then
    LOGGER_STACK_ACTIVE=0
else
    rc=$?
    sci_oran_error "logger stop failed rc=${rc}"
    exit "$rc"
fi

VALIDATION_TIME="$(sci_oran_utc_now)"

sci_oran_manifest_set_lifecycle \
    "$MANIFEST_PATH" \
    "VALIDATION" \
    "$VALIDATION_TIME"

sci_oran_log INFO "lifecycle=VALIDATION"

if sci_oran_validate_run_evidence "$RUN_DIR"
then
    :
else
    rc=$?
    sci_oran_error "evidence validation failed rc=${rc}"
    exit "$rc"
fi

if sci_oran_write_run_checksums "$RUN_DIR"
then
    :
else
    rc=$?
    sci_oran_error "checksum generation failed rc=${rc}"
    exit "$rc"
fi

FINALIZATION_TIME="$(sci_oran_utc_now)"

sci_oran_manifest_set_lifecycle \
    "$MANIFEST_PATH" \
    "FINALIZATION" \
    "$FINALIZATION_TIME"

sci_oran_log INFO "lifecycle=FINALIZATION"

if sci_oran_manifest_record_summary \
    "$MANIFEST_PATH" \
    "$RUN_DIR" \
    "$SCI_ORAN_TRAFFIC_START_UTC" \
    "$SCI_ORAN_TRAFFIC_END_UTC" \
    "$SCI_ORAN_TRAFFIC_EXIT_CODE"
then
    :
else
    rc=$?
    sci_oran_error "manifest summary failed rc=${rc}"
    exit "$rc"
fi

if sci_oran_manifest_record_execution \
    "$MANIFEST_PATH" \
    "$TRAFFIC_COMMAND" \
    "$COOLDOWN_S"
then
    :
else
    rc=$?
    sci_oran_error "execution metadata failed rc=${rc}"
    exit "$rc"
fi

if sci_oran_manifest_record_kpm     "$MANIFEST_PATH"     "$KPM_ENABLED"     "$SCI_ORAN_KPM_STATUS"
then
    :
else
    rc=$?
    sci_oran_error "KPM manifest update failed rc=${rc}"
    exit "$rc"
fi

COMPLETED_TIME="$(sci_oran_utc_now)"

sci_oran_manifest_set_lifecycle \
    "$MANIFEST_PATH" \
    "COMPLETED" \
    "$COMPLETED_TIME"

sci_oran_manifest_set_final_status \
    "$MANIFEST_PATH" \
    "COMPLETED" \
    "$COMPLETED_TIME"

RUN_COMPLETED=1

sci_oran_log INFO "lifecycle=COMPLETED"

LOGGER_STACK_ACTIVE=0

echo "EXPERIMENT_ID=$EXPERIMENT_ID"
echo "RUN_ID=$RUN_ID"
echo "RUN_DIR=$RUN_DIR"
echo "MANIFEST_PATH=$MANIFEST_PATH"
echo "RESOURCE_PID=$RESOURCE_PID"
echo "NATIVE_PID=$NATIVE_PID"
echo "TRAFFIC_START_UTC=$SCI_ORAN_TRAFFIC_START_UTC"
echo "TRAFFIC_END_UTC=$SCI_ORAN_TRAFFIC_END_UTC"
echo "TRAFFIC_EXIT_CODE=$SCI_ORAN_TRAFFIC_EXIT_CODE"
echo "CHECKSUM_PATH=${RUN_DIR}/checksums/SHA256SUMS"
echo "KPM_PID=$SCI_ORAN_KPM_PID"
echo "KPM_STATUS=$SCI_ORAN_KPM_STATUS"
echo "FINAL_STATUS=COMPLETED"
echo "RUNNER_COMPLETE=PASS"
