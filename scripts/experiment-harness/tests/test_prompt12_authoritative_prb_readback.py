import importlib.util
import pathlib
import unittest


REPO = pathlib.Path(__file__).resolve().parents[3]

TOOL = (
    REPO
    / "scripts/experiment-harness"
    / "prompt12-authoritative-prb-readback.py"
)

CONTRACT = (
    REPO
    / "experiments/manifests"
    / "prompt12-authoritative-prb-readback-contract-v1.json"
)

spec = importlib.util.spec_from_file_location(
    "prompt12_authoritative_prb_readback",
    TOOL,
)

module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class AuthoritativePrbReadbackTest(
    unittest.TestCase
):
    def test_source_contract(self):
        self.assertEqual(
            module.AUTHORITATIVE_LOG_PATH,
            "/tmp/gnb.log",
        )

        self.assertEqual(
            module.AUTHORITATIVE_SOURCE,
            "CONTAINER:/tmp/gnb.log",
        )

        self.assertFalse(
            module.DOCKER_LOGS_IS_AUTHORITATIVE
        )

    def test_j31_regression_case(self):
        text = "\n".join(
            [
                (
                    "2026-10-04T07:18:11.369385 "
                    "[SCHED   ] [I] "
                    "PRB_ACTUATOR_APPLIED "
                    "ue=0 rnti=0x4601 cell=0 "
                    "applied_min_prbs=0 "
                    "applied_max_prbs=275"
                ),
                (
                    "2026-10-04T09:18:27.644785 "
                    "[SCHED   ] [I] "
                    "PRB_ACTUATOR_APPLIED "
                    "ue=0 rnti=0x4601 cell=0 "
                    "applied_min_prbs=0 "
                    "applied_max_prbs=26"
                ),
            ]
        )

        markers = module.parse_markers(text)

        result = module.evaluate_markers(
            markers,
            module.parse_time(
                "2026-10-04T09:18:20"
            ),
            module.parse_time(
                "2026-10-04T09:19:30"
            ),
            0,
            26,
        )

        self.assertEqual(
            result["gate"],
            "PASS",
        )

        self.assertEqual(
            result["expected_marker_count"],
            1,
        )

        self.assertEqual(
            result["selected"][
                "applied_min_prbs"
            ],
            0,
        )

        self.assertEqual(
            result["selected"][
                "applied_max_prbs"
            ],
            26,
        )

    def test_missing_expected_marker_fails(self):
        text = (
            "2026-10-04T09:18:27.644785 "
            "PRB_ACTUATOR_APPLIED "
            "applied_min_prbs=0 "
            "applied_max_prbs=39"
        )

        result = module.evaluate_markers(
            module.parse_markers(text),
            module.parse_time(
                "2026-10-04T09:18:20"
            ),
            module.parse_time(
                "2026-10-04T09:19:30"
            ),
            0,
            26,
        )

        self.assertEqual(
            result["gate"],
            "FAIL_NOT_FOUND",
        )

    def test_duplicate_expected_marker_fails_closed(self):
        line = (
            "2026-10-04T09:18:27.644785 "
            "PRB_ACTUATOR_APPLIED "
            "applied_min_prbs=0 "
            "applied_max_prbs=26"
        )

        result = module.evaluate_markers(
            module.parse_markers(
                line + "\n" + line
            ),
            module.parse_time(
                "2026-10-04T09:18:20"
            ),
            module.parse_time(
                "2026-10-04T09:19:30"
            ),
            0,
            26,
        )

        self.assertEqual(
            result["gate"],
            "FAIL_AMBIGUOUS",
        )

    def test_contract_exists(self):
        self.assertTrue(
            CONTRACT.is_file()
        )


if __name__ == "__main__":
    unittest.main()
