#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd -P)"

CANONICAL_WRAPPER="$REPO_ROOT/sci-oran/ansible/lifecycle/bin/tb3-lifecycle.sh"

if [ ! -x "$CANONICAL_WRAPPER" ]; then
    echo "ERROR: canonical lifecycle wrapper is not executable: $CANONICAL_WRAPPER" >&2
    exit 1
fi

exec "$CANONICAL_WRAPPER" "$@"
