#!/usr/bin/env python3
"""Independent, read-only adjudication of one completed Prompt12 T2 bundle.

This file never sends traffic, touches Docker, starts a provider or writes FIFO.
It requires exact state readback AND observable canonical data, not mere
Ansible return code. An exclusive adjudication record is the only output.
"""
import argparse
import json
import os
from pathlib import Path
import sys
from jsonschema import Draft202012Validator

SCHEMA = "sci_oran_prompt12_t2_scientific_adjudication_v1"


class EvidenceError(Exception):
    pass


def require(ok, reason):
    if not ok:
        raise EvidenceError(reason)


def read_json(path, label):
    require(path.is_file() and not path.is_symlink(), label + "_MISSING")
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise EvidenceError(label + "_INVALID") from exc
    require(isinstance(obj, dict), label + "_NOT_OBJECT")
    return obj


def option(argv, flag):
    require(isinstance(argv, list) and argv.count(flag) == 1, "ARGUMENT_CARDINALITY:" + flag)
    i = argv.index(flag)
    require(i + 1 < len(argv), "ARGUMENT_MISSING:" + flag)
    return argv[i + 1]


def jsonl(path, label):
    require(path.is_file() and not path.is_symlink(), label + "_MISSING")
    try:
        values = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
                  if line.strip()]
    except (OSError, ValueError) as exc:
        raise EvidenceError(label + "_INVALID") from exc
    require(values and all(isinstance(x, dict) for x in values), label + "_EMPTY_OR_INVALID")
    return values


def adjudicate(materialization, initial26_id):
    plan = read_json(materialization, "T2_MATERIALIZATION")
    require(plan.get("schema") == "sci_oran_prompt12_resume_single_transition_materialization_v1"
            and plan.get("transition_label") == "T2"
            and plan.get("transition_index") == 2
            and plan.get("expected_timeline_event_count") == 3,
            "T2_MATERIALIZATION_IDENTITY_INVALID")
    executor = Path(option(plan["trigger_command"], "--output"))
    run = executor.parent.parent
    require(run.is_absolute() and materialization.parent == run / "runtime",
            "T2_RUN_SCOPE_INVALID")
    require(executor == run / "control" / "T2.executor.json", "EXECUTOR_PATH_INVALID")
    initial = run / "initial26" / initial26_id / "result.env"
    require(initial.is_file() and not initial.is_symlink(), "INITIAL26_EVIDENCE_MISSING")
    lines = set(initial.read_text(encoding="utf-8").splitlines())
    for expected in (
        "POSTCONTROL_APPLIED_PRB_STATE=0:26",
        "U_CMD_GATE=PASS", "U_ACK_GATE=PASS", "U_APPLIED_READBACK_GATE=PASS",
        "SCIENTIFIC_TRAFFIC_EXECUTED=NO", "FIFO_TRIGGER_EXECUTED=NO",
    ):
        require(expected in lines, "INITIAL26_GATE_INVALID:" + expected)
    precontrol = read_json(run / "precontrol" / "T2.json", "T2_PRECONTROL")
    for key in ("output_stationarity_gate", "freshness_gate", "precontrol_admission_gate"):
        require(precontrol.get(key) == "PASS", "PRECONTROL_" + key.upper() + "_INVALID")
    intent = read_json(executor.with_name("T2.trigger-intent.json"), "TRIGGER_INTENT")
    critical = read_json(executor.with_name("T2.critical-outcome.json"), "CRITICAL_OUTCOME")
    exe = read_json(executor, "EXECUTOR_OUTCOME")
    require(intent.get("scientific_trigger_replay_decision") == "NEVER_AUTOMATICALLY_REPLAY",
            "TRIGGER_INTENT_NO_REPLAY_INVALID")
    require(critical.get("state") == "TRIGGER_CONFIRMED_AWAITING_READBACK"
            and critical.get("trigger_dispatch_attempted") is True
            and critical.get("trigger_execution_confirmed") is True
            and critical.get("operation_id") == intent.get("operation_id"),
            "CRITICAL_TRIGGER_CONFIRMATION_INVALID")
    for key, expected in {
        "EXECUTOR_GATE": "PASS",
        "CONTROL_EXECUTED": "YES",
        "SCIENTIFIC_TRIGGER_CONSUMED": "YES",
        "TRIGGER_WRITE_ATTEMPT_COUNT": 1,
        "TRIGGER_WRITE_SUCCESS_COUNT": 1,
        "EXECUTOR_START_SAMPLE_AGE_GATE": "PASS",
    }.items():
        require(exe.get(key) == expected, "TRIGGER_EXECUTOR_" + key + "_INVALID")
    readback = read_json(Path(str(materialization) + ".applied-readback.json"),
                         "AUTHORITATIVE_READBACK")
    require(readback.get("schema") == "sci_oran_prompt12_authoritative_prb_readback_v1"
            and readback.get("authoritative_source") == "CONTAINER:/tmp/gnb.log"
            and readback.get("docker_logs_is_authoritative") is False
            and readback.get("u_applied_readback_gate") == "PASS"
            and readback.get("expected_min_prbs") == 0
            and readback.get("expected_max_prbs") == 39
            and isinstance(readback.get("selected"), dict)
            and readback["selected"].get("applied_min_prbs") == 0
            and readback["selected"].get("applied_max_prbs") == 39,
            "AUTHORITATIVE_39_PRBS_NOT_PROVEN")
    post = read_json(Path(str(materialization) + ".post-stationarity.json"),
                     "T2_POST_STATIONARITY")
    require(post.get("output_stationarity_gate") == "PASS" and
            post.get("minimum_phase_duration_gate") == "PASS",
            "POST_STATIONARITY_NOT_PASS")
    raw = Path(plan["traffic_command"][4])
    stamps = Path(plan["traffic_command"][5])
    require(raw.is_file() and raw.stat().st_size > 0
            and stamps.is_file() and stamps.stat().st_size > 0,
            "TRAFFIC_RAW_EVIDENCE_MISSING")
    final = plan["finalization_command"]
    canonical = Path(option(final, "--canonical-output"))
    timeline = Path(option(final, "--timeline-output"))
    require(canonical == run / "processed" / "iperf3-receiver.intervals.canonical.jsonl",
            "CANONICAL_PATH_NOT_RUN_SCOPED")
    require(timeline == run / "processed" / "actuator-timeline.jsonl",
            "TIMELINE_PATH_NOT_RUN_SCOPED")
    intervals = jsonl(canonical, "CANONICAL_RECEIVER")
    timeline_rows = jsonl(timeline, "ACTUATOR_TIMELINE")
    require(len(timeline_rows) == 3, "ACTUATOR_TIMELINE_EVENT_COUNT_NOT_THREE")
    # Validate the actual scientific data against the canonical schema,
    # not just the finalizer return code or the existence of JSONL files.
    repo = Path(__file__).resolve().parents[2]
    schema_file = repo / "datasets" / "schemas" / "sci-oran-prompt12-siso-v1.0.0.schema.json"
    schema = read_json(schema_file, "SCIENTIFIC_SCHEMA")
    for kind, rows in (("iperfInterval", intervals), ("actuatorEvent", timeline_rows)):
        validator = Draft202012Validator({
            "$schema": schema["$schema"],
            "$defs": schema["$defs"],
            "$ref": "#/$defs/" + kind,
        })
        for i, item in enumerate(rows):
            err = next(validator.iter_errors(item), None)
            require(err is None, "SCHEMA_INVALID:" + kind + ":" + str(i))
    exp = intervals[0]["experiment_id"]
    run_id = intervals[0]["run_id"]
    require(all(r["experiment_id"] == exp and r["run_id"] == run_id for r in intervals + timeline_rows),
            "SCIENTIFIC_EVIDENCE_RUN_ID_MISMATCH")
    require(len(intervals) >= 750, "CANONICAL_INTERVAL_COUNT_INSUFFICIENT")
    starts = [row["interval_start_s"] for row in intervals]
    ends = [row["interval_end_s"] for row in intervals]
    require(min(starts) <= 1.5 and max(ends) >= 175.0 and max(ends) <= 181.0,
            "SCIENTIFIC_TRAFFIC_180S_COVERAGE_INSUFFICIENT")
    require(all(ends[i] > starts[i] and starts[i] >= ends[i - 1] - 0.000002
                for i in range(1, len(intervals))), "CANONICAL_INTERVAL_TIME_NONMONOTONIC")
    require(all(starts[i] - ends[i - 1] <= 0.201 for i in range(1, len(intervals))),
            "CANONICAL_INTERVAL_TIME_GAP_TOO_LARGE")
    require(all(0 < x["interval_duration_s"] <= 0.200001 for x in intervals),
            "SCIENTIFIC_SAMPLING_PERIOD_NOT_0P2")
    require(all(intervals[i]["timestamp_utc_ns"] >= intervals[i-1]["timestamp_utc_ns"]
                for i in range(1, len(intervals))), "CANONICAL_TIMESTAMP_NONMONOTONIC")
    events = [row["event_type"] for row in timeline_rows]
    require(events == ["command", "acknowledgement", "applied_readback"],
            "SCIENTIFIC_TIMELINE_EVENT_ORDER_INVALID")
    require(timeline_rows[0].get("requested_max_prb_ratio_pct") == 75
            and timeline_rows[1].get("acknowledgement_status") == "PASS"
            and timeline_rows[2].get("applied_min_prbs") == 0
            and timeline_rows[2].get("applied_max_prbs") == 39,
            "SCIENTIFIC_TIMELINE_NOT_26_TO_39")
    require(timeline_rows[0]["timestamp_utc_ns"] <= timeline_rows[1]["timestamp_utc_ns"]
            <= timeline_rows[2]["timestamp_utc_ns"],
            "SCIENTIFIC_TIMELINE_TIME_ORDER_INVALID")
    report = {
        "schema": SCHEMA,
        "scientific_t2_gate": "PASS",
        "experiment_run_directory": str(run),
        "initial_applied_prbs": 26,
        "applied_prbs": 39,
        "trigger_write_attempt_count": 1,
        "trigger_write_success_count": 1,
        "canonical_interval_count": len(intervals),
        "actuator_timeline_event_count": 3,
        "raw_evidence_preserved": True,
        "pre_stationarity_gate": "PASS",
        "post_stationarity_gate": "PASS",
        "applied_readback_gate": "PASS",
        "automatic_trigger_replay": False,
    }
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    p.add_argument("--materialization", required=True)
    p.add_argument("--initial26-operation-id", required=True)
    args = p.parse_args(argv)
    try:
        require(args.initial26_operation_id and "/" not in args.initial26_operation_id
                and ".." not in args.initial26_operation_id, "INITIAL26_ID_INVALID")
        materialization = Path(args.materialization)
        result = adjudicate(materialization, args.initial26_operation_id)
        # Preserve exact adjudication as evidence; no overwrite or retry.
        out = materialization.with_name("t2-scientific-adjudication.json")
        fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(result, stream, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        print(json.dumps(result, sort_keys=True))
        return 0
    except (EvidenceError, OSError, ValueError) as exc:
        print("SCIENTIFIC_T2_ADJUDICATION_GATE=BLOCKED", file=sys.stderr)
        print("FAIL_REASON=" + str(exc), file=sys.stderr)
        return 65


if __name__ == "__main__":
    raise SystemExit(main())
