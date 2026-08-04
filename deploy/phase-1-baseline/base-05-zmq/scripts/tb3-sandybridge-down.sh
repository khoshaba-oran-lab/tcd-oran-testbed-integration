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

failure()
{
    rc=$?

    echo
    echo "[FAIL] Tb3 Sandy Bridge shutdown: line=$LINENO rc=$rc command=$BASH_COMMAND" >&2

    docker compose \
        -f "$COMPOSE_FILE" \
        -f "$OVERRIDE_FILE" \
        ps -a >&2 || true

    exit "$rc"
}
trap failure ERR

cd "$BASE_DIR"

test -f "$COMPOSE_FILE"
test -f "$OVERRIDE_FILE"

echo "=== TB3 SANDY BRIDGE SHUTDOWN ==="

echo
echo "=== 1. STOP SRSUE ==="

docker compose \
    -f "$COMPOSE_FILE" \
    -f "$OVERRIDE_FILE" \
    stop \
    --timeout 15 \
    srsue

echo "SRSUE_STOP=PASS"

echo
echo "=== 2. STOP GNB ==="

docker compose \
    -f "$COMPOSE_FILE" \
    -f "$OVERRIDE_FILE" \
    stop \
    --timeout 15 \
    gnb

echo "GNB_STOP=PASS"

echo
echo "=== 3. STOP 5GC ==="

docker compose \
    -f "$COMPOSE_FILE" \
    -f "$OVERRIDE_FILE" \
    stop \
    --timeout 30 \
    5gc

echo "FIVE_GC_STOP=PASS"

echo
echo "=== 4. REMOVE CONTAINERS AND COMPOSE NETWORK ==="

docker compose \
    -f "$COMPOSE_FILE" \
    -f "$OVERRIDE_FILE" \
    down \
    --remove-orphans

echo "COMPOSE_DOWN=PASS"

echo
echo "=== 5. VERIFY SHUTDOWN ==="

for SERVICE in 5gc gnb srsue
do
    CID="$(
        docker compose \
            -f "$COMPOSE_FILE" \
            -f "$OVERRIDE_FILE" \
            ps -aq "$SERVICE"
    )"

    test -z "$CID"

    echo "SERVICE_${SERVICE}_CONTAINER=absent"
done

echo
echo "TB3_SANDYBRIDGE_DOWN=PASS"
echo "CONTAINERS_REMOVED=yes"
echo "COMPOSE_NETWORK_REMOVED=yes"
echo "DOCKER_IMAGES_REMOVED=no"
echo "DOCKER_VOLUMES_REMOVED=no"
