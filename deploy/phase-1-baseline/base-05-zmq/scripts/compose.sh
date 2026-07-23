#!/usr/bin/env bash

set -euo pipefail

BASE_DIR="$(
    cd "$(dirname "${BASH_SOURCE[0]}")/.." &&
    pwd
)"

COMPOSE_FILE="$BASE_DIR/compose.runtime.yml"
OPEN5GS_ENV="$BASE_DIR/configs/open5gs.env"

if [[ ! -f "$COMPOSE_FILE" ]]; then
    echo "ERROR: Compose file is missing:" >&2
    echo "  $COMPOSE_FILE" >&2
    exit 1
fi

if [[ ! -f "$OPEN5GS_ENV" ]]; then
    echo "ERROR: local Open5GS environment file is missing:" >&2
    echo "  $OPEN5GS_ENV" >&2
    echo >&2
    echo "Create it from the audited example:" >&2
    echo "  cp configs/open5gs.env.example configs/open5gs.env" >&2
    echo "  chmod 600 configs/open5gs.env" >&2
    exit 1
fi

exec docker compose \
    --project-directory "$BASE_DIR" \
    -f "$COMPOSE_FILE" \
    "$@"
