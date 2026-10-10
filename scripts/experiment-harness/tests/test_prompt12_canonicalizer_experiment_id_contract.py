import ast
import pathlib
import re
import unittest

SOURCE = (
    pathlib.Path(__file__).resolve().parents[1]
    / "canonicalize-iperf-receiver.py"
)

class CanonicalizationError(Exception):
    pass

def load_actual_validator():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    selected = []
    required = {"EXPERIMENT_RE", "RUN_RE"}

    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = {
                target.id for target in node.targets
                if isinstance(target, ast.Name)
            }
            if names & required:
                selected.append(node)
                required -= names
        elif (
            isinstance(node, ast.FunctionDef)
            and node.name == "validate_identity"
        ):
            selected.append(node)

    if required or len(selected) != 3:
        raise AssertionError("VALIDATION_SOURCE_CONTRACT_CHANGED")

    namespace = {
        "re": re,
        "CanonicalizationError": CanonicalizationError,
    }

    module = ast.Module(body=selected, type_ignores=[])
    exec(compile(module, str(SOURCE), "exec"), namespace)

    return namespace["validate_identity"]

class ExperimentIDContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validate = staticmethod(load_actual_validator())

    def test_accepted_experiment_ids(self):
        for number in (1, 4, 5, 9, 10, 99):
            exp_id = f"EXP-20261010-DL-18000K-R{number:02d}"
            with self.subTest(experiment_id=exp_id):
                self.validate(
                    exp_id,
                    "RUN-20261010T172303Z-001",
                )

    def test_rejected_experiment_ids(self):
        invalid = (
            "EXP-20261010-DL-18000K-R00",
            "EXP-20261010-DL-18000K-R100",
            "EXP-20261010-DL-18000K-R9",
            "EXP-20261010-DL-19000K-R09",
            "EXP-20261010-T2-26TO39-DL-18000K-R09",
            "EXP-2026101-DL-18000K-R09",
        )
        for exp_id in invalid:
            with self.subTest(experiment_id=exp_id):
                with self.assertRaises(CanonicalizationError):
                    self.validate(
                        exp_id,
                        "RUN-20261010T172303Z-001",
                    )

    def test_run_id_validation_unchanged(self):
        with self.assertRaises(CanonicalizationError):
            self.validate(
                "EXP-20261010-DL-18000K-R09",
                "RUN-INVALID",
            )

if __name__ == "__main__":
    unittest.main(verbosity=2)
