#!/usr/bin/env bash

set -Eeuo pipefail
export LC_ALL=C

REPO_ROOT="$(
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." &&
    pwd -P
)"

TARGET="$REPO_ROOT/deploy/phase-1-baseline/base-05-zmq/scripts/tb3-sandybridge-down.sh"

test -x "$TARGET"

exec "$TARGET" "$@"
