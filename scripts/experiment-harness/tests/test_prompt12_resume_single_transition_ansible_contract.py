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

    def test_trigger_capture_readback_stationarity_order(self):
        trigger = self.text.index(
            "Execute exactly-once T2 scientific trigger"
        )
        capture = self.text.index(
            "Capture authoritative T2 readback window end"
        )
        bind = self.text.index(
            "Late-bind authoritative T2 readback window end"
        )
        readback = self.text.index(
            "Obtain authoritative applied PRB readback"
        )
        stationarity = self.text.index(
            "Execute pure resumed T2 post-step stationarity"
        )

        self.assertLess(trigger, capture)
        self.assertLess(capture, bind)
        self.assertLess(bind, readback)
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

    def test_trigger_has_no_retry_semantics(self):
        start = self.text.index(
            "Execute exactly-once T2 scientific trigger"
        )
        end = self.text.index(
            "Capture authoritative T2 readback window end"
        )
        block = self.text[start:end]

        self.assertNotIn("retries:", block)
        self.assertNotIn("until:", block)

    def test_traffic_and_late_binding_remain_before_trigger(self):
        traffic = self.text.index(
            "Require bounded traffic active immediately before T2 trigger"
        )
        late_bind = self.text.index(
            "Late-bind T2 control authorization in memory"
        )
        trigger = self.text.index(
            "Execute exactly-once T2 scientific trigger"
        )

        self.assertLess(traffic, late_bind)
        self.assertLess(late_bind, trigger)
        self.assertIn(
            "PROMPT12_T2_EXPLICIT_FIFO_CONTROL",
            self.text,
        )

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
            "Execute exactly-once T2 scientific trigger"
        )

        self.assertLess(end_play, traffic)
        self.assertLess(end_play, trigger)


if __name__ == "__main__":
    unittest.main()
