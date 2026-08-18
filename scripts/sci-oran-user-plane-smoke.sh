#!/usr/bin/env bash
set -uo pipefail

SMOKE_VERSION="1.0.0"

EX_NOT_READY=21
EX_SOFTWARE=22

REPO_ROOT="$(
    cd "$(dirname "${BASH_SOURCE[0]}")/.." &&
    pwd
)"

cd "$REPO_ROOT" || exit "$EX_SOFTWARE"

POLICY="$REPO_ROOT/deploy/phase-2-flexric/tb3-runtime/locks/user-plane-readiness.policy"
BASE_LOCK="$REPO_ROOT/deploy/phase-1-baseline/base-05-zmq/locks/base-05-zmq-runtime.lock"

EXPECTED_TOOLBOX_ID="sha256:2f60d32db88bb07cfc8af06830fe5e25b3183c107591ce5044e1711eb28b0adb"

get_value()
{
    FILE="$1"
    KEY="$2"

    awk -F= -v key="$KEY" '
        $1 == key {
            sub(/^[^=]*=/, "")
            print
            exit
        }
    ' "$FILE"
}

if [ ! -f "$POLICY" ] ||
   [ ! -f "$BASE_LOCK" ]
then
    echo "USER_PLANE_SMOKE_INPUT_CONTRACT_GATE=FAIL"
    exit "$EX_SOFTWARE"
fi

PROJECT="$(get_value "$BASE_LOCK" RUNTIME_PROJECT_NAME)"

TOOLBOX_REF="$(get_value "$POLICY" TRANSIENT_TOOLBOX_IMAGE)"
EXPECTED_UE_INTERFACE="$(get_value "$POLICY" EXPECTED_UE_INTERFACE)"
EXPECTED_UE_PDU_IPV4="$(get_value "$POLICY" EXPECTED_UE_PDU_IPV4)"
EXPECTED_UPF_IPV4="$(get_value "$POLICY" EXPECTED_UPF_IPV4)"
PACKET_COUNT="$(get_value "$POLICY" DIAGNOSTIC_TRAFFIC_PACKET_COUNT)"

for VALUE in \
    "$PROJECT" \
    "$TOOLBOX_REF" \
    "$EXPECTED_UE_INTERFACE" \
    "$EXPECTED_UE_PDU_IPV4" \
    "$EXPECTED_UPF_IPV4" \
    "$PACKET_COUNT"
do
    if [ -z "$VALUE" ]; then
        echo "USER_PLANE_SMOKE_INPUT_CONTRACT_GATE=FAIL"
        exit "$EX_SOFTWARE"
    fi
done

echo "USER_PLANE_SMOKE_INPUT_CONTRACT_GATE=PASS"

UTC_COMPACT="$(date -u '+%Y%m%dT%H%M%SZ')"
UTC_TIMESTAMP="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
SMOKE_ID="UPSMK-${UTC_COMPACT}-$$"

EVIDENCE_ROOT="/tmp/sci-oran/user-plane-smoke"
EVIDENCE_DIR="$EVIDENCE_ROOT/$SMOKE_ID"
SUMMARY_TMP="$EVIDENCE_DIR/summary.env.tmp"
SUMMARY="$EVIDENCE_DIR/summary.env"
LATEST="$EVIDENCE_ROOT/latest.env"

mkdir -p "$EVIDENCE_DIR"

GIT_BRANCH="$(git branch --show-current 2>/dev/null || true)"
GIT_HEAD="$(git rev-parse HEAD 2>/dev/null || true)"

if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
    GIT_WORKTREE="DIRTY"
else
    GIT_WORKTREE="CLEAN"
fi

echo "SCI_ORAN_USER_PLANE_SMOKE_VERSION=$SMOKE_VERSION"
echo "SMOKE_ID=$SMOKE_ID"
echo "UTC_TIMESTAMP=$UTC_TIMESTAMP"
echo "GIT_BRANCH=$GIT_BRANCH"
echo "GIT_HEAD=$GIT_HEAD"
echo "GIT_WORKTREE=$GIT_WORKTREE"

UE="$(
    docker ps \
        --filter "label=com.docker.compose.project=$PROJECT" \
        --filter "label=com.docker.compose.service=srsue" \
        --format '{{.Names}}' |
    head -n 1
)"

GNB="$(
    docker ps \
        --filter "label=com.docker.compose.project=$PROJECT" \
        --filter "label=com.docker.compose.service=gnb" \
        --format '{{.Names}}' |
    head -n 1
)"

CORE="$(
    docker ps \
        --filter "label=com.docker.compose.project=$PROJECT" \
        --filter "label=com.docker.compose.service=5gc" \
        --format '{{.Names}}' |
    head -n 1
)"

RUNTIME_GATE="PASS"

if [ -z "$UE" ] ||
   [ -z "$GNB" ] ||
   [ -z "$CORE" ]
then
    RUNTIME_GATE="FAIL"
fi

echo "UE_CONTAINER=$UE"
echo "GNB_CONTAINER=$GNB"
echo "5GC_CONTAINER=$CORE"
echo "USER_PLANE_RUNTIME_RESOLUTION_GATE=$RUNTIME_GATE"

if [ "$RUNTIME_GATE" != "PASS" ]; then
    {
        echo "SMOKE_ID=$SMOKE_ID"
        echo "UTC_TIMESTAMP=$UTC_TIMESTAMP"
        echo "USER_PLANE_RUNTIME_RESOLUTION_GATE=FAIL"
        echo "USER_PLANE_FUNCTIONAL_SMOKE_GATE=FAIL"
    } > "$SUMMARY_TMP"

    mv "$SUMMARY_TMP" "$SUMMARY"
    cp "$SUMMARY" "$LATEST"

    exit "$EX_NOT_READY"
fi

fingerprint()
{
    docker inspect "$1" \
        --format '{{.State.Pid}}|{{.State.StartedAt}}|{{.RestartCount}}'
}

image_id()
{
    docker inspect "$1" \
        --format '{{.Image}}'
}

UE_FP_BEFORE="$(fingerprint "$UE")"
GNB_FP_BEFORE="$(fingerprint "$GNB")"
CORE_FP_BEFORE="$(fingerprint "$CORE")"

UE_IMAGE_ID="$(image_id "$UE")"
GNB_IMAGE_ID="$(image_id "$GNB")"
CORE_IMAGE_ID="$(image_id "$CORE")"

TOOLBOX_ID="$(
    docker image inspect "$TOOLBOX_REF" \
        --format '{{.Id}}' \
        2>/dev/null || true
)"

if [ "$TOOLBOX_ID" = "$EXPECTED_TOOLBOX_ID" ]; then
    TOOLBOX_IDENTITY_GATE="PASS"
else
    TOOLBOX_IDENTITY_GATE="FAIL"
fi

echo "TOOLBOX_REF=$TOOLBOX_REF"
echo "TOOLBOX_IMAGE_ID=$TOOLBOX_ID"
echo "TOOLBOX_IDENTITY_GATE=$TOOLBOX_IDENTITY_GATE"

TUN_LINK_GATE="FAIL"
PDU_ADDRESS_GATE="FAIL"
ROUTE_GATE="FAIL"
PING_GATE="FAIL"
COUNTER_GATE="FAIL"
CONTINUITY_GATE="FAIL"

if docker exec "$UE" \
    ip -o link show dev "$EXPECTED_UE_INTERFACE" \
    > "$EVIDENCE_DIR/tun-link.txt" 2>&1
then
    TUN_LINK_GATE="PASS"
fi

if docker exec "$UE" \
    ip -o -4 addr show dev "$EXPECTED_UE_INTERFACE" \
    > "$EVIDENCE_DIR/tun-ip.txt" 2>&1 &&
   grep -Eq \
       "inet[[:space:]]+${EXPECTED_UE_PDU_IPV4//./\\.}/24([[:space:]]|$)" \
       "$EVIDENCE_DIR/tun-ip.txt"
then
    PDU_ADDRESS_GATE="PASS"
fi

if docker exec "$UE" \
    ip route get "$EXPECTED_UPF_IPV4" \
    > "$EVIDENCE_DIR/route-to-upf.txt" 2>&1 &&
   grep -Eq \
       "${EXPECTED_UPF_IPV4//./\\.}.*dev[[:space:]]+${EXPECTED_UE_INTERFACE}.*src[[:space:]]+${EXPECTED_UE_PDU_IPV4//./\\.}" \
       "$EVIDENCE_DIR/route-to-upf.txt"
then
    ROUTE_GATE="PASS"
fi

RX_BEFORE="$(
    docker exec "$UE" \
        cat "/sys/class/net/${EXPECTED_UE_INTERFACE}/statistics/rx_packets" \
        2>/dev/null || echo 0
)"

TX_BEFORE="$(
    docker exec "$UE" \
        cat "/sys/class/net/${EXPECTED_UE_INTERFACE}/statistics/tx_packets" \
        2>/dev/null || echo 0
)"

set +e

docker run \
    --rm \
    --network "container:$UE" \
    "$TOOLBOX_REF" \
    ping \
        -n \
        -I "$EXPECTED_UE_INTERFACE" \
        -c "$PACKET_COUNT" \
        -W 2 \
        "$EXPECTED_UPF_IPV4" \
    > "$EVIDENCE_DIR/ping-upf.txt" 2>&1

PING_RC=$?

set -e

if [ "$PING_RC" -eq 0 ] &&
   grep -Eq \
       "${PACKET_COUNT} packets transmitted, ${PACKET_COUNT}( packets)? received, 0% packet loss" \
       "$EVIDENCE_DIR/ping-upf.txt"
then
    PING_GATE="PASS"
fi

RX_AFTER="$(
    docker exec "$UE" \
        cat "/sys/class/net/${EXPECTED_UE_INTERFACE}/statistics/rx_packets" \
        2>/dev/null || echo 0
)"

TX_AFTER="$(
    docker exec "$UE" \
        cat "/sys/class/net/${EXPECTED_UE_INTERFACE}/statistics/tx_packets" \
        2>/dev/null || echo 0
)"

RX_DELTA=$((RX_AFTER - RX_BEFORE))
TX_DELTA=$((TX_AFTER - TX_BEFORE))
TOTAL_DELTA=$((RX_DELTA + TX_DELTA))

if [ "$TOTAL_DELTA" -gt 0 ]; then
    COUNTER_GATE="PASS"
fi

UE_FP_AFTER="$(fingerprint "$UE")"
GNB_FP_AFTER="$(fingerprint "$GNB")"
CORE_FP_AFTER="$(fingerprint "$CORE")"

if [ "$UE_FP_BEFORE" = "$UE_FP_AFTER" ] &&
   [ "$GNB_FP_BEFORE" = "$GNB_FP_AFTER" ] &&
   [ "$CORE_FP_BEFORE" = "$CORE_FP_AFTER" ]
then
    CONTINUITY_GATE="PASS"
fi

if [ "$TUN_LINK_GATE" = "PASS" ] &&
   [ "$PDU_ADDRESS_GATE" = "PASS" ]
then
    INTERFACE_GATE="PASS"
else
    INTERFACE_GATE="FAIL"
fi

FINAL_GATE="PASS"

for VALUE in \
    "$TOOLBOX_IDENTITY_GATE" \
    "$INTERFACE_GATE" \
    "$ROUTE_GATE" \
    "$PING_GATE" \
    "$COUNTER_GATE" \
    "$CONTINUITY_GATE"
do
    if [ "$VALUE" != "PASS" ]; then
        FINAL_GATE="FAIL"
    fi
done

{
    echo "USER_PLANE_SMOKE_VERSION=$SMOKE_VERSION"
    echo "SMOKE_ID=$SMOKE_ID"
    echo "UTC_TIMESTAMP=$UTC_TIMESTAMP"

    echo "GIT_BRANCH=$GIT_BRANCH"
    echo "GIT_HEAD=$GIT_HEAD"
    echo "GIT_WORKTREE=$GIT_WORKTREE"

    echo "UE_CONTAINER=$UE"
    echo "GNB_CONTAINER=$GNB"
    echo "5GC_CONTAINER=$CORE"

    echo "UE_FINGERPRINT=$UE_FP_AFTER"
    echo "GNB_FINGERPRINT=$GNB_FP_AFTER"
    echo "5GC_FINGERPRINT=$CORE_FP_AFTER"

    echo "UE_IMAGE_ID=$UE_IMAGE_ID"
    echo "GNB_IMAGE_ID=$GNB_IMAGE_ID"
    echo "5GC_IMAGE_ID=$CORE_IMAGE_ID"

    echo "TOOLBOX_REF=$TOOLBOX_REF"
    echo "TOOLBOX_IMAGE_ID=$TOOLBOX_ID"

    echo "EXPECTED_UE_INTERFACE=$EXPECTED_UE_INTERFACE"
    echo "EXPECTED_UE_PDU_IPV4=$EXPECTED_UE_PDU_IPV4"
    echo "EXPECTED_UPF_IPV4=$EXPECTED_UPF_IPV4"

    echo "USER_PLANE_RUNTIME_RESOLUTION_GATE=$RUNTIME_GATE"
    echo "TOOLBOX_IDENTITY_GATE=$TOOLBOX_IDENTITY_GATE"
    echo "UE_TUN_LINK_GATE=$TUN_LINK_GATE"
    echo "UE_USER_PLANE_ADDRESS_GATE=$PDU_ADDRESS_GATE"
    echo "UE_USER_PLANE_INTERFACE_GATE=$INTERFACE_GATE"
    echo "UE_TO_UPF_ROUTE_GATE=$ROUTE_GATE"
    echo "UE_TO_UPF_ICMP_GATE=$PING_GATE"

    echo "TUN_RX_PACKETS_BEFORE=$RX_BEFORE"
    echo "TUN_RX_PACKETS_AFTER=$RX_AFTER"
    echo "TUN_RX_PACKET_DELTA=$RX_DELTA"

    echo "TUN_TX_PACKETS_BEFORE=$TX_BEFORE"
    echo "TUN_TX_PACKETS_AFTER=$TX_AFTER"
    echo "TUN_TX_PACKET_DELTA=$TX_DELTA"

    echo "TUN_TOTAL_PACKET_DELTA=$TOTAL_DELTA"
    echo "TUN_TRAFFIC_COUNTER_DELTA_GATE=$COUNTER_GATE"

    echo "USER_PLANE_PROCESS_CONTINUITY_GATE=$CONTINUITY_GATE"
    echo "USER_PLANE_FUNCTIONAL_SMOKE_GATE=$FINAL_GATE"

    echo "DIAGNOSTIC_TRAFFIC_GENERATED=YES"
    echo "TRANSIENT_TOOLBOX_CONTAINER_USED=YES"
    echo "PERSISTENT_RUNTIME_CONFIGURATION_MODIFIED=NO"

} > "$SUMMARY_TMP"

mv "$SUMMARY_TMP" "$SUMMARY"
cp "$SUMMARY" "$LATEST"

cat "$SUMMARY"

echo
echo "EVIDENCE_DIR=$EVIDENCE_DIR"
echo "LATEST_EVIDENCE=$LATEST"

if [ "$FINAL_GATE" = "PASS" ]; then
    exit 0
fi

exit "$EX_NOT_READY"
