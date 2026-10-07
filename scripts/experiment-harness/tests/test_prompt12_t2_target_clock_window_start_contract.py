import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[3]

PLAYBOOK = (
    ROOT
    / "sci-oran"
    / "ansible"
    / "experiments"
    / "prompt12"
    / "playbooks"
    / "prompt12-resume-single-transition.yml"
)


class Prompt12T2TargetClockWindowStartContractTest(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.text = PLAYBOOK.read_text(
            encoding="utf-8"
        )

    def test_target_clock_capture_precedes_trigger(self):
        markers = [
            "Capture authoritative T2 readback window start",
            "Bind authoritative T2 readback window start",
            "Execute exactly-once T2 scientific trigger",
            "Capture authoritative T2 readback window end",
            "Obtain authoritative applied PRB readback",
        ]

        positions = [
            self.text.index(marker)
            for marker in markers
        ]

        self.assertEqual(
            positions,
            sorted(positions),
        )

    def test_window_start_is_captured_by_target_task(self):
        start = self.text.index(
            "Capture authoritative T2 readback window start"
        )
        stop = self.text.index(
            "Bind authoritative T2 readback window start"
        )

        block = self.text[start:stop]

        self.assertIn(
            "ansible.builtin.command:",
            block,
        )
        self.assertIn(
            "- /bin/date",
            block,
        )
        self.assertIn(
            "- -u",
            block,
        )
        self.assertIn(
            "+%Y-%m-%dT%H:%M:%S.%6NZ",
            block,
        )
        self.assertIn(
            "register: sci_oran_prompt12_readback_window_start",
            block,
        )
        self.assertIn(
            "changed_when: false",
            block,
        )
        self.assertNotIn(
            "delegate_to:",
            block,
        )
        self.assertNotIn(
            "ssh ",
            block,
        )

    def test_captured_target_time_replaces_window_start_value(self):
        start = self.text.index(
            "Bind authoritative T2 readback window start"
        )
        stop = self.text.index(
            "Execute exactly-once T2 scientific trigger"
        )

        block = self.text[start:stop]

        self.assertIn(
            "sci_oran_prompt12_authoritative_readback_argv:",
            block,
        )
        self.assertIn(
            ".index(",
            block,
        )
        self.assertIn(
            "'--window-start'",
            block,
        )
        self.assertIn(
            "sci_oran_prompt12_readback_window_start.stdout",
            block,
        )
        self.assertIn(
            "| trim",
            block,
        )

    def test_play_targets_tb3_by_default(self):
        self.assertIn(
            "hosts: \"{{ "
            "sci_oran_prompt12_inventory_target "
            "| default('tb3-dell') }}\"",
            self.text,
        )


if __name__ == "__main__":
    unittest.main()
