import pathlib
import unittest


REPO = pathlib.Path(
    "/home/khoshaba/project/tcd-oran-testbed-integration"
)

PLAYBOOK = (
    REPO
    / "sci-oran"
    / "ansible"
    / "experiments"
    / "prompt12"
    / "playbooks"
    / "prompt12-resume-single-transition.yml"
)


class ResumeSingleTransitionAnsibleContractTest(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.text = PLAYBOOK.read_text(
            encoding="utf-8"
        )

    def test_dynamic_readback_window_end_contract_exists(self):
        self.assertIn(
            "@PROMPT12_READBACK_WINDOW_END@",
            self.text,
        )
        self.assertIn(
            "Capture authoritative T2 readback window end",
            self.text,
        )
        self.assertIn(
            "Late-bind authoritative T2 readback window end",
            self.text,
        )
        self.assertIn(
            "PROMPT12_T2_READBACK_WINDOW_END_LATE_BIND_FAILED",
            self.text,
        )

    def test_local_trigger_precedes_authoritative_readback_and_stationarity(self):
        trigger = self.text.index(
            "Execute resumed T2 initial precontrol and exactly-once scientific trigger"
        )
        bind = self.text.index(
            "Bind authoritative T2 readback window start from critical section"
        )
        capture = self.text.index(
            "Capture authoritative T2 readback window end"
        )
        readback = self.text.index(
            "Obtain authoritative applied PRB readback"
        )
        stationarity = self.text.index(
            "Execute pure resumed T2 post-step stationarity"
        )
        self.assertLess(trigger, bind)
        self.assertLess(bind, capture)
        self.assertLess(capture, readback)
        self.assertLess(readback, stationarity)

    def test_readback_uses_effective_late_bound_argv(self):
        start = self.text.index(
            "Obtain authoritative applied PRB readback"
        )
        end = self.text.index(
            "Decode authoritative applied PRB readback"
        )
        block = self.text[start:end]

        self.assertIn(
            'argv: "{{ sci_oran_prompt12_effective_authoritative_readback_argv }}"',
            block,
        )
        self.assertNotIn(
            'argv: "{{ sci_oran_prompt12_authoritative_readback_argv }}"',
            block,
        )

    def test_authoritative_state_contract_remains_0_39(self):
        self.assertIn(
            "CONTAINER:/tmp/gnb.log",
            self.text,
        )
        self.assertIn(
            "expected_min_prbs == 0",
            self.text,
        )
        self.assertIn(
            "expected_max_prbs == 39",
            self.text,
        )
        self.assertIn(
            "selected.applied_max_prbs == 39",
            self.text,
        )

    def test_local_critical_section_has_no_retry_semantics(self):
        start = self.text.index(
            "Execute resumed T2 initial precontrol and exactly-once scientific trigger"
        )
        end = self.text.index("Capture T2 post-phase start")
        block = self.text[start:end]
        self.assertNotIn("retries:", block)
        self.assertNotIn("until:", block)
        self.assertIn("prompt12-t2-critical-section.py", block)
        self.assertIn("SCI_ORAN_PROMPT12_LIVE_CONTROL_ENABLE", block)

    def test_live_traffic_preflight_and_authorization_before_trigger(self):
        traffic_argv = self.text.index("Validate bounded traffic evidence argv contract")
        traffic_launch = self.text.index("Start bounded scientific traffic asynchronously")
        critical = self.text.index(
            "Execute resumed T2 initial precontrol and exactly-once scientific trigger"
        )
        self.assertLess(traffic_argv, traffic_launch)
        self.assertLess(traffic_launch, critical)
        self.assertNotIn("sci_oran_prompt12_execution_operation_id", self.text)
        self.assertIn("PROMPT12_T2_EXPLICIT_FIFO_CONTROL", self.text)

    def test_t3_handoff_and_trigger_remain_absent(self):
        self.assertIn(
            "not sci_oran_prompt12_single.t3_handoff_present",
            self.text,
        )
        self.assertIn(
            "not sci_oran_prompt12_single.t3_trigger_present",
            self.text,
        )

    def test_offline_validation_ends_before_live_execution(self):
        end_play = self.text.index(
            "End safely after offline validation"
        )
        traffic = self.text.index(
            "Start bounded scientific traffic asynchronously"
        )
        trigger = self.text.index(
            "Execute resumed T2 initial precontrol and exactly-once scientific trigger"
        )

        self.assertLess(end_play, traffic)
        self.assertLess(end_play, trigger)


    def test_failure_handler_preserves_evidence_without_scientific_replay(self):
        self.assertIn(
            "Run one bounded T2 experiment with evidence-preserving failure handling",
            self.text,
        )
        self.assertIn("      rescue:", self.text)
        self.assertIn(".failure.json", self.text)
        self.assertIn("automatic_replay': false", self.text)
        self.assertIn("scientific_pass': false", self.text)
        self.assertIn("force: false", self.text)
        self.assertIn("PROMPT12_T2_FAIL_CLOSED_NO_REPLAY_EVIDENCE_PRESERVED", self.text)
        self.assertNotIn("ansible.builtin.shell:", self.text)

    def test_dynamic_readback_window_end_uses_microsecond_precision(self):
        start = self.text.index(
            "Capture authoritative T2 readback window end"
        )
        end = self.text.index(
            "Late-bind authoritative T2 readback window end"
        )
        block = self.text[start:end]

        self.assertIn(
            "+%Y-%m-%dT%H:%M:%S.%6NZ",
            block,
        )
        self.assertNotIn(
            "+%Y-%m-%dT%H:%M:%SZ",
            block,
        )



if __name__ == "__main__":
    unittest.main()
