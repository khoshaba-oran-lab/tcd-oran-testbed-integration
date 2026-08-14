#!/usr/bin/env bash
set -Eeuo pipefail

DOCTOR_VERSION="0.11.1"
EX_NOT_READY=20

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

BASE_LOCK="${REPO_ROOT}/deploy/phase-1-baseline/base-05-zmq/locks/base-05-zmq-runtime.lock"
PROFILE="${REPO_ROOT}/deploy/phase-1-baseline/base-05-zmq/profiles/tb3-dell-sandybridge.env"
GNB_LOCK="${REPO_ROOT}/deploy/phase-2-flexric/tb3-runtime/captured-action11/gnb-runtime.lock"
RIC_LOCK="${REPO_ROOT}/deploy/phase-2-flexric/tb3-runtime/locks/tb3-ric-runtime.lock"
DIAG_LOCK="${REPO_ROOT}/deploy/images/diagnostic/images.lock.json"
GNB_CFG="${REPO_ROOT}/deploy/phase-2-flexric/tb3-runtime/configs/gnb-e2sm-rc.yaml"
UE_CFG="${REPO_ROOT}/deploy/phase-1-baseline/base-05-zmq/configs/ue_zmq_base05.conf"

get_value()
{
    local file="$1"
    local key="$2"

    awk -F= -v key="$key" '
        $1 == key {
            sub(/^[^=]*=/, "")
            print
            exit
        }
    ' "$file"
}

gate="PASS"
failure_reason="NONE"

UTC_TIMESTAMP="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
READINESS_ID="RDY-$(date -u '+%Y%m%dT%H%M%SZ')-$$"

echo "SCI_ORAN_DOCTOR_VERSION=${DOCTOR_VERSION}"
echo "READINESS_ID=${READINESS_ID}"
echo "UTC_TIMESTAMP=${UTC_TIMESTAMP}"
echo "REPO_ROOT=${REPO_ROOT}"

cd "$REPO_ROOT"

echo "GIT_BRANCH=$(git branch --show-current)"
echo "GIT_HEAD=$(git rev-parse HEAD)"

if [ -n "$(git status --porcelain)" ]; then
    echo "GIT_WORKTREE=DIRTY"
else
    echo "GIT_WORKTREE=CLEAN"
fi

echo
echo "===== HOST ====="

HOST_READINESS_GATE="PASS"

for file in \
    "$BASE_LOCK" \
    "$PROFILE" \
    "$GNB_LOCK" \
    "$RIC_LOCK" \
    "$DIAG_LOCK" \
    "$GNB_CFG" \
    "$UE_CFG"
do
    if [ ! -f "$file" ]; then
        echo "MISSING_CONTRACT=$file"
        HOST_READINESS_GATE="FAIL"
    fi
done

if docker info >/dev/null 2>&1; then
    echo "DOCKER_DAEMON_GATE=PASS"
else
    echo "DOCKER_DAEMON_GATE=FAIL"
    HOST_READINESS_GATE="FAIL"
fi

echo "HOST_READINESS_GATE=${HOST_READINESS_GATE}"

echo
echo "===== HOST RESOURCE READINESS ====="

HOST_RESOURCE_POLICY="$REPO_ROOT/deploy/phase-2-flexric/tb3-runtime/locks/host-resource-readiness.policy"

HOST_RESOURCE_READINESS_GATE="PASS"

HOST_RESOURCE_POLICY_GATE="FAIL"
HOST_CPU_CAPACITY_GATE="FAIL"
HOST_LOAD_CAPACITY_GATE="FAIL"
HOST_MEMORY_CAPACITY_GATE="FAIL"
HOST_HOME_FILESYSTEM_CAPACITY_GATE="FAIL"
HOST_DOCKER_FILESYSTEM_CAPACITY_GATE="FAIL"
HOST_INODE_CAPACITY_GATE="FAIL"
HOST_PRESSURE_GATE="FAIL"
HOST_SWAP_POLICY_GATE="FAIL"

if [ -f "$HOST_RESOURCE_POLICY" ]; then
    HOST_RESOURCE_POLICY_GATE="PASS"
fi

echo "HOST_RESOURCE_POLICY=$HOST_RESOURCE_POLICY"
echo "HOST_RESOURCE_POLICY_GATE=${HOST_RESOURCE_POLICY_GATE}"

if [ "$HOST_RESOURCE_POLICY_GATE" = "PASS" ]; then

    MIN_CPU_COUNT="$(
        get_value "$HOST_RESOURCE_POLICY" MIN_CPU_COUNT
    )"

    MAX_LOAD1_PER_CPU="$(
        get_value "$HOST_RESOURCE_POLICY" MAX_LOAD1_PER_CPU
    )"

    MAX_LOAD5_PER_CPU="$(
        get_value "$HOST_RESOURCE_POLICY" MAX_LOAD5_PER_CPU
    )"

    MIN_MEMORY_AVAILABLE_PERCENT="$(
        get_value "$HOST_RESOURCE_POLICY" MIN_MEMORY_AVAILABLE_PERCENT
    )"

    MIN_MEMORY_AVAILABLE_KB="$(
        get_value "$HOST_RESOURCE_POLICY" MIN_MEMORY_AVAILABLE_KB
    )"

    MIN_HOME_FS_AVAILABLE_KB="$(
        get_value "$HOST_RESOURCE_POLICY" MIN_HOME_FS_AVAILABLE_KB
    )"

    MAX_HOME_FS_USED_PERCENT="$(
        get_value "$HOST_RESOURCE_POLICY" MAX_HOME_FS_USED_PERCENT
    )"

    MIN_DOCKER_FS_AVAILABLE_KB="$(
        get_value "$HOST_RESOURCE_POLICY" MIN_DOCKER_FS_AVAILABLE_KB
    )"

    MAX_DOCKER_FS_USED_PERCENT="$(
        get_value "$HOST_RESOURCE_POLICY" MAX_DOCKER_FS_USED_PERCENT
    )"

    MAX_HOME_FS_INODES_USED_PERCENT="$(
        get_value "$HOST_RESOURCE_POLICY" MAX_HOME_FS_INODES_USED_PERCENT
    )"

    PSI_REQUIRED="$(
        get_value "$HOST_RESOURCE_POLICY" PSI_REQUIRED
    )"

    MAX_CPU_PSI_SOME_AVG60="$(
        get_value "$HOST_RESOURCE_POLICY" MAX_CPU_PSI_SOME_AVG60
    )"

    MAX_MEMORY_PSI_FULL_AVG60="$(
        get_value "$HOST_RESOURCE_POLICY" MAX_MEMORY_PSI_FULL_AVG60
    )"

    MAX_IO_PSI_FULL_AVG60="$(
        get_value "$HOST_RESOURCE_POLICY" MAX_IO_PSI_FULL_AVG60
    )"

    SWAP_REQUIRED="$(
        get_value "$HOST_RESOURCE_POLICY" SWAP_REQUIRED
    )"

else
    MIN_CPU_COUNT=""
    MAX_LOAD1_PER_CPU=""
    MAX_LOAD5_PER_CPU=""
    MIN_MEMORY_AVAILABLE_PERCENT=""
    MIN_MEMORY_AVAILABLE_KB=""
    MIN_HOME_FS_AVAILABLE_KB=""
    MAX_HOME_FS_USED_PERCENT=""
    MIN_DOCKER_FS_AVAILABLE_KB=""
    MAX_DOCKER_FS_USED_PERCENT=""
    MAX_HOME_FS_INODES_USED_PERCENT=""
    PSI_REQUIRED=""
    MAX_CPU_PSI_SOME_AVG60=""
    MAX_MEMORY_PSI_FULL_AVG60=""
    MAX_IO_PSI_FULL_AVG60=""
    SWAP_REQUIRED=""
fi

HOST_RESOURCE_POLICY_CONTRACT_GATE="PASS"

for VALUE in \
    "$MIN_CPU_COUNT" \
    "$MAX_LOAD1_PER_CPU" \
    "$MAX_LOAD5_PER_CPU" \
    "$MIN_MEMORY_AVAILABLE_PERCENT" \
    "$MIN_MEMORY_AVAILABLE_KB" \
    "$MIN_HOME_FS_AVAILABLE_KB" \
    "$MAX_HOME_FS_USED_PERCENT" \
    "$MIN_DOCKER_FS_AVAILABLE_KB" \
    "$MAX_DOCKER_FS_USED_PERCENT" \
    "$MAX_HOME_FS_INODES_USED_PERCENT" \
    "$PSI_REQUIRED" \
    "$MAX_CPU_PSI_SOME_AVG60" \
    "$MAX_MEMORY_PSI_FULL_AVG60" \
    "$MAX_IO_PSI_FULL_AVG60" \
    "$SWAP_REQUIRED"
do
    if [ -z "$VALUE" ]; then
        HOST_RESOURCE_POLICY_CONTRACT_GATE="FAIL"
    fi
done

echo "HOST_RESOURCE_POLICY_CONTRACT_GATE=${HOST_RESOURCE_POLICY_CONTRACT_GATE}"

if [ "$HOST_RESOURCE_POLICY_GATE" != "PASS" ] ||
   [ "$HOST_RESOURCE_POLICY_CONTRACT_GATE" != "PASS" ]
then
    HOST_RESOURCE_READINESS_GATE="FAIL"
fi

float_le()
{
    awk -v actual="$1" -v limit="$2" '
        BEGIN {
            exit !(actual + 0 <= limit + 0)
        }
    '
}

float_ge()
{
    awk -v actual="$1" -v limit="$2" '
        BEGIN {
            exit !(actual + 0 >= limit + 0)
        }
    '
}

echo
echo "----- CPU + LOAD CAPACITY -----"

HOST_CPU_COUNT="$(nproc)"

read -r HOST_LOAD1 HOST_LOAD5 HOST_LOAD15 _ \
    < /proc/loadavg

HOST_LOAD1_PER_CPU="$(
    awk \
        -v load_value="$HOST_LOAD1" \
        -v cpu="$HOST_CPU_COUNT" \
        'BEGIN {printf "%.4f", load_value / cpu}'
)"

HOST_LOAD5_PER_CPU="$(
    awk \
        -v load_value="$HOST_LOAD5" \
        -v cpu="$HOST_CPU_COUNT" \
        'BEGIN {printf "%.4f", load_value / cpu}'
)"

echo "HOST_CPU_COUNT=${HOST_CPU_COUNT}"
echo "HOST_LOAD1=${HOST_LOAD1}"
echo "HOST_LOAD5=${HOST_LOAD5}"
echo "HOST_LOAD15=${HOST_LOAD15}"
echo "HOST_LOAD1_PER_CPU=${HOST_LOAD1_PER_CPU}"
echo "HOST_LOAD5_PER_CPU=${HOST_LOAD5_PER_CPU}"

if [ -n "$MIN_CPU_COUNT" ] &&
   [ "$HOST_CPU_COUNT" -ge "$MIN_CPU_COUNT" ]
then
    HOST_CPU_CAPACITY_GATE="PASS"
fi

if [ -n "$MAX_LOAD1_PER_CPU" ] &&
   [ -n "$MAX_LOAD5_PER_CPU" ] &&
   float_le "$HOST_LOAD1_PER_CPU" "$MAX_LOAD1_PER_CPU" &&
   float_le "$HOST_LOAD5_PER_CPU" "$MAX_LOAD5_PER_CPU"
then
    HOST_LOAD_CAPACITY_GATE="PASS"
fi

echo "HOST_CPU_CAPACITY_GATE=${HOST_CPU_CAPACITY_GATE}"
echo "HOST_LOAD_CAPACITY_GATE=${HOST_LOAD_CAPACITY_GATE}"

echo
echo "----- MEMORY CAPACITY -----"

HOST_MEM_TOTAL_KB="$(
    awk '/^MemTotal:/ {print $2}' /proc/meminfo
)"

HOST_MEM_AVAILABLE_KB="$(
    awk '/^MemAvailable:/ {print $2}' /proc/meminfo
)"

HOST_MEM_AVAILABLE_PERCENT="$(
    awk \
        -v available="$HOST_MEM_AVAILABLE_KB" \
        -v total="$HOST_MEM_TOTAL_KB" \
        'BEGIN {printf "%.2f", available * 100 / total}'
)"

HOST_SWAP_TOTAL_KB="$(
    awk '/^SwapTotal:/ {print $2}' /proc/meminfo
)"

echo "HOST_MEM_TOTAL_KB=${HOST_MEM_TOTAL_KB}"
echo "HOST_MEM_AVAILABLE_KB=${HOST_MEM_AVAILABLE_KB}"
echo "HOST_MEM_AVAILABLE_PERCENT=${HOST_MEM_AVAILABLE_PERCENT}"
echo "HOST_SWAP_TOTAL_KB=${HOST_SWAP_TOTAL_KB}"

if [ -n "$MIN_MEMORY_AVAILABLE_KB" ] &&
   [ "$HOST_MEM_AVAILABLE_KB" -ge "$MIN_MEMORY_AVAILABLE_KB" ] &&
   float_ge \
       "$HOST_MEM_AVAILABLE_PERCENT" \
       "$MIN_MEMORY_AVAILABLE_PERCENT"
then
    HOST_MEMORY_CAPACITY_GATE="PASS"
fi

if [ "$SWAP_REQUIRED" = "false" ]; then
    HOST_SWAP_POLICY_GATE="PASS"
elif [ "$SWAP_REQUIRED" = "true" ] &&
     [ "$HOST_SWAP_TOTAL_KB" -gt 0 ]
then
    HOST_SWAP_POLICY_GATE="PASS"
fi

echo "HOST_MEMORY_CAPACITY_GATE=${HOST_MEMORY_CAPACITY_GATE}"
echo "HOST_SWAP_POLICY_GATE=${HOST_SWAP_POLICY_GATE}"

echo
echo "----- HOME FILESYSTEM CAPACITY -----"

HOST_HOME_FS_AVAILABLE_KB="$(
    df -Pk "$HOME" |
    awk 'NR == 2 {print $4}'
)"

HOST_HOME_FS_USED_PERCENT="$(
    df -Pk "$HOME" |
    awk 'NR == 2 {gsub(/%/, "", $5); print $5}'
)"

echo "HOST_HOME_FS_AVAILABLE_KB=${HOST_HOME_FS_AVAILABLE_KB}"
echo "HOST_HOME_FS_USED_PERCENT=${HOST_HOME_FS_USED_PERCENT}"

if [ -n "$MIN_HOME_FS_AVAILABLE_KB" ] &&
   [ "$HOST_HOME_FS_AVAILABLE_KB" -ge "$MIN_HOME_FS_AVAILABLE_KB" ] &&
   [ "$HOST_HOME_FS_USED_PERCENT" -le "$MAX_HOME_FS_USED_PERCENT" ]
then
    HOST_HOME_FILESYSTEM_CAPACITY_GATE="PASS"
fi

echo "HOST_HOME_FILESYSTEM_CAPACITY_GATE=${HOST_HOME_FILESYSTEM_CAPACITY_GATE}"

echo
echo "----- DOCKER FILESYSTEM CAPACITY -----"

HOST_DOCKER_ROOT="$(
    docker info \
        --format '{{.DockerRootDir}}' \
        2>/dev/null || true
)"

HOST_DOCKER_FS_AVAILABLE_KB=""
HOST_DOCKER_FS_USED_PERCENT=""

if [ -n "$HOST_DOCKER_ROOT" ] &&
   [ -d "$HOST_DOCKER_ROOT" ]
then
    HOST_DOCKER_FS_AVAILABLE_KB="$(
        df -Pk "$HOST_DOCKER_ROOT" |
        awk 'NR == 2 {print $4}'
    )"

    HOST_DOCKER_FS_USED_PERCENT="$(
        df -Pk "$HOST_DOCKER_ROOT" |
        awk 'NR == 2 {gsub(/%/, "", $5); print $5}'
    )"
fi

echo "HOST_DOCKER_ROOT=${HOST_DOCKER_ROOT}"
echo "HOST_DOCKER_FS_AVAILABLE_KB=${HOST_DOCKER_FS_AVAILABLE_KB}"
echo "HOST_DOCKER_FS_USED_PERCENT=${HOST_DOCKER_FS_USED_PERCENT}"

if [ -n "$HOST_DOCKER_FS_AVAILABLE_KB" ] &&
   [ -n "$HOST_DOCKER_FS_USED_PERCENT" ] &&
   [ "$HOST_DOCKER_FS_AVAILABLE_KB" -ge "$MIN_DOCKER_FS_AVAILABLE_KB" ] &&
   [ "$HOST_DOCKER_FS_USED_PERCENT" -le "$MAX_DOCKER_FS_USED_PERCENT" ]
then
    HOST_DOCKER_FILESYSTEM_CAPACITY_GATE="PASS"
fi

echo "HOST_DOCKER_FILESYSTEM_CAPACITY_GATE=${HOST_DOCKER_FILESYSTEM_CAPACITY_GATE}"

echo
echo "----- INODE CAPACITY -----"

HOST_INODES_USED_PERCENT="$(
    df -Pi "$HOME" |
    awk 'NR == 2 {gsub(/%/, "", $5); print $5}'
)"

echo "HOST_INODES_USED_PERCENT=${HOST_INODES_USED_PERCENT}"

if [ -n "$HOST_INODES_USED_PERCENT" ] &&
   [ "$HOST_INODES_USED_PERCENT" -le "$MAX_HOME_FS_INODES_USED_PERCENT" ]
then
    HOST_INODE_CAPACITY_GATE="PASS"
fi

echo "HOST_INODE_CAPACITY_GATE=${HOST_INODE_CAPACITY_GATE}"

echo
echo "----- PRESSURE STALL INFORMATION -----"

psi_value()
{
    FILE="$1"
    CLASS="$2"
    FIELD="$3"

    awk \
        -v class="$CLASS" \
        -v field="$FIELD" '
            $1 == class {
                for (i = 2; i <= NF; i++) {
                    split($i, kv, "=")

                    if (kv[1] == field) {
                        print kv[2]
                        exit
                    }
                }
            }
        ' "$FILE"
}

HOST_CPU_PSI_SOME_AVG60=""
HOST_MEMORY_PSI_FULL_AVG60=""
HOST_IO_PSI_FULL_AVG60=""

if [ -r /proc/pressure/cpu ]; then
    HOST_CPU_PSI_SOME_AVG60="$(
        psi_value \
            /proc/pressure/cpu \
            some \
            avg60
    )"
fi

if [ -r /proc/pressure/memory ]; then
    HOST_MEMORY_PSI_FULL_AVG60="$(
        psi_value \
            /proc/pressure/memory \
            full \
            avg60
    )"
fi

if [ -r /proc/pressure/io ]; then
    HOST_IO_PSI_FULL_AVG60="$(
        psi_value \
            /proc/pressure/io \
            full \
            avg60
    )"
fi

echo "HOST_CPU_PSI_SOME_AVG60=${HOST_CPU_PSI_SOME_AVG60}"
echo "HOST_MEMORY_PSI_FULL_AVG60=${HOST_MEMORY_PSI_FULL_AVG60}"
echo "HOST_IO_PSI_FULL_AVG60=${HOST_IO_PSI_FULL_AVG60}"

if [ "$PSI_REQUIRED" = "false" ]; then
    HOST_PRESSURE_GATE="PASS"
elif [ "$PSI_REQUIRED" = "true" ] &&
     [ -n "$HOST_CPU_PSI_SOME_AVG60" ] &&
     [ -n "$HOST_MEMORY_PSI_FULL_AVG60" ] &&
     [ -n "$HOST_IO_PSI_FULL_AVG60" ] &&
     float_le \
         "$HOST_CPU_PSI_SOME_AVG60" \
         "$MAX_CPU_PSI_SOME_AVG60" &&
     float_le \
         "$HOST_MEMORY_PSI_FULL_AVG60" \
         "$MAX_MEMORY_PSI_FULL_AVG60" &&
     float_le \
         "$HOST_IO_PSI_FULL_AVG60" \
         "$MAX_IO_PSI_FULL_AVG60"
then
    HOST_PRESSURE_GATE="PASS"
fi

echo "HOST_PRESSURE_GATE=${HOST_PRESSURE_GATE}"

echo
echo "----- HOST RESOURCE FINAL DECISION -----"

for HOST_RESOURCE_GATE_VALUE in \
    "$HOST_RESOURCE_POLICY_GATE" \
    "$HOST_RESOURCE_POLICY_CONTRACT_GATE" \
    "$HOST_CPU_CAPACITY_GATE" \
    "$HOST_LOAD_CAPACITY_GATE" \
    "$HOST_MEMORY_CAPACITY_GATE" \
    "$HOST_HOME_FILESYSTEM_CAPACITY_GATE" \
    "$HOST_DOCKER_FILESYSTEM_CAPACITY_GATE" \
    "$HOST_INODE_CAPACITY_GATE" \
    "$HOST_PRESSURE_GATE" \
    "$HOST_SWAP_POLICY_GATE"
do
    if [ "$HOST_RESOURCE_GATE_VALUE" != "PASS" ]; then
        HOST_RESOURCE_READINESS_GATE="FAIL"
    fi
done

echo "HOST_RESOURCE_READINESS_GATE=${HOST_RESOURCE_READINESS_GATE}"

echo
echo "===== REPOSITORY REPRODUCIBILITY ====="

REPOSITORY_POLICY="$REPO_ROOT/deploy/phase-2-flexric/tb3-runtime/locks/repository-readiness.policy"

REPOSITORY_REPRODUCIBILITY_GATE="PASS"

REPOSITORY_POLICY_GATE="FAIL"
REPOSITORY_POLICY_CONTRACT_GATE="FAIL"
REPOSITORY_GIT_REPOSITORY_GATE="FAIL"
REPOSITORY_BRANCH_GATE="FAIL"
REPOSITORY_TRACKED_DEPENDENCIES_GATE="FAIL"
REPOSITORY_DEVELOPMENT_SCOPE_GATE="FAIL"
REPOSITORY_SCRIPT_SYNTAX_GATE="FAIL"

echo "REPOSITORY_POLICY=$REPOSITORY_POLICY"

if [ -f "$REPOSITORY_POLICY" ]; then
    REPOSITORY_POLICY_GATE="PASS"
fi

echo "REPOSITORY_POLICY_GATE=${REPOSITORY_POLICY_GATE}"

REPOSITORY_POLICY_VERSION=""
REPOSITORY_EXPECTED_BRANCH=""

RUNTIME_GATE_REQUIRE_GIT_REPOSITORY=""
RUNTIME_GATE_REQUIRE_EXPECTED_BRANCH=""
RUNTIME_GATE_REQUIRE_TRACKED_DEPENDENCIES=""
RUNTIME_GATE_REQUIRE_TRACKED_DEPENDENCIES_CLEAN=""
RUNTIME_GATE_REQUIRE_REMOTE_SYNC=""
RUNTIME_GATE_REQUIRE_GLOBAL_CLEAN_WORKTREE=""
RUNTIME_GATE_ALLOW_PROMPT11B_DEVELOPMENT_FILES_UNTRACKED=""

FINAL_CHECKPOINT_REQUIRE_REMOTE_SYNC=""
FINAL_CHECKPOINT_REQUIRE_PROMPT11B_SCOPE_TRACKED=""
FINAL_CHECKPOINT_REQUIRE_PROMPT11B_SCOPE_CLEAN=""
FINAL_CHECKPOINT_REQUIRE_GLOBAL_CLEAN_WORKTREE=""

REPOSITORY_TRACKED_DEPENDENCY_COUNT=""
REPOSITORY_DEVELOPMENT_FILE_COUNT=""

if [ "$REPOSITORY_POLICY_GATE" = "PASS" ]; then

    REPOSITORY_POLICY_VERSION="$(
        get_value \
            "$REPOSITORY_POLICY" \
            REPOSITORY_READINESS_POLICY_VERSION
    )"

    REPOSITORY_EXPECTED_BRANCH="$(
        get_value \
            "$REPOSITORY_POLICY" \
            EXPECTED_BRANCH
    )"

    RUNTIME_GATE_REQUIRE_GIT_REPOSITORY="$(
        get_value \
            "$REPOSITORY_POLICY" \
            RUNTIME_GATE_REQUIRE_GIT_REPOSITORY
    )"

    RUNTIME_GATE_REQUIRE_EXPECTED_BRANCH="$(
        get_value \
            "$REPOSITORY_POLICY" \
            RUNTIME_GATE_REQUIRE_EXPECTED_BRANCH
    )"

    RUNTIME_GATE_REQUIRE_TRACKED_DEPENDENCIES="$(
        get_value \
            "$REPOSITORY_POLICY" \
            RUNTIME_GATE_REQUIRE_TRACKED_DEPENDENCIES
    )"

    RUNTIME_GATE_REQUIRE_TRACKED_DEPENDENCIES_CLEAN="$(
        get_value \
            "$REPOSITORY_POLICY" \
            RUNTIME_GATE_REQUIRE_TRACKED_DEPENDENCIES_CLEAN
    )"

    RUNTIME_GATE_REQUIRE_REMOTE_SYNC="$(
        get_value \
            "$REPOSITORY_POLICY" \
            RUNTIME_GATE_REQUIRE_REMOTE_SYNC
    )"

    RUNTIME_GATE_REQUIRE_GLOBAL_CLEAN_WORKTREE="$(
        get_value \
            "$REPOSITORY_POLICY" \
            RUNTIME_GATE_REQUIRE_GLOBAL_CLEAN_WORKTREE
    )"

    RUNTIME_GATE_ALLOW_PROMPT11B_DEVELOPMENT_FILES_UNTRACKED="$(
        get_value \
            "$REPOSITORY_POLICY" \
            RUNTIME_GATE_ALLOW_PROMPT11B_DEVELOPMENT_FILES_UNTRACKED
    )"

    FINAL_CHECKPOINT_REQUIRE_REMOTE_SYNC="$(
        get_value \
            "$REPOSITORY_POLICY" \
            FINAL_CHECKPOINT_REQUIRE_REMOTE_SYNC
    )"

    FINAL_CHECKPOINT_REQUIRE_PROMPT11B_SCOPE_TRACKED="$(
        get_value \
            "$REPOSITORY_POLICY" \
            FINAL_CHECKPOINT_REQUIRE_PROMPT11B_SCOPE_TRACKED
    )"

    FINAL_CHECKPOINT_REQUIRE_PROMPT11B_SCOPE_CLEAN="$(
        get_value \
            "$REPOSITORY_POLICY" \
            FINAL_CHECKPOINT_REQUIRE_PROMPT11B_SCOPE_CLEAN
    )"

    FINAL_CHECKPOINT_REQUIRE_GLOBAL_CLEAN_WORKTREE="$(
        get_value \
            "$REPOSITORY_POLICY" \
            FINAL_CHECKPOINT_REQUIRE_GLOBAL_CLEAN_WORKTREE
    )"

    REPOSITORY_TRACKED_DEPENDENCY_COUNT="$(
        get_value \
            "$REPOSITORY_POLICY" \
            TRACKED_DEPENDENCY_COUNT
    )"

    REPOSITORY_DEVELOPMENT_FILE_COUNT="$(
        get_value \
            "$REPOSITORY_POLICY" \
            PROMPT11B_DEVELOPMENT_FILE_COUNT
    )"
fi

echo "REPOSITORY_POLICY_VERSION=${REPOSITORY_POLICY_VERSION}"
echo "REPOSITORY_EXPECTED_BRANCH=${REPOSITORY_EXPECTED_BRANCH}"
echo "REPOSITORY_TRACKED_DEPENDENCY_COUNT=${REPOSITORY_TRACKED_DEPENDENCY_COUNT}"
echo "REPOSITORY_DEVELOPMENT_FILE_COUNT=${REPOSITORY_DEVELOPMENT_FILE_COUNT}"

if [ "$REPOSITORY_POLICY_VERSION" = "1" ] &&
   [ "$REPOSITORY_EXPECTED_BRANCH" = "feat/tb3-dell-reproducibility" ] &&
   [ "$RUNTIME_GATE_REQUIRE_GIT_REPOSITORY" = "true" ] &&
   [ "$RUNTIME_GATE_REQUIRE_EXPECTED_BRANCH" = "true" ] &&
   [ "$RUNTIME_GATE_REQUIRE_TRACKED_DEPENDENCIES" = "true" ] &&
   [ "$RUNTIME_GATE_REQUIRE_TRACKED_DEPENDENCIES_CLEAN" = "true" ] &&
   [ "$RUNTIME_GATE_REQUIRE_REMOTE_SYNC" = "false" ] &&
   [ "$RUNTIME_GATE_REQUIRE_GLOBAL_CLEAN_WORKTREE" = "false" ] &&
   [ "$RUNTIME_GATE_ALLOW_PROMPT11B_DEVELOPMENT_FILES_UNTRACKED" = "true" ] &&
   [ "$FINAL_CHECKPOINT_REQUIRE_REMOTE_SYNC" = "true" ] &&
   [ "$FINAL_CHECKPOINT_REQUIRE_PROMPT11B_SCOPE_TRACKED" = "true" ] &&
   [ "$FINAL_CHECKPOINT_REQUIRE_PROMPT11B_SCOPE_CLEAN" = "true" ] &&
   [ "$FINAL_CHECKPOINT_REQUIRE_GLOBAL_CLEAN_WORKTREE" = "false" ] &&
   [ "$REPOSITORY_TRACKED_DEPENDENCY_COUNT" = "9" ] &&
   [ "$REPOSITORY_DEVELOPMENT_FILE_COUNT" = "5" ]
then
    REPOSITORY_POLICY_CONTRACT_GATE="PASS"
fi

echo "REPOSITORY_POLICY_CONTRACT_GATE=${REPOSITORY_POLICY_CONTRACT_GATE}"

echo
echo "----- GIT REPOSITORY + BRANCH -----"

REPOSITORY_INSIDE_WORK_TREE="$(
    git -C "$REPO_ROOT" \
        rev-parse \
        --is-inside-work-tree \
        2>/dev/null ||
    true
)"

REPOSITORY_CURRENT_BRANCH="$(
    git -C "$REPO_ROOT" \
        branch \
        --show-current \
        2>/dev/null ||
    true
)"

echo "REPOSITORY_INSIDE_WORK_TREE=${REPOSITORY_INSIDE_WORK_TREE}"
echo "REPOSITORY_CURRENT_BRANCH=${REPOSITORY_CURRENT_BRANCH}"

if [ "$REPOSITORY_INSIDE_WORK_TREE" = "true" ]; then
    REPOSITORY_GIT_REPOSITORY_GATE="PASS"
fi

if [ -n "$REPOSITORY_EXPECTED_BRANCH" ] &&
   [ "$REPOSITORY_CURRENT_BRANCH" = "$REPOSITORY_EXPECTED_BRANCH" ]
then
    REPOSITORY_BRANCH_GATE="PASS"
fi

echo "REPOSITORY_GIT_REPOSITORY_GATE=${REPOSITORY_GIT_REPOSITORY_GATE}"
echo "REPOSITORY_BRANCH_GATE=${REPOSITORY_BRANCH_GATE}"

echo
echo "----- TRACKED DEPENDENCIES -----"

REPOSITORY_TRACKED_DEPENDENCIES_GATE="PASS"
REPOSITORY_TRACKED_DEPENDENCIES_VALIDATED=0
REPOSITORY_BASH_SCRIPT_COUNT=0
REPOSITORY_SCRIPT_SYNTAX_GATE="PASS"

if ! [[ "$REPOSITORY_TRACKED_DEPENDENCY_COUNT" =~ ^[0-9]+$ ]] ||
   [ "$REPOSITORY_TRACKED_DEPENDENCY_COUNT" -le 0 ]
then
    REPOSITORY_TRACKED_DEPENDENCIES_GATE="FAIL"
else
    for ((
        INDEX = 1;
        INDEX <= REPOSITORY_TRACKED_DEPENDENCY_COUNT;
        INDEX++
    ))
    do
        KEY="$(
            printf \
                'TRACKED_DEPENDENCY_%02d' \
                "$INDEX"
        )"

        DEPENDENCY="$(
            get_value \
                "$REPOSITORY_POLICY" \
                "$KEY"
        )"

        echo "REPOSITORY_${KEY}=${DEPENDENCY}"

        if [ -z "$DEPENDENCY" ] ||
           [ ! -f "$REPO_ROOT/$DEPENDENCY" ]
        then
            REPOSITORY_TRACKED_DEPENDENCIES_GATE="FAIL"
            continue
        fi

        if ! git -C "$REPO_ROOT" \
            ls-files \
            --error-unmatch \
            "$DEPENDENCY" \
            >/dev/null 2>&1
        then
            REPOSITORY_TRACKED_DEPENDENCIES_GATE="FAIL"
            continue
        fi

        if ! git -C "$REPO_ROOT" \
            diff \
            --quiet \
            HEAD \
            -- \
            "$DEPENDENCY"
        then
            REPOSITORY_TRACKED_DEPENDENCIES_GATE="FAIL"
            continue
        fi

        REPOSITORY_TRACKED_DEPENDENCIES_VALIDATED=$((REPOSITORY_TRACKED_DEPENDENCIES_VALIDATED + 1))

        case "$DEPENDENCY" in
            *.sh)
                REPOSITORY_BASH_SCRIPT_COUNT=$((REPOSITORY_BASH_SCRIPT_COUNT + 1))

                if ! bash -n \
                    "$REPO_ROOT/$DEPENDENCY" \
                    >/dev/null 2>&1
                then
                    REPOSITORY_SCRIPT_SYNTAX_GATE="FAIL"
                fi
                ;;
        esac
    done
fi

if [ "$REPOSITORY_TRACKED_DEPENDENCIES_VALIDATED" != "$REPOSITORY_TRACKED_DEPENDENCY_COUNT" ]; then
    REPOSITORY_TRACKED_DEPENDENCIES_GATE="FAIL"
fi

echo "REPOSITORY_TRACKED_DEPENDENCIES_VALIDATED=${REPOSITORY_TRACKED_DEPENDENCIES_VALIDATED}"
echo "REPOSITORY_TRACKED_DEPENDENCIES_GATE=${REPOSITORY_TRACKED_DEPENDENCIES_GATE}"

echo
echo "----- PROMPT 11B DEVELOPMENT SCOPE -----"

REPOSITORY_DEVELOPMENT_SCOPE_GATE="PASS"
REPOSITORY_DEVELOPMENT_FILES_VALIDATED=0

if ! [[ "$REPOSITORY_DEVELOPMENT_FILE_COUNT" =~ ^[0-9]+$ ]] ||
   [ "$REPOSITORY_DEVELOPMENT_FILE_COUNT" -le 0 ]
then
    REPOSITORY_DEVELOPMENT_SCOPE_GATE="FAIL"
else
    for ((
        INDEX = 1;
        INDEX <= REPOSITORY_DEVELOPMENT_FILE_COUNT;
        INDEX++
    ))
    do
        KEY="$(
            printf \
                'PROMPT11B_DEVELOPMENT_FILE_%02d' \
                "$INDEX"
        )"

        DEVELOPMENT_FILE="$(
            get_value \
                "$REPOSITORY_POLICY" \
                "$KEY"
        )"

        echo "REPOSITORY_${KEY}=${DEVELOPMENT_FILE}"

        if [ -z "$DEVELOPMENT_FILE" ] ||
           [ ! -f "$REPO_ROOT/$DEVELOPMENT_FILE" ]
        then
            REPOSITORY_DEVELOPMENT_SCOPE_GATE="FAIL"
            continue
        fi

        REPOSITORY_DEVELOPMENT_FILES_VALIDATED=$((REPOSITORY_DEVELOPMENT_FILES_VALIDATED + 1))

        case "$DEVELOPMENT_FILE" in
            *.sh)
                REPOSITORY_BASH_SCRIPT_COUNT=$((REPOSITORY_BASH_SCRIPT_COUNT + 1))

                if ! bash -n \
                    "$REPO_ROOT/$DEVELOPMENT_FILE" \
                    >/dev/null 2>&1
                then
                    REPOSITORY_SCRIPT_SYNTAX_GATE="FAIL"
                fi
                ;;
        esac
    done
fi

if [ "$REPOSITORY_DEVELOPMENT_FILES_VALIDATED" != "$REPOSITORY_DEVELOPMENT_FILE_COUNT" ]; then
    REPOSITORY_DEVELOPMENT_SCOPE_GATE="FAIL"
fi

if [ "$REPOSITORY_BASH_SCRIPT_COUNT" -ne 4 ]; then
    REPOSITORY_SCRIPT_SYNTAX_GATE="FAIL"
fi

echo "REPOSITORY_DEVELOPMENT_FILES_VALIDATED=${REPOSITORY_DEVELOPMENT_FILES_VALIDATED}"
echo "REPOSITORY_DEVELOPMENT_SCOPE_GATE=${REPOSITORY_DEVELOPMENT_SCOPE_GATE}"
echo "REPOSITORY_BASH_SCRIPT_COUNT=${REPOSITORY_BASH_SCRIPT_COUNT}"
echo "REPOSITORY_SCRIPT_SYNTAX_GATE=${REPOSITORY_SCRIPT_SYNTAX_GATE}"

echo
echo "----- RUNTIME REPRODUCIBILITY DECISION -----"

echo "REPOSITORY_REMOTE_SYNC_CHECKED_BY_RUNTIME_GATE=NO"
echo "REPOSITORY_GLOBAL_CLEAN_WORKTREE_REQUIRED=NO"
echo "REPOSITORY_PROMPT11B_UNTRACKED_FILES_ALLOWED=YES"

for REPOSITORY_GATE_VALUE in \
    "$REPOSITORY_POLICY_GATE" \
    "$REPOSITORY_POLICY_CONTRACT_GATE" \
    "$REPOSITORY_GIT_REPOSITORY_GATE" \
    "$REPOSITORY_BRANCH_GATE" \
    "$REPOSITORY_TRACKED_DEPENDENCIES_GATE" \
    "$REPOSITORY_DEVELOPMENT_SCOPE_GATE" \
    "$REPOSITORY_SCRIPT_SYNTAX_GATE"
do
    if [ "$REPOSITORY_GATE_VALUE" != "PASS" ]; then
        REPOSITORY_REPRODUCIBILITY_GATE="FAIL"
    fi
done

echo "REPOSITORY_REPRODUCIBILITY_GATE=${REPOSITORY_REPRODUCIBILITY_GATE}"

echo
echo "===== EXPECTED RUNTIME ====="

PROJECT="$(get_value "$BASE_LOCK" RUNTIME_PROJECT_NAME)"

EXPECTED_5GC_ID="$(get_value "$PROFILE" TB3_OPEN5GS_IMAGE_ID)"
EXPECTED_UE_ID="$(get_value "$PROFILE" TB3_SRSUE_IMAGE_ID)"
EXPECTED_GNB_ID="$(get_value "$GNB_LOCK" IMAGE_ID)"
EXPECTED_RIC_ID="$(get_value "$RIC_LOCK" IMAGE_ID)"
RIC_NAME="$(get_value "$RIC_LOCK" CONTAINER_NAME)"

echo "EXPECTED_COMPOSE_PROJECT=${PROJECT}"
echo "EXPECTED_RIC_CONTAINER=${RIC_NAME}"

resolve_compose_container()
{
    local service="$1"
    local ids=()

    mapfile -t ids < <(
        docker ps -aq \
            --filter "label=com.docker.compose.project=${PROJECT}" \
            --filter "label=com.docker.compose.service=${service}"
    )

    if [ "${#ids[@]}" -eq 1 ]; then
        printf '%s\n' "${ids[0]}"
    fi
}

check_container()
{
    local role="$1"
    local target="$2"
    local expected_image_id="$3"

    if [ -z "$target" ] ||
       ! docker inspect "$target" >/dev/null 2>&1
    then
        echo "${role}_EXISTS=FAIL"
        return 1
    fi

    echo "${role}_EXISTS=PASS"

    local running
    local actual_image_id

    running="$(docker inspect "$target" --format '{{.State.Running}}')"
    actual_image_id="$(docker inspect "$target" --format '{{.Image}}')"

    docker inspect "$target" --format \
"${role}_NAME={{.Name}}
${role}_PID={{.State.Pid}}
${role}_STARTED_AT={{.State.StartedAt}}
${role}_RESTART_COUNT={{.RestartCount}}
${role}_OOM_KILLED={{.State.OOMKilled}}
${role}_EXIT_CODE={{.State.ExitCode}}
${role}_HEALTH={{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}
${role}_IMAGE_REF={{.Config.Image}}
${role}_IMAGE_ID={{.Image}}
${role}_NETWORK_MODE={{.HostConfig.NetworkMode}}"

    if [ "$running" = "true" ]; then
        echo "${role}_RUNNING=PASS"
    else
        echo "${role}_RUNNING=FAIL"
        return 1
    fi

    echo "${role}_EXPECTED_IMAGE_ID=${expected_image_id}"

    if [ "$actual_image_id" = "$expected_image_id" ]; then
        echo "${role}_IMAGE_IDENTITY=PASS"
    else
        echo "${role}_IMAGE_IDENTITY=FAIL"
        return 1
    fi

    return 0
}

echo
echo "===== CONTAINERS ====="

CONTAINER_READINESS_GATE="PASS"

CID_5GC="$(resolve_compose_container 5gc)"
CID_GNB="$(resolve_compose_container gnb)"
CID_UE="$(resolve_compose_container srsue)"

check_container "5GC" "$CID_5GC" "$EXPECTED_5GC_ID" ||
    CONTAINER_READINESS_GATE="FAIL"

check_container "GNB" "$CID_GNB" "$EXPECTED_GNB_ID" ||
    CONTAINER_READINESS_GATE="FAIL"

check_container "UE" "$CID_UE" "$EXPECTED_UE_ID" ||
    CONTAINER_READINESS_GATE="FAIL"

check_container "RIC" "$RIC_NAME" "$EXPECTED_RIC_ID" ||
    CONTAINER_READINESS_GATE="FAIL"

echo "CONTAINER_READINESS_GATE=${CONTAINER_READINESS_GATE}"

echo
echo "===== NETWORK ====="

NETWORK_READINESS_GATE="PASS"

NETWORK_KEY="$(get_value "$BASE_LOCK" RUNTIME_NETWORK)"
EXPECTED_SUBNET="$(get_value "$BASE_LOCK" RUNTIME_SUBNET)"
EXPECTED_NETWORK="${PROJECT}_${NETWORK_KEY}"

EXPECTED_5GC_IP="$(
    awk '
        /^[[:space:]]*amf:/ {inside=1; next}
        inside && /^[[:space:]]*addr:/ {
            print $2
            exit
        }
    ' "$GNB_CFG"
)"

EXPECTED_GNB_IP="$(
    awk '
        /^[[:space:]]*bind_addr:/ {
            print $2
            exit
        }
    ' "$GNB_CFG"
)"

EXPECTED_RIC_IP="$(get_value "$RIC_LOCK" RIC_IP)"

echo "EXPECTED_NETWORK=${EXPECTED_NETWORK}"
echo "EXPECTED_SUBNET=${EXPECTED_SUBNET}"
echo "EXPECTED_5GC_IP=${EXPECTED_5GC_IP}"
echo "EXPECTED_GNB_IP=${EXPECTED_GNB_IP}"
echo "EXPECTED_RIC_IP=${EXPECTED_RIC_IP}"

if docker network inspect "$EXPECTED_NETWORK" >/dev/null 2>&1; then
    echo "DOCKER_NETWORK_EXISTENCE_GATE=PASS"

    ACTUAL_SUBNET="$(
        docker network inspect "$EXPECTED_NETWORK" \
            --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}'
    )"

    ACTUAL_GATEWAY="$(
        docker network inspect "$EXPECTED_NETWORK" \
            --format '{{range .IPAM.Config}}{{.Gateway}}{{end}}'
    )"

    echo "ACTUAL_SUBNET=${ACTUAL_SUBNET}"
    echo "ACTUAL_GATEWAY=${ACTUAL_GATEWAY}"

    if [ "$ACTUAL_SUBNET" = "$EXPECTED_SUBNET" ]; then
        echo "DOCKER_NETWORK_SUBNET_GATE=PASS"
    else
        echo "DOCKER_NETWORK_SUBNET_GATE=FAIL"
        NETWORK_READINESS_GATE="FAIL"
    fi
else
    echo "DOCKER_NETWORK_EXISTENCE_GATE=FAIL"
    NETWORK_READINESS_GATE="FAIL"
fi

network_container_ip()
{
    local target="$1"

    if [ -z "$target" ] ||
       ! docker inspect "$target" >/dev/null 2>&1
    then
        printf '%s\n' ""
        return 0
    fi

    docker inspect "$target" \
        --format "{{with index .NetworkSettings.Networks \"$EXPECTED_NETWORK\"}}{{.IPAddress}}{{end}}" \
        2>/dev/null || true
}

ACTUAL_5GC_IP="$(network_container_ip "$CID_5GC")"
ACTUAL_GNB_IP="$(network_container_ip "$CID_GNB")"
ACTUAL_UE_IP="$(network_container_ip "$CID_UE")"
ACTUAL_RIC_IP="$(network_container_ip "$RIC_NAME")"

echo "ACTUAL_5GC_IP=${ACTUAL_5GC_IP}"
echo "ACTUAL_GNB_IP=${ACTUAL_GNB_IP}"
echo "ACTUAL_UE_IP=${ACTUAL_UE_IP}"
echo "ACTUAL_RIC_IP=${ACTUAL_RIC_IP}"

if [ -n "$ACTUAL_5GC_IP" ]; then
    echo "5GC_NETWORK_MEMBER_GATE=PASS"
else
    echo "5GC_NETWORK_MEMBER_GATE=FAIL"
    NETWORK_READINESS_GATE="FAIL"
fi

if [ -n "$ACTUAL_GNB_IP" ]; then
    echo "GNB_NETWORK_MEMBER_GATE=PASS"
else
    echo "GNB_NETWORK_MEMBER_GATE=FAIL"
    NETWORK_READINESS_GATE="FAIL"
fi

if [ -n "$ACTUAL_UE_IP" ]; then
    echo "UE_NETWORK_MEMBER_GATE=PASS"
else
    echo "UE_NETWORK_MEMBER_GATE=FAIL"
    NETWORK_READINESS_GATE="FAIL"
fi

if [ -n "$ACTUAL_RIC_IP" ]; then
    echo "RIC_NETWORK_MEMBER_GATE=PASS"
else
    echo "RIC_NETWORK_MEMBER_GATE=FAIL"
    NETWORK_READINESS_GATE="FAIL"
fi

if [ "$ACTUAL_5GC_IP" = "$EXPECTED_5GC_IP" ]; then
    echo "5GC_NETWORK_IP_GATE=PASS"
else
    echo "5GC_NETWORK_IP_GATE=FAIL"
    NETWORK_READINESS_GATE="FAIL"
fi

if [ "$ACTUAL_GNB_IP" = "$EXPECTED_GNB_IP" ]; then
    echo "GNB_NETWORK_IP_GATE=PASS"
else
    echo "GNB_NETWORK_IP_GATE=FAIL"
    NETWORK_READINESS_GATE="FAIL"
fi

if [ "$ACTUAL_RIC_IP" = "$EXPECTED_RIC_IP" ]; then
    echo "RIC_NETWORK_IP_GATE=PASS"
else
    echo "RIC_NETWORK_IP_GATE=FAIL"
    NETWORK_READINESS_GATE="FAIL"
fi

if [ -n "$ACTUAL_UE_IP" ]; then
    echo "UE_NETWORK_IP_PRESENT_GATE=PASS"
else
    echo "UE_NETWORK_IP_PRESENT_GATE=FAIL"
    NETWORK_READINESS_GATE="FAIL"
fi

echo "NETWORK_READINESS_GATE=${NETWORK_READINESS_GATE}"

echo
echo "===== ZMQ ====="

ZMQ_READINESS_GATE="PASS"

GNB_ZMQ_LISTEN_PORT="$(
    sed -n \
        's/.*tx_port=tcp:\/\/\*:\([0-9][0-9]*\).*/\1/p' \
        "$GNB_CFG" |
    head -n 1
)"

GNB_ZMQ_PEER_PORT="$(
    sed -n \
        's/.*rx_port=tcp:\/\/srsue:\([0-9][0-9]*\).*/\1/p' \
        "$GNB_CFG" |
    head -n 1
)"

UE_ZMQ_LISTEN_PORT="$(
    sed -n \
        's/.*tx_port=tcp:\/\/\*:\([0-9][0-9]*\).*/\1/p' \
        "$UE_CFG" |
    head -n 1
)"

UE_ZMQ_PEER_PORT="$(
    sed -n \
        's/.*rx_port=tcp:\/\/gnb:\([0-9][0-9]*\).*/\1/p' \
        "$UE_CFG" |
    head -n 1
)"

echo "GNB_ZMQ_LISTEN_PORT=${GNB_ZMQ_LISTEN_PORT}"
echo "GNB_ZMQ_PEER_PORT=${GNB_ZMQ_PEER_PORT}"
echo "UE_ZMQ_LISTEN_PORT=${UE_ZMQ_LISTEN_PORT}"
echo "UE_ZMQ_PEER_PORT=${UE_ZMQ_PEER_PORT}"

if [ -z "$GNB_ZMQ_LISTEN_PORT" ] ||
   [ -z "$GNB_ZMQ_PEER_PORT" ] ||
   [ -z "$UE_ZMQ_LISTEN_PORT" ] ||
   [ -z "$UE_ZMQ_PEER_PORT" ] ||
   [ "$GNB_ZMQ_LISTEN_PORT" != "$UE_ZMQ_PEER_PORT" ] ||
   [ "$UE_ZMQ_LISTEN_PORT" != "$GNB_ZMQ_PEER_PORT" ]
then
    echo "ZMQ_CONFIG_COHERENCE_GATE=FAIL"
    ZMQ_READINESS_GATE="FAIL"
else
    echo "ZMQ_CONFIG_COHERENCE_GATE=PASS"
fi

ZMQ_TMP="$(
    mktemp -d \
        "${TMPDIR:-/tmp}/sci-oran-doctor-zmq.XXXXXX"
)"

cleanup_zmq_tmp()
{
    rm -rf "$ZMQ_TMP"
}

trap cleanup_zmq_tmp EXIT

ZMQ_CAPTURE_GATE="PASS"

for snap in 1 2 3
do
    if docker exec "$CID_GNB" cat /proc/net/tcp \
        > "${ZMQ_TMP}/gnb-${snap}.tcp"
    then
        echo "GNB_ZMQ_TCP_CAPTURE_${snap}=PASS"
    else
        echo "GNB_ZMQ_TCP_CAPTURE_${snap}=FAIL"
        ZMQ_CAPTURE_GATE="FAIL"
    fi

    if docker exec "$CID_UE" cat /proc/net/tcp \
        > "${ZMQ_TMP}/ue-${snap}.tcp"
    then
        echo "UE_ZMQ_TCP_CAPTURE_${snap}=PASS"
    else
        echo "UE_ZMQ_TCP_CAPTURE_${snap}=FAIL"
        ZMQ_CAPTURE_GATE="FAIL"
    fi

    if [ "$snap" -lt 3 ]; then
        sleep 1
    fi
done

echo "ZMQ_TCP_CAPTURE_GATE=${ZMQ_CAPTURE_GATE}"

if [ "$ZMQ_CAPTURE_GATE" != "PASS" ]; then
    ZMQ_READINESS_GATE="FAIL"
else
    ZMQ_ANALYSIS="$(
        python3 - \
            "$ZMQ_TMP" \
            "$ACTUAL_GNB_IP" \
            "$ACTUAL_UE_IP" \
            "$GNB_ZMQ_LISTEN_PORT" \
            "$UE_ZMQ_LISTEN_PORT" <<'PY_ZMQ'
import socket
import struct
import sys
from pathlib import Path

root = Path(sys.argv[1])
gnb_ip = sys.argv[2]
ue_ip = sys.argv[3]
gnb_listen = int(sys.argv[4])
ue_listen = int(sys.argv[5])

TCP_ESTABLISHED = "01"
TCP_LISTEN = "0A"

def decode_ipv4(value):
    raw = struct.pack("<I", int(value, 16))
    return socket.inet_ntoa(raw)

def decode_endpoint(value):
    addr_hex, port_hex = value.split(":")
    return decode_ipv4(addr_hex), int(port_hex, 16)

def read_tcp(path):
    rows = []

    with path.open("r", encoding="utf-8") as f:
        next(f)

        for line in f:
            parts = line.split()

            if len(parts) < 4:
                continue

            local_ip, local_port = decode_endpoint(parts[1])
            remote_ip, remote_port = decode_endpoint(parts[2])

            rows.append({
                "local_ip": local_ip,
                "local_port": local_port,
                "remote_ip": remote_ip,
                "remote_port": remote_port,
                "state": parts[3],
            })

    return rows

overall = True

for snap in range(1, 4):
    gnb = read_tcp(root / f"gnb-{snap}.tcp")
    ue = read_tcp(root / f"ue-{snap}.tcp")

    checks = {
        "GNB_LISTEN": any(
            r["local_port"] == gnb_listen
            and r["state"] == TCP_LISTEN
            for r in gnb
        ),
        "UE_LISTEN": any(
            r["local_port"] == ue_listen
            and r["state"] == TCP_LISTEN
            for r in ue
        ),
        "GNB_TO_UE_ESTABLISHED": any(
            r["remote_ip"] == ue_ip
            and r["remote_port"] == ue_listen
            and r["state"] == TCP_ESTABLISHED
            for r in gnb
        ),
        "UE_ACCEPT_GNB_ESTABLISHED": any(
            r["local_port"] == ue_listen
            and r["remote_ip"] == gnb_ip
            and r["state"] == TCP_ESTABLISHED
            for r in ue
        ),
        "UE_TO_GNB_ESTABLISHED": any(
            r["remote_ip"] == gnb_ip
            and r["remote_port"] == gnb_listen
            and r["state"] == TCP_ESTABLISHED
            for r in ue
        ),
        "GNB_ACCEPT_UE_ESTABLISHED": any(
            r["local_port"] == gnb_listen
            and r["remote_ip"] == ue_ip
            and r["state"] == TCP_ESTABLISHED
            for r in gnb
        ),
    }

    snapshot_ok = all(checks.values())
    overall = overall and snapshot_ok

    for name, value in checks.items():
        print(
            f"SNAPSHOT_{snap}_{name}="
            f"{'PASS' if value else 'FAIL'}"
        )

    print(
        f"SNAPSHOT_{snap}_ZMQ_SOCKET_GATE="
        f"{'PASS' if snapshot_ok else 'FAIL'}"
    )

print(
    "ZMQ_STABILITY_GATE="
    + ("PASS" if overall else "FAIL")
)

print(
    "ZMQ_ANALYSIS_GATE="
    + ("PASS" if overall else "FAIL")
)
PY_ZMQ
    )"

    printf '%s\n' "$ZMQ_ANALYSIS"

    if printf '%s\n' "$ZMQ_ANALYSIS" |
       grep -Fxq "ZMQ_ANALYSIS_GATE=PASS"
    then
        :
    else
        ZMQ_READINESS_GATE="FAIL"
    fi
fi

echo "ZMQ_READINESS_GATE=${ZMQ_READINESS_GATE}"

echo
echo "===== N2 SCTP ====="

N2_READINESS_GATE="PASS"

N2_AMF_IP="$(
    awk '
        /^[[:space:]]*amf:/ {inside=1; next}
        inside && /^[[:space:]]*addr:/ {
            print $2
            exit
        }
    ' "$GNB_CFG"
)"

N2_AMF_PORT="$(
    awk '
        /^[[:space:]]*amf:/ {inside=1; next}
        inside && /^[[:space:]]*port:/ {
            print $2
            exit
        }
    ' "$GNB_CFG"
)"

N2_GNB_IP="$(
    awk '
        /^[[:space:]]*amf:/ {inside=1; next}
        inside && /^[[:space:]]*bind_addr:/ {
            print $2
            exit
        }
    ' "$GNB_CFG"
)"

echo "N2_GNB_IP=${N2_GNB_IP}"
echo "N2_AMF_IP=${N2_AMF_IP}"
echo "N2_AMF_PORT=${N2_AMF_PORT}"

if [ -z "$N2_GNB_IP" ] ||
   [ -z "$N2_AMF_IP" ] ||
   [ -z "$N2_AMF_PORT" ]
then
    echo "N2_CONFIG_CONTRACT_GATE=FAIL"
    N2_READINESS_GATE="FAIL"
else
    echo "N2_CONFIG_CONTRACT_GATE=PASS"
fi

N2_PROC_GATE="PASS"

if [ -n "$CID_GNB" ] &&
   docker exec "$CID_GNB" test -r /proc/net/sctp/assocs
then
    echo "GNB_SCTP_PROC_GATE=PASS"
else
    echo "GNB_SCTP_PROC_GATE=FAIL"
    N2_PROC_GATE="FAIL"
fi

if [ -n "$CID_5GC" ] &&
   docker exec "$CID_5GC" test -r /proc/net/sctp/assocs
then
    echo "5GC_SCTP_PROC_GATE=PASS"
else
    echo "5GC_SCTP_PROC_GATE=FAIL"
    N2_PROC_GATE="FAIL"
fi

echo "N2_SCTP_PROC_CHANNEL_GATE=${N2_PROC_GATE}"

if [ "$N2_PROC_GATE" != "PASS" ]; then
    N2_READINESS_GATE="FAIL"
else
    N2_TMP="$(
        mktemp -d \
            "${TMPDIR:-/tmp}/sci-oran-doctor-n2.XXXXXX"
    )"

    N2_CAPTURE_GATE="PASS"

    for snap in 1 2 3
    do
        if docker exec "$CID_GNB" cat /proc/net/sctp/assocs \
            > "${N2_TMP}/gnb-${snap}.assocs"
        then
            echo "GNB_N2_SCTP_CAPTURE_${snap}=PASS"
        else
            echo "GNB_N2_SCTP_CAPTURE_${snap}=FAIL"
            N2_CAPTURE_GATE="FAIL"
        fi

        if docker exec "$CID_5GC" cat /proc/net/sctp/assocs \
            > "${N2_TMP}/5gc-${snap}.assocs"
        then
            echo "5GC_N2_SCTP_CAPTURE_${snap}=PASS"
        else
            echo "5GC_N2_SCTP_CAPTURE_${snap}=FAIL"
            N2_CAPTURE_GATE="FAIL"
        fi

        if [ "$snap" -lt 3 ]; then
            sleep 1
        fi
    done

    echo "N2_SCTP_CAPTURE_GATE=${N2_CAPTURE_GATE}"

    if [ "$N2_CAPTURE_GATE" != "PASS" ]; then
        N2_READINESS_GATE="FAIL"
    else
        N2_ANALYSIS="$(
            python3 - \
                "$N2_TMP" \
                "$N2_GNB_IP" \
                "$N2_AMF_IP" \
                "$N2_AMF_PORT" <<'PY_N2'
from pathlib import Path
import sys

root = Path(sys.argv[1])
gnb_ip = sys.argv[2]
amf_ip = sys.argv[3]
amf_port = int(sys.argv[4])

# Kernel state value printed by /proc/net/sctp/assocs
# for an established SCTP association.
SCTP_KERNEL_ESTABLISHED = 3

# Fields following the remote address list:
# HBINT INS OUTS MAXRT T1X T2X RTXC wmema wmemq sndbuf rcvbuf
TRAILING_FIELDS = 11


def clean_addr(value):
    return value.lstrip("*")


def parse_assocs(path):
    rows = []

    with path.open("r", encoding="utf-8") as f:
        next(f, None)

        for raw in f:
            parts = raw.split()

            if len(parts) < 26 or "<->" not in parts:
                continue

            try:
                sep = parts.index("<->")
                remote_end = len(parts) - TRAILING_FIELDS

                if sep <= 13 or remote_end <= sep + 1:
                    continue

                rows.append({
                    "state": int(parts[4]),
                    "assoc_id": parts[6],
                    "lport": int(parts[11]),
                    "rport": int(parts[12]),
                    "laddrs": [
                        clean_addr(x)
                        for x in parts[13:sep]
                    ],
                    "raddrs": [
                        clean_addr(x)
                        for x in parts[sep + 1:remote_end]
                    ],
                })

            except (ValueError, IndexError):
                continue

    return rows


def gnb_candidates(rows):
    return [
        row for row in rows
        if row["rport"] == amf_port
        and gnb_ip in row["laddrs"]
        and amf_ip in row["raddrs"]
    ]


def core_candidates(rows):
    return [
        row for row in rows
        if row["lport"] == amf_port
        and amf_ip in row["laddrs"]
        and gnb_ip in row["raddrs"]
    ]


overall = True
gnb_ids = []
core_ids = []

for snap in range(1, 4):

    gnb_rows = parse_assocs(
        root / f"gnb-{snap}.assocs"
    )

    core_rows = parse_assocs(
        root / f"5gc-{snap}.assocs"
    )

    gnb = gnb_candidates(gnb_rows)
    core = core_candidates(core_rows)

    gnb_present = bool(gnb)
    core_present = bool(core)

    gnb_established = any(
        row["state"] == SCTP_KERNEL_ESTABLISHED
        for row in gnb
    )

    core_established = any(
        row["state"] == SCTP_KERNEL_ESTABLISHED
        for row in core
    )

    gnb_id = (
        ",".join(sorted({row["assoc_id"] for row in gnb}))
        if gnb else "NONE"
    )

    core_id = (
        ",".join(sorted({row["assoc_id"] for row in core}))
        if core else "NONE"
    )

    gnb_ids.append(gnb_id)
    core_ids.append(core_id)

    snapshot_ok = (
        gnb_present
        and core_present
        and gnb_established
        and core_established
    )

    overall = overall and snapshot_ok

    print(
        f"SNAPSHOT_{snap}_GNB_N2_ASSOCIATION_PRESENT="
        f"{'PASS' if gnb_present else 'FAIL'}"
    )

    print(
        f"SNAPSHOT_{snap}_5GC_N2_ASSOCIATION_PRESENT="
        f"{'PASS' if core_present else 'FAIL'}"
    )

    print(
        f"SNAPSHOT_{snap}_GNB_N2_ESTABLISHED="
        f"{'PASS' if gnb_established else 'FAIL'}"
    )

    print(
        f"SNAPSHOT_{snap}_5GC_N2_ESTABLISHED="
        f"{'PASS' if core_established else 'FAIL'}"
    )

    print(f"SNAPSHOT_{snap}_GNB_ASSOC_ID={gnb_id}")
    print(f"SNAPSHOT_{snap}_5GC_ASSOC_ID={core_id}")

    for row in gnb:
        print(
            "GNB_N2_ASSOC "
            f"ST={row['state']} "
            f"LPORT={row['lport']} "
            f"RPORT={row['rport']} "
            f"LADDRS={','.join(row['laddrs'])} "
            f"RADDRS={','.join(row['raddrs'])}"
        )

    for row in core:
        print(
            "5GC_N2_ASSOC "
            f"ST={row['state']} "
            f"LPORT={row['lport']} "
            f"RPORT={row['rport']} "
            f"LADDRS={','.join(row['laddrs'])} "
            f"RADDRS={','.join(row['raddrs'])}"
        )

    print(
        f"SNAPSHOT_{snap}_N2_ASSOCIATION_GATE="
        f"{'PASS' if snapshot_ok else 'FAIL'}"
    )


gnb_stable = (
    len(set(gnb_ids)) == 1
    and gnb_ids[0] != "NONE"
)

core_stable = (
    len(set(core_ids)) == 1
    and core_ids[0] != "NONE"
)

stable = overall and gnb_stable and core_stable

print(
    "N2_GNB_ASSOC_ID_STABILITY_GATE="
    + ("PASS" if gnb_stable else "FAIL")
)

print(
    "N2_5GC_ASSOC_ID_STABILITY_GATE="
    + ("PASS" if core_stable else "FAIL")
)

print(
    "N2_ASSOCIATION_STABILITY_GATE="
    + ("PASS" if stable else "FAIL")
)

print(
    "N2_ANALYSIS_GATE="
    + ("PASS" if stable else "FAIL")
)
PY_N2
        )"

        printf '%s\n' "$N2_ANALYSIS"

        if printf '%s\n' "$N2_ANALYSIS" |
           grep -Fxq "N2_ANALYSIS_GATE=PASS"
        then
            :
        else
            N2_READINESS_GATE="FAIL"
        fi
    fi

    rm -rf "$N2_TMP"
fi

echo "N2_READINESS_GATE=${N2_READINESS_GATE}"

echo
echo "===== E2 SCTP ====="

E2_READINESS_GATE="PASS"

E2_RIC_IP="$(get_value "$RIC_LOCK" RIC_IP)"
E2_RIC_PORT="$(get_value "$RIC_LOCK" E2_PORT)"
E2_GNB_IP="$ACTUAL_GNB_IP"

echo "E2_GNB_IP=${E2_GNB_IP}"
echo "E2_RIC_IP=${E2_RIC_IP}"
echo "E2_RIC_PORT=${E2_RIC_PORT}"

if [ -z "$E2_GNB_IP" ] ||
   [ -z "$E2_RIC_IP" ] ||
   [ -z "$E2_RIC_PORT" ] ||
   [ "$ACTUAL_RIC_IP" != "$E2_RIC_IP" ]
then
    echo "E2_RUNTIME_CONTRACT_GATE=FAIL"
    E2_READINESS_GATE="FAIL"
else
    echo "E2_RUNTIME_CONTRACT_GATE=PASS"
fi

E2_PROC_GATE="PASS"

if [ -n "$CID_GNB" ] &&
   docker exec "$CID_GNB" test -r /proc/net/sctp/assocs
then
    echo "GNB_E2_SCTP_PROC_GATE=PASS"
else
    echo "GNB_E2_SCTP_PROC_GATE=FAIL"
    E2_PROC_GATE="FAIL"
fi

if [ -n "$RIC_NAME" ] &&
   docker exec "$RIC_NAME" test -r /proc/net/sctp/assocs
then
    echo "RIC_E2_SCTP_PROC_GATE=PASS"
else
    echo "RIC_E2_SCTP_PROC_GATE=FAIL"
    E2_PROC_GATE="FAIL"
fi

echo "E2_SCTP_PROC_CHANNEL_GATE=${E2_PROC_GATE}"

if [ "$E2_PROC_GATE" != "PASS" ]; then
    E2_READINESS_GATE="FAIL"
else
    E2_TMP="$(
        mktemp -d \
            "${TMPDIR:-/tmp}/sci-oran-doctor-e2.XXXXXX"
    )"

    E2_CAPTURE_GATE="PASS"

    for snap in 1 2 3
    do
        if docker exec "$CID_GNB" cat /proc/net/sctp/assocs \
            > "${E2_TMP}/gnb-${snap}.assocs"
        then
            echo "GNB_E2_SCTP_CAPTURE_${snap}=PASS"
        else
            echo "GNB_E2_SCTP_CAPTURE_${snap}=FAIL"
            E2_CAPTURE_GATE="FAIL"
        fi

        if docker exec "$RIC_NAME" cat /proc/net/sctp/assocs \
            > "${E2_TMP}/ric-${snap}.assocs"
        then
            echo "RIC_E2_SCTP_CAPTURE_${snap}=PASS"
        else
            echo "RIC_E2_SCTP_CAPTURE_${snap}=FAIL"
            E2_CAPTURE_GATE="FAIL"
        fi

        if [ "$snap" -lt 3 ]; then
            sleep 1
        fi
    done

    echo "E2_SCTP_CAPTURE_GATE=${E2_CAPTURE_GATE}"

    if [ "$E2_CAPTURE_GATE" != "PASS" ]; then
        E2_READINESS_GATE="FAIL"
    else
        E2_ANALYSIS="$(
            python3 - \
                "$E2_TMP" \
                "$E2_GNB_IP" \
                "$E2_RIC_IP" \
                "$E2_RIC_PORT" <<'PY_E2'
from pathlib import Path
import sys

root = Path(sys.argv[1])
gnb_ip = sys.argv[2]
ric_ip = sys.argv[3]
e2_port = int(sys.argv[4])

SCTP_KERNEL_ESTABLISHED = 3
TRAILING_FIELDS = 11


def clean_addr(value):
    return value.lstrip("*")


def parse_assocs(path):
    rows = []

    with path.open("r", encoding="utf-8") as f:
        next(f, None)

        for raw in f:
            parts = raw.split()

            if "<->" not in parts:
                continue

            try:
                sep = parts.index("<->")
                remote_end = len(parts) - TRAILING_FIELDS

                if sep <= 13 or remote_end <= sep + 1:
                    continue

                rows.append({
                    "state": int(parts[4]),
                    "assoc_id": parts[6],
                    "lport": int(parts[11]),
                    "rport": int(parts[12]),
                    "laddrs": [
                        clean_addr(x)
                        for x in parts[13:sep]
                    ],
                    "raddrs": [
                        clean_addr(x)
                        for x in parts[sep + 1:remote_end]
                    ],
                })

            except (ValueError, IndexError):
                continue

    return rows


def gnb_candidates(rows):
    return [
        row for row in rows
        if row["rport"] == e2_port
        and gnb_ip in row["laddrs"]
        and ric_ip in row["raddrs"]
    ]


def ric_candidates(rows):
    return [
        row for row in rows
        if row["lport"] == e2_port
        and ric_ip in row["laddrs"]
        and gnb_ip in row["raddrs"]
    ]


overall = True
gnb_ids = []
ric_ids = []

for snap in range(1, 4):

    gnb_rows = parse_assocs(
        root / f"gnb-{snap}.assocs"
    )

    ric_rows = parse_assocs(
        root / f"ric-{snap}.assocs"
    )

    gnb = gnb_candidates(gnb_rows)
    ric = ric_candidates(ric_rows)

    gnb_present = bool(gnb)
    ric_present = bool(ric)

    gnb_established = any(
        row["state"] == SCTP_KERNEL_ESTABLISHED
        for row in gnb
    )

    ric_established = any(
        row["state"] == SCTP_KERNEL_ESTABLISHED
        for row in ric
    )

    gnb_id = (
        ",".join(sorted({row["assoc_id"] for row in gnb}))
        if gnb else "NONE"
    )

    ric_id = (
        ",".join(sorted({row["assoc_id"] for row in ric}))
        if ric else "NONE"
    )

    gnb_ids.append(gnb_id)
    ric_ids.append(ric_id)

    snapshot_ok = (
        gnb_present
        and ric_present
        and gnb_established
        and ric_established
    )

    overall = overall and snapshot_ok

    print(
        f"SNAPSHOT_{snap}_GNB_E2_ASSOCIATION_PRESENT="
        f"{'PASS' if gnb_present else 'FAIL'}"
    )

    print(
        f"SNAPSHOT_{snap}_RIC_E2_ASSOCIATION_PRESENT="
        f"{'PASS' if ric_present else 'FAIL'}"
    )

    print(
        f"SNAPSHOT_{snap}_GNB_E2_ESTABLISHED="
        f"{'PASS' if gnb_established else 'FAIL'}"
    )

    print(
        f"SNAPSHOT_{snap}_RIC_E2_ESTABLISHED="
        f"{'PASS' if ric_established else 'FAIL'}"
    )

    print(
        f"SNAPSHOT_{snap}_GNB_E2_ASSOC_ID={gnb_id}"
    )

    print(
        f"SNAPSHOT_{snap}_RIC_E2_ASSOC_ID={ric_id}"
    )

    for row in gnb:
        print(
            "GNB_E2_ASSOC "
            f"ST={row['state']} "
            f"LPORT={row['lport']} "
            f"RPORT={row['rport']} "
            f"LADDRS={','.join(row['laddrs'])} "
            f"RADDRS={','.join(row['raddrs'])}"
        )

    for row in ric:
        print(
            "RIC_E2_ASSOC "
            f"ST={row['state']} "
            f"LPORT={row['lport']} "
            f"RPORT={row['rport']} "
            f"LADDRS={','.join(row['laddrs'])} "
            f"RADDRS={','.join(row['raddrs'])}"
        )

    print(
        f"SNAPSHOT_{snap}_E2_ASSOCIATION_GATE="
        f"{'PASS' if snapshot_ok else 'FAIL'}"
    )


gnb_stable = (
    len(set(gnb_ids)) == 1
    and gnb_ids[0] != "NONE"
)

ric_stable = (
    len(set(ric_ids)) == 1
    and ric_ids[0] != "NONE"
)

stable = overall and gnb_stable and ric_stable

print(
    "E2_GNB_ASSOC_ID_STABILITY_GATE="
    + ("PASS" if gnb_stable else "FAIL")
)

print(
    "E2_RIC_ASSOC_ID_STABILITY_GATE="
    + ("PASS" if ric_stable else "FAIL")
)

print(
    "E2_ASSOCIATION_STABILITY_GATE="
    + ("PASS" if stable else "FAIL")
)

print(
    "E2_ANALYSIS_GATE="
    + ("PASS" if stable else "FAIL")
)
PY_E2
        )"

        printf '%s\n' "$E2_ANALYSIS"

        if printf '%s\n' "$E2_ANALYSIS" |
           grep -Fxq "E2_ANALYSIS_GATE=PASS"
        then
            :
        else
            E2_READINESS_GATE="FAIL"
        fi
    fi

    rm -rf "$E2_TMP"
fi

echo "E2_READINESS_GATE=${E2_READINESS_GATE}"

echo
echo "===== E2SM-RC ====="

E2SM_RC_READINESS_GATE="PASS"

echo "EXPECTED_RAN_FUNCTION_ID=3"
echo "EXPECTED_SERVICE_MODEL=ORAN-E2SM-RC"

echo
echo "----- PROCESS FINGERPRINT BEFORE -----"

RC_GNB_PID_BEFORE="$(
    docker inspect "$CID_GNB" \
        --format '{{.State.Pid}}' \
        2>/dev/null || true
)"

RC_GNB_STARTED_BEFORE="$(
    docker inspect "$CID_GNB" \
        --format '{{.State.StartedAt}}' \
        2>/dev/null || true
)"

RC_GNB_RESTART_BEFORE="$(
    docker inspect "$CID_GNB" \
        --format '{{.RestartCount}}' \
        2>/dev/null || true
)"

RC_RIC_PID_BEFORE="$(
    docker inspect "$RIC_NAME" \
        --format '{{.State.Pid}}' \
        2>/dev/null || true
)"

RC_RIC_STARTED_BEFORE="$(
    docker inspect "$RIC_NAME" \
        --format '{{.State.StartedAt}}' \
        2>/dev/null || true
)"

RC_RIC_RESTART_BEFORE="$(
    docker inspect "$RIC_NAME" \
        --format '{{.RestartCount}}' \
        2>/dev/null || true
)"

echo "E2SM_RC_GNB_PID=${RC_GNB_PID_BEFORE}"
echo "E2SM_RC_GNB_STARTED_AT=${RC_GNB_STARTED_BEFORE}"
echo "E2SM_RC_GNB_RESTART_COUNT=${RC_GNB_RESTART_BEFORE}"

echo "E2SM_RC_RIC_PID=${RC_RIC_PID_BEFORE}"
echo "E2SM_RC_RIC_STARTED_AT=${RC_RIC_STARTED_BEFORE}"
echo "E2SM_RC_RIC_RESTART_COUNT=${RC_RIC_RESTART_BEFORE}"

if [ -z "$RC_GNB_PID_BEFORE" ] ||
   [ -z "$RC_GNB_STARTED_BEFORE" ] ||
   [ -z "$RC_RIC_PID_BEFORE" ] ||
   [ -z "$RC_RIC_STARTED_BEFORE" ]
then
    echo "E2SM_RC_RUNTIME_FINGERPRINT_GATE=FAIL"
    E2SM_RC_READINESS_GATE="FAIL"
else
    echo "E2SM_RC_RUNTIME_FINGERPRINT_GATE=PASS"
fi

RC_TMP="$(
    mktemp -d \
        "${TMPDIR:-/tmp}/sci-oran-doctor-e2sm-rc.XXXXXX"
)"

RC_LOG="${RC_TMP}/ric-current.log"

echo
echo "----- CURRENT RIC LOG -----"

if [ -n "$RC_RIC_STARTED_BEFORE" ] &&
   docker logs \
       --timestamps \
       --since "$RC_RIC_STARTED_BEFORE" \
       "$RIC_NAME" \
       > "$RC_LOG" 2>&1
then
    echo "E2SM_RC_CURRENT_LOG_CAPTURE_GATE=PASS"
else
    echo "E2SM_RC_CURRENT_LOG_CAPTURE_GATE=FAIL"
    E2SM_RC_READINESS_GATE="FAIL"
    : > "$RC_LOG"
fi

RC_LOAD_LINE="$(
    grep -Ei \
        'Loading SM ID[[:space:]]*=[[:space:]]*3[[:space:]]+with def[[:space:]]*=[[:space:]]*ORAN-E2SM-RC' \
        "$RC_LOG" |
    head -n 1 ||
    true
)"

RC_SETUP_LINE="$(
    grep -Ei \
        'E2 SETUP-REQUEST rx' \
        "$RC_LOG" |
    head -n 1 ||
    true
)"

RC_ACCEPT_LINE="$(
    grep -Ei \
        'Accepting RAN function ID[[:space:]]*3[[:space:]]+with def[[:space:]]*=[[:space:]]*ORAN-E2SM-RC' \
        "$RC_LOG" |
    head -n 1 ||
    true
)"

echo
echo "----- EXACT CURRENT-SESSION EVENTS -----"

printf 'E2SM_RC_LOAD_EVENT=%s\n' \
    "${RC_LOAD_LINE:-MISSING}"

printf 'E2_SETUP_REQUEST_EVENT=%s\n' \
    "${RC_SETUP_LINE:-MISSING}"

printf 'RAN_FUNCTION_3_ACCEPT_EVENT=%s\n' \
    "${RC_ACCEPT_LINE:-MISSING}"

if [ -n "$RC_LOAD_LINE" ]; then
    echo "E2SM_RC_SERVICE_MODEL_LOAD_GATE=PASS"
else
    echo "E2SM_RC_SERVICE_MODEL_LOAD_GATE=FAIL"
    E2SM_RC_READINESS_GATE="FAIL"
fi

if [ -n "$RC_SETUP_LINE" ]; then
    echo "E2_SETUP_REQUEST_CURRENT_SESSION_GATE=PASS"
else
    echo "E2_SETUP_REQUEST_CURRENT_SESSION_GATE=FAIL"
    E2SM_RC_READINESS_GATE="FAIL"
fi

if [ -n "$RC_ACCEPT_LINE" ]; then
    echo "RAN_FUNCTION_3_ACCEPTANCE_GATE=PASS"
else
    echo "RAN_FUNCTION_3_ACCEPTANCE_GATE=FAIL"
    E2SM_RC_READINESS_GATE="FAIL"
fi

echo
echo "----- TEMPORAL VALIDATION -----"

RC_TIME_ANALYSIS="$(
    python3 - \
        "$RC_RIC_STARTED_BEFORE" \
        "$RC_LOAD_LINE" \
        "$RC_SETUP_LINE" \
        "$RC_ACCEPT_LINE" <<'PY_RC'
from datetime import datetime
import sys


def parse_iso(value):
    value = value.strip()

    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    return datetime.fromisoformat(value)


def line_timestamp(line):
    if not line:
        return None

    return parse_iso(line.split()[0])


try:
    started = parse_iso(sys.argv[1])
    load = line_timestamp(sys.argv[2])
    setup = line_timestamp(sys.argv[3])
    accept = line_timestamp(sys.argv[4])

    present = all(
        value is not None
        for value in (load, setup, accept)
    )

    fresh = (
        present
        and load >= started
        and setup >= started
        and accept >= started
    )

    ordered = (
        present
        and load <= setup <= accept
    )

    print(
        "E2SM_RC_EVENT_FRESHNESS_GATE="
        + ("PASS" if fresh else "FAIL")
    )

    print(
        "E2SM_RC_EVENT_ORDER_GATE="
        + ("PASS" if ordered else "FAIL")
    )

except Exception as exc:
    print("E2SM_RC_EVENT_FRESHNESS_GATE=FAIL")
    print("E2SM_RC_EVENT_ORDER_GATE=FAIL")
    print(
        "E2SM_RC_TIMESTAMP_PARSE_ERROR="
        + str(exc).replace("\n", " ")
    )
PY_RC
)"

printf '%s\n' "$RC_TIME_ANALYSIS"

if ! printf '%s\n' "$RC_TIME_ANALYSIS" |
     grep -Fxq "E2SM_RC_EVENT_FRESHNESS_GATE=PASS"
then
    E2SM_RC_READINESS_GATE="FAIL"
fi

if ! printf '%s\n' "$RC_TIME_ANALYSIS" |
     grep -Fxq "E2SM_RC_EVENT_ORDER_GATE=PASS"
then
    E2SM_RC_READINESS_GATE="FAIL"
fi

echo
echo "----- NEGATIVE EVIDENCE SCREEN -----"

RC_NEGATIVE_PATTERN='rejecting RAN function ID[[:space:]]*3|failed.*ORAN-E2SM-RC|ORAN-E2SM-RC.*failed|unsupported.*ORAN-E2SM-RC'

if grep -Eiq \
    "$RC_NEGATIVE_PATTERN" \
    "$RC_LOG"
then
    echo "E2SM_RC_NEGATIVE_EVIDENCE_GATE=FAIL"
    E2SM_RC_READINESS_GATE="FAIL"
else
    echo "E2SM_RC_NEGATIVE_EVIDENCE_GATE=PASS"
fi

echo
echo "----- PROCESS FINGERPRINT AFTER -----"

RC_GNB_PID_AFTER="$(
    docker inspect "$CID_GNB" \
        --format '{{.State.Pid}}' \
        2>/dev/null || true
)"

RC_GNB_STARTED_AFTER="$(
    docker inspect "$CID_GNB" \
        --format '{{.State.StartedAt}}' \
        2>/dev/null || true
)"

RC_GNB_RESTART_AFTER="$(
    docker inspect "$CID_GNB" \
        --format '{{.RestartCount}}' \
        2>/dev/null || true
)"

RC_RIC_PID_AFTER="$(
    docker inspect "$RIC_NAME" \
        --format '{{.State.Pid}}' \
        2>/dev/null || true
)"

RC_RIC_STARTED_AFTER="$(
    docker inspect "$RIC_NAME" \
        --format '{{.State.StartedAt}}' \
        2>/dev/null || true
)"

RC_RIC_RESTART_AFTER="$(
    docker inspect "$RIC_NAME" \
        --format '{{.RestartCount}}' \
        2>/dev/null || true
)"

if [ "$RC_GNB_PID_BEFORE" = "$RC_GNB_PID_AFTER" ] &&
   [ "$RC_GNB_STARTED_BEFORE" = "$RC_GNB_STARTED_AFTER" ] &&
   [ "$RC_GNB_RESTART_BEFORE" = "$RC_GNB_RESTART_AFTER" ] &&
   [ "$RC_RIC_PID_BEFORE" = "$RC_RIC_PID_AFTER" ] &&
   [ "$RC_RIC_STARTED_BEFORE" = "$RC_RIC_STARTED_AFTER" ] &&
   [ "$RC_RIC_RESTART_BEFORE" = "$RC_RIC_RESTART_AFTER" ]
then
    echo "E2SM_RC_PROCESS_CONTINUITY_GATE=PASS"
else
    echo "E2SM_RC_PROCESS_CONTINUITY_GATE=FAIL"
    E2SM_RC_READINESS_GATE="FAIL"
fi

rm -rf "$RC_TMP"

if [ "$E2SM_RC_READINESS_GATE" = "PASS" ]; then
    echo "RAN_FUNCTION_3_GATE=PASS"
else
    echo "RAN_FUNCTION_3_GATE=FAIL"
fi

echo "E2SM_RC_READINESS_GATE=${E2SM_RC_READINESS_GATE}"

echo
echo "===== UE SESSION ====="

UE_SESSION_READINESS_GATE="PASS"

EXPECTED_UE_PDU_IPV4="10.45.1.2"
EXPECTED_UE_PDU_PREFIX="24"

echo "EXPECTED_UE_PDU_IPV4=${EXPECTED_UE_PDU_IPV4}"
echo "EXPECTED_UE_PDU_PREFIX=${EXPECTED_UE_PDU_PREFIX}"

UE_SESSION_UE_CONTAINER="$(
    docker ps \
        --filter "label=com.docker.compose.project=${PROJECT}" \
        --filter "label=com.docker.compose.service=srsue" \
        --format '{{.Names}}' |
    head -n 1
)"

UE_SESSION_5GC_CONTAINER="$(
    docker ps \
        --filter "label=com.docker.compose.project=${PROJECT}" \
        --filter "label=com.docker.compose.service=5gc" \
        --format '{{.Names}}' |
    head -n 1
)"

echo "UE_SESSION_UE_CONTAINER=${UE_SESSION_UE_CONTAINER}"
echo "UE_SESSION_5GC_CONTAINER=${UE_SESSION_5GC_CONTAINER}"

if [ -n "$UE_SESSION_UE_CONTAINER" ] &&
   [ -n "$UE_SESSION_5GC_CONTAINER" ]
then
    echo "UE_SESSION_RUNTIME_RESOLUTION_GATE=PASS"
else
    echo "UE_SESSION_RUNTIME_RESOLUTION_GATE=FAIL"
    UE_SESSION_READINESS_GATE="FAIL"
fi

echo
echo "----- PROCESS FINGERPRINT BEFORE -----"

UE_SESSION_UE_PID_BEFORE="$(
    docker inspect "$UE_SESSION_UE_CONTAINER" \
        --format '{{.State.Pid}}' \
        2>/dev/null || true
)"

UE_SESSION_UE_STARTED_BEFORE="$(
    docker inspect "$UE_SESSION_UE_CONTAINER" \
        --format '{{.State.StartedAt}}' \
        2>/dev/null || true
)"

UE_SESSION_UE_RESTART_BEFORE="$(
    docker inspect "$UE_SESSION_UE_CONTAINER" \
        --format '{{.RestartCount}}' \
        2>/dev/null || true
)"

UE_SESSION_5GC_PID_BEFORE="$(
    docker inspect "$UE_SESSION_5GC_CONTAINER" \
        --format '{{.State.Pid}}' \
        2>/dev/null || true
)"

UE_SESSION_5GC_STARTED_BEFORE="$(
    docker inspect "$UE_SESSION_5GC_CONTAINER" \
        --format '{{.State.StartedAt}}' \
        2>/dev/null || true
)"

UE_SESSION_5GC_RESTART_BEFORE="$(
    docker inspect "$UE_SESSION_5GC_CONTAINER" \
        --format '{{.RestartCount}}' \
        2>/dev/null || true
)"

echo "UE_SESSION_UE_PID=${UE_SESSION_UE_PID_BEFORE}"
echo "UE_SESSION_UE_STARTED_AT=${UE_SESSION_UE_STARTED_BEFORE}"
echo "UE_SESSION_UE_RESTART_COUNT=${UE_SESSION_UE_RESTART_BEFORE}"

echo "UE_SESSION_5GC_PID=${UE_SESSION_5GC_PID_BEFORE}"
echo "UE_SESSION_5GC_STARTED_AT=${UE_SESSION_5GC_STARTED_BEFORE}"
echo "UE_SESSION_5GC_RESTART_COUNT=${UE_SESSION_5GC_RESTART_BEFORE}"

if [ -n "$UE_SESSION_UE_PID_BEFORE" ] &&
   [ -n "$UE_SESSION_UE_STARTED_BEFORE" ] &&
   [ -n "$UE_SESSION_5GC_PID_BEFORE" ] &&
   [ -n "$UE_SESSION_5GC_STARTED_BEFORE" ]
then
    echo "UE_SESSION_RUNTIME_FINGERPRINT_GATE=PASS"
else
    echo "UE_SESSION_RUNTIME_FINGERPRINT_GATE=FAIL"
    UE_SESSION_READINESS_GATE="FAIL"
fi

UE_SESSION_TMP="$(
    mktemp -d \
        "${TMPDIR:-/tmp}/sci-oran-doctor-ue-session.XXXXXX"
)"

UE_SESSION_UE_LOG="${UE_SESSION_TMP}/ue.log"
UE_SESSION_5GC_LOG="${UE_SESSION_TMP}/5gc.log"
UE_SESSION_TUN_LINK="${UE_SESSION_TMP}/tun-link.txt"
UE_SESSION_TUN_IP="${UE_SESSION_TMP}/tun-ip.txt"

echo
echo "----- CURRENT PROCESS LOGS -----"

UE_SESSION_LOG_CAPTURE_GATE="PASS"

if [ -n "$UE_SESSION_UE_STARTED_BEFORE" ] &&
   docker logs \
       --timestamps \
       --since "$UE_SESSION_UE_STARTED_BEFORE" \
       "$UE_SESSION_UE_CONTAINER" \
       > "$UE_SESSION_UE_LOG" 2>&1
then
    echo "UE_CURRENT_LOG_CAPTURE_GATE=PASS"
else
    echo "UE_CURRENT_LOG_CAPTURE_GATE=FAIL"
    UE_SESSION_LOG_CAPTURE_GATE="FAIL"
    : > "$UE_SESSION_UE_LOG"
fi

if [ -n "$UE_SESSION_5GC_STARTED_BEFORE" ] &&
   docker logs \
       --timestamps \
       --since "$UE_SESSION_5GC_STARTED_BEFORE" \
       "$UE_SESSION_5GC_CONTAINER" \
       > "$UE_SESSION_5GC_LOG" 2>&1
then
    echo "5GC_CURRENT_LOG_CAPTURE_GATE=PASS"
else
    echo "5GC_CURRENT_LOG_CAPTURE_GATE=FAIL"
    UE_SESSION_LOG_CAPTURE_GATE="FAIL"
    : > "$UE_SESSION_5GC_LOG"
fi

echo "UE_SESSION_CURRENT_LOG_CAPTURE_GATE=${UE_SESSION_LOG_CAPTURE_GATE}"

if [ "$UE_SESSION_LOG_CAPTURE_GATE" != "PASS" ]; then
    UE_SESSION_READINESS_GATE="FAIL"
fi

echo
echo "----- LIVE TUN STATE -----"

UE_TUN_LINK_GATE="FAIL"
UE_PDU_ADDRESS_GATE="FAIL"

if docker exec "$UE_SESSION_UE_CONTAINER" \
    ip -o link show dev tun_srsue \
    > "$UE_SESSION_TUN_LINK" 2>&1
then
    UE_TUN_LINK_GATE="PASS"
fi

if docker exec "$UE_SESSION_UE_CONTAINER" \
    ip -o -4 addr show dev tun_srsue \
    > "$UE_SESSION_TUN_IP" 2>&1 &&
   grep -Eq \
       'inet[[:space:]]+10\.45\.1\.2/24([[:space:]]|$)' \
       "$UE_SESSION_TUN_IP"
then
    UE_PDU_ADDRESS_GATE="PASS"
fi

echo "UE_TUN_LINK_GATE=${UE_TUN_LINK_GATE}"
echo "UE_PDU_ADDRESS_GATE=${UE_PDU_ADDRESS_GATE}"

if [ "$UE_TUN_LINK_GATE" != "PASS" ] ||
   [ "$UE_PDU_ADDRESS_GATE" != "PASS" ]
then
    UE_SESSION_READINESS_GATE="FAIL"
fi

echo
echo "----- CURRENT SESSION EVENT ANALYSIS -----"

UE_SESSION_ANALYSIS="$(
    python3 - \
        "$UE_SESSION_UE_LOG" \
        "$UE_SESSION_5GC_LOG" \
        "$UE_SESSION_UE_STARTED_BEFORE" \
        "$UE_SESSION_5GC_STARTED_BEFORE" <<'PY_UE'
from datetime import datetime
from pathlib import Path
import re
import sys

ue_path = Path(sys.argv[1])
core_path = Path(sys.argv[2])
ue_started_raw = sys.argv[3]
core_started_raw = sys.argv[4]


def parse_ts(value):
    value = value.strip()

    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    return datetime.fromisoformat(value)


def collect(path, pattern):
    events = []

    for line in path.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines():

        if not pattern.search(line):
            continue

        parts = line.split(maxsplit=1)

        if not parts:
            continue

        try:
            timestamp = parse_ts(parts[0])
        except Exception:
            continue

        events.append((timestamp, line))

    return events


def latest(events):
    if not events:
        return None

    return max(events, key=lambda item: item[0])


def show(name, event):
    if event is None:
        print(f"{name}=MISSING")
    else:
        print(f"{name}={event[1]}")


try:
    ue_started = parse_ts(ue_started_raw)
    core_started = parse_ts(core_started_raw)

    rrc = latest(
        collect(
            ue_path,
            re.compile(
                r"RRC Connected",
                re.I,
            ),
        )
    )

    pdu = latest(
        collect(
            ue_path,
            re.compile(
                r"PDU Session Establishment successful"
                r".*IP:\s*10\.45\.1\.2",
                re.I,
            ),
        )
    )

    registration = latest(
        collect(
            core_path,
            re.compile(
                r"\[imsi-[0-9]+\].*Registration complete",
                re.I,
            ),
        )
    )

    core_pdu = latest(
        collect(
            core_path,
            re.compile(
                r"UE SUPI\[imsi-[0-9]+\]"
                r".*IPv4\[10\.45\.1\.2\]",
                re.I,
            ),
        )
    )

    removed = latest(
        collect(
            core_path,
            re.compile(
                r"Removed Session:"
                r".*IPv4:\[10\.45\.1\.2\]",
                re.I,
            ),
        )
    )

    deregistered = latest(
        collect(
            core_path,
            re.compile(
                r"\[imsi-[0-9]+\]"
                r".*Implicit De-registered",
                re.I,
            ),
        )
    )

    show(
        "LATEST_UE_RRC_CONNECTED_EVENT",
        rrc,
    )

    show(
        "LATEST_UE_PDU_SUCCESS_EVENT",
        pdu,
    )

    show(
        "LATEST_5GC_REGISTRATION_COMPLETE_EVENT",
        registration,
    )

    show(
        "LATEST_5GC_PDU_CONTEXT_EVENT",
        core_pdu,
    )

    show(
        "LATEST_5GC_SESSION_REMOVED_EVENT",
        removed,
    )

    show(
        "LATEST_5GC_IMPLICIT_DEREGISTERED_EVENT",
        deregistered,
    )

    rrc_fresh = (
        rrc is not None
        and rrc[0] >= ue_started
    )

    pdu_fresh = (
        pdu is not None
        and pdu[0] >= ue_started
    )

    registration_fresh = (
        registration is not None
        and registration[0] >= core_started
    )

    core_pdu_fresh = (
        core_pdu is not None
        and core_pdu[0] >= core_started
    )

    pdu_current = (
        pdu_fresh
        and core_pdu_fresh
        and (
            removed is None
            or pdu[0] > removed[0]
        )
    )

    registration_current = (
        registration_fresh
        and (
            deregistered is None
            or registration[0] > deregistered[0]
        )
    )

    removal_gate = (
        removed is None
        or pdu is None
        or removed[0] <= pdu[0]
    )

    deregistration_gate = (
        deregistered is None
        or registration is None
        or deregistered[0] <= registration[0]
    )

    core_state = (
        rrc_fresh
        and pdu_fresh
        and registration_fresh
        and core_pdu_fresh
        and pdu_current
        and registration_current
        and removal_gate
        and deregistration_gate
    )

    print(
        "UE_RRC_FRESH_EVENT_GATE="
        + ("PASS" if rrc_fresh else "FAIL")
    )

    print(
        "UE_PDU_ESTABLISHMENT_FRESH_EVENT_GATE="
        + ("PASS" if pdu_fresh else "FAIL")
    )

    print(
        "5GC_REGISTRATION_FRESH_EVENT_GATE="
        + ("PASS" if registration_fresh else "FAIL")
    )

    print(
        "5GC_PDU_CONTEXT_FRESH_EVENT_GATE="
        + ("PASS" if core_pdu_fresh else "FAIL")
    )

    print(
        "PDU_SESSION_CURRENT_STATE_GATE="
        + ("PASS" if pdu_current else "FAIL")
    )

    print(
        "UE_REGISTRATION_CURRENT_STATE_GATE="
        + ("PASS" if registration_current else "FAIL")
    )

    print(
        "PDU_REMOVAL_AFTER_ESTABLISHMENT_GATE="
        + ("PASS" if removal_gate else "FAIL")
    )

    print(
        "DEREGISTRATION_AFTER_REGISTRATION_GATE="
        + ("PASS" if deregistration_gate else "FAIL")
    )

    print(
        "UE_SESSION_CORE_STATE_GATE="
        + ("PASS" if core_state else "FAIL")
    )

    print(
        "UE_SESSION_ANALYSIS_GATE="
        + ("PASS" if core_state else "FAIL")
    )

except Exception as exc:
    print("UE_RRC_FRESH_EVENT_GATE=FAIL")
    print("UE_PDU_ESTABLISHMENT_FRESH_EVENT_GATE=FAIL")
    print("5GC_REGISTRATION_FRESH_EVENT_GATE=FAIL")
    print("5GC_PDU_CONTEXT_FRESH_EVENT_GATE=FAIL")
    print("PDU_SESSION_CURRENT_STATE_GATE=FAIL")
    print("UE_REGISTRATION_CURRENT_STATE_GATE=FAIL")
    print("PDU_REMOVAL_AFTER_ESTABLISHMENT_GATE=FAIL")
    print("DEREGISTRATION_AFTER_REGISTRATION_GATE=FAIL")
    print("UE_SESSION_CORE_STATE_GATE=FAIL")
    print("UE_SESSION_ANALYSIS_GATE=FAIL")
    print(
        "UE_SESSION_ANALYSIS_ERROR="
        + str(exc).replace("\n", " ")
    )
PY_UE
)"

printf '%s\n' "$UE_SESSION_ANALYSIS"

if ! printf '%s\n' "$UE_SESSION_ANALYSIS" |
     grep -Fxq "UE_SESSION_ANALYSIS_GATE=PASS"
then
    UE_SESSION_READINESS_GATE="FAIL"
fi

echo
echo "----- PROCESS FINGERPRINT AFTER -----"

UE_SESSION_UE_PID_AFTER="$(
    docker inspect "$UE_SESSION_UE_CONTAINER" \
        --format '{{.State.Pid}}' \
        2>/dev/null || true
)"

UE_SESSION_UE_STARTED_AFTER="$(
    docker inspect "$UE_SESSION_UE_CONTAINER" \
        --format '{{.State.StartedAt}}' \
        2>/dev/null || true
)"

UE_SESSION_UE_RESTART_AFTER="$(
    docker inspect "$UE_SESSION_UE_CONTAINER" \
        --format '{{.RestartCount}}' \
        2>/dev/null || true
)"

UE_SESSION_5GC_PID_AFTER="$(
    docker inspect "$UE_SESSION_5GC_CONTAINER" \
        --format '{{.State.Pid}}' \
        2>/dev/null || true
)"

UE_SESSION_5GC_STARTED_AFTER="$(
    docker inspect "$UE_SESSION_5GC_CONTAINER" \
        --format '{{.State.StartedAt}}' \
        2>/dev/null || true
)"

UE_SESSION_5GC_RESTART_AFTER="$(
    docker inspect "$UE_SESSION_5GC_CONTAINER" \
        --format '{{.RestartCount}}' \
        2>/dev/null || true
)"

if [ "$UE_SESSION_UE_PID_BEFORE" = "$UE_SESSION_UE_PID_AFTER" ] &&
   [ "$UE_SESSION_UE_STARTED_BEFORE" = "$UE_SESSION_UE_STARTED_AFTER" ] &&
   [ "$UE_SESSION_UE_RESTART_BEFORE" = "$UE_SESSION_UE_RESTART_AFTER" ] &&
   [ "$UE_SESSION_5GC_PID_BEFORE" = "$UE_SESSION_5GC_PID_AFTER" ] &&
   [ "$UE_SESSION_5GC_STARTED_BEFORE" = "$UE_SESSION_5GC_STARTED_AFTER" ] &&
   [ "$UE_SESSION_5GC_RESTART_BEFORE" = "$UE_SESSION_5GC_RESTART_AFTER" ]
then
    echo "UE_SESSION_PROCESS_CONTINUITY_GATE=PASS"
else
    echo "UE_SESSION_PROCESS_CONTINUITY_GATE=FAIL"
    UE_SESSION_READINESS_GATE="FAIL"
fi

rm -rf "$UE_SESSION_TMP"

echo "UE_SESSION_READINESS_GATE=${UE_SESSION_READINESS_GATE}"

echo
echo "===== USER PLANE EVIDENCE ====="

USER_PLANE_READINESS_GATE="PASS"

USER_PLANE_POLICY="$REPO_ROOT/deploy/phase-2-flexric/tb3-runtime/locks/user-plane-readiness.policy"

USER_PLANE_POLICY_GATE="FAIL"
USER_PLANE_EVIDENCE_FILE_GATE="FAIL"
USER_PLANE_EVIDENCE_REQUIRED_GATES_GATE="FAIL"
USER_PLANE_EVIDENCE_FRESHNESS_GATE="FAIL"
USER_PLANE_EVIDENCE_RUNTIME_FINGERPRINT_GATE="FAIL"
USER_PLANE_EVIDENCE_IMAGE_IDENTITY_GATE="FAIL"
USER_PLANE_EVIDENCE_SIDE_EFFECT_GATE="FAIL"

if [ -f "$USER_PLANE_POLICY" ]; then
    USER_PLANE_POLICY_GATE="PASS"
fi

echo "USER_PLANE_POLICY_GATE=${USER_PLANE_POLICY_GATE}"

if [ "$USER_PLANE_POLICY_GATE" = "PASS" ]; then

    USER_PLANE_EVIDENCE="$(
        get_value \
            "$USER_PLANE_POLICY" \
            SMOKE_EVIDENCE_LATEST_PATH
    )"

    USER_PLANE_MAX_AGE_SECONDS="$(
        get_value \
            "$USER_PLANE_POLICY" \
            SMOKE_EVIDENCE_MAX_AGE_SECONDS
    )"

    USER_PLANE_REQUIRED_GATES="$(
        get_value \
            "$USER_PLANE_POLICY" \
            REQUIRED_SMOKE_GATES
    )"

else
    USER_PLANE_EVIDENCE=""
    USER_PLANE_MAX_AGE_SECONDS=""
    USER_PLANE_REQUIRED_GATES=""
fi

echo "USER_PLANE_EVIDENCE=${USER_PLANE_EVIDENCE}"
echo "USER_PLANE_MAX_AGE_SECONDS=${USER_PLANE_MAX_AGE_SECONDS}"

if [ "$USER_PLANE_POLICY_GATE" != "PASS" ] ||
   [ -z "$USER_PLANE_EVIDENCE" ] ||
   [ -z "$USER_PLANE_MAX_AGE_SECONDS" ] ||
   [ -z "$USER_PLANE_REQUIRED_GATES" ] ||
   ! [[ "$USER_PLANE_MAX_AGE_SECONDS" =~ ^[0-9]+$ ]]
then
    echo "USER_PLANE_POLICY_CONTRACT_GATE=FAIL"
    USER_PLANE_READINESS_GATE="FAIL"
else
    echo "USER_PLANE_POLICY_CONTRACT_GATE=PASS"
fi

if [ -n "$USER_PLANE_EVIDENCE" ] &&
   [ -f "$USER_PLANE_EVIDENCE" ]
then
    USER_PLANE_EVIDENCE_FILE_GATE="PASS"
fi

echo "USER_PLANE_EVIDENCE_FILE_GATE=${USER_PLANE_EVIDENCE_FILE_GATE}"

if [ "$USER_PLANE_EVIDENCE_FILE_GATE" != "PASS" ]; then
    USER_PLANE_READINESS_GATE="FAIL"
fi

if [ "$USER_PLANE_EVIDENCE_FILE_GATE" = "PASS" ]; then

    echo
    echo "----- REQUIRED SMOKE GATES -----"

    USER_PLANE_EVIDENCE_REQUIRED_GATES_GATE="PASS"

    OLD_IFS="$IFS"
    IFS=','
    read -r -a USER_PLANE_REQUIRED_ARRAY \
        <<< "$USER_PLANE_REQUIRED_GATES"
    IFS="$OLD_IFS"

    for REQUIRED_GATE in \
        "${USER_PLANE_REQUIRED_ARRAY[@]}"
    do
        REQUIRED_VALUE="$(
            get_value \
                "$USER_PLANE_EVIDENCE" \
                "$REQUIRED_GATE"
        )"

        echo "${REQUIRED_GATE}=${REQUIRED_VALUE:-MISSING}"

        if [ "$REQUIRED_VALUE" != "PASS" ]; then
            USER_PLANE_EVIDENCE_REQUIRED_GATES_GATE="FAIL"
        fi
    done

    for REQUIRED_GATE in \
        USER_PLANE_RUNTIME_RESOLUTION_GATE \
        TOOLBOX_IDENTITY_GATE
    do
        REQUIRED_VALUE="$(
            get_value \
                "$USER_PLANE_EVIDENCE" \
                "$REQUIRED_GATE"
        )"

        echo "${REQUIRED_GATE}=${REQUIRED_VALUE:-MISSING}"

        if [ "$REQUIRED_VALUE" != "PASS" ]; then
            USER_PLANE_EVIDENCE_REQUIRED_GATES_GATE="FAIL"
        fi
    done

    echo "USER_PLANE_EVIDENCE_REQUIRED_GATES_GATE=${USER_PLANE_EVIDENCE_REQUIRED_GATES_GATE}"

    if [ "$USER_PLANE_EVIDENCE_REQUIRED_GATES_GATE" != "PASS" ]; then
        USER_PLANE_READINESS_GATE="FAIL"
    fi

    echo
    echo "----- EVIDENCE FRESHNESS -----"

    USER_PLANE_EVIDENCE_TIMESTAMP="$(
        get_value \
            "$USER_PLANE_EVIDENCE" \
            UTC_TIMESTAMP
    )"

    USER_PLANE_EVIDENCE_EPOCH="$(
        python3 - "$USER_PLANE_EVIDENCE_TIMESTAMP" <<'PY_UP_TS'
from datetime import datetime
import sys

value = sys.argv[1].strip()

try:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    print(int(datetime.fromisoformat(value).timestamp()))
except Exception:
    pass
PY_UP_TS
    )"

    USER_PLANE_NOW_EPOCH="$(date -u '+%s')"

    echo "USER_PLANE_EVIDENCE_TIMESTAMP=${USER_PLANE_EVIDENCE_TIMESTAMP}"

    if [ -n "$USER_PLANE_EVIDENCE_EPOCH" ] &&
       [[ "$USER_PLANE_EVIDENCE_EPOCH" =~ ^[0-9]+$ ]] &&
       [[ "$USER_PLANE_NOW_EPOCH" =~ ^[0-9]+$ ]]
    then
        USER_PLANE_EVIDENCE_AGE_SECONDS="$((USER_PLANE_NOW_EPOCH - USER_PLANE_EVIDENCE_EPOCH))"

        echo "USER_PLANE_EVIDENCE_AGE_SECONDS=${USER_PLANE_EVIDENCE_AGE_SECONDS}"

        if [ "$USER_PLANE_EVIDENCE_AGE_SECONDS" -ge 0 ] &&
           [ "$USER_PLANE_EVIDENCE_AGE_SECONDS" -le "$USER_PLANE_MAX_AGE_SECONDS" ]
        then
            USER_PLANE_EVIDENCE_FRESHNESS_GATE="PASS"
        fi
    else
        echo "USER_PLANE_EVIDENCE_AGE_SECONDS=INVALID"
    fi

    echo "USER_PLANE_EVIDENCE_FRESHNESS_GATE=${USER_PLANE_EVIDENCE_FRESHNESS_GATE}"

    if [ "$USER_PLANE_EVIDENCE_FRESHNESS_GATE" != "PASS" ]; then
        USER_PLANE_READINESS_GATE="FAIL"
    fi

    echo
    echo "----- CURRENT RUNTIME FINGERPRINT -----"

    USER_PLANE_UE="$(
        docker ps \
            --filter "label=com.docker.compose.project=${PROJECT}" \
            --filter "label=com.docker.compose.service=srsue" \
            --format '{{.Names}}' |
        head -n 1
    )"

    USER_PLANE_GNB="$(
        docker ps \
            --filter "label=com.docker.compose.project=${PROJECT}" \
            --filter "label=com.docker.compose.service=gnb" \
            --format '{{.Names}}' |
        head -n 1
    )"

    USER_PLANE_5GC="$(
        docker ps \
            --filter "label=com.docker.compose.project=${PROJECT}" \
            --filter "label=com.docker.compose.service=5gc" \
            --format '{{.Names}}' |
        head -n 1
    )"

    user_plane_fingerprint()
    {
        docker inspect "$1" \
            --format '{{.State.Pid}}|{{.State.StartedAt}}|{{.RestartCount}}' \
            2>/dev/null || true
    }

    user_plane_image_id()
    {
        docker inspect "$1" \
            --format '{{.Image}}' \
            2>/dev/null || true
    }

    if [ -n "$USER_PLANE_UE" ] &&
       [ -n "$USER_PLANE_GNB" ] &&
       [ -n "$USER_PLANE_5GC" ]
    then
        USER_PLANE_CURRENT_UE_FP="$(
            user_plane_fingerprint "$USER_PLANE_UE"
        )"

        USER_PLANE_CURRENT_GNB_FP="$(
            user_plane_fingerprint "$USER_PLANE_GNB"
        )"

        USER_PLANE_CURRENT_5GC_FP="$(
            user_plane_fingerprint "$USER_PLANE_5GC"
        )"

        USER_PLANE_EVIDENCE_UE_FP="$(
            get_value "$USER_PLANE_EVIDENCE" UE_FINGERPRINT
        )"

        USER_PLANE_EVIDENCE_GNB_FP="$(
            get_value "$USER_PLANE_EVIDENCE" GNB_FINGERPRINT
        )"

        USER_PLANE_EVIDENCE_5GC_FP="$(
            get_value "$USER_PLANE_EVIDENCE" 5GC_FINGERPRINT
        )"

        echo "USER_PLANE_CURRENT_UE_FINGERPRINT=${USER_PLANE_CURRENT_UE_FP}"
        echo "USER_PLANE_EVIDENCE_UE_FINGERPRINT=${USER_PLANE_EVIDENCE_UE_FP}"

        echo "USER_PLANE_CURRENT_GNB_FINGERPRINT=${USER_PLANE_CURRENT_GNB_FP}"
        echo "USER_PLANE_EVIDENCE_GNB_FINGERPRINT=${USER_PLANE_EVIDENCE_GNB_FP}"

        echo "USER_PLANE_CURRENT_5GC_FINGERPRINT=${USER_PLANE_CURRENT_5GC_FP}"
        echo "USER_PLANE_EVIDENCE_5GC_FINGERPRINT=${USER_PLANE_EVIDENCE_5GC_FP}"

        if [ "$USER_PLANE_CURRENT_UE_FP" = "$USER_PLANE_EVIDENCE_UE_FP" ] &&
           [ "$USER_PLANE_CURRENT_GNB_FP" = "$USER_PLANE_EVIDENCE_GNB_FP" ] &&
           [ "$USER_PLANE_CURRENT_5GC_FP" = "$USER_PLANE_EVIDENCE_5GC_FP" ]
        then
            USER_PLANE_EVIDENCE_RUNTIME_FINGERPRINT_GATE="PASS"
        fi

        USER_PLANE_CURRENT_UE_IMAGE="$(
            user_plane_image_id "$USER_PLANE_UE"
        )"

        USER_PLANE_CURRENT_GNB_IMAGE="$(
            user_plane_image_id "$USER_PLANE_GNB"
        )"

        USER_PLANE_CURRENT_5GC_IMAGE="$(
            user_plane_image_id "$USER_PLANE_5GC"
        )"

        USER_PLANE_EVIDENCE_UE_IMAGE="$(
            get_value "$USER_PLANE_EVIDENCE" UE_IMAGE_ID
        )"

        USER_PLANE_EVIDENCE_GNB_IMAGE="$(
            get_value "$USER_PLANE_EVIDENCE" GNB_IMAGE_ID
        )"

        USER_PLANE_EVIDENCE_5GC_IMAGE="$(
            get_value "$USER_PLANE_EVIDENCE" 5GC_IMAGE_ID
        )"

        if [ "$USER_PLANE_CURRENT_UE_IMAGE" = "$USER_PLANE_EVIDENCE_UE_IMAGE" ] &&
           [ "$USER_PLANE_CURRENT_GNB_IMAGE" = "$USER_PLANE_EVIDENCE_GNB_IMAGE" ] &&
           [ "$USER_PLANE_CURRENT_5GC_IMAGE" = "$USER_PLANE_EVIDENCE_5GC_IMAGE" ]
        then
            USER_PLANE_EVIDENCE_IMAGE_IDENTITY_GATE="PASS"
        fi
    fi

    echo "USER_PLANE_EVIDENCE_RUNTIME_FINGERPRINT_GATE=${USER_PLANE_EVIDENCE_RUNTIME_FINGERPRINT_GATE}"
    echo "USER_PLANE_EVIDENCE_IMAGE_IDENTITY_GATE=${USER_PLANE_EVIDENCE_IMAGE_IDENTITY_GATE}"

    if [ "$USER_PLANE_EVIDENCE_RUNTIME_FINGERPRINT_GATE" != "PASS" ] ||
       [ "$USER_PLANE_EVIDENCE_IMAGE_IDENTITY_GATE" != "PASS" ]
    then
        USER_PLANE_READINESS_GATE="FAIL"
    fi

    echo
    echo "----- SIDE-EFFECT CONTRACT -----"

    USER_PLANE_DIAGNOSTIC_TRAFFIC="$(
        get_value \
            "$USER_PLANE_EVIDENCE" \
            DIAGNOSTIC_TRAFFIC_GENERATED
    )"

    USER_PLANE_TRANSIENT_TOOLBOX="$(
        get_value \
            "$USER_PLANE_EVIDENCE" \
            TRANSIENT_TOOLBOX_CONTAINER_USED
    )"

    USER_PLANE_PERSISTENT_MODIFICATION="$(
        get_value \
            "$USER_PLANE_EVIDENCE" \
            PERSISTENT_RUNTIME_CONFIGURATION_MODIFIED
    )"

    if [ "$USER_PLANE_DIAGNOSTIC_TRAFFIC" = "YES" ] &&
       [ "$USER_PLANE_TRANSIENT_TOOLBOX" = "YES" ] &&
       [ "$USER_PLANE_PERSISTENT_MODIFICATION" = "NO" ]
    then
        USER_PLANE_EVIDENCE_SIDE_EFFECT_GATE="PASS"
    fi

    echo "USER_PLANE_EVIDENCE_SIDE_EFFECT_GATE=${USER_PLANE_EVIDENCE_SIDE_EFFECT_GATE}"

    if [ "$USER_PLANE_EVIDENCE_SIDE_EFFECT_GATE" != "PASS" ]; then
        USER_PLANE_READINESS_GATE="FAIL"
    fi

fi

echo "USER_PLANE_READINESS_GATE=${USER_PLANE_READINESS_GATE}"

echo
echo "===== TRAFFIC HARNESS CAPABILITY ====="

TRAFFIC_HARNESS_READINESS_GATE="PASS"

TRAFFIC_HARNESS="$REPO_ROOT/scripts/experiment-harness/run-experiment.sh"
TRAFFIC_WINDOW_LIB="$REPO_ROOT/scripts/experiment-harness/lib/traffic-window.sh"

TRAFFIC_HARNESS_FILE_GATE="FAIL"
TRAFFIC_HARNESS_EXECUTABLE_GATE="FAIL"
TRAFFIC_HARNESS_SYNTAX_GATE="FAIL"
TRAFFIC_WINDOW_FILE_GATE="FAIL"
TRAFFIC_WINDOW_SYNTAX_GATE="FAIL"
TRAFFIC_COMMAND_CLI_CONTRACT_GATE="FAIL"
TRAFFIC_COMMAND_REQUIRED_GATE="FAIL"
TRAFFIC_WINDOW_FUNCTION_UNIQUENESS_GATE="FAIL"
TRAFFIC_WINDOW_ARGUMENT_VALIDATION_GATE="FAIL"
TRAFFIC_WINDOW_DISPATCH_GATE="FAIL"
TRAFFIC_COMMAND_EXECUTION_PATH_GATE="FAIL"

echo "TRAFFIC_HARNESS=$TRAFFIC_HARNESS"
echo "TRAFFIC_WINDOW_LIB=$TRAFFIC_WINDOW_LIB"

echo
echo "----- HARNESS FILE CONTRACT -----"

if [ -f "$TRAFFIC_HARNESS" ]; then
    TRAFFIC_HARNESS_FILE_GATE="PASS"
fi

if [ -x "$TRAFFIC_HARNESS" ]; then
    TRAFFIC_HARNESS_EXECUTABLE_GATE="PASS"
fi

if [ "$TRAFFIC_HARNESS_FILE_GATE" = "PASS" ] &&
   bash -n "$TRAFFIC_HARNESS" >/dev/null 2>&1
then
    TRAFFIC_HARNESS_SYNTAX_GATE="PASS"
fi

echo "TRAFFIC_HARNESS_FILE_GATE=${TRAFFIC_HARNESS_FILE_GATE}"
echo "TRAFFIC_HARNESS_EXECUTABLE_GATE=${TRAFFIC_HARNESS_EXECUTABLE_GATE}"
echo "TRAFFIC_HARNESS_SYNTAX_GATE=${TRAFFIC_HARNESS_SYNTAX_GATE}"

echo
echo "----- TRAFFIC WINDOW LIBRARY CONTRACT -----"

if [ -f "$TRAFFIC_WINDOW_LIB" ]; then
    TRAFFIC_WINDOW_FILE_GATE="PASS"
fi

if [ "$TRAFFIC_WINDOW_FILE_GATE" = "PASS" ] &&
   bash -n "$TRAFFIC_WINDOW_LIB" >/dev/null 2>&1
then
    TRAFFIC_WINDOW_SYNTAX_GATE="PASS"
fi

echo "TRAFFIC_WINDOW_FILE_GATE=${TRAFFIC_WINDOW_FILE_GATE}"
echo "TRAFFIC_WINDOW_SYNTAX_GATE=${TRAFFIC_WINDOW_SYNTAX_GATE}"

echo
echo "----- EXTERNAL TRAFFIC COMMAND CONTRACT -----"

if [ "$TRAFFIC_HARNESS_FILE_GATE" = "PASS" ] &&
   grep -Fq \
       -- '--traffic-command COMMAND' \
       "$TRAFFIC_HARNESS" &&
   grep -Fq \
       -- '--traffic-command)' \
       "$TRAFFIC_HARNESS"
then
    TRAFFIC_COMMAND_CLI_CONTRACT_GATE="PASS"
fi

if [ "$TRAFFIC_HARNESS_FILE_GATE" = "PASS" ] &&
   grep -Fq \
       '[[ -n "$TRAFFIC_COMMAND" ]] || exit "$EX_USAGE"' \
       "$TRAFFIC_HARNESS"
then
    TRAFFIC_COMMAND_REQUIRED_GATE="PASS"
fi

echo "TRAFFIC_COMMAND_CLI_CONTRACT_GATE=${TRAFFIC_COMMAND_CLI_CONTRACT_GATE}"
echo "TRAFFIC_COMMAND_REQUIRED_GATE=${TRAFFIC_COMMAND_REQUIRED_GATE}"

echo
echo "----- TRAFFIC WINDOW FUNCTION CONTRACT -----"

if [ "$TRAFFIC_WINDOW_FILE_GATE" = "PASS" ]; then

    TRAFFIC_WINDOW_FUNCTION_COUNT="$(
        grep -Ec \
            '^[[:space:]]*sci_oran_run_traffic_window[[:space:]]*\(\)[[:space:]]*\{' \
            "$TRAFFIC_WINDOW_LIB" ||
        true
    )"

else
    TRAFFIC_WINDOW_FUNCTION_COUNT=0
fi

echo "TRAFFIC_WINDOW_FUNCTION_COUNT=${TRAFFIC_WINDOW_FUNCTION_COUNT}"

if [ "$TRAFFIC_WINDOW_FUNCTION_COUNT" -eq 1 ]; then
    TRAFFIC_WINDOW_FUNCTION_UNIQUENESS_GATE="PASS"
fi

if [ "$TRAFFIC_WINDOW_FILE_GATE" = "PASS" ] &&
   grep -Fq \
       '[[ -n "$traffic_command" ]] || return 64' \
       "$TRAFFIC_WINDOW_LIB"
then
    TRAFFIC_WINDOW_ARGUMENT_VALIDATION_GATE="PASS"
fi

echo "TRAFFIC_WINDOW_FUNCTION_UNIQUENESS_GATE=${TRAFFIC_WINDOW_FUNCTION_UNIQUENESS_GATE}"
echo "TRAFFIC_WINDOW_ARGUMENT_VALIDATION_GATE=${TRAFFIC_WINDOW_ARGUMENT_VALIDATION_GATE}"

echo
echo "----- HARNESS TO EXECUTION-PATH CONTRACT -----"

if [ "$TRAFFIC_HARNESS_FILE_GATE" = "PASS" ] &&
   grep -Eq \
       'sci_oran_run_traffic_window.*"\$TRAFFIC_COMMAND"' \
       "$TRAFFIC_HARNESS"
then
    TRAFFIC_WINDOW_DISPATCH_GATE="PASS"
fi

if [ "$TRAFFIC_WINDOW_FILE_GATE" = "PASS" ] &&
   grep -Fq \
       'bash -lc "$traffic_command"' \
       "$TRAFFIC_WINDOW_LIB"
then
    TRAFFIC_COMMAND_EXECUTION_PATH_GATE="PASS"
fi

echo "TRAFFIC_WINDOW_DISPATCH_GATE=${TRAFFIC_WINDOW_DISPATCH_GATE}"
echo "TRAFFIC_COMMAND_EXECUTION_PATH_GATE=${TRAFFIC_COMMAND_EXECUTION_PATH_GATE}"

echo
echo "----- TRAFFIC HARNESS FINAL CAPABILITY -----"

for TRAFFIC_GATE_VALUE in \
    "$TRAFFIC_HARNESS_FILE_GATE" \
    "$TRAFFIC_HARNESS_EXECUTABLE_GATE" \
    "$TRAFFIC_HARNESS_SYNTAX_GATE" \
    "$TRAFFIC_WINDOW_FILE_GATE" \
    "$TRAFFIC_WINDOW_SYNTAX_GATE" \
    "$TRAFFIC_COMMAND_CLI_CONTRACT_GATE" \
    "$TRAFFIC_COMMAND_REQUIRED_GATE" \
    "$TRAFFIC_WINDOW_FUNCTION_UNIQUENESS_GATE" \
    "$TRAFFIC_WINDOW_ARGUMENT_VALIDATION_GATE" \
    "$TRAFFIC_WINDOW_DISPATCH_GATE" \
    "$TRAFFIC_COMMAND_EXECUTION_PATH_GATE"
do
    if [ "$TRAFFIC_GATE_VALUE" != "PASS" ]; then
        TRAFFIC_HARNESS_READINESS_GATE="FAIL"
    fi
done

echo "TRAFFIC_WORKLOAD_SELECTION=OUT_OF_SCOPE"
echo "TRAFFIC_WORKLOAD_EXECUTED_BY_DOCTOR=NO"
echo "TRAFFIC_HARNESS_READINESS_GATE=${TRAFFIC_HARNESS_READINESS_GATE}"

echo
echo "===== FUTURE READINESS GATES ====="

PROCESS_CONTINUITY_GATE="NOT_EVALUATED"
READINESS_ARTIFACT_GATE="NOT_EVALUATED"
READINESS_FRESHNESS_GATE="NOT_EVALUATED"

for name in \
    PROCESS_CONTINUITY_GATE \
    READINESS_ARTIFACT_GATE \
    READINESS_FRESHNESS_GATE
do
    printf '%s=%s\n' "$name" "${!name}"
done

echo
echo "===== FINAL SUMMARY ====="

echo "DOCTOR_READ_ONLY_GATE=PASS"
echo "HOST_READINESS_GATE=${HOST_READINESS_GATE}"
echo "HOST_RESOURCE_READINESS_GATE=${HOST_RESOURCE_READINESS_GATE}"
echo "CONTAINER_READINESS_GATE=${CONTAINER_READINESS_GATE}"
echo "NETWORK_READINESS_GATE=${NETWORK_READINESS_GATE}"
echo "ZMQ_READINESS_GATE=${ZMQ_READINESS_GATE}"
echo "N2_READINESS_GATE=${N2_READINESS_GATE}"
echo "E2_READINESS_GATE=${E2_READINESS_GATE}"
echo "E2SM_RC_READINESS_GATE=${E2SM_RC_READINESS_GATE}"
echo "UE_SESSION_READINESS_GATE=${UE_SESSION_READINESS_GATE}"
echo "USER_PLANE_READINESS_GATE=${USER_PLANE_READINESS_GATE}"
echo "TRAFFIC_HARNESS_READINESS_GATE=${TRAFFIC_HARNESS_READINESS_GATE}"

echo "REPOSITORY_REPRODUCIBILITY_GATE=${REPOSITORY_REPRODUCIBILITY_GATE}"

if [ "$HOST_READINESS_GATE" != "PASS" ]; then
    gate="FAIL"
    failure_reason="HOST_READINESS_GATE"
elif [ "$HOST_RESOURCE_READINESS_GATE" != "PASS" ]; then
    gate="FAIL"
    failure_reason="HOST_RESOURCE_READINESS_GATE"
elif [ "$CONTAINER_READINESS_GATE" != "PASS" ]; then
    gate="FAIL"
    failure_reason="CONTAINER_READINESS_GATE"
elif [ "$NETWORK_READINESS_GATE" != "PASS" ]; then
    gate="FAIL"
    failure_reason="NETWORK_READINESS_GATE"
elif [ "$ZMQ_READINESS_GATE" != "PASS" ]; then
    gate="FAIL"
    failure_reason="ZMQ_READINESS_GATE"
elif [ "$N2_READINESS_GATE" != "PASS" ]; then
    gate="FAIL"
    failure_reason="N2_READINESS_GATE"
elif [ "$E2_READINESS_GATE" != "PASS" ]; then
    gate="FAIL"
    failure_reason="E2_READINESS_GATE"
elif [ "$E2SM_RC_READINESS_GATE" != "PASS" ]; then
    gate="FAIL"
    failure_reason="E2SM_RC_READINESS_GATE"
elif [ "$UE_SESSION_READINESS_GATE" != "PASS" ]; then
    gate="FAIL"
    failure_reason="UE_SESSION_READINESS_GATE"
elif [ "$USER_PLANE_READINESS_GATE" != "PASS" ]; then
    gate="FAIL"
    failure_reason="USER_PLANE_READINESS_GATE"
elif [ "$TRAFFIC_HARNESS_READINESS_GATE" != "PASS" ]; then
    gate="FAIL"
    failure_reason="TRAFFIC_HARNESS_READINESS_GATE"
elif [ "$REPOSITORY_REPRODUCIBILITY_GATE" != "PASS" ]; then
    gate="FAIL"
    failure_reason="REPOSITORY_REPRODUCIBILITY_GATE"
else
    gate="FAIL"
    failure_reason="MANDATORY_GATES_NOT_YET_IMPLEMENTED"
fi

echo "SCI_ORAN_READY_GATE=${gate}"
echo "FAILURE_REASON=${failure_reason}"

if [ "$gate" = "PASS" ]; then
    exit 0
fi

exit "$EX_NOT_READY"
