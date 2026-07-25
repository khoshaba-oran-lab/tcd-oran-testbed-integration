#!/usr/bin/env bash

set -euo pipefail

BASE_DIR="$(
    cd "$(dirname "${BASH_SOURCE[0]}")/.." &&
    pwd
)"

exec docker compose \
    --project-directory "$BASE_DIR" \
    -f "$BASE_DIR/compose.emulator.yml" \
    "$@"
