#!/usr/bin/env bash

set -Eeuo pipefail
export LC_ALL=C

SCRIPT_DIR="$(
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &&
    pwd -P
)"

BASE_DIR="$(
    cd -- "$SCRIPT_DIR/.." &&
    pwd -P
)"

COMPOSE_FILE="$BASE_DIR/compose.runtime.yml"
OVERRIDE_FILE="$BASE_DIR/compose.sandybridge.yml"
OPEN5GS_ENV="$BASE_DIR/configs/open5gs.env"

failure()
{
    rc=$?

    echo
    echo "[FAIL] Tb3 Sandy Bridge startup: line=$LINENO rc=$rc command=$BASH_COMMAND" >&2

    echo
    echo "=== SERVICE STATUS ===" >&2

    docker compose \
        -f "$COMPOSE_FILE" \
        -f "$OVERRIDE_FILE" \
        ps -a >&2 || true

    echo
    echo "=== RECENT LOGS ===" >&2

    docker compose \
        -f "$COMPOSE_FILE" \
        -f "$OVERRIDE_FILE" \
        logs \
        --no-color \
        --tail 60 \
        5gc gnb srsue >&2 || true

    exit "$rc"
}
trap failure ERR

compose()
{
    docker compose \
        -f "$COMPOSE_FILE" \
        -f "$OVERRIDE_FILE" \
        "$@"
}

service_cid()
{
    local service="$1"

    compose ps -q "$service"
}

wait_running()
{
    local service="$1"
    local timeout_seconds="$2"

    local cid=""
    local state=""
    local elapsed=0

    while test "$elapsed" -lt "$timeout_seconds"
    do
        cid="$(service_cid "$service")"

        if test -n "$cid"; then
            state="$(
                docker inspect \
                    --format '{{.State.Status}}' \
                    "$cid"
            )"

            if test "$state" = "running"; then
                echo "SERVICE_${service}_STATE=running"
                return 0
            fi

            if test "$state" = "exited" || test "$state" = "dead"; then
                echo "SERVICE_${service}_STATE=$state" >&2
                return 1
            fi
        fi

        sleep 2
        elapsed=$((elapsed + 2))
    done

    echo "SERVICE_${service}_RUNNING_TIMEOUT=yes" >&2
    return 1
}

wait_healthy()
{
    local service="$1"
    local timeout_seconds="$2"

    local cid=""
    local state=""
    local health=""
    local elapsed=0

    while test "$elapsed" -lt "$timeout_seconds"
    do
        cid="$(service_cid "$service")"

        if test -n "$cid"; then
            state="$(
                docker inspect \
                    --format '{{.State.Status}}' \
                    "$cid"
            )"

            health="$(
                docker inspect \
                    --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}not-configured{{end}}' \
                    "$cid"
            )"

            if test "$state" = "running" && test "$health" = "healthy"; then
                echo "SERVICE_${service}_STATE=running"
                echo "SERVICE_${service}_HEALTH=healthy"
                return 0
            fi

            if test "$state" = "exited" || test "$state" = "dead"; then
                echo "SERVICE_${service}_STATE=$state" >&2
                return 1
            fi
        fi

        sleep 2
        elapsed=$((elapsed + 2))
    done

    echo "SERVICE_${service}_HEALTH_TIMEOUT=yes" >&2
    return 1
}

wait_ue_tunnel()
{
    local timeout_seconds="$1"

    local cid=""
    local ue_cidr=""
    local elapsed=0

    while test "$elapsed" -lt "$timeout_seconds"
    do
        cid="$(service_cid srsue)"

        if test -n "$cid"; then
            ue_cidr="$(
                docker exec "$cid" sh -c \
                    "ip -o -4 addr show dev tun_srsue 2>/dev/null | awk '{print \$4; exit}'" \
                    2>/dev/null ||
                true
            )"

            if test -n "$ue_cidr"; then
                echo "UE_TUNNEL=tun_srsue"
                echo "UE_CIDR=$ue_cidr"
                return 0
            fi
        fi

        sleep 2
        elapsed=$((elapsed + 2))
    done

    echo "UE_TUNNEL_TIMEOUT=yes" >&2
    return 1
}

cd "$BASE_DIR"

test -f "$COMPOSE_FILE"
test -f "$OVERRIDE_FILE"
test -f "$OPEN5GS_ENV"

docker version >/dev/null
compose config --quiet

echo "=== TB3 SANDY BRIDGE STARTUP ==="

echo
echo "=== 1. START 5GC ==="

compose up \
    -d \
    --no-build \
    --no-deps \
    5gc

wait_healthy 5gc 120

echo "FIVE_GC_START=PASS"

echo
echo "=== 2. START GNB ==="

compose up \
    -d \
    --no-build \
    --no-deps \
    gnb

wait_running gnb 30

sleep 5

echo "GNB_START=PASS"

echo
echo "=== 3. START SRSUE ==="

compose up \
    -d \
    --no-build \
    --no-deps \
    srsue

wait_running srsue 30
wait_ue_tunnel 120

echo "SRSUE_START=PASS"
echo "UE_REGISTRATION_GATE=PASS"

echo
echo "=== 4. FINAL STATUS ==="

compose ps -a

echo
echo "TB3_SANDYBRIDGE_UP=PASS"
echo "RADIO_START_ORDER=5gc_then_gnb_then_srsue"
echo "UE_REGISTRATION_GATE=PASS"
