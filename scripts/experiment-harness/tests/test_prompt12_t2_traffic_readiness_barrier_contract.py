import pathlib
import unittest


REPO = pathlib.Path(__file__).resolve().parents[3]

PLAYBOOK = (
    REPO
    / "sci-oran"
    / "ansible"
    / "experiments"
    / "prompt12"
    / "playbooks"
    / "prompt12-resume-single-transition.yml"
)


class Prompt12T2TrafficReadinessBarrierContractTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.source = PLAYBOOK.read_text(encoding="utf-8")

    def position(self, marker):
        value = self.source.find(marker)
        self.assertGreaterEqual(
            value,
            0,
            f"missing marker: {marker}",
        )
        return value

    def test_readiness_barrier_precedes_initial_precontrol(self):
        start = self.position(
            "- name: Start bounded scientific traffic asynchronously"
        )
        active = self.position(
            "- name: Require bounded traffic active after launch"
        )
        raw = self.position(
            "- name: Wait for bounded traffic raw evidence to become nonempty"
        )
        timestamps = self.position(
            "- name: Wait for bounded traffic timestamp evidence to become nonempty"
        )
        accumulate = self.position(
            "- name: Accumulate minimum Prompt12 pre-phase"
        )
        post_active = self.position(
            "- name: Require bounded traffic active after minimum pre-phase"
        )
        growth = self.position(
            "- name: Require bounded traffic evidence growth"
        )
        precontrol = self.position(
            "- name: Execute resumed T2 initial precontrol"
        )
        precontrol_gate = self.position(
            "- name: Require resumed T2 initial precontrol stationarity"
        )
        ratio = self.position(
            "- name: Execute T2 ratio binding"
        )

        self.assertTrue(
            start
            < active
            < raw
            < timestamps
            < accumulate
            < post_active
            < growth
            < precontrol
            < precontrol_gate
            < ratio
        )

    def test_prephase_is_at_least_eleven_seconds(self):
        marker = (
            "- name: Accumulate minimum "
            "Prompt12 pre-phase"
        )

        self.assertEqual(
            self.source.count(marker),
            1,
        )

        start = self.source.index(marker)

        end = self.source.find(
            "\n    - name:",
            start + len(marker),
        )

        self.assertNotEqual(
            end,
            -1,
        )

        block = self.source[start:end]

        seconds_lines = [
            line.strip()
            for line in block.splitlines()
            if line.strip().startswith("seconds:")
        ]

        self.assertEqual(
            len(seconds_lines),
            1,
        )

        seconds = int(
            seconds_lines[0]
            .split(":", 1)[1]
            .strip()
        )

        self.assertGreaterEqual(
            seconds,
            11,
        )

        self.assertIn(
            ">= 11000000000",
            self.source,
        )

    def test_barrier_proves_async_job_active_before_and_after(self):
        self.assertGreaterEqual(
            self.source.count(
                "ansible.builtin.async_status:"
            ),
            4,
        )
        self.assertIn(
            "PROMPT12_TRAFFIC_NOT_ACTIVE_AFTER_LAUNCH",
            self.source,
        )
        self.assertIn(
            "PROMPT12_TRAFFIC_NOT_ACTIVE_AFTER_PREPHASE",
            self.source,
        )

    def test_barrier_proves_receiver_evidence_growth(self):
        self.assertIn(
            "sci_oran_prompt12_single.traffic_command[4]",
            self.source,
        )
        self.assertIn(
            "sci_oran_prompt12_single.traffic_command[5]",
            self.source,
        )
        self.assertIn(
            "sci_oran_prompt12_raw_postphase.stat.size",
            self.source,
        )
        self.assertIn(
            "sci_oran_prompt12_timestamp_postphase.stat.size",
            self.source,
        )
        self.assertIn(
            "PROMPT12_TRAFFIC_PREPHASE_EVIDENCE_GATE_FAILED",
            self.source,
        )

    def test_initial_precontrol_must_pass_before_ratio_binding(self):
        gate = self.position(
            "- name: Require resumed T2 initial precontrol stationarity"
        )
        ratio = self.position(
            "- name: Execute T2 ratio binding"
        )

        self.assertLess(gate, ratio)

        self.assertIn(
            "output_stationarity_gate == 'PASS'",
            self.source,
        )
        self.assertIn(
            "minimum_phase_duration_gate == 'PASS'",
            self.source,
        )
        self.assertIn(
            "statistical_phase_candidate == 'PASS'",
            self.source,
        )

    def test_no_new_shell_or_live_control_is_added(self):
        barrier_start = self.position(
            "- name: Validate bounded traffic evidence argv contract"
        )
        precontrol = self.position(
            "- name: Execute resumed T2 initial precontrol"
        )

        barrier = self.source[barrier_start:precontrol]

        self.assertNotIn(
            "ansible.builtin.shell:",
            barrier,
        )
        self.assertNotIn(
            "docker ",
            barrier,
        )
        self.assertNotIn(
            "TRIGGER",
            barrier,
        )


if __name__ == "__main__":
    unittest.main()
