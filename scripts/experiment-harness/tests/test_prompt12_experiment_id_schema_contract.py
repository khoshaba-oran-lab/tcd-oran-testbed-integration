import json
import pathlib
import unittest
from jsonschema import Draft202012Validator

SCHEMA = pathlib.Path(__file__).resolve().parents[3] / 'datasets/schemas/sci-oran-prompt12-siso-v1.0.0.schema.json'

class ExperimentIdSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(SCHEMA.read_text(encoding='utf-8'))
        Draft202012Validator.check_schema(cls.schema)

    def test_identity_range(self):
        v = Draft202012Validator(self.schema['$defs']['prompt12ExperimentId'])
        for n in (1, 4, 5, 9, 10, 99):
            self.assertTrue(v.is_valid(f'EXP-20261010-DL-18000K-R{n:02d}'))
        for bad in (
            'EXP-20261010-DL-18000K-R00',
            'EXP-20261010-DL-18000K-R100',
            'EXP-20261010-DL-18000K-R9'
        ):
            self.assertFalse(v.is_valid(bad))

    def test_legacy_conditions_preserved(self):
        self.assertEqual(len(self.schema['allOf']), 4)
        for n, branch in enumerate(self.schema['allOf'], 1):
            row = {
                'repeat_id': f'R{n:02d}',
                'experiment_id': f'EXP-20261010-DL-18000K-R{n:02d}',
                'model_use_class': 'holdout_validation' if n == 4 else 'estimation'
            }
            v = Draft202012Validator(branch)
            self.assertTrue(v.is_valid(row))
            self.assertFalse(v.is_valid({
                **row,
                'experiment_id': 'EXP-20261010-DL-18000K-R09'
            }))
            self.assertFalse(v.is_valid({
                **row,
                'model_use_class': 'invalid'
            }))

    def test_r09_does_not_match_legacy_conditions(self):
        row = {
            'repeat_id': 'R09',
            'experiment_id': 'EXP-20261010-DL-18000K-R09'
        }
        self.assertTrue(all(
            Draft202012Validator(b).is_valid(row)
            for b in self.schema['allOf']
        ))

if __name__ == '__main__':
    unittest.main(verbosity=2)
