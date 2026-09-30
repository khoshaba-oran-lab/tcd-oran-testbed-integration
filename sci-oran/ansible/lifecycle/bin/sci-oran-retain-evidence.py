#!/usr/bin/env python3
"""
Repository-controlled Sci_O-RAN evidence retention transfer tool.

Modes are deliberately separated:

    plan
        Read-only source qualification and rsync dry-run.

    transfer
        Copy one explicitly selected acquisition subtree into an isolated
        .incoming/<operation-id>/payload staging tree.

    verify
        Generate deterministic SHA-256 manifests independently for the source
        and destination staging payload and compare them.

    promote
        Atomically rename a verified incoming operation into its final
        retained-evidence location.

There is intentionally no source-deletion mode.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from typing import Any


OPERATION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class RetentionError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise RetentionError(message)


def run(
    argv: list[str],
    *,
    capture: bool = True,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        text=True,
        capture_output=capture,
        check=check,
    )


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        dir=str(path.parent),
        text=True,
    )

    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(
                value,
                handle,
                sort_keys=True,
                indent=2,
                ensure_ascii=False,
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def repository_root() -> Path:
    return Path(__file__).resolve().parents[4]


def validate_operation_id(value: str) -> str:
    if not OPERATION_ID_RE.fullmatch(value):
        fail(
            "operation-id must match "
            "[A-Za-z0-9][A-Za-z0-9._-]{0,127}"
        )

    return value


def validate_source_relative(value: str) -> str:
    if value == ".":
        return value

    candidate = PurePosixPath(value)

    if candidate.is_absolute():
        fail("source-relative must not be absolute")

    if not candidate.parts:
        fail("source-relative is empty")

    if any(part in ("", ".", "..") for part in candidate.parts):
        fail("source-relative contains an unsafe path component")

    return candidate.as_posix()


def inventory_host_data(
    repo: Path,
    inventory_host: str,
) -> dict[str, Any]:
    inventory = repo / "sci-oran/ansible/inventory.ini"

    if not inventory.is_file():
        fail(f"inventory not found: {inventory}")

    completed = run(
        [
            "ansible-inventory",
            "-i",
            str(inventory),
            "--host",
            inventory_host,
        ]
    )

    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        fail(f"invalid ansible-inventory JSON: {exc}")

    required = (
        "ansible_host",
        "ansible_user",
        "sci_oran_runtime_acquisition_root",
    )

    for key in required:
        if key not in value:
            fail(f"inventory host is missing required variable: {key}")

        if not isinstance(value[key], str) or not value[key].strip():
            fail(f"inventory variable is empty or non-string: {key}")

    return value


def controller_retained_root(repo: Path) -> Path:
    config = repo / "sci-oran/ansible/controller-storage.yml"

    if not config.is_file():
        fail(f"controller storage configuration not found: {config}")

    text = config.read_text(encoding="utf-8")

    match = re.search(
        r'^sci_oran_controller_storage_root:\s*"([^"]+)"\s*$',
        text,
        flags=re.MULTILINE,
    )

    if not match:
        fail("cannot resolve sci_oran_controller_storage_root")

    storage_root = Path(match.group(1))

    if not storage_root.is_absolute():
        fail("controller storage root is not absolute")

    required_fragments = (
        "sci_oran_controller_retained_evidence_root:",
        "sci_oran_controller_storage_root }}/retained-evidence",
    )

    for fragment in required_fragments:
        if fragment not in text:
            fail(
                "controller retained-evidence configuration does not match "
                "the qualified canonical contract"
            )

    retained_root = storage_root / "retained-evidence"

    return retained_root


def ssh_base(user: str, host: str) -> list[str]:
    return [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=10",
        f"{user}@{host}",
    ]


def remote_source_path(
    acquisition_root: str,
    source_relative: str,
) -> str:
    root = PurePosixPath(acquisition_root)

    if not root.is_absolute():
        fail("runtime acquisition root is not absolute")

    if source_relative == ".":
        result = root
    else:
        result = root / PurePosixPath(source_relative)

    return result.as_posix()


def remote_source_snapshot(
    user: str,
    host: str,
    source: str,
) -> dict[str, Any]:
    script = r'''
import json
import os
import pathlib
import stat
import sys

root = pathlib.Path(sys.argv[1])

if not root.exists():
    raise SystemExit("SOURCE_ABSENT")

if not root.is_dir():
    raise SystemExit("SOURCE_NOT_DIRECTORY")

if root.is_symlink():
    raise SystemExit("SOURCE_IS_SYMLINK")

regular = 0
directories = 0
symlinks = 0
fifo = 0
sockets = 0
block = 0
char = 0
total_bytes = 0
unreadable = 0

for current, dirs, files in os.walk(root, topdown=True, followlinks=False):
    directories += 1

    dirs.sort()
    files.sort()

    for name in dirs:
        path = pathlib.Path(current) / name
        mode = path.lstat().st_mode

        if stat.S_ISLNK(mode):
            symlinks += 1

    for name in files:
        path = pathlib.Path(current) / name
        st = path.lstat()
        mode = st.st_mode

        if stat.S_ISREG(mode):
            regular += 1
            total_bytes += st.st_size

            if not os.access(path, os.R_OK):
                unreadable += 1
        elif stat.S_ISLNK(mode):
            symlinks += 1
        elif stat.S_ISFIFO(mode):
            fifo += 1
        elif stat.S_ISSOCK(mode):
            sockets += 1
        elif stat.S_ISBLK(mode):
            block += 1
        elif stat.S_ISCHR(mode):
            char += 1

print(json.dumps({
    "regular_files": regular,
    "directories": directories,
    "symlinks": symlinks,
    "fifo": fifo,
    "sockets": sockets,
    "block_devices": block,
    "char_devices": char,
    "total_regular_file_bytes": total_bytes,
    "unreadable_regular_files": unreadable,
}, sort_keys=True))
'''.strip()

    remote_command = (
        "python3 -c "
        + shlex.quote(script)
        + " "
        + shlex.quote(source)
    )

    completed = run(
        ssh_base(user, host) + [remote_command]
    )

    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        fail(f"invalid remote source snapshot JSON: {exc}")

    if value["symlinks"] != 0:
        fail("source contains symlinks")

    for key in (
        "fifo",
        "sockets",
        "block_devices",
        "char_devices",
    ):
        if value[key] != 0:
            fail(f"source contains unsupported special objects: {key}")

    if value["unreadable_regular_files"] != 0:
        fail("source contains unreadable regular files")

    return value


def write_remote_manifest(
    destination: Path,
    user: str,
    host: str,
    source: str,
) -> None:
    script = r'''
import hashlib
import json
import os
import pathlib
import stat
import sys

root = pathlib.Path(sys.argv[1])

if not root.exists() or not root.is_dir() or root.is_symlink():
    raise SystemExit("INVALID_SOURCE_ROOT")

records = []

for current, dirs, files in os.walk(root, topdown=True, followlinks=False):
    dirs.sort()
    files.sort()

    for name in files:
        path = pathlib.Path(current) / name
        st = path.lstat()

        if not stat.S_ISREG(st.st_mode):
            continue

        rel = path.relative_to(root).as_posix()

        digest = hashlib.sha256()

        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)

        records.append((rel, digest.hexdigest(), st.st_size))

records.sort(key=lambda item: item[0])

previous = None

for rel, digest, size in records:
    if rel == previous:
        raise SystemExit("DUPLICATE_RELATIVE_PATH")

    previous = rel

    print(json.dumps({
        "path": rel,
        "sha256": digest,
        "size": size,
    }, sort_keys=True, separators=(",", ":")))
'''.strip()

    remote_command = (
        "python3 -c "
        + shlex.quote(script)
        + " "
        + shlex.quote(source)
    )

    destination.parent.mkdir(parents=True, exist_ok=True)

    with destination.open("w", encoding="utf-8", newline="\n") as output:
        completed = subprocess.run(
            ssh_base(user, host) + [remote_command],
            text=True,
            stdout=output,
            stderr=subprocess.PIPE,
        )

    if completed.returncode != 0:
        fail(
            "remote source manifest generation failed: "
            + completed.stderr.strip()
        )


def write_local_manifest(
    destination: Path,
    root: Path,
) -> None:
    if not root.exists() or not root.is_dir() or root.is_symlink():
        fail("invalid destination payload root")

    records: list[tuple[str, str, int]] = []

    for current, dirs, files in os.walk(
        root,
        topdown=True,
        followlinks=False,
    ):
        dirs.sort()
        files.sort()

        for name in files:
            path = Path(current) / name
            st = path.lstat()

            if not path.is_file() or path.is_symlink():
                fail(f"unexpected non-regular destination object: {path}")

            rel = path.relative_to(root).as_posix()

            records.append(
                (
                    rel,
                    sha256_file(path),
                    st.st_size,
                )
            )

    records.sort(key=lambda item: item[0])

    previous: str | None = None

    destination.parent.mkdir(parents=True, exist_ok=True)

    with destination.open("w", encoding="utf-8", newline="\n") as handle:
        for rel, digest, size in records:
            if rel == previous:
                fail(f"duplicate destination relative path: {rel}")

            previous = rel

            handle.write(
                json.dumps(
                    {
                        "path": rel,
                        "sha256": digest,
                        "size": size,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            )


def read_manifest(path: Path) -> dict[str, tuple[str, int]]:
    result: dict[str, tuple[str, int]] = {}

    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.rstrip("\n")

            if not line:
                fail(f"empty manifest record at line {line_number}")

            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                fail(
                    f"invalid manifest JSON at line {line_number}: {exc}"
                )

            rel = value.get("path")
            digest = value.get("sha256")
            size = value.get("size")

            if not isinstance(rel, str) or not rel:
                fail(f"invalid path at manifest line {line_number}")

            if rel in result:
                fail(f"duplicate manifest path: {rel}")

            if (
                not isinstance(digest, str)
                or not re.fullmatch(r"[0-9a-f]{64}", digest)
            ):
                fail(f"invalid SHA-256 at manifest line {line_number}")

            if not isinstance(size, int) or size < 0:
                fail(f"invalid size at manifest line {line_number}")

            result[rel] = (digest, size)

    return result


def directory_count(root: Path) -> int:
    count = 0

    for current, dirs, _files in os.walk(
        root,
        topdown=True,
        followlinks=False,
    ):
        count += 1

        for name in dirs:
            path = Path(current) / name

            if path.is_symlink():
                fail(f"unexpected destination symlink: {path}")

    return count


def rsync_command(
    user: str,
    host: str,
    source: str,
    destination: Path,
    *,
    dry_run: bool,
) -> list[str]:
    argv = [
        "rsync",
        "-a",
        "--protect-args",
        "--stats",
        "-e",
        "ssh -o BatchMode=yes -o ConnectTimeout=10",
    ]

    if dry_run:
        argv.extend(
            [
                "--dry-run",
                "--itemize-changes",
            ]
        )

    argv.extend(
        [
            f"{user}@{host}:{source.rstrip('/')}/",
            f"{destination}/",
        ]
    )

    return argv


def paths_for_operation(
    retained_root: Path,
    operation_id: str,
) -> dict[str, Path]:
    incoming_root = retained_root / ".incoming"
    staging = incoming_root / operation_id
    payload = staging / "payload"
    control = staging / "control"
    final = retained_root / operation_id

    return {
        "incoming_root": incoming_root,
        "staging": staging,
        "payload": payload,
        "control": control,
        "final": final,
    }


def resolve_context(args: argparse.Namespace) -> dict[str, Any]:
    repo = repository_root()

    data = inventory_host_data(repo, args.inventory_host)

    source_relative = validate_source_relative(args.source_relative)

    source = remote_source_path(
        data["sci_oran_runtime_acquisition_root"],
        source_relative,
    )

    retained_root = controller_retained_root(repo)

    if not retained_root.exists():
        fail(f"retained root does not exist: {retained_root}")

    if not retained_root.is_dir() or retained_root.is_symlink():
        fail(f"retained root is not a normal directory: {retained_root}")

    operation_id = validate_operation_id(args.operation_id)

    paths = paths_for_operation(retained_root, operation_id)

    return {
        "repo": repo,
        "inventory_host": args.inventory_host,
        "ansible_host": data["ansible_host"],
        "ansible_user": data["ansible_user"],
        "acquisition_root": data["sci_oran_runtime_acquisition_root"],
        "source_relative": source_relative,
        "source": source,
        "retained_root": retained_root,
        "operation_id": operation_id,
        "paths": paths,
    }


def ensure_operation_absent(ctx: dict[str, Any]) -> None:
    paths = ctx["paths"]

    if paths["staging"].exists() or paths["staging"].is_symlink():
        fail(f"staging operation already exists: {paths['staging']}")

    if paths["final"].exists() or paths["final"].is_symlink():
        fail(f"final retained operation already exists: {paths['final']}")


def mode_plan(ctx: dict[str, Any]) -> int:
    ensure_operation_absent(ctx)

    snapshot = remote_source_snapshot(
        ctx["ansible_user"],
        ctx["ansible_host"],
        ctx["source"],
    )

    plan = {
        "mode": "plan",
        "operation_id": ctx["operation_id"],
        "inventory_host": ctx["inventory_host"],
        "resolved_runtime_host": ctx["ansible_host"],
        "source_root": ctx["source"],
        "destination_staging": str(ctx["paths"]["staging"]),
        "destination_final": str(ctx["paths"]["final"]),
        "source_snapshot": snapshot,
        "source_deletion_performed": False,
    }

    print("PLAN_JSON=" + json.dumps(plan, sort_keys=True))

    command = rsync_command(
        ctx["ansible_user"],
        ctx["ansible_host"],
        ctx["source"],
        ctx["retained_root"],
        dry_run=True,
    )

    completed = run(command)

    if "Number of deleted files: 0" not in completed.stdout:
        fail("rsync dry-run did not report zero deleted files")

    print(completed.stdout, end="")

    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)

    if any(ctx["retained_root"].iterdir()):
        fail("plan mode mutated retained-evidence root")

    print("PLAN_GATE=PASS")
    print("MUTATION_PERFORMED=NO")
    print("SOURCE_DELETION_PERFORMED=NO")

    return 0


def mode_transfer(ctx: dict[str, Any]) -> int:
    ensure_operation_absent(ctx)

    snapshot = remote_source_snapshot(
        ctx["ansible_user"],
        ctx["ansible_host"],
        ctx["source"],
    )

    paths = ctx["paths"]

    paths["payload"].mkdir(parents=True, exist_ok=False)
    paths["control"].mkdir(parents=True, exist_ok=False)

    operation = {
        "schema": "sci_oran_retained_evidence_transfer_v1",
        "mode": "transfer",
        "operation_id": ctx["operation_id"],
        "inventory_host": ctx["inventory_host"],
        "resolved_runtime_host": ctx["ansible_host"],
        "source_root": ctx["source"],
        "source_relative": ctx["source_relative"],
        "destination_staging": str(paths["staging"]),
        "destination_payload": str(paths["payload"]),
        "destination_final": str(paths["final"]),
        "source_snapshot_before_transfer": snapshot,
        "source_deletion_performed": False,
    }

    atomic_write_json(
        paths["control"] / "operation.json",
        operation,
    )

    write_remote_manifest(
        paths["control"] / "source-manifest.jsonl",
        ctx["ansible_user"],
        ctx["ansible_host"],
        ctx["source"],
    )

    source_manifest_sha = sha256_file(
        paths["control"] / "source-manifest.jsonl"
    )

    atomic_write_json(
        paths["control"] / "source-manifest.identity.json",
        {
            "algorithm": "SHA-256",
            "sha256": source_manifest_sha,
        },
    )

    command = rsync_command(
        ctx["ansible_user"],
        ctx["ansible_host"],
        ctx["source"],
        paths["payload"],
        dry_run=False,
    )

    completed = run(command)

    (paths["control"] / "rsync.stdout").write_text(
        completed.stdout,
        encoding="utf-8",
    )

    (paths["control"] / "rsync.stderr").write_text(
        completed.stderr,
        encoding="utf-8",
    )

    atomic_write_json(
        paths["control"] / "transfer-result.json",
        {
            "status": "PASS",
            "rsync_returncode": completed.returncode,
            "source_manifest_sha256": source_manifest_sha,
            "source_deletion_performed": False,
        },
    )

    print(f"STAGING_OPERATION={paths['staging']}")
    print(f"SOURCE_MANIFEST_SHA256={source_manifest_sha}")
    print("TRANSFER_GATE=PASS")
    print("PROMOTION_PERFORMED=NO")
    print("SOURCE_DELETION_PERFORMED=NO")

    return 0


def mode_verify(ctx: dict[str, Any]) -> int:
    paths = ctx["paths"]

    if not paths["staging"].is_dir() or paths["staging"].is_symlink():
        fail("staging operation does not exist as a normal directory")

    if paths["final"].exists() or paths["final"].is_symlink():
        fail("final retained operation already exists")

    source_manifest = paths["control"] / "source-manifest.jsonl"
    transfer_result = paths["control"] / "transfer-result.json"

    if not source_manifest.is_file():
        fail("source manifest is absent")

    if not transfer_result.is_file():
        fail("transfer result is absent")

    snapshot_after = remote_source_snapshot(
        ctx["ansible_user"],
        ctx["ansible_host"],
        ctx["source"],
    )

    regenerated_source_manifest = (
        paths["control"] / "source-manifest.verify.jsonl"
    )

    write_remote_manifest(
        regenerated_source_manifest,
        ctx["ansible_user"],
        ctx["ansible_host"],
        ctx["source"],
    )

    destination_manifest = (
        paths["control"] / "destination-manifest.jsonl"
    )

    write_local_manifest(
        destination_manifest,
        paths["payload"],
    )

    source_original = read_manifest(source_manifest)
    source_verify = read_manifest(regenerated_source_manifest)
    destination = read_manifest(destination_manifest)

    if source_original != source_verify:
        fail("source evidence changed between transfer and verification")

    if source_verify != destination:
        missing = sorted(set(source_verify) - set(destination))
        unexpected = sorted(set(destination) - set(source_verify))

        changed = sorted(
            path
            for path in set(source_verify) & set(destination)
            if source_verify[path] != destination[path]
        )

        atomic_write_json(
            paths["control"] / "verification-result.json",
            {
                "status": "FAIL",
                "missing_count": len(missing),
                "unexpected_count": len(unexpected),
                "changed_count": len(changed),
                "missing_sample": missing[:20],
                "unexpected_sample": unexpected[:20],
                "changed_sample": changed[:20],
                "source_deletion_performed": False,
            },
        )

        fail("source and destination manifests differ")

    destination_directories = directory_count(paths["payload"])

    if len(destination) != snapshot_after["regular_files"]:
        fail("destination regular-file cardinality differs from source")

    if destination_directories != snapshot_after["directories"]:
        fail("destination directory cardinality differs from source")

    destination_bytes = sum(size for _digest, size in destination.values())

    if destination_bytes != snapshot_after["total_regular_file_bytes"]:
        fail("destination byte count differs from source")

    source_manifest_sha = sha256_file(regenerated_source_manifest)
    destination_manifest_sha = sha256_file(destination_manifest)

    atomic_write_json(
        paths["control"] / "verification-result.json",
        {
            "status": "PASS",
            "regular_files": len(destination),
            "directories": destination_directories,
            "total_regular_file_bytes": destination_bytes,
            "source_manifest_sha256": source_manifest_sha,
            "destination_manifest_sha256": destination_manifest_sha,
            "manifest_semantic_equality": True,
            "source_deletion_performed": False,
        },
    )

    print(f"REGULAR_FILE_COUNT={len(destination)}")
    print(f"DIRECTORY_COUNT={destination_directories}")
    print(f"TOTAL_REGULAR_FILE_BYTES={destination_bytes}")
    print(f"SOURCE_MANIFEST_SHA256={source_manifest_sha}")
    print(f"DESTINATION_MANIFEST_SHA256={destination_manifest_sha}")
    print("MANIFEST_SEMANTIC_EQUALITY=YES")
    print("VERIFY_GATE=PASS")
    print("PROMOTION_PERFORMED=NO")
    print("SOURCE_DELETION_PERFORMED=NO")

    return 0


def mode_promote(ctx: dict[str, Any]) -> int:
    paths = ctx["paths"]

    if not paths["staging"].is_dir() or paths["staging"].is_symlink():
        fail("staging operation does not exist as a normal directory")

    if paths["final"].exists() or paths["final"].is_symlink():
        fail("final retained operation already exists")

    verification_path = paths["control"] / "verification-result.json"

    if not verification_path.is_file():
        fail("verification result is absent")

    try:
        verification = json.loads(
            verification_path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as exc:
        fail(f"invalid verification result JSON: {exc}")

    if verification.get("status") != "PASS":
        fail("promotion requires verification status PASS")

    if verification.get("manifest_semantic_equality") is not True:
        fail("promotion requires manifest semantic equality")

    shutil.move(
        str(paths["staging"]),
        str(paths["final"]),
    )

    promoted_control = paths["final"] / "control"

    atomic_write_json(
        promoted_control / "promotion-result.json",
        {
            "status": "PASS",
            "operation_id": ctx["operation_id"],
            "final_destination": str(paths["final"]),
            "source_deletion_performed": False,
        },
    )

    print(f"FINAL_DESTINATION={paths['final']}")
    print("PROMOTION_GATE=PASS")
    print("SOURCE_DELETION_PERFORMED=NO")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Bounded controller-side Sci_O-RAN evidence retention transfer"
        )
    )

    parser.add_argument(
        "mode",
        choices=("plan", "transfer", "verify", "promote"),
    )

    parser.add_argument(
        "--inventory-host",
        required=True,
        help="Canonical Ansible inventory host name.",
    )

    parser.add_argument(
        "--operation-id",
        required=True,
        help="Unique retention transfer operation identifier.",
    )

    parser.add_argument(
        "--source-relative",
        required=True,
        help=(
            "Path relative to sci_oran_runtime_acquisition_root. "
            "Use '.' only for an explicitly authorised whole-root operation."
        ),
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        ctx = resolve_context(args)

        if args.mode == "plan":
            return mode_plan(ctx)

        if args.mode == "transfer":
            return mode_transfer(ctx)

        if args.mode == "verify":
            return mode_verify(ctx)

        if args.mode == "promote":
            return mode_promote(ctx)

        fail(f"unsupported mode: {args.mode}")

    except RetentionError as exc:
        print(f"ERROR={exc}", file=sys.stderr)
        return 1

    except subprocess.CalledProcessError as exc:
        print(
            f"ERROR=command failed rc={exc.returncode}: "
            + " ".join(shlex.quote(x) for x in exc.cmd),
            file=sys.stderr,
        )

        if exc.stdout:
            print(exc.stdout, file=sys.stderr, end="")

        if exc.stderr:
            print(exc.stderr, file=sys.stderr, end="")

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
