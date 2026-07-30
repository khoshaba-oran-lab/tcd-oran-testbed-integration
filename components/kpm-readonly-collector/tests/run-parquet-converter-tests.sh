#!/usr/bin/env bash
set -Eeuo pipefail
export LC_ALL=C

IMAGE_TAG="${1:?image tag is required}"

docker run --rm \
    --network none \
    --read-only \
    --tmpfs /tmp:rw,nosuid,nodev,noexec,size=128m \
    --entrypoint python \
    "$IMAGE_TAG" \
    /opt/tcd-kpm/tests/test_parquet_converter.py

echo "PARQUET_TEST_CONTAINER_NETWORK=none"
echo "PARQUET_TEST_CONTAINER_ROOTFS=read_only"
echo "PARQUET_CONVERTER_CONTAINER_TEST=PASS"
