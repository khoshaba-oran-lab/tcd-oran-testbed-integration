#!/usr/bin/env bash
set -euo pipefail

PIPELINE_VERSION="1"

TRAFFIC_ADAPTER="scripts/experiment-harness/adapters/prompt12-siso-traffic.sh"
PARSE_SCRIPT="scripts/experiment-harness/parse-iperf-receiver.py"
CANON_SCRIPT="scripts/experiment-harness/canonicalize-iperf-receiver.py"
SCHEMA="datasets/schemas/sci-oran-prompt12-siso-v1.0.0.schema.json"

usage()
{
    cat <<'USAGE'
Usage:

  prompt12-receiver-pipeline.sh contract

  prompt12-receiver-pipeline.sh plan \
      <experiment-id> \
      <run-id> \
      <receiver-container-name> \
      <run-duration-s> \
      <run-dir>

  prompt12-receiver-pipeline.sh process-no-transition \
      <experiment-id> \
      <run-id> \
      <run-dir>

  prompt12-receiver-pipeline.sh plan-actuator-transitions \
      <experiment-id> \
      <run-id> \
      <run-dir> \
      <actuator-timeline>

  prompt12-receiver-pipeline.sh process-actuator-transitions \
      <experiment-id> \
      <run-id> \
      <run-dir> \
      <actuator-timeline>

Scope:

  This runner integrates the Prompt-12 receiver measurement pipeline.

  plan:
    prints the complete traffic acquisition and processing plan;
    executes no Docker command and no iperf3 workload.

  process-no-transition:
    processes already-acquired receiver evidence only;
    executes no Docker command and no iperf3 workload.

Transition-aware processing:

  process-no-transition:
    processes evidence containing no actuator transition.

  plan-actuator-transitions:
    prints the transition-aware offline processing plan only;
    executes no parser, Docker command, iperf3 workload or E2 control.

  process-actuator-transitions:
    processes already-acquired receiver evidence;
    requires an existing actuator timeline;
    calls transition-aware canonicalization;
    executes no Docker command, iperf3 workload or E2 control.

  Live traffic execution remains unsupported by this runner.
USAGE
}

fail()
{
    printf 'ERROR=%s\n' "$*" >&2
    exit 64
}

validate_experiment_id()
{
    local value="$1"

    [[ "$value" =~ ^EXP-[0-9]{8}-DL-18000K-R0[1-4]$ ]] || \
        fail "invalid Prompt-12 experiment ID"
}

validate_run_id()
{
    local value="$1"

    [[ "$value" =~ ^RUN-[0-9]{8}T[0-9]{6}Z-[0-9]{3}$ ]] || \
        fail "invalid Prompt-12 run ID"
}

validate_duration()
{
    local value="$1"

    [[ "$value" =~ ^[1-9][0-9]*$ ]] || \
        fail "run duration must be a positive integer"
}

validate_receiver_name()
{
    local value="$1"

    [[ "$value" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]*$ ]] || \
        fail "invalid receiver container name"
}

validate_run_dir()
{
    local value="$1"

    [ -n "$value" ] || fail "run directory must not be empty"
}

validate_actuator_timeline_arg()
{
    local value="$1"

    [ -n "$value" ] || fail "actuator timeline path must not be empty"
}

paths_for_run()
{
    local run_dir="$1"

    RAW_OUTPUT="${run_dir}/raw/iperf3-receiver.stdout.log"
    TIMESTAMP_OUTPUT="${run_dir}/raw/iperf3-receiver.timestamps.jsonl"
    STDERR_OUTPUT="${run_dir}/raw/iperf3-receiver.stderr.log"

    STAGING_OUTPUT="${run_dir}/processed/iperf3-receiver.intervals.staging.jsonl"
    CANONICAL_OUTPUT="${run_dir}/processed/iperf3-receiver.intervals.canonical.jsonl"
}

print_cmd()
{
    local label="$1"
    shift

    printf '%s=' "$label"
    printf ' %q' "$@"
    printf '\n'
}

show_contract()
{
    cat <<EOF_CONTRACT
PROMPT12_RECEIVER_PIPELINE_VERSION=$PIPELINE_VERSION

TRAFFIC_ADAPTER=$TRAFFIC_ADAPTER
PARSE_SCRIPT=$PARSE_SCRIPT
CANONICALIZER_SCRIPT=$CANON_SCRIPT
SCHEMA=$SCHEMA

PRIMARY_SOURCE=UE_SIDE_IPERF3_SERVER_STDOUT
PRIMARY_OUTPUT_FIELD=throughput_kbit_s
PRIMARY_OUTPUT_INTERVAL_S=0.2

RUN_ID_SEMANTICS=EXECUTION_ATTEMPT_ID
RUN_ID_PATTERN=RUN-YYYYMMDDTHHMMSSZ-NNN
REPEAT_ID_SEMANTICS=EXPERIMENT_ID_SUFFIX_R01_R04

RAW_STDOUT_FILE=raw/iperf3-receiver.stdout.log
RAW_TIMESTAMP_FILE=raw/iperf3-receiver.timestamps.jsonl
RAW_STDERR_FILE=raw/iperf3-receiver.stderr.log

STAGING_FILE=processed/iperf3-receiver.intervals.staging.jsonl
CANONICAL_FILE=processed/iperf3-receiver.intervals.canonical.jsonl

RAW_TIMESTAMP_REWRITE_ALLOWED=NO
RAW_CONTENT_REWRITE_ALLOWED=NO

SUPPORTED_CLASSIFICATION_SCOPES=no-actuator-transitions,actuator-transitions
TRANSITION_AWARE_CANONICALIZATION_READY=YES
ACTUATOR_TIMELINE_REQUIRED_FOR_TRANSITION_SCOPE=YES
TRANSITION_PROCESSING_PLAN_SUBCOMMAND=plan-actuator-transitions
TRANSITION_PROCESSING_SUBCOMMAND=process-actuator-transitions

LIVE_TRAFFIC_EXECUTION_SUPPORTED_BY_THIS_RUNNER=NO
EOF_CONTRACT
}

case "${1:-}" in
    contract)
        [ "$#" -eq 1 ] || fail "contract takes no arguments"
        show_contract
        ;;

    plan)
        [ "$#" -eq 6 ] || fail "plan requires 5 arguments"

        experiment_id="$2"
        run_id="$3"
        receiver_name="$4"
        duration_s="$5"
        run_dir="$6"

        validate_experiment_id "$experiment_id"
        validate_run_id "$run_id"
        validate_receiver_name "$receiver_name"
        validate_duration "$duration_s"
        validate_run_dir "$run_dir"

        paths_for_run "$run_dir"

        echo "PROMPT12_RECEIVER_PIPELINE_PLAN_EXECUTION=NO"
        echo "PROMPT12_RECEIVER_PIPELINE_PLAN_BEGIN"

        "$TRAFFIC_ADAPTER" plan \
            "$receiver_name" \
            "$duration_s" \
            "$RAW_OUTPUT" \
            "$TIMESTAMP_OUTPUT" \
            "$STDERR_OUTPUT"

        print_cmd \
            PARSE_CMD \
            env \
            PYTHONDONTWRITEBYTECODE=1 \
            python3 \
            "$PARSE_SCRIPT" \
            --raw-input "$RAW_OUTPUT" \
            --timestamp-input "$TIMESTAMP_OUTPUT" \
            --output "$STAGING_OUTPUT"

        print_cmd \
            CANONICALIZE_CMD \
            env \
            PYTHONDONTWRITEBYTECODE=1 \
            python3 \
            "$CANON_SCRIPT" \
            --input "$STAGING_OUTPUT" \
            --output "$CANONICAL_OUTPUT" \
            --schema "$SCHEMA" \
            --experiment-id "$experiment_id" \
            --run-id "$run_id" \
            --classification-scope no-actuator-transitions

        echo "PROMPT12_RECEIVER_PIPELINE_PLAN_END"
        ;;

    plan-actuator-transitions)
        [ "$#" -eq 5 ] || \
            fail "plan-actuator-transitions requires 4 arguments"

        experiment_id="$2"
        run_id="$3"
        run_dir="$4"
        actuator_timeline="$5"

        validate_experiment_id "$experiment_id"
        validate_run_id "$run_id"
        validate_run_dir "$run_dir"
        validate_actuator_timeline_arg "$actuator_timeline"

        paths_for_run "$run_dir"

        echo "PROMPT12_TRANSITION_PIPELINE_PLAN_EXECUTION=NO"
        echo "PROMPT12_TRANSITION_PIPELINE_PLAN_BEGIN"

        print_cmd \
            PARSE_CMD \
            env \
            PYTHONDONTWRITEBYTECODE=1 \
            python3 \
            "$PARSE_SCRIPT" \
            --raw-input "$RAW_OUTPUT" \
            --timestamp-input "$TIMESTAMP_OUTPUT" \
            --output "$STAGING_OUTPUT"

        print_cmd \
            CANONICALIZE_CMD \
            env \
            PYTHONDONTWRITEBYTECODE=1 \
            python3 \
            "$CANON_SCRIPT" \
            --input "$STAGING_OUTPUT" \
            --output "$CANONICAL_OUTPUT" \
            --schema "$SCHEMA" \
            --experiment-id "$experiment_id" \
            --run-id "$run_id" \
            --classification-scope actuator-transitions \
            --actuator-timeline "$actuator_timeline"

        echo "CLASSIFICATION_SCOPE=actuator-transitions"
        echo "ACTUATOR_TIMELINE=$actuator_timeline"
        echo "DOCKER_EXECUTION=NO"
        echo "IPERF3_EXECUTION=NO"
        echo "E2_CONTROL_EXECUTION=NO"

        echo "PROMPT12_TRANSITION_PIPELINE_PLAN_END"
        ;;

    process-actuator-transitions)
        [ "$#" -eq 5 ] || \
            fail "process-actuator-transitions requires 4 arguments"

        experiment_id="$2"
        run_id="$3"
        run_dir="$4"
        actuator_timeline="$5"

        validate_experiment_id "$experiment_id"
        validate_run_id "$run_id"
        validate_run_dir "$run_dir"
        validate_actuator_timeline_arg "$actuator_timeline"

        paths_for_run "$run_dir"

        test -f "$actuator_timeline" || \
            fail "actuator timeline missing"

        test -f "$RAW_OUTPUT" || \
            fail "raw receiver output missing"

        test -f "$TIMESTAMP_OUTPUT" || \
            fail "receiver timestamp input missing"

        mkdir -p "${run_dir}/processed"

        PYTHONDONTWRITEBYTECODE=1 \
        python3 "$PARSE_SCRIPT" \
            --raw-input "$RAW_OUTPUT" \
            --timestamp-input "$TIMESTAMP_OUTPUT" \
            --output "$STAGING_OUTPUT"

        PYTHONDONTWRITEBYTECODE=1 \
        python3 "$CANON_SCRIPT" \
            --input "$STAGING_OUTPUT" \
            --output "$CANONICAL_OUTPUT" \
            --schema "$SCHEMA" \
            --experiment-id "$experiment_id" \
            --run-id "$run_id" \
            --classification-scope actuator-transitions \
            --actuator-timeline "$actuator_timeline"

        echo "PROMPT12_RECEIVER_PIPELINE_PROCESS=PASS"
        echo "CLASSIFICATION_SCOPE=actuator-transitions"
        echo "ACTUATOR_TIMELINE=$actuator_timeline"
        echo "STAGING_OUTPUT=$STAGING_OUTPUT"
        echo "CANONICAL_OUTPUT=$CANONICAL_OUTPUT"
        echo "DOCKER_EXECUTION=NO"
        echo "IPERF3_EXECUTION=NO"
        echo "E2_CONTROL_EXECUTION=NO"
        ;;

    process-no-transition)
        [ "$#" -eq 4 ] || \
            fail "process-no-transition requires 3 arguments"

        experiment_id="$2"
        run_id="$3"
        run_dir="$4"

        validate_experiment_id "$experiment_id"
        validate_run_id "$run_id"
        validate_run_dir "$run_dir"

        paths_for_run "$run_dir"

        test -f "$RAW_OUTPUT" || fail "raw receiver output missing"
        test -f "$TIMESTAMP_OUTPUT" || fail "receiver timestamp input missing"

        mkdir -p "${run_dir}/processed"

        PYTHONDONTWRITEBYTECODE=1 \
        python3 "$PARSE_SCRIPT" \
            --raw-input "$RAW_OUTPUT" \
            --timestamp-input "$TIMESTAMP_OUTPUT" \
            --output "$STAGING_OUTPUT"

        PYTHONDONTWRITEBYTECODE=1 \
        python3 "$CANON_SCRIPT" \
            --input "$STAGING_OUTPUT" \
            --output "$CANONICAL_OUTPUT" \
            --schema "$SCHEMA" \
            --experiment-id "$experiment_id" \
            --run-id "$run_id" \
            --classification-scope no-actuator-transitions

        echo "PROMPT12_RECEIVER_PIPELINE_PROCESS=PASS"
        echo "CLASSIFICATION_SCOPE=no-actuator-transitions"
        echo "STAGING_OUTPUT=$STAGING_OUTPUT"
        echo "CANONICAL_OUTPUT=$CANONICAL_OUTPUT"
        ;;

    -h|--help|help)
        usage
        ;;

    *)
        usage >&2
        exit 64
        ;;
esac
