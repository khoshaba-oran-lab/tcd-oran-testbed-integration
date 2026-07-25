#!/usr/bin/env bash
set -euo pipefail
umask 077
export LC_ALL=C

SCRIPT_DIR="$(
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &&
    pwd -P
)"

STACK_DIR="$(
    cd -- "$SCRIPT_DIR/.." &&
    pwd -P
)"

CONTEXT="$STACK_DIR/docker"
DOCKERFILE="$CONTEXT/Dockerfile.flexric.p2"
MUTEX_PATCH="$CONTEXT/patches/0001-xapp-oran-moni-initialize-mutex.patch"
BOUNDS_PATCH="$CONTEXT/patches/0002-xapp-oran-moni-bound-meas-info-index.patch"

IMAGE_TAG="${IMAGE_TAG:-tcd-oran/flexric-emulator:e2ap-v2-kpm-v3-b1d6d36-p2}"
BUILD_LOG="${BUILD_LOG:-$PWD/p2-image-build.log}"

EXPECTED_DOCKERFILE_SHA256="605d3a8259d1434cb174b376f6dc8a72d8e8d4240408745e1670a8e41ca2be50"
EXPECTED_MUTEX_PATCH_SHA256="787fe4e8f98f0417e0c5d5fa8f578b25b888754e48a1ac4c7780324abbee83f3"
EXPECTED_BOUNDS_PATCH_SHA256="78280f4c58659ab1d41cf6e1d2bb5a750869fcf33e7311be27a0c6f1d376a757"

MIN_FREE_BYTES=$((20 * 1024 * 1024 * 1024))

free_bytes="$(
    df --output=avail -B1 / |
    tail -n 1 |
    tr -d ' '
)"

if [[ "$free_bytes" -lt "$MIN_FREE_BYTES" ]]; then
    echo "ERROR: less than 20 GiB is available" >&2
    exit 20
fi

for required in \
    "$DOCKERFILE" \
    "$MUTEX_PATCH" \
    "$BOUNDS_PATCH"
do
    if [[ ! -f "$required" ]]; then
        echo "ERROR: required build input is unavailable: $required" >&2
        exit 21
    fi
done

if [[ -e "$BUILD_LOG" ]]; then
    echo "ERROR: build log already exists: $BUILD_LOG" >&2
    exit 22
fi

if docker image inspect "$IMAGE_TAG" >/dev/null 2>&1; then
    echo "ERROR: image tag already exists: $IMAGE_TAG" >&2
    exit 23
fi

echo "$EXPECTED_DOCKERFILE_SHA256  $DOCKERFILE" |
    sha256sum -c -

echo "$EXPECTED_MUTEX_PATCH_SHA256  $MUTEX_PATCH" |
    sha256sum -c -

echo "$EXPECTED_BOUNDS_PATCH_SHA256  $BOUNDS_PATCH" |
    sha256sum -c -

docker build \
    --pull=false \
    --progress=plain \
    --build-arg "BASE_IMAGE=ubuntu@sha256:4fbb8e6a8395de5a7550b33509421a2bafbc0aab6c06ba2cef9ebffbc7092d90" \
    --build-arg "SOURCE_REPOSITORY=https://github.com/merimdzaferagic/CONVERGE-summer-school.git" \
    --build-arg "SOURCE_CONVERGE_COMMIT=b1d6d36334a44a0dfeaacd643b82948259355d7c" \
    --build-arg "FLEXRIC_SUBTREE_PATH=srsRAN/docker/flexRIC/flexric" \
    --build-arg "FLEXRIC_TREE=bfd1a35b019f9ea7f48d5ee95e2751219e7ad578" \
    --build-arg "E2AP_VERSION=E2AP_V2" \
    --build-arg "KPM_VERSION=KPM_V3_00" \
    --build-arg "XAPP_DB=NONE_XAPP" \
    --build-arg "BUILD_JOBS=2" \
    --file "$DOCKERFILE" \
    --tag "$IMAGE_TAG" \
    "$CONTEXT" \
    |& tee "$BUILD_LOG"
