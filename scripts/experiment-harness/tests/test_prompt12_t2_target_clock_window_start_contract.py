import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
PLAYBOOK = (
    ROOT / "sci-oran" / "ansible" / "experiments" / "prompt12" / "playbooks"
    / "prompt12-resume-single-transition.yml"
)
CRITICAL = (
    ROOT / "scripts" / "experiment-harness" / "prompt12-t2-critical-section.py"
)


class Prompt12T2TargetClockWindowStartContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = PLAYBOOK.read_text(encoding="utf-8")
        cls.runner = CRITICAL.read_text(encoding="utf-8")

    def test_local_trigger_produces_readback_start_before_remote_readback(self):
        markers = [
            "Execute resumed T2 initial precontrol and exactly-once scientific trigger",
            "Bind authoritative T2 readback window start from critical section",
            "Capture authoritative T2 readback window end",
            "Obtain authoritative applied PRB readback",
        ]
        positions = [self.text.index(marker) for marker in markers]
        self.assertEqual(positions, sorted(positions))

    def test_window_start_is_captured_on_target_before_trigger_dispatch(self):
        capture = self.runner.index("readback_start = datetime.datetime.now(")
        invoke = self.runner.index('trigger = run_child(resolved_trigger, "TRIGGER")')
        self.assertLess(capture, invoke)
        block = self.runner[capture:invoke]
        self.assertIn("datetime.timezone.utc", block)
        self.assertIn("%Y-%m-%dT%H:%M:%S.%fZ", block)
        self.assertNotIn("subprocess.run", block)
        self.assertNotIn("ssh ", block)

    def test_target_timestamp_is_bound_into_authoritative_reader(self):
        start = self.text.index(
            "Bind authoritative T2 readback window start from critical section"
        )
        stop = self.text.index("Capture T2 post-phase start")
        block = self.text[start:stop]
        self.assertIn("sci_oran_prompt12_authoritative_readback_argv:", block)
        self.assertIn("'--window-start'", block)
        self.assertIn("sci_oran_prompt12_initial_pre_report.readback_window_start_utc", block)
        self.assertNotIn("/bin/date", block)
        self.assertNotIn("delegate_to:", block)

    def test_play_targets_tb3_by_default(self):
        self.assertIn(
            "hosts: \"{{ sci_oran_prompt12_inventory_target | default('tb3-dell') }}\"",
            self.text,
        )


if __name__ == "__main__":
    unittest.main()
