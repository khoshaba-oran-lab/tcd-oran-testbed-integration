#!/usr/bin/env python3
"""Offline, fail-closed Sci_O-RAN Prompt12 pre-day-start admission.

Runs the real non-executing materializers in a disposable directory.
No lifecycle, provider, FIFO, traffic, or PRB operation is invoked.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tempfile


class GateFailure(Exception):
    def __init__(self, reason, detail=""):
        super().__init__(reason)
        self.reason = reason
        self.detail = detail


def require(ok, reason, detail=""):
    if not ok:
        raise GateFailure(reason, detail)


def run(argv, label, timeout=40):
    try:
        result = subprocess.run(
            [str(x) for x in argv], stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, timeout=timeout, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GateFailure(label + "_EXECUTION_ERROR", type(exc).__name__) from exc
    if result.returncode != 0:
        details = result.stderr.strip() or result.stdout.strip()
        match = re.search(r"FAIL_REASON=([^\s]+)", details)
        if match:
            details = match.group(1)
        raise GateFailure(label + "_REJECTED", f"rc={result.returncode}; {details[:500]}")
    return result.stdout.strip()


def load_json(path, reason):
    try:
        with path.open(encoding="utf-8") as file:
            return json.load(file)
    except (OSError, ValueError) as exc:
        raise GateFailure(reason, type(exc).__name__) from exc


def validate_sandbox_ratio_paths(paths, sandbox, run_dir):
    """Fail closed if a profile could direct a materializer outside disposable evidence."""
    sandbox_root = sandbox.resolve(strict=True)
    expected_root = (run_dir / "runtime" / "ratio-bindings").resolve(strict=False)
    require(expected_root.is_relative_to(sandbox_root), "SANDBOX_ROOT_INVALID")
    require(isinstance(paths, list) and len(paths) == 6,
            "RATIO_BINDING_COUNT_INVALID")
    normalized = []
    for item in paths:
        require(isinstance(item, str) and item, "RATIO_BINDING_PATH_INVALID")
        candidate = Path(item)
        require(candidate.is_absolute(), "RATIO_BINDING_PATH_NOT_ABSOLUTE", item)
        resolved = candidate.resolve(strict=False)
        require(resolved.is_relative_to(expected_root),
                "RATIO_BINDING_PATH_OUTSIDE_SANDBOX", item)
        require(not os.path.lexists(candidate), "RATIO_BINDING_PRECREATED", item)
        normalized.append(str(resolved))
    require(len(set(normalized)) == 6, "RATIO_BINDING_PATH_DUPLICATE")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--approved-head", required=True)
    parser.add_argument("--evidence-root", required=True)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--fifo-path", help="Optional consistency check; derived from provider identity by default")
    parser.add_argument("--portable-admission", required=True)
    parser.add_argument("--frozen-config", required=True)
    parser.add_argument("--allocation", help="Existing, read-only prelaunch allocation, if applicable")
    args = parser.parse_args()

    require(socket.gethostname().split(".")[0] == "tb3-dell", "HOST_MISMATCH")
    repo = Path(args.repo)
    evidence = Path(args.evidence_root)
    require(repo.is_absolute() and repo.is_dir() and not repo.is_symlink(), "REPO_INVALID")
    require(evidence.is_absolute() and evidence.is_dir() and not evidence.is_symlink(), "EVIDENCE_ROOT_INVALID")
    require(args.experiment_id and args.run_id, "RUN_IDENTITY_MISSING")
    require("/" not in args.experiment_id and "/" not in args.run_id, "RUN_IDENTITY_PATH_TRAVERSAL")
    require(args.experiment_id not in (".", "..") and args.run_id not in (".", ".."), "RUN_IDENTITY_PATH_TRAVERSAL")
    experiment_dir = evidence / args.experiment_id
    if experiment_dir.is_dir():
        collisions = [
            item.name for item in experiment_dir.iterdir()
            if item.name == args.run_id or item.name.startswith(args.run_id + ".")
        ]
        require(not collisions, "RUN_ID_PREVIOUSLY_USED_OR_ARCHIVED", ",".join(sorted(collisions)[:4]))
    require(not os.path.lexists(experiment_dir / args.run_id), "RUN_DIRECTORY_ALREADY_EXISTS")

    head = run(["git", "-C", repo, "rev-parse", "HEAD"], "GIT_HEAD")
    require(head == args.approved_head, "HEAD_NOT_APPROVED", head)
    branch = run(["git", "-C", repo, "branch", "--show-current"], "GIT_BRANCH")
    require(branch == "main", "WRONG_BRANCH", branch)
    worktree = run(["git", "-C", repo, "status", "--porcelain=v1"], "GIT_STATUS")
    require(not worktree, "DIRTY_REPOSITORY", worktree[:250])

    scripts = repo / "scripts" / "experiment-harness"
    tools = {
        "PROFILE": scripts / "prompt12-bounded-runtime-profile-materializer.py",
        "BINDINGS": scripts / "prompt12-bounded-production-binding-builder.py",
        "RESUME": scripts / "prompt12-resume-precontrol-materializer.py",
        "T2": scripts / "prompt12-resume-single-transition-materializer.py",
        "PROVIDER_LAUNCH": scripts / "prompt12-production-provider-launch-materializer.py",
        "IDENTITY": scripts / "prompt12-production-provider-identity-materializer.py",
    }
    for label, path in tools.items():
        require(path.is_file() and not path.is_symlink(), label + "_TOOL_MISSING", str(path))
    portable = Path(args.portable_admission)
    frozen = Path(args.frozen_config)
    require(portable.is_file() and not portable.is_symlink(), "PORTABLE_ADMISSION_MISSING")
    require(frozen.is_file() and not frozen.is_symlink(), "FROZEN_CONFIG_MISSING")

    identity_raw = run([
        "/usr/bin/python3", "-B", tools["IDENTITY"],
        "--experiment-id", args.experiment_id,
        "--run-id", args.run_id,
    ], "PROVIDER_IDENTITY_DRY_RUN")
    try:
        identity = json.loads(identity_raw)["provider_identity"]
    except (TypeError, ValueError, KeyError) as exc:
        raise GateFailure("PROVIDER_IDENTITY_OUTPUT_INVALID") from exc
    require(isinstance(identity, str) and re.fullmatch(r"prompt12-provider-[0-9a-f]+", identity) is not None,
            "PROVIDER_IDENTITY_INVALID")
    runtime_root = Path("/home/khoshaba/sci-oran") / ("prompt12-runtime-" + identity.removeprefix("prompt12-provider-"))
    fifo = runtime_root / "actuator.fifo"
    if args.fifo_path:
        require(Path(args.fifo_path) == fifo, "FIFO_IDENTITY_MISMATCH", str(fifo))
    require(runtime_root.parent.is_dir(), "RUNTIME_PARENT_MISSING")
    require(not os.path.lexists(runtime_root), "RUNTIME_ROOT_ALREADY_EXISTS")
    require(not os.path.lexists(fifo), "FIFO_ALREADY_EXISTS")

    if args.allocation:
        allocation_path = Path(args.allocation)
        require(allocation_path.is_file() and not allocation_path.is_symlink(), "ALLOCATION_MISSING")
        allocation = load_json(allocation_path, "ALLOCATION_INVALID")
        require(allocation.get("schema") == "sci_oran_r6_prompt12_r01_prelaunch_allocation_v1", "ALLOCATION_SCHEMA_INVALID")
        expected = {
            "experiment_id": args.experiment_id,
            "run_id": args.run_id,
            "fifo_path": str(fifo),
            "runtime_root": str(runtime_root),
        }
        for key, value in expected.items():
            require(allocation.get(key) == value, "ALLOCATION_" + key.upper() + "_MISMATCH")
        require(allocation.get("provider_identity") == identity, "ALLOCATION_PROVIDER_IDENTITY_MISMATCH")
        for key in ("runtime_root_created", "fifo_created", "provider_started", "reader_started", "traffic_executed", "trigger_executed", "control_executed"):
            require(allocation.get(key) is False, "ALLOCATION_FLAG_INVALID", key)

    # Day-stop expectation: none of the managed radio containers is currently running.
    require(shutil.which("docker") is not None, "DOCKER_CLI_UNAVAILABLE")
    running = run(["docker", "ps", "--format", "{{.Names}}"], "DOCKER_INSPECT")
    names = set(running.splitlines())
    managed = {"base05_srsran_gnb", "base05_srsran_srsue", "base05_open5gs_5gc", "action11_202_flexric_ric_safe"}
    require(not (names & managed), "TB3_ALREADY_RUNNING", ",".join(sorted(names & managed)))
    # Avoid conflicting with a stopped receiver from an earlier attempt.
    container_names = set(run(["docker", "ps", "-a", "--format", "{{.Names}}"], "DOCKER_ALL_CONTAINERS").splitlines())
    expected_receiver = "prompt12-" + args.run_id.lower() + "-receiver"
    require(expected_receiver not in container_names, "RECEIVER_CONTAINER_COLLISION", expected_receiver)

    # The actual implementation is invoked once in disposable /tmp evidence,
    # with the candidate ID. It can reject the precise EXP/RUN syntax and frozen
    # configuration WITHOUT touching the actual experimental evidence root.
    with tempfile.TemporaryDirectory(prefix="sci-oran-prestart-") as scratch:
        sandbox = Path(scratch) / "evidence"
        sandbox.mkdir(mode=0o700)
        offline_fifo = Path(scratch) / 'actuator.fifo'
        os.mkfifo(offline_fifo, mode=0o600)
        py = "/usr/bin/python3"
        run([
            py, "-B", tools["PROFILE"],
            "--evidence-root", sandbox,
            "--experiment-id", args.experiment_id,
            "--run-id", args.run_id,
            "--frozen-config", frozen,
            "--portable-runtime-admission", portable,
            "--actuator-fifo-path", offline_fifo,
            "--max-age-ms", "800",
        ], "PROFILE_DRY_RUN")
        run_dir = sandbox / args.experiment_id / args.run_id
        runtime = run_dir / "runtime"
        profile_path = runtime / "runtime-profile.json"
        profile = load_json(profile_path, "PROFILE_OUTPUT_MISSING")
        require(profile.get("experiment_id") == args.experiment_id, "PROFILE_EXP_MISMATCH")
        require(profile.get("run_id") == args.run_id, "PROFILE_RUN_MISMATCH")
        require(profile.get("actuator_fifo_path") == str(offline_fifo), "PROFILE_FIFO_MISMATCH")
        require(profile.get("traffic_duration_s") == 180, "DURATION_MISMATCH")
        require(profile.get("max_age_ms") == 800, "FRESHNESS_POLICY_MISMATCH")
        ratio = profile.get("ratio_binding_paths")
        validate_sandbox_ratio_paths(ratio, sandbox, run_dir)

        manifest = runtime / "production-binding-manifest.json"
        run([py, "-B", tools["BINDINGS"], "--profile", profile_path, "--output", manifest], "BINDINGS_DRY_RUN")
        require(manifest.is_file(), "BINDING_MANIFEST_MISSING")
        resume = runtime / "t2-resume-precontrol.json"
        run([py, "-B", tools["RESUME"], "--manifest", manifest, "--initial-transition-index", "2", "--output", resume], "RESUME_DRY_RUN")
        t2 = runtime / "t2-single-transition.json"
        run([py, "-B", tools["T2"], "--binding-manifest", manifest, "--resume-materialization", resume, "--initial-transition-index", "2", "--output", t2], "T2_DRY_RUN")
        t2_data = load_json(t2, "T2_OUTPUT_MISSING")
        require(t2_data.get("first_scientific_transition") == "T2", "T2_LABEL_INVALID")
        for key in ("command_executed", "control_executed", "traffic_executed", "t3_handoff_present", "t3_trigger_present"):
            require(t2_data.get(key) is False, "T2_SAFETY_FLAG_INVALID", key)

        # This tool creates an argv description; never execute its output.
        launch_text = run([
            py, "-B", tools["PROVIDER_LAUNCH"],
            "--experiment-id", args.experiment_id,
            "--run-id", args.run_id,
            "--fifo-path", offline_fifo,
            "--ratio-binding-paths-json", json.dumps(ratio, separators=(",", ":")),
            "--initial-transition-index", "2",
        ], "PROVIDER_LAUNCH_DRY_RUN")
        try:
            launch = json.loads(launch_text)
        except ValueError as exc:
            raise GateFailure("PROVIDER_LAUNCH_OUTPUT_INVALID", str(exc)) from exc
        require(isinstance(launch, list) and len(launch) >= 2, "PROVIDER_LAUNCH_ARGV_INVALID")
        require(not os.path.lexists(runtime_root), "RUNTIME_ROOT_CREATED_UNEXPECTEDLY")

    return {
        "PRESTART_GATE": "PASS",
        "HOST": "tb3-dell",
        "HEAD": head,
        "EXPERIMENT_ID": args.experiment_id,
        "RUN_ID": args.run_id,
        "DERIVED_FIFO": str(fifo),
        "PROVIDER_IDENTITY": identity,
        "PROFILE_DRY_RUN": "PASS",
        "BINDINGS_DRY_RUN": "PASS",
        "RESUME_T2_DRY_RUN": "PASS",
        "PROVIDER_LAUNCH_DRY_RUN": "PASS",
        "PROVIDER_IDENTITY_DRY_RUN": "PASS",
        "ACTUAL_EVIDENCE_WRITE_REQUESTED": "NO",
        "LIFECYCLE_STARTED": "NO",
        "PROVIDER_STARTED": "NO",
        "SCIENTIFIC_TRAFFIC": "NO",
        "FIFO_TRIGGER": "NO",
        "PRB_CONTROL": "NO",
        "CAUTION": "Preflight only; does not authorise live T2 or guarantee live freshness",
    }


if __name__ == "__main__":
    try:
        print(json.dumps(main(), sort_keys=True))
    except GateFailure as exc:
        print(json.dumps({"PRESTART_GATE": "BLOCKED", "REASON": exc.reason, "DETAIL": exc.detail}, sort_keys=True))
        sys.exit(20)
    except Exception as exc:
        print(json.dumps({"PRESTART_GATE": "BLOCKED", "REASON": "UNEXPECTED_PREFLIGHT_ERROR", "DETAIL": type(exc).__name__}, sort_keys=True))
        sys.exit(21)
