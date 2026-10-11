#!/usr/bin/env python3
"""Fail-closed T2 input assembly using existing, non-executing materializers.

Modes:
  offline-validate: disposable sandbox and synthetic FIFO; nothing live.
  prepare: bounded evidence writes for a *new* run with a prearmed real FIFO.

This script NEVER calls Docker, Ansible, smoke, Doctor, traffic or PRB control.
It is a component of an eventual operator macrooperation, not the macrooperation.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import stat
import subprocess
import sys
import tempfile

SCHEMA = "sci_oran_prompt12_t2_input_assembly_v1"
AUTH_TOKEN = "AUTHORISE_PROMPT12_T2_INPUT_PREPARATION"
ENV_INTERLOCK = "SCI_ORAN_PROMPT12_T2_INPUT_PREP_ENABLE"
EXPERIMENT_RE = re.compile(r"^EXP-\d{8}-DL-18000K-R(?:0[1-9]|[1-9]\d)$")
RUN_RE = re.compile(r"^RUN-\d{8}T\d{6}Z-\d{3}$")
TOOL_NAMES = (
    "prompt12-bounded-runtime-profile-materializer.py",
    "prompt12-bounded-production-binding-builder.py",
    "prompt12-resume-precontrol-materializer.py",
    "prompt12-resume-single-transition-materializer.py",
)


class AssemblyError(Exception):
    pass


def require(condition, reason):
    if not condition:
        raise AssemblyError(reason)


def load_object(path, reason):
    try:
        with Path(path).open(encoding="utf-8") as stream:
            value = json.load(stream)
    except (OSError, ValueError) as exc:
        raise AssemblyError(reason) from exc
    require(isinstance(value, dict), reason)
    return value


def write_exclusive(path, value):
    path = Path(path)
    require(not os.path.lexists(path), "OUTPUT_ALREADY_EXISTS")
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as exc:
        raise AssemblyError("EXCLUSIVE_OUTPUT_WRITE_FAILED") from exc


def run(argv, label):
    try:
        result = subprocess.run(
            [str(part) for part in argv],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=45,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AssemblyError(label + "_EXECUTION_ERROR") from exc
    if result.returncode != 0:
        detail = (result.stderr.strip() or result.stdout.strip())[-240:]
        raise AssemblyError(f"{label}_REJECTED_RC_{result.returncode}:{detail}")
    return result.stdout


def validate_identity(experiment_id, run_id):
    require(EXPERIMENT_RE.fullmatch(experiment_id), "EXPERIMENT_ID_FORMAT_INVALID")
    require(RUN_RE.fullmatch(run_id), "RUN_ID_FORMAT_INVALID")
    require(experiment_id[4:12] == run_id[4:12], "RUN_DATE_MISMATCH")
    require(len(experiment_id) <= 64 and len(run_id) <= 64, "IDENTITY_TOO_LONG")


def identity_fifo(experiment_id, run_id):
    digest = hashlib.sha256(
        (experiment_id + "\x00" + run_id).encode("utf-8")
    ).hexdigest()[:32]
    return Path("/home/khoshaba/sci-oran") / ("prompt12-runtime-" + digest) / "actuator.fifo"


def check_repo(repo, expected_head, require_clean):
    require(repo.is_absolute() and repo.is_dir() and not repo.is_symlink(), "REPO_INVALID")
    head = run(["git", "-C", repo, "rev-parse", "HEAD"], "GIT_HEAD").strip()
    require(head == expected_head, "GIT_HEAD_MISMATCH")
    branch = run(["git", "-C", repo, "branch", "--show-current"], "GIT_BRANCH").strip()
    require(branch == "main", "GIT_BRANCH_NOT_MAIN")
    if require_clean:
        status = run(["git", "-C", repo, "status", "--porcelain=v1", "--untracked-files=all"], "GIT_STATUS")
        require(not status.strip(), "REPOSITORY_NOT_CLEAN")
    base = repo / "scripts" / "experiment-harness"
    for name in TOOL_NAMES:
        path = base / name
        require(path.is_file() and not path.is_symlink(), "TOOL_NOT_FOUND:" + name)
    return base


def prepare_inputs(evidence, experiment_id, run_id, frozen, portable, fifo, tools, offline=False):
    require(evidence.is_absolute() and evidence.is_dir() and not evidence.is_symlink(), "EVIDENCE_ROOT_INVALID")
    experiment_dir = evidence / experiment_id
    run_dir = experiment_dir / run_id
    require(not os.path.lexists(run_dir), "RUN_ID_ALREADY_CONSUMED")
    require(not (experiment_dir.is_symlink() if os.path.lexists(experiment_dir) else False),
            "EXPERIMENT_PARENT_SYMLINK")
    profile = run_dir / "runtime" / "runtime-profile.json"
    binding = run_dir / "runtime" / "production-binding-manifest.json"
    resume = run_dir / "runtime" / "t2-resume-precontrol.json"
    single = run_dir / "runtime" / "t2-single-transition.json"
    try:
        run([
            sys.executable, "-B", tools / TOOL_NAMES[0],
            "--evidence-root", evidence,
            "--experiment-id", experiment_id,
            "--run-id", run_id,
            "--frozen-config", frozen,
            "--portable-runtime-admission", portable,
            "--actuator-fifo-path", fifo,
            "--max-age-ms", "800",
        ], "RUNTIME_PROFILE")
        require(profile.is_file(), "RUNTIME_PROFILE_MISSING")
        profile_value = load_object(profile, "RUNTIME_PROFILE_INVALID")
        require(profile_value.get("experiment_id") == experiment_id, "PROFILE_EXP_MISMATCH")
        require(profile_value.get("run_id") == run_id, "PROFILE_RUN_MISMATCH")
        require(profile_value.get("traffic_duration_s") == 180, "TRAFFIC_DURATION_NOT_180")
        require(profile_value.get("max_age_ms") == 800, "PRETRIGGER_FRESHNESS_NOT_800")
        require(profile_value.get("actuator_fifo_path") == str(fifo), "PROFILE_FIFO_MISMATCH")
        run([sys.executable, "-B", tools / TOOL_NAMES[1], "--profile", profile, "--output", binding], "BINDING")
        require(binding.is_file(), "BINDING_OUTPUT_MISSING")
        binding_value = load_object(binding, "BINDING_INVALID")
        require(len(binding_value.get("transitions", [])) == 6, "BINDING_TRANSITIONS_INVALID")
        require(binding_value["transitions"][1].get("label") == "T2", "T2_BINDING_MISSING")
        run([
            sys.executable, "-B", tools / TOOL_NAMES[2],
            "--manifest", binding, "--initial-transition-index", "2", "--output", resume,
        ], "RESUME_PRECONTROL")
        require(resume.is_file(), "RESUME_PRECONTROL_MISSING")
        resume_value = load_object(resume, "RESUME_PRECONTROL_INVALID")
        require(resume_value.get("first_scientific_transition") == "T2", "RESUME_NOT_T2")
        require(resume_value.get("control_executed") is False, "RESUME_CONTROL_ALREADY_EXECUTED")
        require(resume_value.get("traffic_executed") is False, "RESUME_TRAFFIC_ALREADY_EXECUTED")
        if offline:
            run([
                sys.executable, "-B", tools / TOOL_NAMES[3],
                "--binding-manifest", binding,
                "--resume-materialization", resume,
                "--initial-transition-index", "2", "--output", single,
            ], "SINGLE_TRANSITION")
            result = load_object(single, "SINGLE_TRANSITION_INVALID")
            require(result.get("transition_label") == "T2", "SINGLE_TRANSITION_NOT_T2")
            for flag in ("command_executed", "control_executed", "traffic_executed", "t3_trigger_present"):
                require(result.get(flag) is False, "SINGLE_TRANSITION_UNSAFE:" + flag)
        else:
            # Existing Ansible T2 playbook owns the creation of this artifact.
            require(not os.path.lexists(single), "SINGLE_TRANSITION_OUTPUT_NOT_FRESH")
        values = {
            "schema": SCHEMA,
            "experiment_id": experiment_id,
            "run_id": run_id,
            "runtime_profile": str(profile),
            "binding_manifest": str(binding),
            "resume_materialization": str(resume),
            "single_transition_output": str(single),
            "initial26_applied_gate": "NOT_EXECUTED",
            "smoke_gate": "NOT_EXECUTED",
            "doctor_gate": "NOT_EXECUTED",
            "scientific_t2": "NOT_EXECUTED",
            "control_executed": False,
            "traffic_executed": False,
            "live_authorization_bound": False,
            "assembly_gate": "PASS",
        }
        if not offline:
            write_exclusive(run_dir / "runtime" / "t2-input-assembly.json", values)
        return values
    except Exception as exc:
        # A newly allocated RUN is *consumed* on any post-allocation failure.
        # Never delete or reuse a potentially incomplete run.
        if run_dir.is_dir() and not offline:
            failure = run_dir / "runtime" / "t2-input-assembly.failure.json"
            if failure.parent.is_dir() and not os.path.lexists(failure):
                try:
                    write_exclusive(failure, {
                        "schema": SCHEMA,
                        "assembly_gate": "FAIL_CLOSED",
                        "reason": str(exc)[:400],
                        "run_replay_allowed": False,
                        "control_executed": False,
                        "traffic_executed": False,
                    })
                except AssemblyError:
                    pass
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--mode", choices=("offline-validate", "prepare"), required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--approved-head", required=True)
    parser.add_argument("--evidence-root", required=True)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--frozen-config", required=True)
    parser.add_argument("--portable-admission", required=True)
    parser.add_argument("--fifo-path")
    parser.add_argument("--preparation-token")
    args = parser.parse_args(argv)
    try:
        validate_identity(args.experiment_id, args.run_id)
        repo = Path(args.repo)
        live = args.mode == "prepare"
        if live:
            require(socket.gethostname().split(".")[0] == "tb3-dell", "HOST_NOT_TB3_DELL")
            require(os.environ.get(ENV_INTERLOCK) == "YES", "PREPARATION_INTERLOCK_MISSING")
            require(args.preparation_token == AUTH_TOKEN, "PREPARATION_TOKEN_INVALID")
        tools = check_repo(repo, args.approved_head, require_clean=live)
        frozen = Path(args.frozen_config)
        portable = Path(args.portable_admission)
        require(frozen.is_absolute() and frozen.is_file() and not frozen.is_symlink(), "FROZEN_CONFIG_NOT_FILE")
        require(portable.is_absolute() and portable.is_file() and not portable.is_symlink(), "PORTABLE_ADMISSION_NOT_FILE")
        evidence = Path(args.evidence_root)
        require(evidence.is_absolute(), "EVIDENCE_ROOT_NOT_ABSOLUTE")
        if live:
            require(evidence == Path("/home/khoshaba/sci-oran-evidence/prompt12/t2-26to39"),
                    "EVIDENCE_ROOT_NOT_CANONICAL")
            require(args.fifo_path is not None, "FIFO_NOT_BOUND")
            fifo = Path(args.fifo_path)
            require(fifo == identity_fifo(args.experiment_id, args.run_id), "FIFO_IDENTITY_MISMATCH")
            try:
                require(stat.S_ISFIFO(fifo.stat().st_mode), "FIFO_NOT_FIFO")
            except OSError as exc:
                raise AssemblyError("FIFO_UNAVAILABLE") from exc
            values = prepare_inputs(evidence, args.experiment_id, args.run_id, frozen, portable, fifo, tools)
            print(json.dumps(values, sort_keys=True))
        else:
            require(args.preparation_token is None and args.fifo_path is None,
                    "OFFLINE_MODE_FORBIDS_LIVE_BINDINGS")
            with tempfile.TemporaryDirectory(prefix="sci-oran-t2-assembly-") as scratch:
                sandbox = Path(scratch)
                disposable_evidence = sandbox / "evidence"
                disposable_evidence.mkdir(mode=0o700)
                fifo = sandbox / "actuator.fifo"
                os.mkfifo(fifo, mode=0o600)
                values = prepare_inputs(disposable_evidence, args.experiment_id,
                                        args.run_id, frozen, portable, fifo, tools, offline=True)
                values["run_directory_is_disposable"] = True
                values["scientific_t2"] = "NOT_EXECUTED"
                print(json.dumps(values, sort_keys=True))
        return 0
    except Exception as exc:
        reason = str(exc) if isinstance(exc, AssemblyError) else "UNEXPECTED_" + type(exc).__name__
        print("T2_INPUT_ASSEMBLY_GATE=BLOCKED", file=sys.stderr)
        print("FAIL_REASON=" + reason, file=sys.stderr)
        print("SCIENTIFIC_TRAFFIC=NO", file=sys.stderr)
        print("FIFO_TRIGGER=NO", file=sys.stderr)
        print("PRB_CONTROL=NO", file=sys.stderr)
        return 65


if __name__ == "__main__":
    raise SystemExit(main())
