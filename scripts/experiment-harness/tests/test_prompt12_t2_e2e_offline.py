#!/usr/bin/env python3
"""Scientific control-plane E2E simulation; NO live RAN/traffic/FIFO write.

Runs the actual provider argv, runtime profile, production bindings, resume
and T2 materializers. Smoke/Doctor/initial26/FIFO/39 PRB are explicitly
SYNTHETIC, never misrepresented as actual scientific evidence.
"""
import importlib.util
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
import unittest

BASE = Path(__file__).resolve().parents[1]
REPO = BASE.parents[1]
EXP = "EXP-20261011-DL-18000K-R01"
RUN = "RUN-20261011T120000Z-001"
INITIAL = "initial26-" + RUN


def get(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


PLAN = get("prearm", BASE / "prompt12-t2-prearm-plan.py")
ASSEMBLER = get("assembler", BASE / "prompt12-t2-input-assembler.py")
READINESS = get("readiness", BASE / "prompt12-t2-readiness-sequence.py")
VALIDATOR = get("validator", BASE / "prompt12-t2-evidence-adjudicator.py")
LAUNCHER = get("launcher", BASE / "prompt12-production-provider-manager-launcher.py")
FIXTURE = get("fixture", BASE / "tests" / "test_prompt12_bounded_production_binding_builder.py")


class T2E2EOffline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = cls("test_real_materializer_does_not_scientifically_execute")
        cls.fixture.build_fixture()
        f = cls.fixture
        cls.baseline = {p: p.read_bytes() for p in (
            f.initial,
            f.single,
            f.run_dir / "precontrol" / "T2.json",
            f.run_dir / "control" / "T2.executor.json",
            f.run_dir / "control" / "T2.trigger-intent.json",
            f.run_dir / "control" / "T2.critical-outcome.json",
            Path(str(f.single) + ".applied-readback.json"),
            Path(str(f.single) + ".post-stationarity.json"),
            f.canonical,
            f.timeline,
        )}

    @classmethod
    def tearDownClass(cls):
        cls.fixture.doCleanups()

    def setUp(self):
        # Never copy unittest's private cleanup stack from the shared fixture.
        for name, value in self.fixture.__dict__.items():
            if not name.startswith("_"):
                setattr(self, name, value)

    def tearDown(self):
        for path, content in self.baseline.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)

    def build_fixture(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="t2-e2e-offline-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.evidence = self.root / "evidence"
        self.evidence.mkdir()
        self.parent = self.root / "runtime-parent"
        self.parent.mkdir()
        self.prelaunch = self.root / "prelaunch"
        self.prelaunch.mkdir()
        self.plan = PLAN.build_plan(REPO, self.evidence, EXP, RUN,
                                    self.parent, self.prelaunch)
        self.allocation = LAUNCHER.validate_allocation(Path(self.plan["allocation_json"]))
        # SYNTHETIC FIFO, not opened for a trigger or connected to a provider.
        self.fifo = Path(self.plan["fifo_path"])
        self.fifo.parent.mkdir()
        os.mkfifo(self.fifo)
        baseline, _ = FIXTURE.create_profile(self.root / "fixtures")
        # Frozen legacy Python may exist only on coll.vntu.org; it is NOT
        # the runtime host interpreter and must never be executed on tb3.
        frozen = {"python_executable": "/nonexistent/controller-only/python39",
                  "tool_paths": baseline["tool_paths"],
                  "traffic_duration_s": 180, "trigger_token": "TRIGGER",
                  "stable_ms": 40, "snapshot_timeout_ms": 1000,
                  "timeline_readiness_poll_ms": 100,
                  "timeline_readiness_timeout_ms": 5000}
        self.frozen = self.root / "frozen.json"
        self.frozen.write_text(json.dumps(frozen), encoding="utf-8")
        admission = {"schema": "sci_oran_r6_f_portable_runtime_admission_v1",
                     "host": socket.getfqdn(), "python_executable": sys.executable,
                     "python_version": sys.version.split()[0],
                     "jsonschema_required": True,
                     "jsonschema_version": "synthetic",
                     "draft202012_capability": True,
                     "qualification_gate": "PASS"}
        self.admission = self.root / "portable-admission.json"
        self.admission.write_text(json.dumps(admission), encoding="utf-8")
        self.assembly = ASSEMBLER.prepare_inputs(
            self.evidence, EXP, RUN, self.frozen, self.admission, self.fifo,
            BASE, offline=False)
        self.run_dir = self.evidence / EXP / RUN
        self.assertTrue((self.run_dir / "precontrol").is_dir())
        self.assertTrue((self.run_dir / "control").is_dir())
        self.assertFalse((self.run_dir / "precontrol" / "T2.json").exists())
        self.assertFalse((self.run_dir / "control" / "T2.executor.json").exists())
        self.assertEqual(json.loads(Path(self.assembly["runtime_profile"]).read_text())
                         ["ratio_binding_paths"], self.plan["ratio_binding_paths"])

        self.ops = self.root / "readiness-ops"
        self.ops.mkdir()
        latest = self.root / "latest.env"
        trace = self.root / "calls.txt"
        smoke = self.root / "smoke.py"
        doctor = self.root / "doctor.py"
        smoke.write_text(
            "from pathlib import Path\n"
            + f"Path({str(trace)!r}).write_text('smoke\\n')\n"
            + f"Path({str(latest)!r}).write_text('SMOKE_ID=UPSMK-FAKE\\n')\n"
            + "print('SMOKE_ID=UPSMK-FAKE-001')\n"
            + "print('USER_PLANE_FUNCTIONAL_SMOKE_GATE=PASS')\n"
            + f"print('LATEST_EVIDENCE={latest}')\n", encoding="utf-8")
        doctor.write_text(
            "from pathlib import Path\n"
            + f"with Path({str(trace)!r}).open('a') as f: f.write('doctor\\n')\n"
            + "for key in ('USER_PLANE_READINESS_GATE', 'HOST_RESOURCE_READINESS_GATE', "
              "'READINESS_FRESHNESS_GATE', 'FINAL_ARTIFACT_SCI_ORAN_READY_GATE', "
              "'SCI_ORAN_READY_GATE'): print(key + '=PASS')\n"
            + "print('FAILURE_REASON=NONE')\n", encoding="utf-8")
        self.readiness = READINESS.run_sequence(
            [sys.executable, str(smoke)], [sys.executable, str(doctor)],
            self.ops, "UP-F03-001", latest)
        self.trace = trace

        initial_dir = self.run_dir / "initial26" / INITIAL
        initial_dir.mkdir(parents=True)
        self.initial = initial_dir / "result.env"
        self.initial.write_text("\n".join([
            "POSTCONTROL_APPLIED_PRB_STATE=0:26", "U_CMD_GATE=PASS",
            "U_ACK_GATE=PASS", "U_APPLIED_READBACK_GATE=PASS",
            "SCIENTIFIC_TRAFFIC_EXECUTED=NO", "FIFO_TRIGGER_EXECUTED=NO",
        ]) + "\n", encoding="utf-8")
        self.single = Path(self.assembly["single_transition_output"])
        proc = subprocess.run([
            sys.executable, "-B", str(BASE / "prompt12-resume-single-transition-materializer.py"),
            "--binding-manifest", self.assembly["binding_manifest"],
            "--resume-materialization", self.assembly["resume_materialization"],
            "--initial-transition-index", "2", "--output", str(self.single),
        ], capture_output=True, text=True, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.materialized = json.loads(self.single.read_text())
        self.build_synthetic_scientific_evidence()

    def build_synthetic_scientific_evidence(self):
        r = self.run_dir
        # These parents must come from the REAL assembler, not the fixture.
        self.assertTrue((r / "precontrol").is_dir())
        self.assertTrue((r / "control").is_dir())
        (r / "precontrol" / "T2.json").write_text(json.dumps({
            "output_stationarity_gate": "PASS", "freshness_gate": "PASS",
            "precontrol_admission_gate": "PASS",
        }))
        out = r / "control" / "T2.executor.json"
        self.assertEqual(out, Path(VALIDATOR.option(self.materialized["trigger_command"], "--output")))
        (r / "control" / "T2.trigger-intent.json").write_text(json.dumps({
            "operation_id": "T2-FAKE-F03",
            "scientific_trigger_replay_decision": "NEVER_AUTOMATICALLY_REPLAY"}))
        (r / "control" / "T2.critical-outcome.json").write_text(json.dumps({
            "operation_id": "T2-FAKE-F03", "state": "TRIGGER_CONFIRMED_AWAITING_READBACK",
            "trigger_dispatch_attempted": True, "trigger_execution_confirmed": True,
        }))
        out.write_text(json.dumps({
            "EXECUTOR_GATE": "PASS", "CONTROL_EXECUTED": "YES",
            "SCIENTIFIC_TRIGGER_CONSUMED": "YES",
            "TRIGGER_WRITE_ATTEMPT_COUNT": 1,
            "TRIGGER_WRITE_SUCCESS_COUNT": 1,
            "EXECUTOR_START_SAMPLE_AGE_GATE": "PASS",
        }))
        Path(str(self.single) + ".applied-readback.json").write_text(json.dumps({
            "schema": "sci_oran_prompt12_authoritative_prb_readback_v1",
            "authoritative_source": "CONTAINER:/tmp/gnb.log",
            "docker_logs_is_authoritative": False, "u_applied_readback_gate": "PASS",
            "expected_min_prbs": 0, "expected_max_prbs": 39,
            "selected": {"applied_min_prbs": 0, "applied_max_prbs": 39},
        }))
        Path(str(self.single) + ".post-stationarity.json").write_text(json.dumps({
            "output_stationarity_gate": "PASS", "minimum_phase_duration_gate": "PASS"}))
        for file in self.materialized["traffic_command"][4:6]:
            path = Path(file)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("synthetic-test-only\n")
        canonical = r / "processed" / "iperf3-receiver.intervals.canonical.jsonl"
        self.canonical = canonical
        with canonical.open("w") as out:
            for i in range(900):
                row = {"experiment_id": EXP, "run_id": RUN,
                       "record_id": f"rx-{i:04d}", "timestamp_utc_ns": 10**18 + i * 200_000_000,
                       "rx_wall_ns": 10**18 + i * 200_000_000,
                       "rx_mono_ns": 10**13 + i * 200_000_000,
                       "interval_start_s": round(i * 0.2, 1),
                       "interval_end_s": round((i + 1) * 0.2, 1),
                       "interval_duration_s": 0.2,
                       "throughput_kbit_s": 11000 if i < 250 else 16500,
                       "interval_class": "complete"}
                out.write(json.dumps(row) + "\n")
        timeline = r / "processed" / "actuator-timeline.jsonl"
        self.timeline = timeline
        with timeline.open("w") as out:
            for i, typ in enumerate(("command", "acknowledgement", "applied_readback")):
                row = {"experiment_id": EXP, "run_id": RUN,
                       "record_id": f"actuator-{i}",
                       "timestamp_utc_ns": 10**18 + 50_000_000_000 + i * 200_000_000,
                       "event_type": typ}
                if typ == "command": row["requested_max_prb_ratio_pct"] = 75
                if typ == "acknowledgement": row["acknowledgement_status"] = "PASS"
                if typ == "applied_readback": row.update(applied_min_prbs=0, applied_max_prbs=39)
                out.write(json.dumps(row) + "\n")

    def test_complete_synthetic_chain_and_independent_adjudicator(self):
        self.assertEqual(self.trace.read_text().splitlines(), ["smoke", "doctor"])
        self.assertEqual(self.readiness["readiness_handoff_gate"], "PASS")
        value = VALIDATOR.adjudicate(self.single, INITIAL)
        self.assertEqual(value["scientific_t2_gate"], "PASS")
        self.assertEqual(value["canonical_interval_count"], 900)
        self.assertEqual(value["trigger_write_attempt_count"], 1)
        self.assertFalse(value["automatic_trigger_replay"])

    def test_scientific_adjudicator_cli_writes_exclusive_record(self):
        report = self.run_dir / "runtime" / "t2-scientific-adjudication.json"
        try:
            self.assertEqual(VALIDATOR.main([
                "--materialization", str(self.single),
                "--initial26-operation-id", INITIAL]), 0)
            actual = json.loads(report.read_text())
            self.assertEqual(actual["scientific_t2_gate"], "PASS")
            self.assertEqual(actual["trigger_write_attempt_count"], 1)
            # A second adjudication must not overwrite the existing record.
            self.assertNotEqual(VALIDATOR.main([
                "--materialization", str(self.single),
                "--initial26-operation-id", INITIAL]), 0)
        finally:
            report.unlink(missing_ok=True)

    def test_provider_plan_no_replay_and_exact_identity(self):
        root, identity = PLAN.expected_identity(EXP, RUN, self.parent)
        self.assertEqual(self.plan["runtime_root"], str(root))
        self.assertEqual(self.plan["provider_identity"], identity)
        with self.assertRaisesRegex(PLAN.PlanError, "RUNTIME_ROOT_ALREADY_CONSUMED"):
            PLAN.build_plan(REPO, self.evidence, EXP, RUN, self.parent, self.prelaunch)
        with self.assertRaisesRegex(ASSEMBLER.AssemblyError, "RUN_ID_ALREADY_CONSUMED"):
            ASSEMBLER.prepare_inputs(self.evidence, EXP, RUN, self.frozen, self.admission,
                                     self.fifo, BASE, offline=False)

    def test_missing_initial26_blocks_even_with_all_39_prb_evidence(self):
        self.initial.unlink()
        with self.assertRaisesRegex(VALIDATOR.EvidenceError, "INITIAL26_EVIDENCE_MISSING"):
            VALIDATOR.adjudicate(self.single, INITIAL)

    def test_invalid_authoritative_applied_state_blocks(self):
        path = Path(str(self.single) + ".applied-readback.json")
        value = json.loads(path.read_text())
        value["selected"]["applied_max_prbs"] = 26
        path.write_text(json.dumps(value))
        with self.assertRaisesRegex(VALIDATOR.EvidenceError, "AUTHORITATIVE_39_PRBS_NOT_PROVEN"):
            VALIDATOR.adjudicate(self.single, INITIAL)

    def test_duplicate_fifo_write_attempt_blocks(self):
        path = self.run_dir / "control" / "T2.executor.json"
        value = json.loads(path.read_text())
        value["TRIGGER_WRITE_ATTEMPT_COUNT"] = 2
        path.write_text(json.dumps(value))
        with self.assertRaisesRegex(VALIDATOR.EvidenceError, "TRIGGER_EXECUTOR"):
            VALIDATOR.adjudicate(self.single, INITIAL)

    def test_truncated_canonical_data_blocks(self):
        rows = self.canonical.read_text().splitlines()
        self.canonical.write_text("\n".join(rows[:400]) + "\n")
        with self.assertRaisesRegex(VALIDATOR.EvidenceError, "INTERVAL_COUNT_INSUFFICIENT"):
            VALIDATOR.adjudicate(self.single, INITIAL)

    def test_scientific_trace_with_long_gap_blocks(self):
        rows = self.canonical.read_text().splitlines()
        # Same 180-second outer coverage and >750 records, but a missing
        # 20-second block must NOT be admitted as a continuous sampled trace.
        self.canonical.write_text("\n".join(rows[:400] + rows[500:]) + "\n")
        with self.assertRaisesRegex(VALIDATOR.EvidenceError, "TIME_GAP_TOO_LARGE"):
            VALIDATOR.adjudicate(self.single, INITIAL)

    def test_wrong_timeline_applied_state_blocks(self):
        rows = [json.loads(x) for x in self.timeline.read_text().splitlines()]
        rows[-1]["applied_max_prbs"] = 26
        self.timeline.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
        with self.assertRaisesRegex(VALIDATOR.EvidenceError, "SCIENTIFIC_TIMELINE_NOT_26_TO_39"):
            VALIDATOR.adjudicate(self.single, INITIAL)

    def test_corrupt_canonical_schema_blocks(self):
        rows = [json.loads(x) for x in self.canonical.read_text().splitlines()]
        rows[0]["throughput_kbit_s"] = -1
        self.canonical.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
        with self.assertRaisesRegex(VALIDATOR.EvidenceError, "SCHEMA_INVALID:iperfInterval"):
            VALIDATOR.adjudicate(self.single, INITIAL)

    def test_real_materializer_does_not_scientifically_execute(self):
        for flag in ("command_executed", "control_executed", "traffic_executed"):
            self.assertIs(self.materialized[flag], False)
        self.assertEqual(self.plan["control_executed"], False)
        self.assertEqual(self.assembly["scientific_t2"], "NOT_EXECUTED")

    def test_host_specific_python_from_portable_admission_not_frozen(self):
        profile = json.loads(Path(self.assembly["runtime_profile"]).read_text())
        frozen = json.loads(self.frozen.read_text())
        admission = json.loads(self.admission.read_text())
        self.assertNotEqual(frozen["python_executable"],
                            admission["python_executable"])
        self.assertEqual(profile["python_executable"],
                         admission["python_executable"])
        self.assertEqual(profile["python_executable"], sys.executable)
        self.assertFalse(Path(frozen["python_executable"]).exists())

    def test_macro_uses_runtime_interpreter_for_preflight_and_adjudication(self):
        path = REPO / "sci-oran/ansible/experiments/prompt12/playbooks/prompt12-t2-experiment.yml"
        source = path.read_text(encoding="utf-8")

        def task(name):
            marker = "    - name: " + name + "\n"
            self.assertEqual(source.count(marker), 1)
            return source.split(marker, 1)[1].split("    - name: ", 1)[0]

        preflight = task("Materialize fresh portable runtime admission")
        self.assertIn("- --python-executable\n          - /usr/bin/python3", preflight)
        binding = task("Bind host-qualified Python from validated runtime profile")
        self.assertIn("(sci_oran_t2_profile_raw.content | b64decode | from_json).python_executable", binding)
        adjudication = task("Independently classify one scientific T2 evidence bundle")
        self.assertIn("- '{{ sci_oran_t2_admitted_python }}'", adjudication)
        self.assertNotIn("sci_oran_t2_frozen_values.python_executable", source)
        self.assertIn("- sci_oran_t2_admitted_python == '/usr/bin/python3'", source)

    def test_macro_rejects_missing_control_evidence_before_initial26(self):
        path = REPO / "sci-oran/ansible/experiments/prompt12/playbooks/prompt12-t2-experiment.yml"
        source = path.read_text(encoding="utf-8")
        assembly = source.index("    - name: Assemble new RUN using existing production materializers")
        admission = source.index("    - name: Inspect T2 evidence output parents before initial26")
        reject = source.index("    - name: Require T2 output parents and unused trigger evidence")
        initial26 = source.index("- import_playbook: prompt12-initial26-preconditioning.yml")
        self.assertLess(assembly, admission)
        self.assertLess(admission, reject)
        self.assertLess(reject, initial26)
        self.assertIn("EXPERIMENT_T2_OUTPUT_PARENTS_OR_REPLAY_GUARD_FAILED", source)

    def test_macro_yml_strict_order_and_unique_scientific_import(self):
        # This structural contract must work in the pinned jsonschema venv,
        # which intentionally does not require PyYAML. Native Ansible syntax
        # validation is a separate qualification gate on the controller.
        path = REPO / "sci-oran/ansible/experiments/prompt12/playbooks/prompt12-t2-experiment.yml"
        source = path.read_text(encoding="utf-8")
        plays = list(re.finditer(
            r"(?m)^- (name|import_playbook):[ \t]*([^\r\n]+)$", source))
        self.assertEqual([m.group(1) for m in plays],
                         ["name", "import_playbook", "name", "import_playbook", "name"])
        self.assertEqual([m.group(2).strip() for m in plays if m.group(1) == "import_playbook"],
                         ["prompt12-initial26-preconditioning.yml", "prompt12-resume-single-transition.yml"])
        first_play = source[plays[0].start():plays[1].start()]
        names = re.findall(r"(?m)^    - name: ([^\r\n]+)$", first_play)
        self.assertLess(names.index("Wait only for observed UE PDU-interface readiness"),
                        names.index("Run one user-plane smoke immediately before one Doctor"))
        self.assertLess(names.index("Run one user-plane smoke immediately before one Doctor"),
                        names.index("Produce exclusive deterministic provider plan before RUN allocation"))
        self.assertLess(names.index("Start and prove one persistent prearmed provider"),
                        names.index("Assemble new RUN using existing production materializers"))


if __name__ == "__main__":
    unittest.main()
