#!/usr/bin/env bash
set -euo pipefail

PROMPT12_TRAFFIC_CONTRACT_VERSION="1"

PROMPT12_TOOLBOX_IMAGE_ID="sha256:2f60d32db88bb07cfc8af06830fe5e25b3183c107591ce5044e1711eb28b0adb"

PROMPT12_CORE_CONTAINER="base05_open5gs_5gc"
PROMPT12_UE_CONTAINER="base05_srsran_srsue"

PROMPT12_SOURCE_IP="10.45.1.1"
PROMPT12_RECEIVER_IP="10.45.1.2"

PROMPT12_IPERF_PORT="5201"
PROMPT12_OFFERED_RATE="18M"
PROMPT12_PRIMARY_INTERVAL_S="0.2"

PROMPT12_RECEIVER_READY_TIMEOUT_MS="5000"
PROMPT12_RECEIVER_READY_POLL_S="0.02"
PROMPT12_RECEIVER_READY_MARKER="Server listening on 5201"

PROMPT12_CAPTURE_SCRIPT="scripts/experiment-harness/capture-iperf-receiver.py"

usage()
{
    cat <<'USAGE'
Usage:

  prompt12-siso-traffic.sh contract

  prompt12-siso-traffic.sh plan \
      <receiver-container-name> \
      <run-duration-s> \
      <raw-output> \
      <timestamp-output> \
      <stderr-output>

  prompt12-siso-traffic.sh create-receiver \
      <receiver-container-name>

  prompt12-siso-traffic.sh capture-receiver \
      <receiver-container-name> \
      <raw-output> \
      <timestamp-output> \
      <stderr-output>

  prompt12-siso-traffic.sh wait-receiver-ready \
      <receiver-container-name> \
      <timestamp-output>

  prompt12-siso-traffic.sh run-client \
      <run-duration-s>

Safety:

  plan and contract never execute Docker or iperf3.

  Live subcommands require:

    SCI_ORAN_PROMPT12_LIVE_TRAFFIC_ENABLE=YES

  Without that exact value they fail closed before Docker execution.
USAGE
}

fail()
{
    printf 'ERROR=%s\n' "$*" >&2
    exit 64
}

require_live_enable()
{
    if [ "${SCI_ORAN_PROMPT12_LIVE_TRAFFIC_ENABLE:-NO}" != "YES" ]; then
        echo "PROMPT12_LIVE_TRAFFIC_INTERLOCK=BLOCKED" >&2
        echo "REQUIRED_ENV=SCI_ORAN_PROMPT12_LIVE_TRAFFIC_ENABLE=YES" >&2
        exit 77
    fi
}

validate_receiver_name()
{
    local value="$1"

    [[ "$value" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]*$ ]] || \
        fail "invalid receiver container name"
}

validate_duration()
{
    local value="$1"

    [[ "$value" =~ ^[1-9][0-9]*$ ]] || \
        fail "run duration must be a positive integer number of seconds"
}

validate_output_path()
{
    local value="$1"

    [ -n "$value" ] || fail "output path must not be empty"
}

print_cmd()
{
    local label="$1"
    shift

    printf '%s=' "$label"
    printf ' %q' "$@"
    printf '\n'
}

receiver_create_argv()
{
    RECEIVER_CREATE_ARGV=(
        docker
        create
        --name "$1"
        --network "container:${PROMPT12_UE_CONTAINER}"
        --restart no
        "$PROMPT12_TOOLBOX_IMAGE_ID"
        iperf3
        -s
        -1
        -B "$PROMPT12_RECEIVER_IP"
        -p "$PROMPT12_IPERF_PORT"
        -i "$PROMPT12_PRIMARY_INTERVAL_S"
        --forceflush
    )
}

receiver_capture_argv()
{
    RECEIVER_CAPTURE_ARGV=(
        python3
        "$PROMPT12_CAPTURE_SCRIPT"
        --raw-output "$2"
        --timestamp-output "$3"
        --stderr-output "$4"
        --
        docker
        start
        -a
        "$1"
    )
}

client_argv()
{
    CLIENT_ARGV=(
        docker
        exec
        "$PROMPT12_CORE_CONTAINER"
        /usr/bin/iperf3
        -c "$PROMPT12_RECEIVER_IP"
        -B "$PROMPT12_SOURCE_IP"
        -u
        -b "$PROMPT12_OFFERED_RATE"
        -i "$PROMPT12_PRIMARY_INTERVAL_S"
        -t "$1"
        --forceflush
    )
}

wait_receiver_ready()
{
    local receiver_name="$1"
    local timestamp_output="$2"
    local start_ns
    local now_ns
    local elapsed_ms
    local state_line
    local running
    local status
    local ready_record

    validate_receiver_name "$receiver_name"
    validate_output_path "$timestamp_output"
    require_live_enable

    start_ns="$(date -u '+%s%N')"

    while true; do
        if ! state_line="$(
            docker inspect \
                -f '{{.State.Running}} {{.State.Status}}' \
                "$receiver_name" \
                2>/dev/null
        )"
        then
            echo "PROMPT12_RECEIVER_READY_GATE=FAIL" >&2
            echo "REASON=RECEIVER_CONTAINER_NOT_FOUND" >&2
            exit 78
        fi

        running="${state_line%% *}"
        status="${state_line#* }"

        if [ "$running" = "true" ]; then
            if [ -s "$timestamp_output" ] && \
               grep -Fq \
                   "\"line_utf8\":\"${PROMPT12_RECEIVER_READY_MARKER}\"" \
                   "$timestamp_output"
            then
                ready_record="$(
                    python3 - \
                        "$timestamp_output" \
                        "$PROMPT12_RECEIVER_READY_MARKER" <<'PY_READY'
import json
import sys

path = sys.argv[1]
marker = sys.argv[2]

with open(path, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()

        if not line:
            continue

        row = json.loads(line)

        if row.get("line_utf8") == marker:
            sequence = row.get("sequence")
            wall = row.get("rx_wall_ns")
            mono = row.get("rx_mono_ns")

            if not isinstance(sequence, int):
                raise SystemExit("invalid readiness sequence")

            if not isinstance(wall, int) or wall <= 0:
                raise SystemExit("invalid readiness rx_wall_ns")

            if not isinstance(mono, int) or mono <= 0:
                raise SystemExit("invalid readiness rx_mono_ns")

            print(f"{sequence} {wall} {mono}")
            raise SystemExit(0)

raise SystemExit(1)
PY_READY
                )"

                set -- $ready_record

                echo "PROMPT12_RECEIVER_READY_GATE=PASS"
                echo "RECEIVER_CONTAINER=$receiver_name"
                echo "RECEIVER_READY_SOURCE=TIMESTAMPED_RECEIVER_CAPTURE"
                echo "RECEIVER_READY_MARKER=SERVER_LISTENING_ON_5201"
                echo "RECEIVER_STATE_SNAPSHOT_RUNNING=true"
                echo "RECEIVER_STATE_SNAPSHOT_STATUS=$status"
                echo "RECEIVER_READY_SEQUENCE=$1"
                echo "RECEIVER_READY_RX_WALL_NS=$2"
                echo "RECEIVER_READY_RX_MONO_NS=$3"

                return 0
            fi
        else
            case "$status" in
                created|running)
                    # docker start -a is allowed to transition the receiver
                    # from created to running while this gate is polling.
                    # This is a transient pre-ready state, not a failure.
                    ;;
                *)
                    echo "PROMPT12_RECEIVER_READY_GATE=FAIL" >&2
                    echo "REASON=RECEIVER_NOT_RUNNING" >&2
                    echo "RECEIVER_RUNNING=$running" >&2
                    echo "RECEIVER_STATUS=$status" >&2
                    exit 78
                    ;;
            esac
        fi

        now_ns="$(date -u '+%s%N')"
        elapsed_ms=$(( (now_ns - start_ns) / 1000000 ))

        if [ "$elapsed_ms" -ge "$PROMPT12_RECEIVER_READY_TIMEOUT_MS" ]; then
            echo "PROMPT12_RECEIVER_READY_GATE=FAIL" >&2
            echo "REASON=TIMESTAMPED_READY_MARKER_TIMEOUT" >&2
            echo "RECEIVER_RUNNING=$running" >&2
            echo "RECEIVER_STATUS=$status" >&2
            echo "READY_TIMEOUT_MS=$PROMPT12_RECEIVER_READY_TIMEOUT_MS" >&2
            exit 78
        fi

        sleep "$PROMPT12_RECEIVER_READY_POLL_S"
    done
}

show_contract()
{
    cat <<EOF_CONTRACT
PROMPT12_TRAFFIC_CONTRACT_VERSION=$PROMPT12_TRAFFIC_CONTRACT_VERSION

TRAFFIC_PROTOCOL=UDP
TRAFFIC_DIRECTION=DOWNLINK
REVERSE_MODE=NO

SENDER_CONTAINER=$PROMPT12_CORE_CONTAINER
SENDER_ROLE=IPERF3_CLIENT
SENDER_BIND_IP=$PROMPT12_SOURCE_IP

RECEIVER_NAMESPACE_TARGET=$PROMPT12_UE_CONTAINER
RECEIVER_ROLE=IPERF3_SERVER
RECEIVER_BIND_IP=$PROMPT12_RECEIVER_IP

TOOLBOX_IMAGE_ID=$PROMPT12_TOOLBOX_IMAGE_ID

IPERF_PORT=$PROMPT12_IPERF_PORT
OFFERED_RATE=$PROMPT12_OFFERED_RATE
PRIMARY_OUTPUT_INTERVAL_S=$PROMPT12_PRIMARY_INTERVAL_S

FIXED_SIZE_TRANSFER_ALLOWED=NO
IPERF_REVERSE_ALLOWED=NO
IPERF_BYTES_ALLOWED=NO
IPERF_BLOCKCOUNT_ALLOWED=NO

RECEIVER_RESTART_POLICY=no
RECEIVER_AUTO_REMOVE=NO

ONE_TRAFFIC_STREAM_PER_RUN=YES
TRAFFIC_CONTINUOUS_ACROSS_T1_T6=YES

PRIMARY_OUTPUT_SOURCE=UE_SIDE_IPERF3_SERVER_STDOUT
PRIMARY_OUTPUT_FIELD=throughput_kbit_s

RECEIVER_READY_GATE_REQUIRED_BEFORE_CLIENT=YES
RECEIVER_READY_GATE_SOURCE=TIMESTAMPED_RECEIVER_CAPTURE
RECEIVER_READY_MARKER=SERVER_LISTENING_ON_5201
RECEIVER_READY_TIMEOUT_MS=$PROMPT12_RECEIVER_READY_TIMEOUT_MS
DOCKER_RUNNING_ALONE_SUFFICIENT_RECEIVER_READINESS=NO
RECEIVER_STATE_SNAPSHOT_MODE=SINGLE_DOCKER_INSPECT
RECEIVER_CREATED_STATE_TREATED_AS_TRANSIENT=YES
EOF_CONTRACT
}

case "${1:-}" in
    contract)
        [ "$#" -eq 1 ] || fail "contract takes no arguments"
        show_contract
        ;;

    plan)
        [ "$#" -eq 6 ] || fail "plan requires 5 arguments"

        receiver_name="$2"
        duration_s="$3"
        raw_output="$4"
        timestamp_output="$5"
        stderr_output="$6"

        validate_receiver_name "$receiver_name"
        validate_duration "$duration_s"
        validate_output_path "$raw_output"
        validate_output_path "$timestamp_output"
        validate_output_path "$stderr_output"

        receiver_create_argv "$receiver_name"

        receiver_capture_argv \
            "$receiver_name" \
            "$raw_output" \
            "$timestamp_output" \
            "$stderr_output"

        client_argv "$duration_s"

        echo "PROMPT12_TRAFFIC_PLAN_EXECUTION=NO"
        echo "PROMPT12_TRAFFIC_PLAN_BEGIN"

        print_cmd \
            RECEIVER_CREATE_CMD \
            "${RECEIVER_CREATE_ARGV[@]}"

        print_cmd \
            RECEIVER_CAPTURE_CMD \
            "${RECEIVER_CAPTURE_ARGV[@]}"

        print_cmd \
            CLIENT_CMD \
            "${CLIENT_ARGV[@]}"

        echo "PROMPT12_TRAFFIC_PLAN_END"
        ;;

    create-receiver)
        [ "$#" -eq 2 ] || fail "create-receiver requires container name"

        validate_receiver_name "$2"
        require_live_enable

        receiver_create_argv "$2"

        exec "${RECEIVER_CREATE_ARGV[@]}"
        ;;

    capture-receiver)
        [ "$#" -eq 5 ] || fail "capture-receiver requires 4 arguments"

        validate_receiver_name "$2"
        validate_output_path "$3"
        validate_output_path "$4"
        validate_output_path "$5"
        require_live_enable

        receiver_capture_argv "$2" "$3" "$4" "$5"

        exec "${RECEIVER_CAPTURE_ARGV[@]}"
        ;;

    wait-receiver-ready)
        [ "$#" -eq 3 ] || \
            fail "wait-receiver-ready requires receiver name and timestamp output"

        wait_receiver_ready "$2" "$3"
        ;;

    run-client)
        [ "$#" -eq 2 ] || fail "run-client requires duration"

        validate_duration "$2"
        require_live_enable

        client_argv "$2"

        exec "${CLIENT_ARGV[@]}"
        ;;

    -h|--help|help)
        usage
        ;;

    *)
        usage >&2
        exit 64
        ;;
esac
