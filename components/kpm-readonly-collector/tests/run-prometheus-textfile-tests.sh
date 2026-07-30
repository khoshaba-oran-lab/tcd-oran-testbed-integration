#!/usr/bin/env bash
set -Eeuo pipefail
export LC_ALL=C

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
BUILD_DIR="$(mktemp -d)"
trap 'rm -rf "$BUILD_DIR"' EXIT

CC_BIN="${CC:-gcc}"

COMMON_FLAGS=(
    -std=c11
    -Wall
    -Wextra
    -Werror
    -pedantic
    -O2
    -g
    -I"$ROOT/include"
)

SOURCES=(
    "$ROOT/src/prometheus_textfile.c"
    "$ROOT/tests/test_prometheus_textfile.c"
)

"$CC_BIN" \
    "${COMMON_FLAGS[@]}" \
    "${SOURCES[@]}" \
    -o "$BUILD_DIR/test-prometheus-textfile-normal"

"$BUILD_DIR/test-prometheus-textfile-normal"
echo "NORMAL_UNIT_TEST=PASS"

"$CC_BIN" \
    "${COMMON_FLAGS[@]}" \
    -O1 \
    -fno-omit-frame-pointer \
    -fsanitize=address,undefined \
    "${SOURCES[@]}" \
    -o "$BUILD_DIR/test-prometheus-textfile-sanitized"

ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 \
UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1 \
    "$BUILD_DIR/test-prometheus-textfile-sanitized"

echo "ASAN_UBSAN_UNIT_TEST=PASS"
echo "PROMETHEUS_TEXTFILE_TEST_RESULT=PASS"
