#!/usr/bin/env python3
import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

SCHEMA = "sci_oran_prompt12_bounded_sequence_v1"
PRE_MIN_S = 11
POST_MIN_S = 10
EXTENSION_S = 5
MAX_EXTENSIONS = 2
PRE_MAX_S = 21
POST_MAX_S = 20
OBSERVATION_MAX_S = 141
EXPERIMENT_MAX_S = 180
TRANSITION_COUNT = 6
LIVE_TOKEN = "AUTHORISE_PROMPT12_BOUNDED_SEQUENCE_LIVE"


class SupervisorError(Exception):
    def __init__(self, reason, rc=70):
        super().__init__(reason)
        self.reason = reason
        self.rc = rc


def command(value, name):
    if not isinstance(value, list) or not value:
        raise SupervisorError(f"INVALID_COMMAND:{name}", 64)
    if not all(isinstance(item, str) and item for item in value):
        raise SupervisorError(f"INVALID_COMMAND:{name}", 64)
    return value


def load_plan(path):
    try:
        plan = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SupervisorError(f"PLAN_READ_FAILED:{type(exc).__name__}", 64)
    if plan.get("schema") != SCHEMA:
        raise SupervisorError("PLAN_SCHEMA_INVALID", 64)
    command(plan.get("traffic_command"), "traffic_command")
    command(plan.get("initial_stationarity_command"), "initial_stationarity_command")
    command(plan.get("finalization_command"), "finalization_command")
    transitions = plan.get("transitions")
    if not isinstance(transitions, list) or len(transitions) != TRANSITION_COUNT:
        raise SupervisorError("TRANSITION_COUNT_INVALID", 64)
    labels = []
    for index, transition in enumerate(transitions, start=1):
        if not isinstance(transition, dict):
            raise SupervisorError(f"TRANSITION_INVALID:{index}", 64)
        label = transition.get("label")
        if label != f"T{index}":
            raise SupervisorError(f"TRANSITION_ORDER_INVALID:{index}", 64)
        labels.append(label)
        command(transition.get("trigger_command"), f"{label}.trigger_command")
        command(
            transition.get("post_stationarity_command"),
            f"{label}.post_stationarity_command",
        )
    if labels != [f"T{index}" for index in range(1, 7)]:
        raise SupervisorError("TRANSITION_LABELS_INVALID", 64)
    return plan


def base_report(mode):
    return {
        "schema": SCHEMA,
        "mode": mode,
        "PRE_STEP_MAXIMUM_DURATION_S": PRE_MAX_S,
        "POST_STEP_MAXIMUM_DURATION_S": POST_MAX_S,
        "MAX_STATIONARITY_EXTENSIONS": MAX_EXTENSIONS,
        "OBSERVATION_BUDGET_MAXIMUM_S": OBSERVATION_MAX_S,
        "EXPERIMENT_MAXIMUM_DURATION_S": EXPERIMENT_MAX_S,
        "CONTROL_EXECUTED": "NO",
        "TRIGGER_WRITE_ATTEMPT_COUNT": 0,
        "TRIGGER_WRITE_SUCCESS_COUNT": 0,
        "SCIENTIFIC_TRIGGER_REPLAY_DECISION": "NOT_APPLICABLE_NO_WRITE_ATTEMPT",
        "SUPERVISOR_GATE": "FAIL_CLOSED",
        "FAIL_CLOSED_REASON": "NOT_STARTED",
    }


def write_report(path, report):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp")
    temporary.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(target)


class DurationBudget:
    def __init__(self, started, clock=time.monotonic):
        self.started = started
        self.clock = clock

    def remaining(self):
        return EXPERIMENT_MAX_S - (self.clock() - self.started)

    def require_remaining(self, reason):
        remaining = self.remaining()
        if remaining <= 0:
            raise SupervisorError(reason, 124)
        return remaining

    @staticmethod
    def phase_limit(role):
        if role == "pre":
            return PRE_MAX_S
        if role == "post":
            return POST_MAX_S
        raise SupervisorError(f"PHASE_ROLE_INVALID:{role}", 64)

    @staticmethod
    def validate_extension_count(count):
        if count < 0 or count > MAX_EXTENSIONS:
            raise SupervisorError("MAX_STATIONARITY_EXTENSIONS_EXCEEDED", 125)


def wait_for_observation(target_elapsed_s, budget, phase_started, role):
    phase_limit = DurationBudget.phase_limit(role)
    if target_elapsed_s > phase_limit:
        reason = "PRE_STEP_TIMEOUT" if role == "pre" else "POST_STEP_TIMEOUT"
        raise SupervisorError(reason, 124)
    elapsed = time.monotonic() - phase_started
    seconds = max(0.0, target_elapsed_s - elapsed)
    global_remaining = budget.require_remaining("EXPERIMENT_TIMEOUT")
    if seconds > global_remaining:
        raise SupervisorError("EXPERIMENT_TIMEOUT", 124)
    time.sleep(seconds)


def run_command(
    argv,
    budget,
    reason,
    accepted=(0,),
    maximum_seconds=None,
    timeout_reason=None,
):
    remaining = budget.require_remaining("EXPERIMENT_TIMEOUT")
    if maximum_seconds is not None:
        if maximum_seconds <= 0:
            raise SupervisorError(reason, 124)
        remaining = min(remaining, maximum_seconds)
    try:
        proc = subprocess.run(
            argv,
            text=True,
            capture_output=True,
            check=False,
            timeout=remaining,
        )
    except subprocess.TimeoutExpired:
        raise SupervisorError(timeout_reason or reason, 124)
    if proc.returncode not in accepted:
        raise SupervisorError(f"{reason}:RC_{proc.returncode}", proc.returncode or 70)
    return proc


def stationarity_gate(argv, budget, phase_started, role):
    minimum = PRE_MIN_S if role == "pre" else POST_MIN_S
    extensions = 0
    while True:
        observation_target = minimum + extensions * EXTENSION_S
        wait_for_observation(
            observation_target,
            budget,
            phase_started,
            role,
        )
        proc = run_command(
            argv,
            budget,
            "STATIONARITY_EVALUATOR_FAILED",
        )
        try:
            record = json.loads(proc.stdout)
        except json.JSONDecodeError:
            raise SupervisorError("STATIONARITY_OUTPUT_INVALID", 65)
        gate = record.get("output_stationarity_gate")
        if gate == "PASS":
            return extensions
        if gate != "FAIL":
            raise SupervisorError("STATIONARITY_GATE_INVALID", 65)
        if extensions >= MAX_EXTENSIONS:
            raise SupervisorError("MAX_STATIONARITY_EXTENSIONS_EXCEEDED", 125)
        extensions += 1
        DurationBudget.validate_extension_count(extensions)


def terminate_process(process):
    if process is None or process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=5)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def run_live(plan, report, authorization_token):
    if os.environ.get("SCI_ORAN_PROMPT12_LIVE_CONTROL_ENABLE") != "YES":
        raise SupervisorError("LIVE_CONTROL_NOT_ENABLED", 77)
    if authorization_token != LIVE_TOKEN:
        raise SupervisorError("LIVE_CONTROL_AUTHORIZATION_TOKEN_INVALID", 77)
    started = time.monotonic()
    budget = DurationBudget(started)
    traffic = None
    try:
        traffic = subprocess.Popen(
            plan["traffic_command"],
            stdin=subprocess.DEVNULL,
            stdout=None,
            stderr=None,
            start_new_session=True,
        )
        pre_started = time.monotonic()
        pre_extensions = stationarity_gate(
            plan["initial_stationarity_command"], budget, pre_started, "pre"
        )
        report["PRE_STEP_EXTENSION_COUNT"] = pre_extensions
        post_counts = []
        for transition in plan["transitions"]:
            if traffic.poll() is not None:
                raise SupervisorError("TRAFFIC_TERMINATED_BEFORE_TRIGGER", 76)
            report["TRIGGER_WRITE_ATTEMPT_COUNT"] += 1
            report["SCIENTIFIC_TRIGGER_REPLAY_DECISION"] = "NEVER_AUTOMATICALLY_REPLAY"
            trigger = run_command(
                transition["trigger_command"],
                budget,
                f"{transition['label']}_TRIGGER_FAILED",
            )
            report["TRIGGER_WRITE_SUCCESS_COUNT"] += 1
            report["CONTROL_EXECUTED"] = "YES"
            report[f"{transition['label']}_TRIGGER_STDOUT"] = trigger.stdout.strip()
            post_started = time.monotonic()
            count = stationarity_gate(
                transition["post_stationarity_command"],
                budget,
                post_started,
                "post",
            )
            post_counts.append(count)
        report["POST_STEP_EXTENSION_COUNTS"] = post_counts
        if traffic.poll() is not None:
            raise SupervisorError("TRAFFIC_TERMINATED_BEFORE_FINALIZATION", 76)
        run_command(
            plan["finalization_command"],
            budget,
            "FINALIZATION_FAILED",
        )
        report["SUPERVISOR_GATE"] = "PASS"
        report["FAIL_CLOSED_REASON"] = "NONE"
        return 0
    finally:
        terminate_process(traffic)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True)
    parser.add_argument("--mode", required=True, choices=("no-control", "live"))
    parser.add_argument("--output", required=True)
    parser.add_argument("--control-authorization-token")
    return parser.parse_args()


def main():
    args = parse_args()
    report = base_report(args.mode)
    try:
        plan = load_plan(args.plan)
        if args.mode == "no-control":
            report["SUPERVISOR_GATE"] = "PASS"
            report["FAIL_CLOSED_REASON"] = "NONE"
            report["NO_CONTROL_DRY_RUN_GATE"] = "PASS"
            rc = 0
        else:
            rc = run_live(plan, report, args.control_authorization_token)
    except SupervisorError as exc:
        report["SUPERVISOR_GATE"] = "FAIL_CLOSED"
        report["FAIL_CLOSED_REASON"] = exc.reason
        rc = exc.rc
    write_report(args.output, report)
    print(f"SUPERVISOR_GATE={report['SUPERVISOR_GATE']}")
    print(f"FAIL_CLOSED_REASON={report['FAIL_CLOSED_REASON']}")
    print(f"CONTROL_EXECUTED={report['CONTROL_EXECUTED']}")
    print(f"TRIGGER_WRITE_ATTEMPT_COUNT={report['TRIGGER_WRITE_ATTEMPT_COUNT']}")
    print(f"TRIGGER_WRITE_SUCCESS_COUNT={report['TRIGGER_WRITE_SUCCESS_COUNT']}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
