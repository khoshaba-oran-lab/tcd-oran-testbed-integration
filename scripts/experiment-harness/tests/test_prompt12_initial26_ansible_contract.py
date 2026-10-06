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
    / "prompt12-initial26-preconditioning.yml"
)


class Initial26AnsibleContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = PLAYBOOK.read_text(encoding="utf-8")

    def test_uses_production_leaf_wrapper(self):
        self.assertIn(
            "prompt12-production-actuator-wrapper.py",
            self.text,
        )
        self.assertIn(
            "82acab967a1459a1f2da36e96d5e3b99aa08971c1941be1de14919a3266494bb",
            self.text,
        )

    def test_ratio_is_exactly_50_percent(self):
        self.assertIn(
            'sci_oran_prompt12_initial26_ratio: "50"',
            self.text,
        )
        self.assertIn(
            "SCI_ORAN_MAX_PRB_RATIO:",
            self.text,
        )

    def test_authoritative_readback_is_required(self):
        self.assertIn(
            "prompt12-authoritative-prb-readback.py",
            self.text,
        )
        self.assertIn(
            "CONTAINER:/tmp/gnb.log",
            self.text,
        )
        self.assertIn(
            "expected_final_max_prbs: 26",
            self.text,
        )

    def test_precondition_requires_startup_275(self):
        self.assertIn(
            "expected_startup_max_prbs: 275",
            self.text,
        )
        self.assertIn(
            "PRECONTROL_APPLIED_PRB_STATE=0:275",
            self.text,
        )

    def test_exactly_once_operation_boundary_exists(self):
        self.assertIn(
            "PROMPT12_INITIAL26_OPERATION_ALREADY_EXISTS",
            self.text,
        )
        self.assertIn(
            "docker_execution_attempt_count == 1",
            self.text,
        )
        self.assertNotIn(
            "retries:",
            self.text,
        )
        self.assertNotIn(
            "until:",
            self.text,
        )

    def test_live_authorization_is_explicit(self):
        self.assertIn(
            "AUTHORISE_PROMPT12_INITIAL26_PRECONDITIONING_LIVE",
            self.text,
        )

    def test_scientific_t2_capabilities_are_absent(self):
        forbidden = (
            "prompt12-bounded-traffic-session.sh",
            "PROMPT12_T2_EXPLICIT_FIFO_CONTROL",
            "actuator.fifo",
            "prompt12-precontrol-trigger-executor.py",
            "async:",
        )
        for token in forbidden:
            self.assertNotIn(token, self.text)

    def test_docker_logs_is_not_used(self):
        self.assertNotIn(
            "docker logs",
            self.text,
        )

    def test_postcontrol_readback_follows_wrapper(self):
        wrapper = self.text.index(
            "Execute initial26 production actuator exactly once"
        )
        post = self.text.index(
            "Obtain authoritative post-control state 26 PRB"
        )
        self.assertLess(wrapper, post)

    def test_no_t2_success_claim(self):
        self.assertIn(
            "T2_26_TO_39_TRANSITION=NOT_EXECUTED",
            self.text,
        )


if __name__ == "__main__":
    unittest.main()
