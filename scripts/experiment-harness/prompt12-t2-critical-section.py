#!/usr/bin/env python3
"""Resumed T2 precontrol -> ratio binding -> FIFO trigger, one local invocation.

Production-only argv from the existing, non-executing T2 materializer is used.
The inspection mode does not execute any child process or write any evidence.
A durable, run-scoped, exclusive intent is created before the first live child;
its existence forbids a second invocation regardless of eventual outcome.
"""

import argparse
import datetime
import json
import os
import pathlib
import re
import subprocess
import sys
import uuid
from typing import Any

SCHEMA = "sci_oran_prompt12_resume_single_transition_materialization_v1"
LIVE_TOKEN = "AUTHORISE_PROMPT12_RESUMED_T2_26_TO_39_LIVE"
CONTROL_TOKEN = "PROMPT12_T2_EXPLICIT_FIFO_CONTROL"
CONTROL_PLACEHOLDER = "@PROMPT12_CONTROL_AUTHORIZATION_TOKEN@"
LIVE_INTERLOCK = "SCI_ORAN_PROMPT12_LIVE_CONTROL_ENABLE"


class CriticalError(Exception):
    pass


def option(argv: list[str], name: str) -> str:
    if argv.count(name) != 1:
        raise CriticalError(f"OPTION_CARDINALITY_INVALID:{name}")
    index = argv.index(name)
    if index + 1 == len(argv):
        raise CriticalError(f"OPTION_VALUE_MISSING:{name}")
    return argv[index + 1]


def command(report: dict[str, Any], key: str, script: str) -> list[str]:
    argv = report.get(key)
    if (
        not isinstance(argv, list)
        or len(argv) < 2
        or any(not isinstance(x, str) or not x or "\x00" in x for x in argv)
        or pathlib.Path(argv[0]).name not in (
            "python3", "python", "python3.9", "python3.10", "python3.11",
            "python3.12", "python3.13",
        )
    ):
        raise CriticalError(f"UNTRUSTED_COMMAND:{key}")
    # Materialization cannot redirect any child to another script that merely
    # has the same basename. It must use the verified script in this checkout.
    expected = pathlib.Path(__file__).resolve().with_name(script)
    try:
        actual = pathlib.Path(argv[1]).resolve(strict=True)
    except OSError as exc:
        raise CriticalError(f"COMMAND_SOURCE_UNAVAILABLE:{key}") from exc
    if actual != expected:
        raise CriticalError(f"COMMAND_SOURCE_IDENTITY_MISMATCH:{key}")
    return argv


def load_plan(path: pathlib.Path) -> tuple[dict[str, Any], dict[str, list[str]], pathlib.Path]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CriticalError(f"MATERIALIZATION_UNAVAILABLE:{type(exc).__name__}") from exc
    if not isinstance(raw, dict) or raw.get("schema") != SCHEMA:
        raise CriticalError("MATERIALIZATION_SCHEMA_INVALID")
    frozen = (
        raw.get("transition_label") == "T2"
        and raw.get("transition_index") == 2
        and raw.get("executed_transition_ordinal") == 1
        and raw.get("expected_actuator_transaction_count") == 1
        and raw.get("expected_timeline_event_count") == 3
        and all(raw.get(key) is False for key in (
            "synthetic_prior_transition_events", "skipped_transition_bindings_consumed",
            "t3_handoff_present", "t3_trigger_present", "command_executed",
            "control_executed", "traffic_executed",
        ))
    )
    if not frozen:
        raise CriticalError("T2_FROZEN_INVARIANT_FAILED")

    pre = command(raw, "initial_precontrol_command", "prompt12-bounded-precontrol-handoff.py")
    ratio = command(raw, "ratio_bind_command", "prompt12-pretrigger-ratio-binding-writer.py")
    trigger = command(raw, "trigger_command", "prompt12-precontrol-trigger-executor.py")
    if pre.count("--stationarity-command") != 1 or pre.count("--freshness-command") != 1:
        raise CriticalError("PRECONTROL_HANDOFF_CONTRACT_INVALID")
    if (
        option(ratio, "--transition-label") != "T2"
        or option(ratio, "--transition-index") != "2"
        or option(ratio, "--requested-ratio-pct") != "75"
        or option(trigger, "--mode") != "fifo"
        or option(trigger, "--max-age-ms") != "800"
        or option(trigger, "--control-authorization-token") != CONTROL_PLACEHOLDER
        or trigger.count(CONTROL_PLACEHOLDER) != 1
    ):
        raise CriticalError("T2_COMMAND_CONTRACT_INVALID")

    source = pathlib.Path(option(pre, "--precontrol-output"))
    trigger_source = pathlib.Path(option(trigger, "--precontrol-json"))
    ratio_output = pathlib.Path(option(ratio, "--output"))
    executor_output = pathlib.Path(option(trigger, "--output"))
    if any(not p.is_absolute() for p in (source, trigger_source, ratio_output, executor_output)):
        raise CriticalError("T2_OUTPUT_PATH_NOT_ABSOLUTE")
    run = executor_output.parent.parent
    if (
        source != trigger_source
        or source != run / "precontrol" / "T2.json"
        or executor_output != run / "control" / "T2.executor.json"
        or ratio_output != run / "runtime" / "ratio-bindings" / "T2.binding.json"
    ):
        raise CriticalError("T2_RUN_SCOPE_MISMATCH")
    return raw, {"precontrol": pre, "ratio": ratio, "trigger": trigger}, executor_output


def write_exclusive(path: pathlib.Path, record: dict[str, Any]) -> None:
    """Never overwrite evidence; persist an irrevocable intent before live work."""
    payload = (json.dumps(record, sort_keys=True, indent=2) + "\n").encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        dir_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except Exception:
        # Never remove a possibly committed intent; a restart must fail closed.
        raise


def run_child(argv: list[str], label: str) -> subprocess.CompletedProcess[str]:
    try:
        proc = subprocess.run(
            argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding="utf-8", check=False,
            timeout=35,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CriticalError(f"{label}_EXECUTION_UNKNOWN:{type(exc).__name__}") from exc
    if proc.returncode != 0:
        raise CriticalError(f"{label}_FAILED:RC_{proc.returncode}")
    return proc


def run_live(plan: dict[str, Any], commands: dict[str, list[str]], executor_output: pathlib.Path, operation_id: str, control_token: str) -> dict[str, Any]:
    intent = executor_output.with_name("T2.trigger-intent.json")
    outcome = executor_output.with_name("T2.critical-outcome.json")
    if not executor_output.parent.is_dir():
        raise CriticalError("CONTROL_EVIDENCE_DIRECTORY_MISSING")
    if intent.exists() or outcome.exists() or executor_output.exists():
        raise CriticalError("T2_OPERATION_ALREADY_CONSUMED_NO_REPLAY")

    # This file is never deleted, including when stationarity, ratio, or FIFO fails.
    # A crash after FIFO submission cannot permit a second trigger invocation.
    write_exclusive(intent, {
        "schema": "sci_oran_prompt12_t2_irrevocable_intent_v1",
        "operation_id": operation_id,
        "transition": "T2",
        "state": "CONSUMED_BEFORE_PRECONTROL_NO_AUTOMATIC_REPLAY",
        "scientific_trigger_replay_decision": "NEVER_AUTOMATICALLY_REPLAY",
        "executor_output": str(executor_output),
        "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    })

    # A second, broader claim prevents reusing an operation ID in a different
    # run of the same experimental scenario. Both claims are exclusive.
    claims = executor_output.parent.parent.parent.parent / ".t2-operation-claims"
    if claims.is_symlink():
        raise CriticalError("GLOBAL_OPERATION_CLAIMS_SYMLINK_FORBIDDEN")
    claims.mkdir(mode=0o700, exist_ok=True)
    if not claims.is_dir():
        raise CriticalError("GLOBAL_OPERATION_CLAIMS_DIRECTORY_INVALID")
    claim = claims / (operation_id + ".json")
    try:
        write_exclusive(claim, {
            "schema": "sci_oran_prompt12_t2_operation_claim_v1",
            "operation_id": operation_id,
            "run_root": str(executor_output.parent.parent),
            "scientific_trigger_replay_decision": "NEVER_AUTOMATICALLY_REPLAY",
        })
    except FileExistsError as exc:
        raise CriticalError("T2_OPERATION_ID_ALREADY_CONSUMED") from exc

    result: dict[str, Any] = {
        "schema": "sci_oran_prompt12_t2_critical_outcome_v1",
        "operation_id": operation_id,
        "state": "FAIL_CLOSED",
        "scientific_trigger_replay_decision": "NEVER_AUTOMATICALLY_REPLAY",
        "trigger_dispatch_attempted": False,
        "trigger_execution_confirmed": False,
        "intent": str(intent),
        "global_operation_claim": str(claim),
    }
    try:
        pre = run_child(commands["precontrol"], "PRECONTROL")
        try:
            stationarity = json.loads(pre.stdout)
        except json.JSONDecodeError as exc:
            raise CriticalError("STATIONARITY_STDOUT_INVALID") from exc
        if not isinstance(stationarity, dict) or any(
            stationarity.get(k) != "PASS" for k in (
                "output_stationarity_gate", "minimum_phase_duration_gate",
                "statistical_phase_candidate",
            )
        ):
            raise CriticalError("T2_PRECONTROL_STATIONARITY_NOT_PASS")

        ratio = run_child(commands["ratio"], "RATIO_BIND")
        if "RATIO_BOUND=PASS" not in ratio.stdout.splitlines():
            raise CriticalError("T2_RATIO_BIND_MARKER_MISSING")

        # Capture the gNB log window start on the runtime host immediately
        # before the local trigger subprocess. Ansible cannot do this atomically.
        readback_start = datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S.%fZ"
        )
        resolved_trigger = [
            control_token if item == CONTROL_PLACEHOLDER else item
            for item in commands["trigger"]
        ]
        result["trigger_dispatch_attempted"] = True
        trigger = run_child(resolved_trigger, "TRIGGER")
        try:
            executor_report = json.loads(executor_output.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CriticalError("TRIGGER_OUTCOME_MISSING_OR_INVALID") from exc
        if not isinstance(executor_report, dict) or not all((
            executor_report.get("EXECUTOR_GATE") == "PASS",
            executor_report.get("CONTROL_EXECUTED") == "YES",
            executor_report.get("SCIENTIFIC_TRIGGER_CONSUMED") == "YES",
            executor_report.get("TRIGGER_WRITE_ATTEMPT_COUNT") == 1,
            executor_report.get("TRIGGER_WRITE_SUCCESS_COUNT") == 1,
            executor_report.get("EXECUTOR_START_SAMPLE_AGE_GATE") == "PASS",
        )):
            raise CriticalError("TRIGGER_EXECUTOR_CONTRACT_NOT_PASS")
        result.update({
            "state": "TRIGGER_CONFIRMED_AWAITING_READBACK",
            "trigger_execution_confirmed": True,
            "readback_window_start_utc": readback_start,
        })
        return {**stationarity, "readback_window_start_utc": readback_start}
    except CriticalError as exc:
        result["failure_reason"] = str(exc)
        raise
    finally:
        # A missing outcome after a crash still leaves the durable intent.
        write_exclusive(outcome, result)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--materialization", required=True)
    parser.add_argument("--mode", choices=("inspect", "live"), default="inspect")
    parser.add_argument("--operation-id")
    parser.add_argument("--live-authorization-token")
    parser.add_argument("--control-authorization-token")
    args = parser.parse_args(argv)
    try:
        plan, commands, executor_output = load_plan(pathlib.Path(args.materialization))
        if args.mode == "inspect":
            if args.live_authorization_token or args.control_authorization_token:
                raise CriticalError("INSPECT_REJECTS_LIVE_AUTHORIZATION")
            print("PROMPT12_T2_CRITICAL_INSPECTION=PASS")
            print("SCIENTIFIC_TRAFFIC_EXECUTED=NO")
            print("CONTROL_EXECUTED=NO")
            return 0
        if (
            args.live_authorization_token != LIVE_TOKEN
            or args.control_authorization_token != CONTROL_TOKEN
            or os.environ.get(LIVE_INTERLOCK) != "YES"
            or (args.operation_id is not None and
                re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{7,127}", args.operation_id) is None)
        ):
            raise CriticalError("T2_LIVE_AUTHORIZATION_INVALID")
        operation_id = args.operation_id or ("prompt12-t2-" + uuid.uuid4().hex)
        stationarity = run_live(plan, commands, executor_output, operation_id, args.control_authorization_token)
        print(json.dumps(stationarity, sort_keys=True))
        return 0
    except (CriticalError, FileExistsError, OSError) as exc:
        print(f"PROMPT12_T2_CRITICAL_SECTION_GATE=FAIL", file=sys.stderr)
        print(f"FAIL_REASON={type(exc).__name__}:{exc}", file=sys.stderr)
        return 70


if __name__ == "__main__":
    sys.exit(main())
