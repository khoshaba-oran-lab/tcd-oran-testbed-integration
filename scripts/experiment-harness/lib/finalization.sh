#!/usr/bin/env bash

# Final evidence validation and checksum helpers.

sci_oran_validate_run_evidence() {
    local run_dir="$1"

    [[ -s "${run_dir}/metadata-snapshot.json" ]] || return 65
    [[ -s "${run_dir}/raw/resource/resource-network.jsonl" ]] || return 65
    [[ -s "${run_dir}/raw/native_gnb/native-gNB.log" ]] || return 65
    [[ -s "${run_dir}/raw/traffic/traffic.stdout.log" ]] || return 65

    [[ -f "${run_dir}/raw/resource/resource-network.stderr.log" ]] || return 65
    [[ -f "${run_dir}/raw/native_gnb/native-gNB.stderr.log" ]] || return 65
    [[ -f "${run_dir}/raw/traffic/traffic.stderr.log" ]] || return 65

    grep -Fxq \
        'UDP_RECEIVER_READY=10.53.1.1:55555' \
        "${run_dir}/raw/native_gnb/native-gNB.log" || return 65

    python3 - "${run_dir}/raw/resource/resource-network.jsonl" <<'PY'
import json
import sys

count = 0

with open(sys.argv[1], encoding="utf-8") as handle:
    for line in handle:
        if not line.strip():
            continue
        row = json.loads(line)
        assert row["schema"] == "sci_oran_resource_network_observability_v1"
        assert "timestamp_utc" in row
        count += 1

assert count > 0
PY
}

sci_oran_write_run_checksums() {
    local run_dir="$1"
    local checksum_path="${run_dir}/checksums/SHA256SUMS"

    [[ ! -e "$checksum_path" ]] || return 73

    mkdir -p "${run_dir}/checksums" || return 73

    python3 - "$run_dir" "$checksum_path" <<'PY'
import hashlib
import os
import sys

root = os.path.abspath(sys.argv[1])
output = os.path.abspath(sys.argv[2])
records = []

for current, _, files in os.walk(root):
    for name in files:
        path = os.path.join(current, name)

        if os.path.abspath(path) == output:
            continue

        relative = os.path.relpath(path, root).replace(os.sep, "/")

        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)

        records.append((relative, digest.hexdigest()))

records.sort()

with open(output, "x", encoding="utf-8", newline="\n") as handle:
    for relative, digest in records:
        handle.write(f"{digest}  {relative}\n")
PY

    [[ -s "$checksum_path" ]]
}

sci_oran_manifest_record_summary() {
    local manifest_path="$1"
    local run_dir="$2"
    local traffic_start_utc="$3"
    local traffic_end_utc="$4"
    local traffic_exit_code="$5"

    python3 - \
        "$manifest_path" \
        "$run_dir" \
        "$traffic_start_utc" \
        "$traffic_end_utc" \
        "$traffic_exit_code" <<'PY'
import hashlib
import json
import os
import sys
import tempfile

manifest_path, run_dir, start, end, exit_code = sys.argv[1:]
checksum_path = os.path.join(run_dir, "checksums", "SHA256SUMS")

digest = hashlib.sha256()

with open(checksum_path, "rb") as handle:
    for block in iter(lambda: handle.read(1024 * 1024), b""):
        digest.update(block)

with open(manifest_path, encoding="utf-8") as handle:
    data = json.load(handle)

data["traffic"] = {
    "end_time_utc": end,
    "exit_code": int(exit_code),
    "start_time_utc": start,
}

data["kpm"] = {
    "enabled": False,
    "status": "disabled",
}

data["validation"] = {
    "evidence_status": "pass",
}

data["checksums"] = {
    "path": "checksums/SHA256SUMS",
    "sha256": digest.hexdigest(),
}

data["provenance"] = {
    "metadata_snapshot_path": "metadata-snapshot.json",
}

directory = os.path.dirname(manifest_path)
fd, temporary = tempfile.mkstemp(prefix=".manifest.", dir=directory)

try:
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())

    os.replace(temporary, manifest_path)
finally:
    if os.path.exists(temporary):
        os.unlink(temporary)
PY
}

sci_oran_manifest_record_execution() {
    local manifest_path="$1"
    local traffic_command="$2"
    local cooldown_s="$3"

    [[ -f "$manifest_path" ]] || return 66
    [[ -n "$traffic_command" ]] || return 64
    [[ "$cooldown_s" =~ ^[0-9]+$ ]] || return 64

    python3 - "$manifest_path" "$traffic_command" "$cooldown_s" <<'PY_EXECUTION'
import json
import os
import sys
import tempfile

path, command, cooldown = sys.argv[1:]

with open(path, encoding="utf-8") as handle:
    data = json.load(handle)

traffic = data.setdefault("traffic", {})
traffic["command"] = command
traffic["cooldown_s"] = int(cooldown)

directory = os.path.dirname(path)
fd, temporary = tempfile.mkstemp(prefix=".manifest.", dir=directory)

try:
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())

    os.replace(temporary, path)
finally:
    if os.path.exists(temporary):
        os.unlink(temporary)
PY_EXECUTION
}

sci_oran_manifest_set_final_status() {
    local manifest_path="$1"
    local final_status="$2"
    local completed_time_utc="$3"

    [[ -f "$manifest_path" ]] || return 66
    [[ "$final_status" =~ ^(COMPLETED|FAILED|INTERRUPTED|REJECTED)$ ]] || return 64
    [[ "$completed_time_utc" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$ ]] || return 64

    python3 - "$manifest_path" "$final_status" "$completed_time_utc" <<'PY_STATUS'
import json
import os
import sys
import tempfile

path, status, completed_time = sys.argv[1:]

with open(path, encoding="utf-8") as handle:
    data = json.load(handle)

data["final_status"] = status
data["completed_time_utc"] = completed_time

directory = os.path.dirname(path)
fd, temporary = tempfile.mkstemp(prefix=".manifest.", dir=directory)

try:
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())

    os.replace(temporary, path)
finally:
    if os.path.exists(temporary):
        os.unlink(temporary)
PY_STATUS
}


sci_oran_manifest_record_kpm() {
    local manifest_path="$1"
    local enabled="$2"
    local status="$3"

    python3 - "$manifest_path" "$enabled" "$status" <<'PY_KPM'
import json
import os
import sys
import tempfile

path, enabled, status = sys.argv[1:]

with open(path, encoding="utf-8") as handle:
    data = json.load(handle)

data["kpm"] = {
    "enabled": enabled.lower() in ("true", "1"),
    "status": status,
}

directory = os.path.dirname(path)
fd, temporary = tempfile.mkstemp(prefix=".manifest.", dir=directory)

try:
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
finally:
    if os.path.exists(temporary):
        os.unlink(temporary)
PY_KPM
}
