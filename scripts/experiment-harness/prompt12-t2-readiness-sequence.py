#!/usr/bin/env python3
"""One diagnostic smoke -> Doctor handoff; no scientific traffic or PRB control.

The diagnostic smoke is deliberately before Doctor. Both may run at most once
per fresh operation ID, and full diagnostic stdout/stderr is preserved.
The live entrypoint is independently gated and MUST NOT be called by offline
qualification. This is not the scientific T2 trigger.
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
import time

SCHEMA = "sci_oran_prompt12_t2_readiness_handoff_v1"
OPERATION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
LIVE_TOKEN = "AUTHORISE_PROMPT12_T2_ONE_SMOKE_AND_DOCTOR"
LIVE_ENV = "SCI_ORAN_PROMPT12_T2_READINESS_ENABLE"
EVIDENCE_LATEST = Path("/tmp/sci-oran/user-plane-smoke/latest.env")
REQUIRED_DOCTOR = (
    "USER_PLANE_READINESS_GATE",
    "HOST_RESOURCE_READINESS_GATE",
    "READINESS_FRESHNESS_GATE",
    "FINAL_ARTIFACT_SCI_ORAN_READY_GATE",
    "SCI_ORAN_READY_GATE",
)


class ReadinessError(Exception):
    pass


def require(condition, reason):
    if not condition:
        raise ReadinessError(reason)


def write_exclusive(path, content):
    path = Path(path)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        fd = os.open(path, flags, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as exc:
        raise ReadinessError("OUTPUT_WRITE_FAILED:" + path.name) from exc


def extract_last(output, key):
    matching = [line.split("=", 1)[1].strip() for line in output.splitlines()
                if line.startswith(key + "=")]
    return matching[-1] if matching else None


def run_one(argv, label, directory, timeout):
    try:
        completed = subprocess.run(
            [str(piece) for piece in argv],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ReadinessError(label + "_EXECUTION_ERROR") from exc
    write_exclusive(directory / (label + ".stdout"), completed.stdout)
    write_exclusive(directory / (label + ".stderr"), completed.stderr)
    require(completed.returncode == 0, label + "_RC_" + str(completed.returncode))
    return completed.stdout


def run_sequence(smoke_argv, doctor_argv, base, operation_id, evidence_latest):
    """Testable single-attempt orchestration. No retries or implicit recovery."""
    require(OPERATION_RE.fullmatch(operation_id), "OPERATION_ID_INVALID")
    require(base.is_absolute() and base.is_dir() and not base.is_symlink(), "EVIDENCE_BASE_INVALID")
    op = base / operation_id
    try:
        op.mkdir(mode=0o700, exist_ok=False)
    except FileExistsError as exc:
        raise ReadinessError("OPERATION_ID_ALREADY_CONSUMED") from exc
    stage = "SMOKE"
    try:
        # Persist intent BEFORE diagnostic traffic; interrupted operations are consumed.
        write_exclusive(op / "intent.json", json.dumps({
            "schema": SCHEMA,
            "operation_id": operation_id,
            "smoke_attempt_limit": 1,
            "doctor_attempt_limit": 1,
            "scientific_traffic_authorized": False,
            "fifo_trigger_authorized": False,
            "prb_control_authorized": False,
        }, sort_keys=True) + "\n")
        smoke_start = time.time_ns()
        smoke_text = run_one(smoke_argv, "smoke", op, timeout=90)
        require(extract_last(smoke_text, "USER_PLANE_FUNCTIONAL_SMOKE_GATE") == "PASS",
                "SMOKE_FUNCTIONAL_GATE_NOT_PASS")
        smoke_id = extract_last(smoke_text, "SMOKE_ID")
        require(smoke_id and OPERATION_RE.fullmatch(smoke_id), "SMOKE_ID_INVALID")
        reported_evidence = extract_last(smoke_text, "LATEST_EVIDENCE")
        require(reported_evidence == str(evidence_latest), "SMOKE_EVIDENCE_PATH_MISMATCH")
        require(evidence_latest.is_file() and evidence_latest.stat().st_size > 0,
                "SMOKE_EVIDENCE_NOT_PRESENT")
        # No older evidence may be reused as fresh evidence for this operation.
        require(evidence_latest.stat().st_mtime_ns >= smoke_start - 2_000_000_000,
                "SMOKE_EVIDENCE_NOT_NEW")
        stage = "DOCTOR"
        doctor_start = time.monotonic_ns()
        doctor_text = run_one(doctor_argv, "doctor", op, timeout=120)
        for key in REQUIRED_DOCTOR:
            require(extract_last(doctor_text, key) == "PASS", "DOCTOR_GATE_NOT_PASS:" + key)
        require(extract_last(doctor_text, "FAILURE_REASON") == "NONE",
                "DOCTOR_FAILURE_REASON_NOT_NONE")
        require(extract_last(doctor_text, "DOCTOR_EXIT_CODE") in ("0", None),
                "DOCTOR_INTERNAL_RC_NOT_ZERO")
        report = {
            "schema": SCHEMA,
            "operation_id": operation_id,
            "smoke_id": smoke_id,
            "smoke_gate": "PASS",
            "doctor_gate": "PASS",
            "smoke_evidence": str(evidence_latest),
            "smoke_stdout_sha256": hashlib.sha256(smoke_text.encode()).hexdigest(),
            "doctor_stdout_sha256": hashlib.sha256(doctor_text.encode()).hexdigest(),
            "doctor_elapsed_ns": time.monotonic_ns() - doctor_start,
            "one_smoke_one_doctor": True,
            "scientific_t2": "NOT_EXECUTED",
            "control_executed": False,
            "traffic_scientific_executed": False,
            "readiness_handoff_gate": "PASS",
        }
        write_exclusive(op / "outcome.json", json.dumps(report, sort_keys=True, indent=2) + "\n")
        return report
    except Exception as exc:
        failure_path = op / "failure.json"
        if not os.path.lexists(failure_path):
            try:
                write_exclusive(failure_path, json.dumps({
                    "schema": SCHEMA,
                    "operation_id": operation_id,
                    "stage": stage,
                    "reason": str(exc)[:300],
                    "automatic_retry": False,
                    "scientific_t2": "NOT_EXECUTED",
                }, sort_keys=True, indent=2) + "\n")
            except ReadinessError:
                pass
        raise


def git_value(repo, *args):
    proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                          text=True, check=False, timeout=15)
    require(proc.returncode == 0, "REPO_GIT_CHECK_FAILED")
    return proc.stdout.strip()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--mode", choices=("inspect", "live"), required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--operation-id", required=True)
    parser.add_argument("--evidence-base", required=True)
    parser.add_argument("--authorization-token")
    args = parser.parse_args(argv)
    try:
        require(OPERATION_RE.fullmatch(args.operation_id), "OPERATION_ID_INVALID")
        repo = Path(args.repo)
        require(repo.is_absolute() and repo.is_dir() and not repo.is_symlink(), "REPOSITORY_INVALID")
        smoke = repo / "scripts" / "sci-oran-user-plane-smoke.sh"
        doctor = repo / "scripts" / "sci-oran-doctor.sh"
        require(smoke.is_file() and not smoke.is_symlink(), "SMOKE_SCRIPT_UNAVAILABLE")
        require(doctor.is_file() and not doctor.is_symlink(), "DOCTOR_SCRIPT_UNAVAILABLE")
        require(git_value(repo, "rev-parse", "HEAD") == args.expected_head,
                "REPOSITORY_HEAD_MISMATCH")
        if args.mode == "inspect":
            require(args.authorization_token is None, "INSPECT_MUST_NOT_BE_AUTHORIZED")
            print("T2_READINESS_SEQUENCE_INSPECTION=PASS")
            print("ORDER=SMOKE_THEN_DOCTOR")
            print("DIAGNOSTIC_SMOKE_EXECUTED=NO")
            print("SCIENTIFIC_T2_EXECUTED=NO")
            return 0
        require(socket.gethostname().split(".")[0] == "tb3-dell", "HOST_NOT_TB3_DELL")
        require(os.environ.get(LIVE_ENV) == "YES", "LIVE_READINESS_INTERLOCK_MISSING")
        require(args.authorization_token == LIVE_TOKEN, "LIVE_READINESS_TOKEN_INVALID")
        require(git_value(repo, "branch", "--show-current") == "main", "BRANCH_NOT_MAIN")
        require(git_value(repo, "status", "--porcelain=v1") == "", "REPOSITORY_DIRTY")
        base = Path(args.evidence_base)
        require(base == Path("/home/khoshaba/sci-oran-evidence/prompt12/t2-26to39/readiness-admissions"),
                "READINESS_EVIDENCE_ROOT_NOT_CANONICAL")
        outcome = run_sequence(["/usr/bin/bash", str(smoke)],
                               ["/usr/bin/bash", str(doctor)],
                               base, args.operation_id, EVIDENCE_LATEST)
        print(json.dumps(outcome, sort_keys=True))
        return 0
    except (ReadinessError, OSError, subprocess.SubprocessError) as exc:
        print("T2_READINESS_HANDOFF_GATE=BLOCKED", file=sys.stderr)
        print("FAIL_REASON=" + str(exc), file=sys.stderr)
        print("SCIENTIFIC_T2_EXECUTED=NO", file=sys.stderr)
        return 65


if __name__ == "__main__":
    raise SystemExit(main())
