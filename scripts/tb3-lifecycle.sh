#!/usr/bin/env bash
set -euo pipefail

usage()
{
    cat <<'USAGE'
Usage:
  tb3-lifecycle.sh <operation> --confirm [operation-id]

Operations:
  deploy
  teardown
  recover
  reset
  day-start
  day-stop

Examples:
  tb3-lifecycle.sh day-start --confirm
  tb3-lifecycle.sh day-stop --confirm

An explicit operation ID may be supplied as the third argument.
Otherwise a new UTC-based operation ID is generated automatically.

This wrapper is intended to run on the Sci_O-RAN Ansible controller.
USAGE
}

fail()
{
    echo "ERROR: $*" >&2
    exit 1
}

if [ "$#" -lt 1 ]; then
    usage
    exit 2
fi

OPERATION="$1"
CONFIRM="${2:-}"
EXPLICIT_ID="${3:-}"

if [ "$OPERATION" = "-h" ] ||
   [ "$OPERATION" = "--help" ] ||
   [ "$OPERATION" = "help" ]
then
    usage
    exit 0
fi

if [ "$CONFIRM" != "--confirm" ]; then
    fail "state-changing lifecycle operations require --confirm"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ANSIBLE_ROOT="${SCI_ORAN_ANSIBLE_ROOT:-$REPO_ROOT/sci-oran/ansible}"
INVENTORY="${SCI_ORAN_INVENTORY:-$ANSIBLE_ROOT/inventory.ini}"
PLAYBOOK_DIR="${SCI_ORAN_PLAYBOOK_DIR:-$ANSIBLE_ROOT/lifecycle/playbooks}"

test -f "$INVENTORY" ||
    fail "inventory not found: $INVENTORY"

UTC_ID="$(date -u '+%Y%m%dT%H%M%SZ')"
NONCE="$(od -An -N4 -tx1 /dev/urandom | tr -d ' \n')"

case "$OPERATION" in
    deploy)
        PREFIX="lifecycle-deploy"
        PLAYBOOK="$PLAYBOOK_DIR/tb3-deploy.yml"
        ID_VAR="operation_id"
        CONFIRM_VAR="confirm_deploy"
        ;;

    teardown)
        PREFIX="lifecycle-teardown"
        PLAYBOOK="$PLAYBOOK_DIR/tb3-teardown.yml"
        ID_VAR="operation_id"
        CONFIRM_VAR="confirm_teardown"
        ;;

    recover)
        PREFIX="lifecycle-recover"
        PLAYBOOK="$PLAYBOOK_DIR/tb3-recover.yml"
        ID_VAR="recovery_operation_id"
        CONFIRM_VAR="confirm_recover"
        ;;

    reset)
        PREFIX="lifecycle-reset"
        PLAYBOOK="$PLAYBOOK_DIR/tb3-reset.yml"
        ID_VAR="reset_operation_id"
        CONFIRM_VAR="confirm_reset"
        ;;

    day-start)
        PREFIX="lifecycle-day-start"
        PLAYBOOK="$PLAYBOOK_DIR/tb3-day-start.yml"
        ID_VAR="day_start_operation_id"
        CONFIRM_VAR="confirm_day_start"
        ;;

    day-stop)
        PREFIX="lifecycle-day-stop"
        PLAYBOOK="$PLAYBOOK_DIR/tb3-day-stop.yml"
        ID_VAR="day_stop_operation_id"
        CONFIRM_VAR="confirm_day_stop"
        ;;

    *)
        usage
        fail "unknown lifecycle operation: $OPERATION"
        ;;
esac

test -f "$PLAYBOOK" ||
    fail "playbook not found: $PLAYBOOK"

if [ -n "$EXPLICIT_ID" ]; then
    OPERATION_ID="$EXPLICIT_ID"
else
    OPERATION_ID="${PREFIX}-${UTC_ID}-${NONCE}"
fi

case "$OPERATION_ID" in
    "${PREFIX}"-????????T??????Z-????????)
        ;;
    *)
        fail "invalid operation ID for $OPERATION: $OPERATION_ID"
        ;;
esac

echo "SCI_ORAN_LIFECYCLE_OPERATION=$OPERATION"
echo "SCI_ORAN_LIFECYCLE_OPERATION_ID=$OPERATION_ID"
echo "SCI_ORAN_LIFECYCLE_PLAYBOOK=$PLAYBOOK"
echo "SCI_ORAN_LIFECYCLE_INVENTORY=$INVENTORY"
echo

exec ansible-playbook \
    -i "$INVENTORY" \
    "$PLAYBOOK" \
    -e "${ID_VAR}=${OPERATION_ID}" \
    -e "${CONFIRM_VAR}=true"
