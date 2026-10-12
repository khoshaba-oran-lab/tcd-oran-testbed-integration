#!/usr/bin/env python3
"""Independent read-only T2-POSTVAL-v1 evidence adjudication.

Frozen windows: pre 80-90 s, post 120-130 s of the 180 s UDP capture.
This is a new scientific protocol, not a forged legacy PRECONTROL PASS.
"""
import argparse
from decimal import Decimal
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from jsonschema import Draft202012Validator

SCHEMA = "sci_oran_t2_postval_scientific_adjudication_v1"
PLAN_SCHEMA = "sci_oran_prompt12_resume_single_transition_materialization_v1"


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


def jsonl(path, label):
    require(path.is_file() and not path.is_symlink(), label + "_MISSING")
    try:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (OSError, ValueError) as exc:
        raise EvidenceError(label + "_INVALID") from exc
    require(rows and all(isinstance(x, dict) for x in rows), label + "_EMPTY")
    return rows


def opt(argv, name):
    require(isinstance(argv, list) and argv.count(name) == 1, "ARGUMENT_INVALID:" + name)
    i = argv.index(name)
    require(i + 1 < len(argv), "ARGUMENT_VALUE_MISSING:" + name)
    return argv[i + 1]


def evaluator():
    path = Path(__file__).resolve().with_name("evaluate-output-stationarity.py")
    spec = importlib.util.spec_from_file_location("postval_official_output_stationarity", path)
    require(spec is not None and spec.loader is not None, "OFFICIAL_EVALUATOR_MISSING")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def frozen_stationarity(rows, first, last, official):
    lo, hi = Decimal(first), Decimal(last)
    subset = [r for r in rows if r["interval_class"] == "complete" and
              Decimal(str(r["interval_start_s"])) >= lo and
              Decimal(str(r["interval_end_s"])) <= hi]
    require(len(subset) == 50, "FROZEN_WINDOW_COUNT_INVALID:" + first)
    require(official.decimal_value(subset[0]["interval_start_s"]) == lo and
            official.decimal_value(subset[-1]["interval_end_s"]) == hi,
            "FROZEN_WINDOW_BOUNDS_INVALID:" + first)
    require(all(official.contiguous(a,b) for a,b in zip(subset,subset[1:])),
            "FROZEN_WINDOW_CONTIGUITY_INVALID:" + first)
    w1, w2 = official.window_metrics(subset[:25]), official.window_metrics(subset[25:])
    cv1, cv2 = w1["cv_pct"], w2["cv_pct"]
    mean_shift = Decimal("100") * abs(w2["mean_kbit_s"] - w1["mean_kbit_s"]) / w1["mean_kbit_s"]
    require(cv1 <= official.CV_MAX_PCT and cv2 <= official.CV_MAX_PCT and
            mean_shift <= official.MEAN_SHIFT_MAX_PCT,
            "FROZEN_WINDOW_STATIONARITY_FAILED:" + first)
    return {"span_s": first + "-" + last, "cv_w1_pct": str(cv1),
            "cv_w2_pct": str(cv2), "mean_shift_pct": str(mean_shift),
            "record_first": subset[0]["record_id"], "record_last": subset[-1]["record_id"]}


def verify_trigger_raw(origin, raw_path, stamps_path):
    """Independently verify the trigger selected a genuine historical receiver line."""
    seq = origin.get("last_sequence")
    expected_sha = origin.get("raw_line_sha256")
    latest_ns = origin.get("latest_sample_timestamp_utc_ns")
    require(type(seq) is int and type(latest_ns) is int and isinstance(expected_sha,str),
            "TRIGGER_SAMPLE_IDENTITY_INVALID")
    stamps = jsonl(stamps_path, "RAW_RECEIVER_TIMESTAMPS")
    matches = [r for r in stamps if r.get("sequence") == seq]
    require(len(matches) == 1, "TRIGGER_SAMPLE_SEQUENCE_INVALID")
    row = matches[0]
    require(row.get("rx_wall_ns") == latest_ns and row.get("raw_line_sha256") == expected_sha,
            "TRIGGER_SAMPLE_PROVENANCE_INVALID")
    try:
        raw = raw_path.read_bytes()
        portion = raw[row["raw_offset_start"]:row["raw_offset_end"]]
    except (OSError, TypeError, ValueError, KeyError) as exc:
        raise EvidenceError("TRIGGER_SAMPLE_RAW_UNREADABLE") from exc
    require(len(portion) == row["raw_line_length_bytes"] and
            hashlib.sha256(portion).hexdigest() == expected_sha,
            "TRIGGER_SAMPLE_RAW_HASH_INVALID")
    return row


def adjudicate(materialization, initial26_id):
    plan = read_json(materialization, "MATERIALIZATION")
    require(plan.get("schema") == PLAN_SCHEMA and plan.get("transition_label") == "T2" and
            plan.get("transition_index") == 2 and plan.get("expected_timeline_event_count") == 3,
            "T2_MATERIALIZATION_INVALID")
    run = materialization.parent.parent
    require(materialization.parent == run / "runtime" and run.is_absolute(),
            "RUN_SCOPE_INVALID")
    initial = run / "initial26" / initial26_id / "result.env"
    require(initial.is_file() and not initial.is_symlink(), "INITIAL26_EVIDENCE_MISSING")
    lines = set(initial.read_text(encoding="utf-8").splitlines())
    for item in ("POSTCONTROL_APPLIED_PRB_STATE=0:26", "U_CMD_GATE=PASS", "U_ACK_GATE=PASS",
                 "U_APPLIED_READBACK_GATE=PASS", "SCIENTIFIC_TRAFFIC_EXECUTED=NO",
                 "FIFO_TRIGGER_EXECUTED=NO"):
        require(item in lines, "INITIAL26_NOT_PROVEN:" + item)
    control = run / "control"
    intent = read_json(control / "T2.trigger-intent.json", "CANONICAL_INTENT")
    outcome = read_json(control / "T2.postval.outcome.json", "POSTVAL_TRIGGER_OUTCOME")
    require(intent.get("protocol") == "T2_POSTVAL_V1" and
            intent.get("scientific_trigger_replay_decision") == "NEVER_AUTOMATICALLY_REPLAY" and
            outcome.get("operation_id") == intent.get("operation_id") and
            outcome.get("protocol") == "T2_POSTVAL_V1" and
            outcome.get("GATE") == "PASS_PENDING_READBACK_AND_POSTVAL" and
            outcome.get("TRIGGER_WRITE_ATTEMPT_COUNT") == 1 and
            outcome.get("TRIGGER_WRITE_SUCCESS_COUNT") == 1 and
            outcome.get("CONTROL_EXECUTED") == "YES" and
            outcome.get("FRESH_AT_WRITE_COMPLETION") is True and
            outcome.get("scientific_trigger_replay_decision") == "NEVER_AUTOMATICALLY_REPLAY",
            "POSTVAL_ONE_SHOT_NOT_PROVEN")
    sample = outcome.get("sample")
    require(isinstance(sample, dict) and sample.get("GATE") == "PASS" and
            sample.get("selection") == "last_two_contiguous_complete_intervals" and
            sample.get("scientific_trigger_enabled") is False and
            Decimal(str(sample.get("latest_interval_end_s"))) >= Decimal("90.0") and
            Decimal(str(sample.get("latest_interval_end_s"))) <= Decimal("90.4"),
            "SAMPLE_SELECTION_INVALID")
    age = outcome.get("AGE_AT_FIFO_WRITE_NS")
    completed = outcome.get("FIFO_WRITE_COMPLETED_UTC_NS")
    require(type(age) is int and 0 <= age <= 800_000_000 and
            type(completed) is int and
            0 <= completed - sample["latest_sample_timestamp_utc_ns"] <= 800_000_000,
            "SCIENTIFIC_FRESHNESS_NOT_PROVEN")
    readback = read_json(Path(str(materialization) + ".applied-readback.json"), "READBACK")
    require(readback.get("schema") == "sci_oran_prompt12_authoritative_prb_readback_v1" and
            readback.get("authoritative_source") == "CONTAINER:/tmp/gnb.log" and
            readback.get("docker_logs_is_authoritative") is False and
            readback.get("u_applied_readback_gate") == "PASS" and
            readback.get("expected_min_prbs") == 0 and
            readback.get("expected_max_prbs") == 39 and
            isinstance(readback.get("selected"), dict) and
            readback["selected"].get("applied_min_prbs") == 0 and
            readback["selected"].get("applied_max_prbs") == 39,
            "AUTHORITATIVE_READBACK39_INVALID")
    raw, stamps = Path(plan["traffic_command"][4]), Path(plan["traffic_command"][5])
    require(raw.is_relative_to(run) and stamps.is_relative_to(run) and
            raw.is_file() and stamps.is_file(), "RAW_RECEIVER_SCOPE_INVALID")
    verify_trigger_raw(sample, raw, stamps)
    final = plan["finalization_command"]
    canonical = Path(opt(final, "--canonical-output"))
    timeline = Path(opt(final, "--timeline-output"))
    require(canonical == run / "processed" / "iperf3-receiver.intervals.canonical.jsonl" and
            timeline == run / "processed" / "actuator-timeline.jsonl", "FINALIZATION_SCOPE_INVALID")
    intervals = jsonl(canonical, "CANONICAL_RECEIVER")
    events = jsonl(timeline, "ACTUATOR_TIMELINE")
    require(len(events) == 3 and [e.get("event_type") for e in events] ==
            ["command", "acknowledgement", "applied_readback"],
            "ACTUATOR_TIMELINE_ORDER_INVALID")
    require(events[0].get("requested_max_prb_ratio_pct") == 75 and
            events[1].get("acknowledgement_status") == "PASS" and
            events[2].get("applied_min_prbs") == 0 and
            events[2].get("applied_max_prbs") == 39 and
            events[0]["timestamp_utc_ns"] <= events[1]["timestamp_utc_ns"] <= events[2]["timestamp_utc_ns"],
            "ACTUATOR_TRANSITION_INVALID")
    require(events[0]["timestamp_utc_ns"] >= sample["latest_sample_timestamp_utc_ns"] and
            events[0]["timestamp_utc_ns"] >= completed - 800_000_000 and
            events[2]["timestamp_utc_ns"] >= events[0]["timestamp_utc_ns"],
            "ACTUATOR_TIMESTAMP_BINDING_INVALID")
    repo = Path(__file__).resolve().parents[2]
    schema = read_json(repo / "datasets" / "schemas" / "sci-oran-prompt12-siso-v1.0.0.schema.json", "SCIENTIFIC_SCHEMA")
    for kind, rows in (("iperfInterval", intervals), ("actuatorEvent", events)):
        validator = Draft202012Validator({"$schema": schema["$schema"], "$defs": schema["$defs"],
                                         "$ref": "#/$defs/" + kind})
        for i, row in enumerate(rows):
            require(next(validator.iter_errors(row), None) is None,
                    "SCHEMA_INVALID:" + kind + ":" + str(i))
    require(all(r.get("experiment_id") == run.parent.name and r.get("run_id") == run.name
                for r in intervals + events), "EVIDENCE_IDENTITY_MISMATCH")
    require(len(intervals) >= 750 and intervals[-1]["interval_end_s"] >= 175.0 and
            intervals[-1]["interval_end_s"] <= 181.0,
            "UDP_180S_COVERAGE_INVALID")
    official = evaluator()
    # All windows are precommitted by protocol; NO adaptive selection for PASS.
    pre = frozen_stationarity(intervals, "80.0", "90.0", official)
    post = frozen_stationarity(intervals, "120.0", "130.0", official)
    require(events[2]["timestamp_utc_ns"] < next(r["rx_wall_ns"] for r in intervals
            if Decimal(str(r["interval_start_s"])) == Decimal("120.0")),
            "POST_WINDOW_BEFORE_APPLIED_READBACK")
    return {"schema": SCHEMA, "protocol": "T2_POSTVAL_V1", "t2_postval_validated": "PASS",
            "scientific_t2_gate": "NOT_APPLICABLE_LEGACY", "applied_prbs": 39,
            "trigger_write_attempt_count": 1, "trigger_write_success_count": 1,
            "pre_stationarity_gate": "PASS", "post_stationarity_gate": "PASS",
            "pre_window": pre, "post_window": post,
            "automatic_trigger_replay": False, "canonical_interval_count": len(intervals)}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    p.add_argument("--materialization", required=True)
    p.add_argument("--initial26-operation-id", required=True)
    args = p.parse_args(argv)
    try:
        require(args.initial26_operation_id and "/" not in args.initial26_operation_id and
                ".." not in args.initial26_operation_id, "INITIAL26_ID_INVALID")
        materialization = Path(args.materialization)
        report = adjudicate(materialization, args.initial26_operation_id)
        path = materialization.parent / "t2-postval-scientific-adjudication.json"
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(report, out, sort_keys=True, indent=2)
            out.write("\n")
            out.flush()
            os.fsync(out.fileno())
        print(json.dumps(report, sort_keys=True))
        return 0
    except (EvidenceError, OSError, ValueError, TypeError, KeyError, StopIteration) as exc:
        print("T2_POSTVAL_VALIDATED=FAIL", file=sys.stderr)
        print("FAIL_REASON=" + str(exc), file=sys.stderr)
        return 65


if __name__ == "__main__":
    raise SystemExit(main())
