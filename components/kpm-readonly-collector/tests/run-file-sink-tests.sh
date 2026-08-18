#!/usr/bin/env bash
set -Eeuo pipefail
export LC_ALL=C

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$(mktemp -d /tmp/tcd-kpm-file-sink-tests-XXXXXX)"
trap 'rm -rf "$BUILD_DIR"' EXIT

COMMON_FLAGS=(
    -std=c11
    -Wall
    -Wextra
    -Werror
    -pedantic
    -I"$ROOT/include"
)

SOURCES=(
    "$ROOT/src/canonical_serialize.c"
    "$ROOT/src/file_sink.c"
    "$ROOT/tests/test_file_sink.c"
)

cc "${COMMON_FLAGS[@]}" -O2 \
    "${SOURCES[@]}" \
    -o "$BUILD_DIR/test-file-sink"

"$BUILD_DIR/test-file-sink"
echo "NORMAL_UNIT_TEST=PASS"

cc "${COMMON_FLAGS[@]}" -O1 -g \
    -fsanitize=address,undefined \
    -fno-omit-frame-pointer \
    "${SOURCES[@]}" \
    -o "$BUILD_DIR/test-file-sink-sanitized"

ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 \
UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1 \
    "$BUILD_DIR/test-file-sink-sanitized"

echo "ASAN_UBSAN_UNIT_TEST=PASS"
echo "FILE_SINK_TEST_RESULT=PASS"
