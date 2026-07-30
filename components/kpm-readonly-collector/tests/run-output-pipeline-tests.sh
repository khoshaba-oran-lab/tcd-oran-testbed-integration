#!/usr/bin/env bash

set -Eeuo pipefail
export LC_ALL=C

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$(mktemp -d)"
trap 'rm -rf "$BUILD_DIR"' EXIT

COMMON=(
    -std=c11
    -D_POSIX_C_SOURCE=200809L
    -Wall
    -Wextra
    -Werror
    -pedantic
    -pthread
    -I"$ROOT/include"
    "$ROOT/src/canonical_serialize.c"
    "$ROOT/src/file_sink.c"
    "$ROOT/src/prometheus_textfile.c"
    "$ROOT/src/output_pipeline.c"
    "$ROOT/tests/test_output_pipeline.c"
)

cc "${COMMON[@]}" -o "$BUILD_DIR/test-output-pipeline"
"$BUILD_DIR/test-output-pipeline"
echo "NORMAL_UNIT_TEST=PASS"

cc "${COMMON[@]}" \
    -O1 \
    -g \
    -fno-omit-frame-pointer \
    -fsanitize=address,undefined \
    -o "$BUILD_DIR/test-output-pipeline-sanitized"

ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 \
UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1 \
    "$BUILD_DIR/test-output-pipeline-sanitized"

echo "ASAN_UBSAN_UNIT_TEST=PASS"
echo "OUTPUT_PIPELINE_TEST_RESULT=PASS"
