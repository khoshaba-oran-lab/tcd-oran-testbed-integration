#!/usr/bin/env bash

set -u
set -o pipefail

SESSION_ADAPTER_DIR="$(
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &&
    pwd
)"
HARNESS_DIR="$(cd -- "${SESSION_ADAPTER_DIR}/.." && pwd)"

DEFAULT_TRAFFIC_ADAPTER="${SESSION_ADAPTER_DIR}/prompt12-siso-traffic.sh"
TRAFFIC_ADAPTER="${SCI_ORAN_PROMPT12_SESSION_TRAFFIC_ADAPTER:-$DEFAULT_TRAFFIC_ADAPTER}"
PROCESS_SUPERVISOR="${HARNESS_DIR}/lib/process-supervisor.sh"

source "$PROCESS_SUPERVISOR"

INT_TIMEOUT_S="${SCI_ORAN_PROMPT12_SESSION_INT_TIMEOUT_S:-5}"
TERM_TIMEOUT_S="${SCI_ORAN_PROMPT12_SESSION_TERM_TIMEOUT_S:-5}"

SESSION_RECEIVER_NAME=""
SESSION_RECEIVER_CREATED="NO"
SESSION_CAPTURE_PID=""
SESSION_CLEANUP_DONE="NO"
SESSION_CONTROL_STDOUT=""
SESSION_CONTROL_STDERR=""

usage()
{
    cat <<'USAGE'
Usage:

  prompt12-bounded-traffic-session.sh contract

  prompt12-bounded-traffic-session.sh plan \
      <receiver-container-name> \
      <duration-s> \
      <raw-output> \
      <timestamp-output> \
      <stderr-output>

  prompt12-bounded-traffic-session.sh run \
      <receiver-container-name> \
      <duration-s> \
      <raw-output> \
      <timestamp-output> \
      <stderr-output>
USAGE
}

fail()
{
    echo "PROMPT12_TRAFFIC_SESSION_GATE=FAIL" >&2
    echo "FAIL_REASON=$1" >&2
    exit "${2:-64}"
}

validate_receiver_name()
{
    [[ "$1" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]*$ ]]
}

validate_duration()
{
    [[ "$1" =~ ^[0-9]+$ ]] || return 1
    (( "$1" > 0 && "$1" <= 180 ))
}

validate_output_path()
{
    [[ -n "$1" ]] || return 1
    [[ "$1" != -* ]]
}

validate_common_arguments()
{
    local receiver_name="$1"
    local duration_s="$2"
    local raw_output="$3"
    local timestamp_output="$4"
    local stderr_output="$5"

    validate_receiver_name "$receiver_name" ||
        return 64
    validate_duration "$duration_s" ||
        return 64
    validate_output_path "$raw_output" ||
        return 64
    validate_output_path "$timestamp_output" ||
        return 64
    validate_output_path "$stderr_output" ||
        return 64

    [[ "$raw_output" != "$timestamp_output" ]] ||
        return 64
    [[ "$raw_output" != "$stderr_output" ]] ||
        return 64
    [[ "$timestamp_output" != "$stderr_output" ]] ||
        return 64

    return 0
}

require_live_enable()
{
    if [ "${SCI_ORAN_PROMPT12_LIVE_TRAFFIC_ENABLE:-NO}" != "YES" ]; then
        echo "PROMPT12_LIVE_TRAFFIC_INTERLOCK=BLOCKED" >&2
        return 77
    fi

    return 0
}

validate_runtime()
{
    [[ "$TRAFFIC_ADAPTER" = /* ]] ||
        return 64
    [[ -x "$TRAFFIC_ADAPTER" ]] ||
        return 69
    command -v docker >/dev/null 2>&1 ||
        return 69
    [[ "$INT_TIMEOUT_S" =~ ^[0-9]+$ ]] ||
        return 64
    [[ "$TERM_TIMEOUT_S" =~ ^[0-9]+$ ]] ||
        return 64
    (( INT_TIMEOUT_S > 0 && TERM_TIMEOUT_S > 0 )) ||
        return 64

    return 0
}

prepare_outputs()
{
    local raw_output="$1"
    local timestamp_output="$2"
    local stderr_output="$3"
    local path

    SESSION_CONTROL_STDOUT="${raw_output}.session.stdout.log"
    SESSION_CONTROL_STDERR="${raw_output}.session.stderr.log"

    for path in \
        "$raw_output" \
        "$timestamp_output" \
        "$stderr_output" \
        "$SESSION_CONTROL_STDOUT" \
        "$SESSION_CONTROL_STDERR"
    do
        [[ ! -e "$path" ]] ||
            return 73
        mkdir -p -- "$(dirname -- "$path")" ||
            return 73
    done

    return 0
}

cleanup_session()
{
    local cleanup_rc=0
    local rc

    if [ "$SESSION_CLEANUP_DONE" = "YES" ]; then
        return 0
    fi

    SESSION_CLEANUP_DONE="YES"

    if [[ "$SESSION_CAPTURE_PID" =~ ^[0-9]+$ ]]; then
        sci_oran_process_stop_graceful \
            "$SESSION_CAPTURE_PID" \
            "$INT_TIMEOUT_S" \
            "$TERM_TIMEOUT_S"
        rc=$?

        if [ "$rc" -ne 0 ]; then
            cleanup_rc="$rc"
        fi

        SESSION_CAPTURE_PID=""
    fi

    if [ "$SESSION_RECEIVER_CREATED" = "YES" ]; then
        docker rm -f -- "$SESSION_RECEIVER_NAME" >/dev/null 2>&1
        rc=$?

        if [ "$rc" -ne 0 ] && [ "$cleanup_rc" -eq 0 ]; then
            cleanup_rc="$rc"
        fi

        SESSION_RECEIVER_CREATED="NO"
    fi

    return "$cleanup_rc"
}

handle_signal()
{
    local exit_code="$1"
    local cleanup_rc

    trap - INT TERM

    cleanup_session
    cleanup_rc=$?

    trap - EXIT

    if [ "$cleanup_rc" -ne 0 ]; then
        exit 70
    fi

    exit "$exit_code"
}

run_session_body()
{
    local receiver_name="$1"
    local duration_s="$2"
    local raw_output="$3"
    local timestamp_output="$4"
    local stderr_output="$5"
    local rc
    local capture_exit_code

    require_live_enable ||
        return $?
    validate_runtime ||
        return $?
    prepare_outputs \
        "$raw_output" \
        "$timestamp_output" \
        "$stderr_output" ||
        return $?

    "$TRAFFIC_ADAPTER" create-receiver "$receiver_name"
    rc=$?

    if [ "$rc" -ne 0 ]; then
        return "$rc"
    fi

    SESSION_RECEIVER_NAME="$receiver_name"
    SESSION_RECEIVER_CREATED="YES"

    sci_oran_process_start \
        "$SESSION_CONTROL_STDOUT" \
        "$SESSION_CONTROL_STDERR" \
        "$TRAFFIC_ADAPTER" \
        capture-receiver \
        "$receiver_name" \
        "$raw_output" \
        "$timestamp_output" \
        "$stderr_output" ||
        return $?

    SESSION_CAPTURE_PID="$SCI_ORAN_LAST_PID"

    "$TRAFFIC_ADAPTER" \
        wait-receiver-ready \
        "$receiver_name" \
        "$timestamp_output"
    rc=$?

    if [ "$rc" -ne 0 ]; then
        return "$rc"
    fi

    if ! sci_oran_process_is_running "$SESSION_CAPTURE_PID"; then
        sci_oran_process_capture_wait "$SESSION_CAPTURE_PID"
        SESSION_CAPTURE_PID=""
        return 76
    fi

    "$TRAFFIC_ADAPTER" run-client "$duration_s"
    rc=$?

    if [ "$rc" -ne 0 ]; then
        return "$rc"
    fi

    sci_oran_process_capture_wait "$SESSION_CAPTURE_PID" ||
        return $?

    capture_exit_code="$SCI_ORAN_LAST_EXIT_CODE"
    SESSION_CAPTURE_PID=""

    if [ "$capture_exit_code" -ne 0 ]; then
        return 70
    fi

    [[ -f "$raw_output" ]] ||
        return 66
    [[ -f "$timestamp_output" ]] ||
        return 66
    [[ -f "$stderr_output" ]] ||
        return 66

    return 0
}

show_contract()
{
    echo "PROMPT12_BOUNDED_TRAFFIC_SESSION_CONTRACT=1"
    echo "TRAFFIC_COMMAND_FORM=ARGV_ARRAY"
    echo "FULL_SESSION_ENTRY_POINT=run"
    echo "LIVE_ENABLE_ENV=SCI_ORAN_PROMPT12_LIVE_TRAFFIC_ENABLE"
    echo "RECEIVER_OWNERSHIP=CREATE_AND_REMOVE_IF_CREATED"
    echo "CAPTURE_PROCESS_OWNERSHIP=LOCAL_CHILD_PID"
    echo "SIGNAL_HANDLING=SIGINT_AND_SIGTERM"
    echo "SHELL_STRING_EXECUTION_ALLOWED=NO"
    echo "CONTROL_EXECUTED=NO"
}

show_plan()
{
    local receiver_name="$1"
    local duration_s="$2"
    local raw_output="$3"
    local timestamp_output="$4"
    local stderr_output="$5"
    local script_path

    script_path="${SESSION_ADAPTER_DIR}/$(basename -- "$0")"

    echo "PROMPT12_BOUNDED_TRAFFIC_SESSION_PLAN=1"
    echo "TRAFFIC_COMMAND_ARGC=7"
    echo "TRAFFIC_COMMAND_ARG_0=$script_path"
    echo "TRAFFIC_COMMAND_ARG_1=run"
    echo "TRAFFIC_COMMAND_ARG_2=$receiver_name"
    echo "TRAFFIC_COMMAND_ARG_3=$duration_s"
    echo "TRAFFIC_COMMAND_ARG_4=$raw_output"
    echo "TRAFFIC_COMMAND_ARG_5=$timestamp_output"
    echo "TRAFFIC_COMMAND_ARG_6=$stderr_output"
    echo "CONTROL_EXECUTED=NO"
}

main()
{
    local mode="${1:-}"
    local run_rc
    local cleanup_rc

    case "$mode" in
        contract)
            [ "$#" -eq 1 ] ||
                fail "contract takes no arguments"
            show_contract
            ;;

        plan)
            [ "$#" -eq 6 ] ||
                fail "plan requires five arguments"
            shift

            validate_common_arguments "$@" ||
                fail "plan arguments are invalid"

            show_plan "$@"
            ;;

        run)
            [ "$#" -eq 6 ] ||
                fail "run requires five arguments"
            shift

            validate_common_arguments "$@" ||
                fail "run arguments are invalid"

            SESSION_RECEIVER_NAME="$1"
            SESSION_RECEIVER_CREATED="NO"
            SESSION_CAPTURE_PID=""
            SESSION_CLEANUP_DONE="NO"

            trap 'cleanup_session >/dev/null 2>&1 || true' EXIT
            trap 'handle_signal 130' INT
            trap 'handle_signal 143' TERM

            run_session_body "$@"
            run_rc=$?

            cleanup_session
            cleanup_rc=$?

            trap - EXIT INT TERM

            if [ "$run_rc" -ne 0 ]; then
                echo "PROMPT12_TRAFFIC_SESSION_GATE=FAIL" >&2
                echo "FAIL_REASON=SESSION_BODY_RC_${run_rc}" >&2
                return "$run_rc"
            fi

            if [ "$cleanup_rc" -ne 0 ]; then
                echo "PROMPT12_TRAFFIC_SESSION_GATE=FAIL" >&2
                echo "FAIL_REASON=SESSION_CLEANUP_RC_${cleanup_rc}" >&2
                return 70
            fi

            echo "PROMPT12_TRAFFIC_SESSION_GATE=PASS"
            echo "RECEIVER_CONTAINER_REMOVED=YES"
            echo "CONTROL_EXECUTED=NO"
            ;;

        *)
            usage >&2
            return 64
            ;;
    esac
}

main "$@"
