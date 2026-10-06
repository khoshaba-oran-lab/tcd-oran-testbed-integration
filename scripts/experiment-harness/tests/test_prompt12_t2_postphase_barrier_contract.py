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


class Prompt12T2PostphaseBarrierContractTest(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.text = PLAYBOOK.read_text(encoding="utf-8")

    def test_postphase_barrier_order(self):
        markers = [
            "Execute exactly-once T2 scientific trigger",
            "Capture T2 post-phase start",
            "Require bounded traffic active immediately after T2 trigger",
            "Capture authoritative T2 readback window end",
            "Obtain authoritative applied PRB readback",
            "Require authoritative T2 applied state 39 PRB",
            "Accumulate minimum T2 post-phase",
            "Require bounded traffic active after minimum T2 post-phase",
            "Require bounded traffic post-phase evidence growth",
            "Execute pure resumed T2 post-step stationarity",
        ]

        positions = [
            self.text.index(marker)
            for marker in markers
        ]

        self.assertEqual(
            positions,
            sorted(positions),
        )

    def test_postphase_minimum_is_ten_seconds(self):
        start = self.text.index(
            "Accumulate minimum T2 post-phase"
        )
        end = self.text.index(
            "Execute pure resumed T2 post-step stationarity"
        )
        block = self.text[start:end]

        self.assertIn("seconds: 10", block)
        self.assertIn(">= 10000000000", block)

    def test_traffic_must_remain_active_after_trigger_and_postphase(self):
        self.assertIn(
            "PROMPT12_TRAFFIC_NOT_ACTIVE_AFTER_T2_TRIGGER",
            self.text,
        )
        self.assertIn(
            "PROMPT12_TRAFFIC_NOT_ACTIVE_AFTER_POSTPHASE",
            self.text,
        )

    def test_raw_and_timestamp_evidence_must_grow(self):
        start = self.text.index(
            "Capture T2 post-phase start"
        )
        end = self.text.index(
            "Execute pure resumed T2 post-step stationarity"
        )
        block = self.text[start:end]

        self.assertIn(
            "traffic_command[4]",
            block,
        )
        self.assertIn(
            "traffic_command[5]",
            block,
        )
        self.assertIn(
            "sci_oran_prompt12_postphase_raw_after.stat.size",
            block,
        )
        self.assertIn(
            "sci_oran_prompt12_postphase_raw_before.stat.size",
            block,
        )
        self.assertIn(
            "sci_oran_prompt12_postphase_timestamps_after.stat.size",
            block,
        )
        self.assertIn(
            "sci_oran_prompt12_postphase_timestamps_before.stat.size",
            block,
        )
        self.assertIn(
            "PROMPT12_TRAFFIC_POSTPHASE_EVIDENCE_GATE_FAILED",
            block,
        )

    def test_post_stationarity_occurs_only_after_postphase_gate(self):
        barrier = self.text.index(
            "Require bounded traffic post-phase evidence growth"
        )
        stationarity = self.text.index(
            "Execute pure resumed T2 post-step stationarity"
        )

        self.assertLess(barrier, stationarity)

    def test_repair_does_not_add_second_t2_trigger(self):
        self.assertEqual(
            self.text.count(
                "Execute exactly-once T2 scientific trigger"
            ),
            1,
        )

        trigger = self.text.index(
            "Execute exactly-once T2 scientific trigger"
        )
        stationarity = self.text.index(
            "Execute pure resumed T2 post-step stationarity"
        )
        block = self.text[trigger:stationarity]

        self.assertNotIn("docker exec", block)
        self.assertNotIn("shell:", block)


if __name__ == "__main__":
    unittest.main()
