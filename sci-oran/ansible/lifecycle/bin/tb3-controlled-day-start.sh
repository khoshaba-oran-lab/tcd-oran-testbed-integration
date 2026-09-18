#!/usr/bin/env bash
set -u
set -o pipefail

export LANG=C.UTF-8
export LC_ALL=C.UTF-8

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
ANSIBLE_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd -P)"
INVENTORY="$ANSIBLE_ROOT/inventory.ini"
PLAYBOOK="$SCRIPT_DIR/../playbooks/tb3-day-start.yml"
LOG_ROOT="${SCI_ORAN_CONTROLLER_LOG_ROOT:-/home/khoshaba/sci-oran/staging/r5-readiness/controller-logs}"

usage() {
    echo "Usage: $0 --preflight | --execute" >&2
}

preflight() {
    local encoding ansible_output ansible_rc

    test "$(hostname)" = "coll.vntu.org" || {
        echo "PREFLIGHT_RESULT=BLOCKED"
        echo "BLOCKER=WRONG_HOST"
        return 2
    }

    test -f "$INVENTORY" || {
        echo "PREFLIGHT_RESULT=BLOCKED"
        echo "BLOCKER=CANONICAL_INVENTORY_MISSING"
        return 2
    }

    test -f "$PLAYBOOK" || {
        echo "PREFLIGHT_RESULT=BLOCKED"
        echo "BLOCKER=DAY_START_PLAYBOOK_MISSING"
        return 2
    }

    test -d "$LOG_ROOT" || {
        echo "PREFLIGHT_RESULT=BLOCKED"
        echo "BLOCKER=CONTROLLER_LOG_DIRECTORY_MISSING"
        return 2
    }

    encoding="$(python3 -c 'import sys; print(sys.getfilesystemencoding())' 2>/dev/null)"
    case "${encoding,,}" in
        utf-8|utf8) ;;
        *)
            echo "PREFLIGHT_RESULT=BLOCKED"
            echo "BLOCKER=NON_UTF8_PYTHON_ENCODING"
            return 2
            ;;
    esac

    ansible_output="$(ansible --version 2>&1)"
    ansible_rc=$?

    if test "$ansible_rc" -ne 0 ||
       printf '%s\n' "$ansible_output" |
       grep -Fqi "requires the locale"; then
        echo "PREFLIGHT_RESULT=BLOCKED"
        echo "BLOCKER=ANSIBLE_UTF8_STARTUP_FAILED"
        return 2
    fi

    echo "PREFLIGHT_RESULT=PASS"
    echo "HOST=$(hostname)"
    echo "LANG=$LANG"
    echo "LC_ALL=$LC_ALL"
    echo "PYTHON_FILESYSTEM_ENCODING=$encoding"
    echo "INVENTORY=$INVENTORY"
    echo "PLAYBOOK=$PLAYBOOK"
    echo "ANSIBLE_VERSION=$(printf '%s\n' "$ansible_output" | head -n 1)"
    echo "ANSIBLE_PLAYBOOK_INVOCATION_COUNT=0"
}

execute_once() {
    local timestamp log playbook_rc log_sha operation_id
    local day_gate target_gate

    test "${SCI_ORAN_DAY_START_AUTHORISATION:-NO}" = "YES" || {
        echo "RESULT=BLOCKED"
        echo "BLOCKER=EXPLICIT_EXECUTION_AUTHORISATION_MISSING"
        return 2
    }

    preflight >/dev/null || {
        echo "RESULT=BLOCKED"
        echo "BLOCKER=CANONICAL_PREFLIGHT_FAILED"
        return 2
    }

    timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
    log="$LOG_ROOT/r5-controlled-day-start-$timestamp.log"

    test ! -e "$log" || {
        echo "RESULT=BLOCKED"
        echo "BLOCKER=CONTROLLER_LOG_ALREADY_EXISTS"
        return 2
    }

    ansible-playbook -i "$INVENTORY" "$PLAYBOOK" \
        -e confirm_day_start=true >"$log" 2>&1
    playbook_rc=$?

    log_sha="$(sha256sum "$log" | awk '{print $1}')"

    operation_id="$(
        grep -Eo \
        'DAY_START_OPERATION_ID=lifecycle-day-start-[A-Za-z0-9._-]+' \
        "$log" | tail -n 1 | cut -d= -f2 || true
    )"

    day_gate="FAIL"
    target_gate="FAIL"

    grep -Fq "DAY_START_GATE=PASS" "$log" &&
        day_gate="PASS"
    grep -Fq "TARGET_POST_DAY_START_GATE=PASS" "$log" &&
        target_gate="PASS"

    echo "ANSIBLE_PLAYBOOK_INVOCATION_COUNT=1"
    echo "PLAYBOOK_RC=$playbook_rc"
    echo "DAY_START_OPERATION_ID=${operation_id:-NOT_AVAILABLE}"
    echo "DAY_START_GATE=$day_gate"
    echo "TARGET_POST_DAY_START_GATE=$target_gate"
    echo "CONTROLLER_LOG=$log"
    echo "CONTROLLER_LOG_SHA256=$log_sha"
    echo "AUTOMATIC_RETRY=NO"

    if test "$playbook_rc" -eq 0 &&
       test -n "$operation_id" &&
       test "$day_gate" = "PASS" &&
       test "$target_gate" = "PASS"; then
        echo "RESULT=PASS"
        return 0
    fi

    tail -n 30 "$log"
    echo "RESULT=FAIL"
    return 1
}

case "${1:-}" in
    --preflight)
        preflight
        ;;
    --execute)
        execute_once
        ;;
    *)
        usage
        exit 64
        ;;
esac
