#!/usr/bin/env bash
set -euo pipefail
umask 077
export LC_ALL=C

SCRIPT_DIR="$(
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &&
    pwd -P
)"

STACK_DIR="$(
    cd -- "$SCRIPT_DIR/.." &&
    pwd -P
)"

COMPOSE_FILE="$STACK_DIR/compose.emulator.yml"
PROJECT_NAME="${PROJECT_NAME:-tcd-p2a-flexric}"

RIC_NAME="${RIC_NAME:-p2a_flexric_ric}"
AGENT_NAME="${AGENT_NAME:-p2a_flexric_e2_agent}"
XAPP_NAME="${XAPP_NAME:-p2a_flexric_reference_xapp}"
XAPP_SERVICE="${XAPP_SERVICE:-reference-xapp}"

P2_TAG="${P2_TAG:-tcd-oran/flexric-emulator:e2ap-v2-kpm-v3-b1d6d36-p2}"

EXPECTED_REVISION="b1d6d36334a44a0dfeaacd643b82948259355d7c"
EXPECTED_TREE="bfd1a35b019f9ea7f48d5ee95e2751219e7ad578"
EXPECTED_PATCH_0001="787fe4e8f98f0417e0c5d5fa8f578b25b888754e48a1ac4c7780324abbee83f3"
EXPECTED_PATCH_0002="78280f4c58659ab1d41cf6e1d2bb5a750869fcf33e7311be27a0c6f1d376a757"
EXPECTED_XAPP_BINARY_SHA256="dc13c53af9134c68336397ff593b21f8be8e7edee869af2626d993a2cf3f523a"
EXPECTED_XAPP_CONFIG_SHA256="c64b101f87825f181c0d7557ec7414831c87102bff9abf0cc96e6a980ad68916"

XAPP_BINARY="/usr/local/bin/flexric/xApp/c/xapp_oran_moni"
XAPP_CONFIG="/etc/flexric/xapp-kpm.conf"

MAX_LIFETIME_SECONDS="${MAX_LIFETIME_SECONDS:-60}"
EVIDENCE_ROOT="${EVIDENCE_ROOT:-$PWD/validation-evidence}"

TS="$(date -u +%Y%m%dT%H%M%SZ)-$$"
EVIDENCE_DIR="$EVIDENCE_ROOT/$TS-reference-xapp-p2"
FULL_LOG="$EVIDENCE_DIR/validation.log"

XAPP_LOG="$EVIDENCE_DIR/xapp.log"
RIC_LOG="$EVIDENCE_DIR/ric.log"
AGENT_LOG="$EVIDENCE_DIR/agent.log"
XAPP_DIFF="$EVIDENCE_DIR/xapp.diff"
MONITOR="$EVIDENCE_DIR/monitor.tsv"
REPORT="$EVIDENCE_DIR/classification.txt"
SUMMARY="$EVIDENCE_DIR/summary.env"

EXTRACTED_XAPP="$EVIDENCE_DIR/xapp_oran_moni"
EXTRACTED_CONFIG="$EVIDENCE_DIR/xapp-kpm.conf"

mkdir -p "$EVIDENCE_DIR"
chmod 700 "$EVIDENCE_DIR"

trial_started="no"
trial_finalized="no"

cleanup()
{
    if [[ "$trial_started" == "yes" && "$trial_finalized" != "yes" ]]; then
        if docker container inspect "$XAPP_NAME" >/dev/null 2>&1; then
            status="$(
                docker inspect \
                    --format '{{.State.Status}}' \
                    "$XAPP_NAME" 2>/dev/null ||
                true
            )"

            if [[ "$status" == "running" ]]; then
                docker stop \
                    --signal SIGINT \
                    --time 10 \
                    "$XAPP_NAME" \
                    >/dev/null 2>&1 ||
                true
            fi
        fi
    fi
}

trap cleanup EXIT
exec > >(tee -a "$FULL_LOG") 2>&1

fail()
{
    echo
    echo "VALIDATION_RESULT=FAILED"
    echo "REASON=$*"
    echo "EVIDENCE_DIR=$EVIDENCE_DIR"
    exit 1
}

count_fixed()
{
    grep -Fic "$1" "$2" 2>/dev/null || true
}

first_line()
{
    grep -nE "$1" "$2" 2>/dev/null |
        head -n 1 |
        cut -d: -f1 ||
        true
}

echo "=== P2 REFERENCE XAPP VALIDATION ==="
echo "COMPOSE_FILE=$COMPOSE_FILE"
echo "EVIDENCE_DIR=$EVIDENCE_DIR"

[[ -f "$COMPOSE_FILE" ]] ||
    fail "Compose file is unavailable"

ric_before="$(
    docker inspect \
        --format '{{.Id}}|{{.State.Status}}|{{.State.StartedAt}}|{{.Image}}' \
        "$RIC_NAME" 2>/dev/null ||
    true
)"

agent_before="$(
    docker inspect \
        --format '{{.Id}}|{{.State.Status}}|{{.State.StartedAt}}|{{.Image}}' \
        "$AGENT_NAME" 2>/dev/null ||
    true
)"

[[ -n "$ric_before" ]] ||
    fail "RIC container is unavailable"

[[ -n "$agent_before" ]] ||
    fail "E2 Agent container is unavailable"

IFS='|' read -r \
    ric_id_before \
    ric_status_before \
    ric_started_before \
    ric_image_before \
    <<<"$ric_before"

IFS='|' read -r \
    agent_id_before \
    agent_status_before \
    agent_started_before \
    agent_image_before \
    <<<"$agent_before"

[[ "$ric_status_before" == "running" ]] ||
    fail "RIC is not running"

[[ "$agent_status_before" == "running" ]] ||
    fail "E2 Agent is not running"

if docker container inspect "$XAPP_NAME" >/dev/null 2>&1; then
    old_xapp_status="$(
        docker inspect \
            --format '{{.State.Status}}' \
            "$XAPP_NAME"
    )"

    [[ "$old_xapp_status" != "running" ]] ||
        fail "reference-xapp is already running"
fi

revision="$(
    docker image inspect "$P2_TAG" \
        --format '{{index .Config.Labels "org.opencontainers.image.revision"}}'
)"

tree="$(
    docker image inspect "$P2_TAG" \
        --format '{{index .Config.Labels "io.tcd-oran.flexric.tree"}}'
)"

patch_0001="$(
    docker image inspect "$P2_TAG" \
        --format '{{index .Config.Labels "io.tcd-oran.flexric.patch-0001-sha256"}}'
)"

patch_0002="$(
    docker image inspect "$P2_TAG" \
        --format '{{index .Config.Labels "io.tcd-oran.flexric.patch-0002-sha256"}}'
)"

[[ "$revision" == "$EXPECTED_REVISION" ]] ||
    fail "p2 revision label differs"

[[ "$tree" == "$EXPECTED_TREE" ]] ||
    fail "p2 FlexRIC tree label differs"

[[ "$patch_0001" == "$EXPECTED_PATCH_0001" ]] ||
    fail "p2 patch 0001 label differs"

[[ "$patch_0002" == "$EXPECTED_PATCH_0002" ]] ||
    fail "p2 patch 0002 label differs"

trial_started="yes"

timeout --foreground 120s \
    docker compose \
        --project-directory "$STACK_DIR" \
        --project-name "$PROJECT_NAME" \
        -f "$COMPOSE_FILE" \
        up \
        -d \
        --no-deps \
        --force-recreate \
        "$XAPP_SERVICE"

xapp_id="$(
    docker inspect \
        --format '{{.Id}}' \
        "$XAPP_NAME"
)"

xapp_started_at="$(
    docker inspect \
        --format '{{.State.StartedAt}}' \
        "$XAPP_NAME"
)"

printf '%s\n' \
    $'elapsed_seconds\tstatus\trunning\texit_code\toom_killed' \
    >"$MONITOR"

start_seconds="$SECONDS"
timed_out="no"

while true; do
    state="$(
        docker inspect \
            --format '{{.State.Status}}|{{.State.Running}}|{{.State.ExitCode}}|{{.State.OOMKilled}}' \
            "$XAPP_NAME"
    )"

    IFS='|' read -r \
        status \
        running \
        exit_code \
        oom_killed \
        <<<"$state"

    elapsed=$((SECONDS - start_seconds))

    printf '%s\t%s\t%s\t%s\t%s\n' \
        "$elapsed" \
        "$status" \
        "$running" \
        "$exit_code" \
        "$oom_killed" \
        | tee -a "$MONITOR"

    if [[ "$status" != "running" && "$status" != "created" ]]; then
        break
    fi

    if [[ "$elapsed" -ge "$MAX_LIFETIME_SECONDS" ]]; then
        timed_out="yes"

        docker stop \
            --signal SIGINT \
            --time 10 \
            "$XAPP_NAME" \
            >/dev/null 2>&1 ||
        true

        break
    fi

    sleep 1
done

final_state="$(
    docker inspect \
        --format '{{.State.Status}}|{{.State.ExitCode}}|{{.State.OOMKilled}}|{{.State.FinishedAt}}|{{.Image}}' \
        "$XAPP_NAME"
)"

IFS='|' read -r \
    final_status \
    final_exit_code \
    final_oom \
    finished_at \
    xapp_image_id \
    <<<"$final_state"

docker logs \
    --timestamps \
    "$XAPP_NAME" \
    >"$XAPP_LOG" 2>&1 ||
true

docker logs \
    --timestamps \
    --since "$xapp_started_at" \
    "$RIC_NAME" \
    >"$RIC_LOG" 2>&1 ||
true

docker logs \
    --timestamps \
    --since "$xapp_started_at" \
    "$AGENT_NAME" \
    >"$AGENT_LOG" 2>&1 ||
true

docker diff "$XAPP_NAME" >"$XAPP_DIFF" 2>&1 || true

docker cp \
    "$XAPP_NAME:$XAPP_BINARY" \
    "$EXTRACTED_XAPP"

docker cp \
    "$XAPP_NAME:$XAPP_CONFIG" \
    "$EXTRACTED_CONFIG"

binary_sha="$(
    sha256sum "$EXTRACTED_XAPP" |
    awk '{print $1}'
)"

config_sha="$(
    sha256sum "$EXTRACTED_CONFIG" |
    awk '{print $1}'
)"

[[ "$binary_sha" == "$EXPECTED_XAPP_BINARY_SHA256" ]] ||
    fail "Runtime xApp binary SHA256 differs"

[[ "$config_sha" == "$EXPECTED_XAPP_CONFIG_SHA256" ]] ||
    fail "Runtime xApp configuration SHA256 differs"

setup_request_count="$(count_fixed 'E42 SETUP-REQUEST' "$XAPP_LOG")"
setup_response_count="$(count_fixed 'E42 SETUP-RESPONSE' "$XAPP_LOG")"
kpm_count="$(count_fixed 'KPM-v3 ind_msg latency' "$XAPP_LOG")"
rnti_count="$(grep -Eic 'RNTI' "$XAPP_LOG" || true)"
record_count="$(count_fixed 'meas record' "$XAPP_LOG")"
delete_request_count="$(count_fixed 'RIC_SUBSCRIPTION_DELETE_REQUEST' "$XAPP_LOG")"
delete_response_count="$(count_fixed 'SUBSCRIPTION DELETE RESPONSE' "$XAPP_LOG")"
stopped_count="$(count_fixed 'Sucessfully stopped' "$XAPP_LOG")"
success_count="$(count_fixed 'Test xApp run SUCCESSFULLY' "$XAPP_LOG")"

subscription_request_count="$(
    grep -Eic \
        'RIC[_ ]SUBSCRIPTION[_ ]REQUEST|RIC SUBSCRIPTION REQUEST|Successfully subscribed' \
        "$XAPP_LOG" ||
    true
)"

crash_count="$(
    grep -Eic \
        'SIGSEGV|segmentation fault|signal 11|core dumped|AddressSanitizer|stack smashing' \
        "$XAPP_LOG" ||
    true
)"

core_count="$(
    grep -Eic \
        '(^|/)(core(\.[^/]*)?|[^/]+\.core)$' \
        "$XAPP_DIFF" ||
    true
)"

callback_line="$(
    first_line \
        'KPM-v3 ind_msg latency|RNTI' \
        "$XAPP_LOG"
)"

delete_request_line="$(
    first_line \
        'RIC_SUBSCRIPTION_DELETE_REQUEST' \
        "$XAPP_LOG"
)"

delete_response_line="$(
    first_line \
        'SUBSCRIPTION DELETE RESPONSE' \
        "$XAPP_LOG"
)"

stopped_line="$(
    first_line \
        'Sucessfully stopped' \
        "$XAPP_LOG"
)"

success_line="$(
    first_line \
        'Test xApp run SUCCESSFULLY' \
        "$XAPP_LOG"
)"

ordered="no"

if [[ -n "$callback_line" &&
      -n "$delete_request_line" &&
      -n "$delete_response_line" &&
      -n "$stopped_line" &&
      -n "$success_line" ]] &&
   (( callback_line < delete_request_line )) &&
   (( delete_request_line < delete_response_line )) &&
   (( delete_response_line <= stopped_line )) &&
   (( stopped_line <= success_line ))
then
    ordered="yes"
fi

callback_activity="no"

if [[ "$kpm_count" -gt 0 &&
      "$rnti_count" -gt 0 &&
      "$record_count" -gt 0 ]]
then
    callback_activity="yes"
fi

subscription_lifecycle="no"

if [[ "$subscription_request_count" -gt 0 &&
      "$delete_request_count" -gt 0 &&
      "$delete_response_count" -gt 0 ]]
then
    subscription_lifecycle="yes"
fi

sigsegv_observed="no"

if [[ "$final_exit_code" -eq 139 ||
      "$crash_count" -gt 0 ||
      "$core_count" -gt 0 ]]
then
    sigsegv_observed="yes"
fi

validation_result="FAIL_OR_INCONCLUSIVE"

if [[ "$timed_out" == "no" &&
      "$final_status" == "exited" &&
      "$final_exit_code" -eq 0 &&
      "$final_oom" == "false" &&
      "$callback_activity" == "yes" &&
      "$subscription_lifecycle" == "yes" &&
      "$ordered" == "yes" &&
      "$stopped_count" -gt 0 &&
      "$success_count" -gt 0 &&
      "$sigsegv_observed" == "no" ]]
then
    validation_result="PASS_FINITE_LIFECYCLE_NO_SIGSEGV"
fi

{
    echo "===== P2 REFERENCE XAPP VALIDATION ====="
    echo "VALIDATION_RESULT=$validation_result"
    echo "XAPP_STATUS=$final_status"
    echo "XAPP_EXIT_CODE=$final_exit_code"
    echo "XAPP_OOM_KILLED=$final_oom"
    echo "LIFECYCLE_TIMED_OUT=$timed_out"
    echo "E42_SETUP_REQUEST_MARKERS=$setup_request_count"
    echo "E42_SETUP_RESPONSE_MARKERS=$setup_response_count"
    echo "SUBSCRIPTION_REQUEST_MARKERS=$subscription_request_count"
    echo "KPM_INDICATION_MARKERS=$kpm_count"
    echo "RNTI_CALLBACK_MARKERS=$rnti_count"
    echo "MEASUREMENT_RECORD_MARKERS=$record_count"
    echo "DELETE_REQUEST_MARKERS=$delete_request_count"
    echo "DELETE_RESPONSE_MARKERS=$delete_response_count"
    echo "CALLBACK_ACTIVITY_PROVEN=$callback_activity"
    echo "SUBSCRIPTION_LIFECYCLE_PROVEN=$subscription_lifecycle"
    echo "ORDERED_GRACEFUL_TERMINAL_FLOW=$ordered"
    echo "CRASH_LOG_MARKERS=$crash_count"
    echo "CORE_CANDIDATES=$core_count"
    echo "SIGSEGV_OBSERVED=$sigsegv_observed"
} | tee "$REPORT"

[[ "$validation_result" == "PASS_FINITE_LIFECYCLE_NO_SIGSEGV" ]] ||
    fail "Lifecycle classification failed"

ric_after="$(
    docker inspect \
        --format '{{.Id}}|{{.State.Status}}|{{.State.StartedAt}}|{{.Image}}' \
        "$RIC_NAME"
)"

agent_after="$(
    docker inspect \
        --format '{{.Id}}|{{.State.Status}}|{{.State.StartedAt}}|{{.Image}}' \
        "$AGENT_NAME"
)"

[[ "$ric_after" == "$ric_before" ]] ||
    fail "RIC container changed during validation"

[[ "$agent_after" == "$agent_before" ]] ||
    fail "E2 Agent container changed during validation"

{
    echo "VALIDATION_RESULT=$validation_result"
    echo "XAPP_ID=$xapp_id"
    echo "XAPP_IMAGE_ID=$xapp_image_id"
    echo "XAPP_BINARY_SHA256=$binary_sha"
    echo "XAPP_CONFIG_SHA256=$config_sha"
    echo "XAPP_EXIT_CODE=$final_exit_code"
    echo "CALLBACK_ACTIVITY_PROVEN=$callback_activity"
    echo "SUBSCRIPTION_LIFECYCLE_PROVEN=$subscription_lifecycle"
    echo "ORDERED_GRACEFUL_TERMINAL_FLOW=$ordered"
    echo "SIGSEGV_OBSERVED=$sigsegv_observed"
    echo "RIC_RECREATED=no"
    echo "AGENT_RECREATED=no"
    echo "EVIDENCE_DIR=$EVIDENCE_DIR"
} | tee "$SUMMARY"

trial_finalized="yes"
trap - EXIT

echo
echo "FULL_LOG=$FULL_LOG"
