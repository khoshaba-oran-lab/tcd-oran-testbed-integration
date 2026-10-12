#!/usr/bin/env python3
"""One scientific T2-POSTVAL-v1 FIFO trigger, after bounded read-only receiver tail.

The previous PRECONTROL stationarity is NOT simulated or bypassed: this is a
separately versioned protocol that requires independent post-validation.
No network/Docker operations, retry, daemon, or PRB readback in this module.
Ansible must authorize live invocation and perform authoritative readback.
"""
import argparse
import datetime
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys
import time
import uuid
from decimal import Decimal

SCHEMA = "sci_oran_t2_postval_one_shot_v1"
PLAN_SCHEMA = "sci_oran_prompt12_resume_single_transition_materialization_v1"
PROFILE_SCHEMA = "sci_oran_prompt12_bounded_sequence_runtime_profile_v1"
LIVE_TOKEN = "AUTHORISE_PROMPT12_RESUMED_T2_26_TO_39_LIVE"
CONTROL_TOKEN = "PROMPT12_T2_EXPLICIT_FIFO_CONTROL"
CONTROL_PLACEHOLDER = "@PROMPT12_CONTROL_AUTHORIZATION_TOKEN@"
INTERLOCK = "SCI_ORAN_PROMPT12_LIVE_CONTROL_ENABLE"
POSTVAL_INTERLOCK = "SCI_ORAN_T2_POSTVAL_V1_ENABLE"
MAX_AGE_NS = 800_000_000
TARGET_INTERVAL_END_S = Decimal("90.0")
LATEST_ACCEPTABLE_END_S = Decimal("90.4")
MAX_WAIT_SECONDS = 90
POLL_SECONDS = 0.05


class PostvalError(Exception):
    pass


def require(condition, reason):
    if not condition:
        raise PostvalError(reason)


def read_obj(path):
    require(path.is_absolute() and path.is_file() and not path.is_symlink(),
            "REQUIRED_JSON_UNAVAILABLE")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PostvalError("INVALID_JSON") from exc
    require(isinstance(data, dict), "JSON_NOT_OBJECT")
    return data


def option(argv, key):
    require(isinstance(argv, list) and argv.count(key) == 1, "OPTION_CARDINALITY:" + key)
    idx = argv.index(key)
    require(idx + 1 < len(argv) and isinstance(argv[idx + 1], str),
            "OPTION_VALUE_INVALID:" + key)
    return argv[idx + 1]


def load_tail():
    path = Path(__file__).resolve().with_name("prompt12-t2-postval-tail-reader.py")
    spec = importlib.util.spec_from_file_location("sci_oran_postval_tail_reader", path)
    require(spec is not None and spec.loader is not None, "TAIL_MODULE_MISSING")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_binding(materialization):
    plan = read_obj(materialization)
    require(plan.get("schema") == PLAN_SCHEMA and
            plan.get("transition_label") == "T2" and
            plan.get("transition_index") == 2 and
            plan.get("executed_transition_ordinal") == 1 and
            plan.get("expected_timeline_event_count") == 3 and
            plan.get("expected_actuator_transaction_count") == 1,
            "T2_MATERIALIZATION_INVALID")
    require(all(plan.get(flag) is False for flag in (
        "synthetic_prior_transition_events", "skipped_transition_bindings_consumed",
        "t3_handoff_present", "t3_trigger_present", "command_executed",
        "control_executed", "traffic_executed")), "T2_FROZEN_INVARIANT_INVALID")
    trigger = plan.get("trigger_command")
    ratio = plan.get("ratio_bind_command")
    require(isinstance(trigger, list) and isinstance(ratio, list), "COMMAND_MISSING")
    require(option(trigger, "--mode") == "fifo" and
            option(trigger, "--max-age-ms") == "800" and
            option(trigger, "--control-authorization-token") == CONTROL_PLACEHOLDER and
            trigger.count(CONTROL_PLACEHOLDER) == 1 and
            option(ratio, "--transition-label") == "T2" and
            option(ratio, "--transition-index") == "2" and
            option(ratio, "--requested-ratio-pct") == "75",
            "T2_COMMAND_CONTRACT_INVALID")
    exe = Path(option(trigger, "--output"))
    run = exe.parent.parent
    require(exe.is_absolute() and exe == run / "control" / "T2.executor.json" and
            materialization == run / "runtime" / materialization.name and
            materialization.name.endswith(".json") and run.is_dir(),
            "RUN_SCOPE_INVALID")
    raw_command = plan.get("traffic_command")
    require(isinstance(raw_command, list) and len(raw_command) == 7,
            "TRAFFIC_COMMAND_INVALID")
    raw, stamps = Path(raw_command[4]), Path(raw_command[5])
    require(raw.is_absolute() and stamps.is_absolute() and raw != stamps and
            raw.is_relative_to(run) and stamps.is_relative_to(run), "SOURCE_SCOPE_INVALID")
    ratio_dest = Path(option(ratio, "--output"))
    require(ratio_dest == run / "runtime" / "ratio-bindings" / "T2.binding.json",
            "RATIO_SCOPE_INVALID")
    profile = read_obj(run / "runtime" / "runtime-profile.json")
    require(profile.get("schema") == PROFILE_SCHEMA and
            profile.get("run_directory") == str(run) and
            profile.get("experiment_id") == run.parent.name and
            profile.get("run_id") == run.name and
            profile.get("max_age_ms") == 800 and
            profile.get("traffic_duration_s") == 180,
            "RUNTIME_PROFILE_IDENTITY_INVALID")
    fifo = Path(option(trigger, "--fifo-path"))
    require(fifo.is_absolute() and str(fifo) == profile.get("actuator_fifo_path") and
            option(trigger, "--trigger-token") == profile.get("trigger_token") and
            isinstance(profile["tool_paths"], dict), "PRODUCTION_FIFO_BINDING_INVALID")
    parser = Path(profile["tool_paths"]["parser"])
    # Production parser must be a real script inside this checked-out harness.
    base = Path(__file__).resolve().parent
    require(parser.is_absolute() and parser.is_file() and not parser.is_symlink() and
            parser.resolve().parent == base and
            callable(load_tail().inspect), "PRODUCTION_PARSER_INVALID")
    return {"plan": plan, "run": run, "raw": raw, "stamps": stamps,
            "parser": parser, "fifo": fifo, "trigger_token": profile["trigger_token"],
            "ratio_dest": ratio_dest, "executor": exe}


def durable_exclusive(path, record):
    require(path.parent.is_dir() and not path.parent.is_symlink(), "EVIDENCE_PARENT_INVALID")
    payload = (json.dumps(record, sort_keys=True, indent=2) + "\n").encode("utf-8")
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    parent_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)


def claim_once(info, operation_id):
    run = info["run"]
    control = run / "control"
    require(control.is_dir() and not control.is_symlink(), "CONTROL_PARENT_INVALID")
    names = ("T2.trigger-intent.json", "T2.critical-outcome.json", "T2.executor.json",
             "T2.postval.outcome.json", "T2.postval.executor.json")
    require(not any(os.path.lexists(control / name) for name in names),
            "RUN_ALREADY_CONSUMED_NO_REPLAY")
    claims = run.parent.parent / ".t2-operation-claims"
    require(not claims.is_symlink(), "CLAIM_ROOT_SYMLINK_FORBIDDEN")
    claims.mkdir(mode=0o700, exist_ok=True)
    require(claims.is_dir(), "CLAIM_ROOT_INVALID")
    # Same canonical intent used by legacy critical section: prevents cross-mode replay.
    durable_exclusive(control / "T2.trigger-intent.json", {
        "schema": "sci_oran_prompt12_t2_irrevocable_intent_v1",
        "operation_id": operation_id, "protocol": "T2_POSTVAL_V1",
        "scientific_trigger_replay_decision": "NEVER_AUTOMATICALLY_REPLAY",
        "state": "CONSUMED_BEFORE_POSTVAL_NO_AUTOMATIC_REPLAY",
    })
    try:
        durable_exclusive(claims / (operation_id + ".json"), {
            "schema": "sci_oran_prompt12_t2_operation_claim_v1",
            "operation_id": operation_id, "run_root": str(run),
            "scientific_trigger_replay_decision": "NEVER_AUTOMATICALLY_REPLAY",
        })
    except FileExistsError as exc:
        raise PostvalError("GLOBAL_OPERATION_ID_CONSUMED") from exc


def verify_ratio(info):
    bind = read_obj(info["ratio_dest"])
    require(bind.get("schema") == "sci_oran_prompt12_v2_pretrigger_ratio_binding_v1" and
            bind.get("experiment_id") == info["run"].parent.name and
            bind.get("run_id") == info["run"].name and
            bind.get("transition_label") == "T2" and
            bind.get("transition_index") == 2 and
            bind.get("requested_ratio_pct") == 75,
            "RATIO_BINDING_NOT_PROVEN")


def source_at_90(info, tail):
    deadline = time.monotonic() + MAX_WAIT_SECONDS
    while time.monotonic() < deadline:
        try:
            sample = tail.inspect(str(info["raw"]), str(info["stamps"]), str(info["parser"]))
        except tail.GateError as exc:
            # Polling is READ-ONLY. Never retry an actuator write or operation ID.
            if str(exc) not in ("TIMESTAMP_UNFINISHED_LAST_LINE", "TIMESTAMP_TAIL_TOO_SHORT",
                                "RAW_OFFSET_INVALID", "COMPLETE_PAIR_UNAVAILABLE",
                                "PREPHASE_UNDER_26_SECONDS", "SAMPLE_AGE_OUT_OF_BOUNDS"):
                raise PostvalError("SOURCE_INVALID:" + str(exc)) from exc
            time.sleep(POLL_SECONDS)
            continue
        end_s = Decimal(str(sample["latest_interval_end_s"]))
        if end_s > LATEST_ACCEPTABLE_END_S:
            raise PostvalError("CONTROL_WINDOW_MISSED")
        if end_s >= TARGET_INTERVAL_END_S:
            return sample
        time.sleep(POLL_SECONDS)
    raise PostvalError("T2_90S_SAMPLE_NOT_AVAILABLE_IN_BOUNDED_WAIT")


def fifo_once(info, sample):
    fifo = info["fifo"]
    require(not fifo.is_symlink() and fifo.is_absolute() and
            stat.S_ISFIFO(fifo.stat().st_mode), "PRODUCTION_FIFO_NOT_FIFO")
    token = info["trigger_token"]
    require(isinstance(token, str) and token and "\n" not in token and "\x00" not in token,
            "TRIGGER_TOKEN_INVALID")
    payload = (token + "\n").encode("utf-8")
    fd = os.open(fifo, os.O_WRONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0))
    attempted = False
    try:
        require(stat.S_ISFIFO(os.fstat(fd).st_mode), "FIFO_IDENTITY_CHANGED")
        # Last scientific freshness check is NEXT TO the irrevocable FIFO write.
        gate_ns = time.time_ns()
        age = gate_ns - sample["latest_sample_timestamp_utc_ns"]
        require(0 <= age <= MAX_AGE_NS, "FRESHNESS_OVER_800_MS_AT_WRITE")
        attempted = True
        n = os.write(fd, payload)
        require(n == len(payload), "FIFO_PARTIAL_WRITE_UNKNOWN_NO_REPLAY")
        completed_ns = time.time_ns()
        return {"TRIGGER_WRITE_ATTEMPT_COUNT": 1, "TRIGGER_WRITE_SUCCESS_COUNT": 1,
                "FIFO_WRITE_COMPLETED_UTC_NS": completed_ns,
                "EXECUTOR_START_SAMPLE_AGE_GATE": "PASS",
                "AGE_AT_FIFO_WRITE_NS": age,
                "FRESH_AT_WRITE_COMPLETION": 0 <= completed_ns - sample["latest_sample_timestamp_utc_ns"] <= MAX_AGE_NS}
    except Exception as exc:
        if attempted:
            raise PostvalError("FIFO_ATTEMPTED_OUTCOME_UNKNOWN_NO_REPLAY") from exc
        raise
    finally:
        os.close(fd)


def live(info, operation_id):
    verify_ratio(info)
    # No claims are removed, including when measurement, FIFO, or post-write evidence fails.
    claim_once(info, operation_id)
    status = {"schema": SCHEMA, "protocol": "T2_POSTVAL_V1",
              "operation_id": operation_id,
              "GATE": "FAIL_CLOSED", "scientific_trigger_replay_decision": "NEVER_AUTOMATICALLY_REPLAY",
              "TRIGGER_WRITE_ATTEMPT_COUNT": 0, "TRIGGER_WRITE_SUCCESS_COUNT": 0,
              "CONTROL_EXECUTED": "NO"}
    try:
        sample = source_at_90(info, load_tail())
        status["sample"] = sample
        start = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        status["readback_window_start_utc"] = start
        # Intent and global claim exist before calling the ONLY FIFO writer.
        status["trigger_dispatch_attempted"] = True
        result = fifo_once(info, sample)
        status.update(result)
        status["CONTROL_EXECUTED"] = "YES" if result["FRESH_AT_WRITE_COMPLETION"] else "UNKNOWN_NO_REPLAY"
        require(result["FRESH_AT_WRITE_COMPLETION"], "WRITE_COMPLETION_EXPIRED_NO_REPLAY")
        status["GATE"] = "PASS_PENDING_READBACK_AND_POSTVAL"
        return status
    except Exception as exc:
        status["failure_reason"] = str(exc)
        status["GATE"] = "FAIL_CLOSED_UNKNOWN_NO_REPLAY"
        if "FIFO_ATTEMPTED_OUTCOME_UNKNOWN_NO_REPLAY" in str(exc):
            status["CONTROL_EXECUTED"] = "UNKNOWN_AFTER_WRITE_ATTEMPT_NO_REPLAY"
            status["TRIGGER_WRITE_ATTEMPT_COUNT"] = "UNKNOWN_NO_REPLAY"
            status["TRIGGER_WRITE_SUCCESS_COUNT"] = "UNKNOWN_NO_REPLAY"
        raise
    finally:
        durable_exclusive(info["run"] / "control" / "T2.postval.outcome.json", status)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    p.add_argument("--materialization", required=True)
    p.add_argument("--mode", choices=("inspect", "live"), required=True)
    p.add_argument("--live-authorization-token")
    p.add_argument("--control-authorization-token")
    p.add_argument("--operation-id")
    args = p.parse_args(argv)
    try:
        path = Path(args.materialization)
        info = load_binding(path)
        if args.mode == "inspect":
            require(not args.live_authorization_token and not args.control_authorization_token and
                    args.operation_id is None, "INSPECT_REJECTS_CONTROL_ARGUMENTS")
            print("T2_POSTVAL_INSPECTION=PASS")
            print("CONTROL_EXECUTED=NO")
            return 0
        require(args.live_authorization_token == LIVE_TOKEN and
                args.control_authorization_token == CONTROL_TOKEN and
                os.environ.get(INTERLOCK) == "YES" and
                os.environ.get(POSTVAL_INTERLOCK) == "YES",
                "POSTVAL_LIVE_NOT_AUTHORIZED")
        operation_id = args.operation_id or ("prompt12-t2-postval-" + uuid.uuid4().hex)
        require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{7,127}", operation_id) is not None,
                "OPERATION_ID_INVALID")
        status = live(info, operation_id)
        print(json.dumps(status, sort_keys=True))
        return 0
    except (PostvalError, FileExistsError, OSError, ValueError, KeyError) as exc:
        print("T2_POSTVAL_ONE_SHOT=FAIL_CLOSED", file=sys.stderr)
        print("REASON=" + type(exc).__name__ + ":" + str(exc), file=sys.stderr)
        return 70


if __name__ == "__main__":
    raise SystemExit(main())
