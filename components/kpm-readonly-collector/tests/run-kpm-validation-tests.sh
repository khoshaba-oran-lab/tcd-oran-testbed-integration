#!/usr/bin/env bash

set -Eeuo pipefail
export LC_ALL=C

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VECTORS="${1:-$ROOT/docs/collector-02/length-mismatch-test-vectors.tsv}"
BUILD_DIR="${2:-$(mktemp -d)}"
KEEP_BUILD_DIR="${TCD_KPM_KEEP_TEST_BUILD_DIR:-no}"

cleanup()
{
    rc=$?
    if test "$KEEP_BUILD_DIR" != yes; then
        rm -rf "$BUILD_DIR"
    fi
    exit "$rc"
}
trap cleanup EXIT

mkdir -p "$BUILD_DIR"

test -f "$VECTORS"
command -v cc >/dev/null

COMMON_FLAGS=(
    -std=c11
    -Wall
    -Wextra
    -Wpedantic
    -Werror
    -O2
    -I"$ROOT/include"
)

cc "${COMMON_FLAGS[@]}" \
    "$ROOT/src/kpm_validation.c" \
    "$ROOT/tests/test_kpm_validation.c" \
    -o "$BUILD_DIR/test-kpm-validation"

"$BUILD_DIR/test-kpm-validation" "$VECTORS" \
    | tee "$BUILD_DIR/normal-test.log"

cc "${COMMON_FLAGS[@]}" \
    -O1 \
    -g \
    -fno-omit-frame-pointer \
    -fsanitize=address,undefined \
    "$ROOT/src/kpm_validation.c" \
    "$ROOT/tests/test_kpm_validation.c" \
    -o "$BUILD_DIR/test-kpm-validation-sanitized"

ASAN_OPTIONS="detect_leaks=1:abort_on_error=1" \
UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1" \
    "$BUILD_DIR/test-kpm-validation-sanitized" "$VECTORS" \
    | tee "$BUILD_DIR/sanitized-test.log"

grep -Fxq 'VECTOR_COUNT=6' "$BUILD_DIR/normal-test.log"
grep -Fxq 'VECTOR_PASS_COUNT=6' "$BUILD_DIR/normal-test.log"
grep -Fxq 'ADDITIONAL_DEFENSIVE_CASES=PASS' "$BUILD_DIR/normal-test.log"
grep -Fxq 'CONTINUATION_SEQUENCE=PASS' "$BUILD_DIR/normal-test.log"
grep -Fxq 'SILENT_TRUNCATION_OBSERVED=no' "$BUILD_DIR/normal-test.log"
grep -Fxq 'VALIDATION_CORE_TEST_RESULT=PASS' "$BUILD_DIR/normal-test.log"
grep -Fxq 'VALIDATION_CORE_TEST_RESULT=PASS' "$BUILD_DIR/sanitized-test.log"

echo "NORMAL_UNIT_TEST=PASS"
echo "ASAN_UBSAN_UNIT_TEST=PASS"
echo "HARDWARE_DATA_REQUIRED=no"
