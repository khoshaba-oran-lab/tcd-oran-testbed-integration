#!/usr/bin/env python3
"""One controller-side EXPERIMENT for Prompt12 T2, with an offline mode.

NO Day-Start/Day-Stop; those always require separate lifecycle authorization.
No automatic retries at any stage. An interrupted live operation is UNKNOWN
and permanently consumed, even when remote PRB/FIFO state is uncertain.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys

MACRO_TOKEN = "AUTHORISE_ONE_PROMPT12_T2_MACRO"
POSTVAL_MACRO_TOKEN = "AUTHORISE_ONE_PROMPT12_T2_POSTVAL_MACRO"
LIVE_ENV = "SCI_ORAN_PROMPT12_T2_EXPERIMENT_ENABLE"
EXP = re.compile(r"^EXP-\d{8}-DL-18000K-R(?:0[1-9]|[1-9]\d)$")
RUN = re.compile(r"^RUN-\d{8}T\d{6}Z-\d{3}$")
REPO = Path("/home/khoshaba/project/tcd-oran-testbed-integration")
CLAIM_ROOT = Path("/home/khoshaba/sci-oran-evidence/prompt12-controller/t2-26to39")


class ExperimentError(Exception):
    pass


def require(value, reason):
    if not value:
        raise ExperimentError(reason)


def exclusive_json(path, data):
    data = dict(data)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as out:
        json.dump(data, out, indent=2, sort_keys=True)
        out.write("\n")
        out.flush()
        os.fsync(out.fileno())


def installed_inventory(repo):
    # Match the canonical lifecycle wrapper's controller-side inventory contract.
    root = repo / "sci-oran" / "ansible"
    return Path(os.environ.get("SCI_ORAN_INVENTORY", str(root / "inventory.ini")))


def git(repo, *argv):
    p = subprocess.run(["git", "-C", str(repo), *argv], capture_output=True,
                       text=True, timeout=15, check=False)
    require(p.returncode == 0, "GIT_CHECK_FAILED:" + argv[0])
    return p.stdout.strip()


def validate(args):
    require(args.repo.is_absolute() and args.repo.is_dir() and not args.repo.is_symlink(),
            "REPOSITORY_INVALID")
    require(EXP.fullmatch(args.experiment_id) and RUN.fullmatch(args.run_id),
            "SCIENTIFIC_ID_FORMAT_INVALID")
    require(args.experiment_id[4:12] == args.run_id[4:12],
            "SCIENTIFIC_ID_DATE_MISMATCH")
    require(re.fullmatch(r"[0-9a-f]{40}", args.approved_head), "APPROVED_HEAD_INVALID")
    require(git(args.repo, "rev-parse", "HEAD") == args.approved_head,
            "GIT_HEAD_NOT_APPROVED")
    playbook = (args.repo / "sci-oran" / "ansible" / "experiments" / "prompt12" /
                "playbooks" / "prompt12-t2-experiment.yml")
    require(playbook.is_file(), "MACRO_PLAYBOOK_MISSING")
    if args.mode == "offline-qualify":
        require(not args.confirm and args.authorization_token is None,
                "OFFLINE_REJECTS_LIVE_AUTHORIZATION")
        return playbook
    require(args.repo == REPO, "LIVE_REPOSITORY_NOT_CANONICAL")
    require(socket.gethostname().split(".")[0] == "coll" or
            socket.getfqdn() == "coll.vntu.org", "LIVE_CONTROLLER_HOST_INVALID")
    require(args.target == "tb3-dell" and args.confirm,
            "EXPLICIT_TARGET_AND_CONFIRM_REQUIRED")
    required_token = POSTVAL_MACRO_TOKEN if args.protocol == "postval-v1" else MACRO_TOKEN
    require(args.authorization_token == required_token and
            os.environ.get(LIVE_ENV) == "YES", "LIVE_MACRO_AUTHORIZATION_MISSING")
    require(git(args.repo, "branch", "--show-current") == "main" and
            not git(args.repo, "status", "--porcelain"), "LIVE_REPOSITORY_NOT_CLEAN_MAIN")
    require(args.experiment_id[4:12] == datetime.now(timezone.utc).strftime("%Y%m%d"),
            "LIVE_EXPERIMENT_DATE_NOT_CURRENT_UTC")
    inventory = installed_inventory(args.repo)
    require(inventory.is_absolute() and inventory.is_file(),
            "INSTALLED_ANSIBLE_INVENTORY_MISSING")
    return playbook


def offline(repo):
    # Tests use real, nonexecuting materializers and synthetic smoke, Doctor,
    # provider, PRB, FIFO/readback and evidence; no Ansible is invoked here.
    test = repo / "scripts" / "experiment-harness" / "tests" / "test_prompt12_t2_e2e_offline.py"
    require(test.is_file(), "OFFLINE_E2E_TEST_MISSING")
    proc = subprocess.run([sys.executable, "-B", str(test)],
                          stdin=subprocess.DEVNULL, check=False)
    require(proc.returncode == 0, "OFFLINE_E2E_QUALIFICATION_FAILED")
    print("T2_OFFLINE_E2E_GATE=PASS")
    print("LIVE_TRAFFIC_EXECUTED=NO")
    print("FIFO_TRIGGER_EXECUTED=NO")
    return 0


def live(args, playbook):
    # Consume identity on the CONTROLLER before invoking even one remote task.
    parent = CLAIM_ROOT / args.experiment_id
    parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    operation = parent / args.run_id
    if operation.exists():
        raise ExperimentError("CONTROLLER_OPERATION_ALREADY_CONSUMED_NO_REPLAY")
    # RUN IDs are globally single-use, not merely unique within an EXP ID.
    # Consume the cross-experiment claim before any remote execution begins.
    claims = CLAIM_ROOT / "_run-id-claims"
    claims.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        (claims / args.run_id).mkdir(mode=0o700, exist_ok=False)
    except FileExistsError as exc:
        raise ExperimentError("CONTROLLER_RUN_ID_ALREADY_CONSUMED_NO_REPLAY") from exc
    try:
        operation.mkdir(mode=0o700, exist_ok=False)
    except FileExistsError as exc:
        raise ExperimentError("CONTROLLER_OPERATION_ALREADY_CONSUMED_NO_REPLAY") from exc
    started = datetime.now(timezone.utc).isoformat()
    exclusive_json(operation / "intent.json", {
        "schema": "sci_oran_prompt12_t2_controller_intent_v1",
        "started_utc": started,
        "experiment_id": args.experiment_id,
        "run_id": args.run_id,
        "approved_head": args.approved_head,
        "exact_run_limit": 1,
        "automatic_retry": False,
        "protocol": args.protocol,
        "day_start_authorized": False,
        "day_stop_authorized": False,
        "replay_decision": "NEVER_AUTOMATICALLY_REPLAY",
    })
    root = args.repo / "sci-oran" / "ansible"
    inventory = installed_inventory(args.repo)
    argv = [
        "ansible-playbook", "-i", str(inventory), str(playbook),
        "--limit", "tb3-dell",
        "--extra-vars", json.dumps({
            "sci_oran_t2_protocol": args.protocol,
            "sci_oran_prompt12_experiment_id": args.experiment_id,
            "sci_oran_prompt12_run_id": args.run_id,
            "sci_oran_prompt12_approved_head": args.approved_head,
            "sci_oran_prompt12_macro_authorization": (POSTVAL_MACRO_TOKEN if args.protocol == "postval-v1" else MACRO_TOKEN),
            "sci_oran_prompt12_inventory_target": "tb3-dell",
        }, separators=(",", ":")),
    ]
    log = operation / "ansible.log"
    rc = None
    observed = set()
    try:
        with log.open("x", encoding="utf-8") as stream:
            process = subprocess.Popen(argv, cwd=root, stdin=subprocess.DEVNULL,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT,
                                       text=True, bufsize=1)
            assert process.stdout is not None
            for line in process.stdout:
                stream.write(line)
                stream.flush()
                print(line, end="", flush=True)
                if "SCI_ORAN_EXPERIMENT_GATE=PASS" in line:
                    observed.add("macro")
                expected_scientific = ("T2_POSTVAL_VALIDATED=PASS" if args.protocol == "postval-v1"
                                       else "SCIENTIFIC_T2_GATE=PASS")
                if expected_scientific in line:
                    observed.add("scientific")
            rc = process.wait()
        require(rc == 0 and observed == {"macro", "scientific"},
                "EXPERIMENT_GATE_NOT_PASS_OR_ANSIBLE_FAILED")
        outcome = {"schema": "sci_oran_prompt12_t2_controller_outcome_v1",
                   "experiment_id": args.experiment_id,
                   "run_id": args.run_id,
                   "approved_head": args.approved_head,
                   "ansible_returncode": rc,
                   "scientific_t2_gate": "PASS" if args.protocol == "legacy" else "NOT_APPLICABLE_POSTVAL",
                   "t2_postval_validated": "PASS" if args.protocol == "postval-v1" else "NOT_APPLICABLE_LEGACY",
                   "protocol": args.protocol,
                   "controller_gate": "PASS",
                   "day_stop_executed": False,
                   "automatic_retry": False}
        exclusive_json(operation / "outcome.json", outcome)
        print("PROMPT12_EXPERIMENT_CONTROLLER_GATE=PASS")
        return 0
    except (Exception, KeyboardInterrupt) as exc:
        # Never restart the Ansible call; remote PRB state may be UNKNOWN.
        failed = {"schema": "sci_oran_prompt12_t2_controller_failure_v1",
                  "run_id": args.run_id,
                  "ansible_returncode": rc,
                  "reason": type(exc).__name__ + ":" + str(exc)[:300],
                  "live_state": "UNKNOWN_NEVER_AUTOMATICALLY_REPLAY",
                  "scientific_pass": False}
        try:
            exclusive_json(operation / "failure.json", failed)
        except OSError:
            pass
        print("PROMPT12_EXPERIMENT_CONTROLLER_GATE=BLOCKED", file=sys.stderr)
        print("SCIENTIFIC_T2=UNKNOWN_NO_REPLAY", file=sys.stderr)
        return 70


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    ap.add_argument("--mode", required=True, choices=("offline-qualify", "live"))
    ap.add_argument("--protocol", choices=("legacy", "postval-v1"), default="legacy")
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--approved-head", required=True)
    ap.add_argument("--experiment-id", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--target", required=True)
    ap.add_argument("--confirm", action="store_true")
    ap.add_argument("--authorization-token")
    args = ap.parse_args(argv)
    try:
        playbook = validate(args)
        if args.mode == "offline-qualify":
            return offline(args.repo)
        return live(args, playbook)
    except (ExperimentError, OSError, subprocess.SubprocessError) as exc:
        print("PROMPT12_EXPERIMENT_CONTROLLER_GATE=BLOCKED", file=sys.stderr)
        print("FAIL_REASON=" + str(exc), file=sys.stderr)
        return 65


if __name__ == "__main__":
    raise SystemExit(main())
