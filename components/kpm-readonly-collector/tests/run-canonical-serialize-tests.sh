#!/usr/bin/env bash
set -Eeuo pipefail
export LC_ALL=C

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$(mktemp -d)"
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
    "$ROOT/tests/test_canonical_serialize.c"
)

cc "${COMMON_FLAGS[@]}" "${SOURCES[@]}" -lm -o "$BUILD_DIR/test-normal"
"$BUILD_DIR/test-normal"
echo "NORMAL_UNIT_TEST=PASS"

cc "${COMMON_FLAGS[@]}" \
    -g \
    -O1 \
    -fno-omit-frame-pointer \
    -fsanitize=address,undefined \
    "${SOURCES[@]}" \
    -lm \
    -o "$BUILD_DIR/test-sanitized"

ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 \
UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1 \
    "$BUILD_DIR/test-sanitized"

echo "ASAN_UBSAN_UNIT_TEST=PASS"
echo "CANONICAL_SERIALIZATION_TEST_RESULT=PASS"
