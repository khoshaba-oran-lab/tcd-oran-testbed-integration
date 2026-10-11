#!/usr/bin/env python3
"""One fresh, non-executing T2 provider plan; no FIFO/provider is started.

The provider must be prearmed BEFORE the existing profile materializer can
allocate the RUN: it requires an existing FIFO, while the provider's reader
requires the future ratio-binding filenames. These filenames are deterministic
and MUST be cross-checked against the materialized runtime profile later.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile

SCHEMA = "sci_oran_prompt12_t2_prearm_plan_v1"
ALLOCATION_SCHEMA = "sci_oran_r6_prompt12_r01_prelaunch_allocation_v1"
TOKEN = "AUTHORISE_PROMPT12_T2_PROVIDER_PLAN"
INTERLOCK = "SCI_ORAN_PROMPT12_T2_PROVIDER_PLAN_ENABLE"
EXP_RE = re.compile(r"^EXP-(\d{8})-DL-18000K-R(?:0[1-9]|[1-9]\d)$")
RUN_RE = re.compile(r"^RUN-(\d{8})T\d{6}Z-\d{3}$")
RUNTIME_PARENT = Path("/home/khoshaba/sci-oran")
EVIDENCE_ROOT = Path("/home/khoshaba/sci-oran-evidence/prompt12/t2-26to39")


class PlanError(Exception):
    pass


def require(condition, why):
    if not condition:
        raise PlanError(why)


def exclusive(path, data):
    require(not os.path.lexists(path), "OUTPUT_ALREADY_EXISTS:" + path.name)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(data, out, indent=2, sort_keys=True)
            out.write("\n")
            out.flush()
            os.fsync(out.fileno())
    except OSError as exc:
        raise PlanError("WRITE_FAILURE:" + path.name) from exc


def invoke(argv, label):
    try:
        result = subprocess.run([str(x) for x in argv], capture_output=True,
                                text=True, stdin=subprocess.DEVNULL,
                                timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PlanError(label + "_EXECUTION_ERROR") from exc
    require(result.returncode == 0, label + "_REJECTED:" + result.stderr[-180:])
    try:
        return json.loads(result.stdout)
    except ValueError as exc:
        raise PlanError(label + "_JSON_INVALID") from exc


def identifiers(exp, run):
    match_e = EXP_RE.fullmatch(exp)
    match_r = RUN_RE.fullmatch(run)
    require(match_e and match_r, "IDENTITY_FORMAT_INVALID")
    require(match_e.group(1) == match_r.group(1), "IDENTITY_DATE_MISMATCH")


def expected_identity(exp, run, parent):
    leaf = hashlib.sha256((exp + "\0" + run).encode("utf-8")).hexdigest()[:32]
    return parent / ("prompt12-runtime-" + leaf), "prompt12-provider-" + leaf


def build_plan(repo, evidence, exp, run, runtime_parent, plan_dir):
    identifiers(exp, run)
    tools = repo / "scripts" / "experiment-harness"
    root, identity = expected_identity(exp, run, runtime_parent)
    fifo = root / "actuator.fifo"
    expected = [str(evidence / exp / run / "runtime" / "ratio-bindings" /
                    ("T%d.binding.json" % i)) for i in range(1, 7)]
    require(not os.path.lexists(root), "RUNTIME_ROOT_ALREADY_CONSUMED")
    require(not os.path.lexists(evidence / exp / run), "RUN_ALREADY_CONSUMED")
    require(plan_dir.is_dir(), "PLAN_DIRECTORY_MISSING")
    launcher = invoke([
        sys.executable, "-B", tools / "prompt12-production-provider-launch-materializer.py",
        "--experiment-id", exp, "--run-id", run,
        "--fifo-path", fifo,
        "--ratio-binding-paths-json", json.dumps(expected, separators=(",", ":")),
        "--initial-transition-index", "2",
    ], "PROVIDER_LAUNCH_MATERIALIZER")
    require(isinstance(launcher, list) and len(launcher) >= 8,
            "PROVIDER_LAUNCH_ARGV_INVALID")
    require(launcher.count("@PROMPT12_ACTUATOR_FIFO@") == 1,
            "PROVIDER_FIFO_PLACEHOLDER_INVALID")
    allocation = {
        "schema": ALLOCATION_SCHEMA,
        "experiment_id": exp,
        "run_id": run,
        "runtime_root": str(root),
        "fifo_path": str(fifo),
        "provider_identity": identity,
        "r01_identity_allocated": True,
        "runtime_root_created": False,
        "fifo_created": False,
        "provider_started": False,
        "reader_started": False,
        "runtime_profile_materialized": False,
        "ratio_bindings_materialized": False,
        "trigger_executed": False,
        "control_executed": False,
        "traffic_executed": False,
    }
    # Allocation and intent are durable before any provider-manager start.
    exclusive(plan_dir / "allocation.json", allocation)
    exclusive(plan_dir / "provider-launch.json", launcher)
    result = {
        "schema": SCHEMA,
        "experiment_id": exp,
        "run_id": run,
        "runtime_root": str(root),
        "fifo_path": str(fifo),
        "provider_identity": identity,
        "ratio_binding_paths": expected,
        "allocation_json": str(plan_dir / "allocation.json"),
        "provider_launch_json": str(plan_dir / "provider-launch.json"),
        "provider_launcher_record": str(plan_dir / "provider-launcher-record.json"),
        "portable_admission": str(plan_dir / "portable-admission.json"),
        "provider_plan_gate": "PASS",
        "provider_started": False,
        "fifo_created": False,
        "traffic_executed": False,
        "control_executed": False,
        "replay_allowed": False,
    }
    exclusive(plan_dir / "plan.json", result)
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    ap.add_argument("--mode", choices=("offline-validate", "prepare"), required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--approved-head", required=True)
    ap.add_argument("--evidence-root", required=True)
    ap.add_argument("--experiment-id", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--authorization-token")
    args = ap.parse_args(argv)
    try:
        repo = Path(args.repo)
        require(repo.is_absolute() and repo.is_dir() and not repo.is_symlink(),
                "REPOSITORY_INVALID")
        proc = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                              capture_output=True, text=True, timeout=15, check=False)
        require(proc.returncode == 0 and proc.stdout.strip() == args.approved_head,
                "APPROVED_HEAD_MISMATCH")
        exp, run = args.experiment_id, args.run_id
        identifiers(exp, run)
        evidence = Path(args.evidence_root)
        require(evidence.is_absolute() and evidence.is_dir() and not evidence.is_symlink(),
                "EVIDENCE_ROOT_INVALID")
        if args.mode == "prepare":
            require(socket.gethostname().split(".")[0] == "tb3-dell",
                    "RUNTIME_HOST_INVALID")
            require(args.authorization_token == TOKEN and
                    os.environ.get(INTERLOCK) == "YES",
                    "LIVE_PREARM_NOT_AUTHORIZED")
            require(evidence == EVIDENCE_ROOT, "EVIDENCE_ROOT_NOT_CANONICAL")
            require(RUNTIME_PARENT.is_dir() and not RUNTIME_PARENT.is_symlink(),
                    "RUNTIME_PARENT_UNAVAILABLE")
            branch = subprocess.run(["git", "-C", str(repo), "branch", "--show-current"],
                                    capture_output=True, text=True, check=False, timeout=15)
            status = subprocess.run(["git", "-C", str(repo), "status", "--porcelain"],
                                    capture_output=True, text=True, check=False, timeout=15)
            require(branch.returncode == 0 and branch.stdout.strip() == "main"
                    and status.returncode == 0 and not status.stdout.strip(),
                    "LIVE_REPOSITORY_NOT_CLEAN_MAIN")
            parent = evidence / "_provider-prelaunch" / exp
            parent.mkdir(parents=True, mode=0o750, exist_ok=True)
            plan_dir = parent / run
            try:
                plan_dir.mkdir(mode=0o700, exist_ok=False)
            except FileExistsError as exc:
                raise PlanError("PRELAUNCH_IDENTITY_ALREADY_CONSUMED") from exc
            # Never automatically delete partially prepared identities.
            result = build_plan(repo, evidence, exp, run, RUNTIME_PARENT, plan_dir)
        else:
            require(args.authorization_token is None, "OFFLINE_AUTHORIZATION_PROHIBITED")
            with tempfile.TemporaryDirectory(prefix="sci-oran-t2-prearm-offline-") as scratch:
                tmp = Path(scratch)
                parent = tmp / "runtime"
                parent.mkdir()
                plan_dir = tmp / "plan"
                plan_dir.mkdir()
                result = build_plan(repo, evidence, exp, run, parent, plan_dir)
                result["disposable_plan"] = True
        print(json.dumps(result, sort_keys=True))
        return 0
    except (PlanError, OSError, subprocess.SubprocessError) as exc:
        print("T2_PREARM_PLAN_GATE=BLOCKED", file=sys.stderr)
        print("FAIL_REASON=" + str(exc), file=sys.stderr)
        print("SCIENTIFIC_TRAFFIC=NO", file=sys.stderr)
        print("FIFO_TRIGGER=NO", file=sys.stderr)
        return 65


if __name__ == "__main__":
    raise SystemExit(main())
