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


class T2TrafficReadinessDiagnosticsContractTest(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.text = PLAYBOOK.read_text(
            encoding="utf-8"
        )

    def test_blind_wait_is_replaced(self):
        self.assertNotIn(
            "- name: Wait for bounded traffic raw evidence file\n",
            self.text,
        )
        self.assertIn(
            "Wait briefly for bounded traffic raw evidence file",
            self.text,
        )

    def test_async_status_is_read_at_readiness_barrier(self):
        self.assertIn(
            "Read bounded traffic status at evidence readiness barrier",
            self.text,
        )
        self.assertIn(
            'jid: "{{ sci_oran_prompt12_traffic_job.ansible_job_id }}"',
            self.text,
        )

    def test_early_exit_diagnostics_are_exposed(self):
        self.assertIn(
            "PROMPT12_TRAFFIC_EVIDENCE_READINESS_FAILED",
            self.text,
        )
        self.assertIn(
            "async_rc={{",
            self.text,
        )
        self.assertIn(
            "async_stdout={{",
            self.text,
        )
        self.assertIn(
            "async_stderr={{",
            self.text,
        )

    def test_readiness_requires_evidence_and_live_job(self):
        self.assertIn(
            "sci_oran_prompt12_raw_evidence_stat.stat.exists",
            self.text,
        )
        self.assertIn(
            "not (sci_oran_prompt12_traffic_readiness.finished | bool)",
            self.text,
        )

    def test_barrier_precedes_precontrol(self):
        launch = self.text.index(
            "Start bounded scientific traffic asynchronously"
        )
        wait = self.text.index(
            "Wait briefly for bounded traffic raw evidence file"
        )
        status = self.text.index(
            "Read bounded traffic status at evidence readiness barrier"
        )
        gate = self.text.index(
            "Require bounded traffic evidence readiness or expose early exit"
        )
        precontrol = self.text.index(
            "Execute resumed T2 initial precontrol"
        )

        self.assertLess(launch, wait)
        self.assertLess(wait, status)
        self.assertLess(status, gate)
        self.assertLess(gate, precontrol)


if __name__ == "__main__":
    unittest.main()
