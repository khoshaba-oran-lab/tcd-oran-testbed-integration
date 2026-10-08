import importlib.util
import pathlib
import tempfile
import unittest


BASE = pathlib.Path(__file__).resolve().parents[1]
HANDOFF = BASE / "prompt12-bounded-precontrol-handoff.py"
FRESHNESS = BASE / "prompt12-precontrol-freshness.py"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PrecontrolOutputSplitTests(unittest.TestCase):

    def test_real_freshness_exclusive_output_contract(self):
        handoff = load_module("p12_handoff_split", HANDOFF)
        freshness = load_module("p12_freshness_split", FRESHNESS)

        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            precheck = root / "stationarity.precheck.json"
            official = root / "stationarity.json"
            candidate = root / "precontrol.candidate.json"

            handoff.write_text_exclusive(
                precheck,
                '{"output_stationarity_gate":"PASS"}\n',
            )

            self.assertTrue(precheck.is_file())
            self.assertFalse(official.exists())

            freshness.ensure_output_absent(str(official))

            with self.assertRaises(freshness.FreshnessError):
                freshness.ensure_output_absent(str(precheck))

            template = [
                "--input",
                handoff.STATIONARITY_JSON_TOKEN,
                "--stationarity-output",
                handoff.STATIONARITY_JSON_TOKEN,
                "--output",
                handoff.PRECONTROL_JSON_TOKEN,
                "--decision-utc-ns",
                handoff.DECISION_UTC_NS_TOKEN,
            ]

            command = handoff.resolve_freshness_command(
                template,
                precheck,
                candidate,
                123456789,
                freshness_stationarity_path=official,
            )

            self.assertEqual(command[1], str(precheck))
            self.assertEqual(command[3], str(official))
            self.assertEqual(command[5], str(candidate))
            self.assertEqual(command[7], "123456789")

            legacy = handoff.resolve_freshness_command(
                [
                    "--input",
                    handoff.STATIONARITY_JSON_TOKEN,
                ],
                precheck,
                candidate,
                123456789,
            )
            self.assertEqual(legacy[1], str(precheck))

            with official.open("x", encoding="utf-8") as stream:
                stream.write('{"output_stationarity_gate":"PASS"}\n')

            self.assertTrue(official.is_file())
            self.assertNotEqual(
                precheck.read_bytes(),
                b"",
            )
            self.assertNotEqual(precheck, official)

            with self.assertRaises(FileExistsError):
                official.open("x")

    def test_handoff_wires_distinct_output_paths(self):
        source = HANDOFF.read_text(encoding="utf-8")

        self.assertIn(
            'attempt / "stationarity.precheck.json"',
            source,
        )
        self.assertIn(
            'attempt / "stationarity.json"',
            source,
        )
        self.assertIn(
            "        stationarity_path,\n"
            "        candidate_path,",
            source,
        )


if __name__ == "__main__":
    unittest.main()
