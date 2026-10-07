import pathlib
import subprocess
import tempfile
import unittest


REPO = pathlib.Path(
    "/home/khoshaba/project/tcd-oran-testbed-integration"
)

ADAPTER = (
    REPO
    / "scripts"
    / "experiment-harness"
    / "adapters"
    / "prompt12-siso-traffic.sh"
)

CAPTURE = (
    REPO
    / "scripts"
    / "experiment-harness"
    / "capture-iperf-receiver.py"
)


class Prompt12SisoTrafficCapturePathContractTest(
    unittest.TestCase
):
    def test_source_derives_capture_path_from_script_location(self):
        text = ADAPTER.read_text(encoding="utf-8")

        self.assertIn(
            'PROMPT12_HARNESS_DIR="$(',
            text,
        )
        self.assertIn(
            'PROMPT12_CAPTURE_SCRIPT="${PROMPT12_HARNESS_DIR}/capture-iperf-receiver.py"',
            text,
        )
        self.assertNotIn(
            'PROMPT12_CAPTURE_SCRIPT="scripts/experiment-harness/capture-iperf-receiver.py"',
            text,
        )

    def test_plan_is_cwd_independent_and_uses_absolute_capture_path(self):
        with tempfile.TemporaryDirectory() as cwd:
            result = subprocess.run(
                [
                    str(ADAPTER),
                    "plan",
                    "prompt12-test-receiver",
                    "10",
                    "/tmp/prompt12-test.raw",
                    "/tmp/prompt12-test.timestamps",
                    "/tmp/prompt12-test.stderr",
                ],
                cwd=cwd,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

        self.assertEqual(
            result.returncode,
            0,
            msg=result.stderr,
        )

        self.assertIn(
            str(CAPTURE),
            result.stdout,
        )

        self.assertNotIn(
            " scripts/experiment-harness/capture-iperf-receiver.py",
            result.stdout,
        )

    def test_capture_script_exists_at_derived_repository_location(self):
        self.assertTrue(CAPTURE.is_file())


if __name__ == "__main__":
    unittest.main()
