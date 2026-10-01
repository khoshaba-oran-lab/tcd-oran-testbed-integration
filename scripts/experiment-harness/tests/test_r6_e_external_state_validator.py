#!/usr/bin/env python3

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
HARNESS = HERE.parent

SCHEMA = (
    HARNESS
    / "r6-e-external-state-reference.schema.json"
)

VALIDATOR = (
    HARNESS
    / "r6-e-external-state-validator.py"
)


def base_record():
    return {
        "schema_version": "1.0.0",
        "record_type": (
            "sci_oran_r6e_external_state_reference_v1"
        ),
        "record_id": "r6e-test-record-001",
        "host": "tb3-dell",
        "absolute_path": (
            "/home/khoshaba/sci-oran-evidence/example"
        ),
        "artifact_class": (
            "VM_LOCAL_ACQUISITION_STATE"
        ),
        "logical_role": "test acquisition evidence",
        "existence_expectation": "PRESENT",
        "liveness_expectation": "NOT_REQUIRED",
        "liveness_state": "NOT_APPLICABLE",
        "retention_state": "ACQUISITION",
        "disposition": "KEEP",
        "blocking_classification": "NOT_BLOCKING",
        "provenance_note": (
            "Synthetic unit-test record only."
        )
    }


class R6EExternalStateValidatorTests(unittest.TestCase):
    def run_record(
        self,
        record,
        expected_host=None,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            record_path = tmpdir / "record.json"

            record_path.write_text(
                json.dumps(
                    record,
                    indent=2,
                    sort_keys=True,
                ),
                encoding="utf-8",
            )

            cmd = [
                sys.executable,
                str(VALIDATOR),
                "--schema",
                str(SCHEMA),
                "--record",
                str(record_path),
            ]

            if expected_host is not None:
                cmd.extend(
                    [
                        "--expected-host",
                        expected_host,
                    ]
                )

            return subprocess.run(
                cmd,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

    def assert_pass(self, record, expected_host=None):
        result = self.run_record(
            record,
            expected_host=expected_host,
        )

        self.assertEqual(
            result.returncode,
            0,
            msg=(
                result.stdout
                + "\n"
                + result.stderr
            ),
        )

        self.assertIn(
            "R6_E_EXTERNAL_STATE_VALIDATION=PASS",
            result.stdout,
        )

    def assert_fail(self, record):
        result = self.run_record(record)

        self.assertNotEqual(
            result.returncode,
            0,
        )

        self.assertIn(
            "R6_E_EXTERNAL_STATE_VALIDATION=FAIL",
            result.stdout,
        )

        return result

    def test_valid_record(self):
        self.assert_pass(
            base_record(),
            expected_host="tb3-dell",
        )

    def test_missing_host_rejected(self):
        record = base_record()
        del record["host"]
        self.assert_fail(record)

    def test_relative_path_rejected(self):
        record = base_record()
        record["absolute_path"] = "relative/path"
        self.assert_fail(record)

    def test_unknown_class_rejected(self):
        record = base_record()
        record["artifact_class"] = "UNKNOWN_CLASS"
        self.assert_fail(record)

    def test_invalid_sha256_rejected(self):
        record = base_record()
        record["object_sha256"] = "not-a-sha256"
        self.assert_fail(record)

    def test_path_presence_does_not_prove_liveness(self):
        record = base_record()
        record["artifact_class"] = (
            "PERSISTENT_EXTERNAL_OPERATIONAL_STATE"
        )
        record["liveness_expectation"] = "REQUIRED"
        record["liveness_state"] = "LIVE"
        record["liveness_evidence"] = {
            "path_present": True,
            "admission_metadata_present": False,
            "live_process_confirmed": False,
            "open_file_or_fifo_confirmed": False,
            "current_control_plane_evidence": False
        }

        result = self.assert_fail(record)

        self.assertIn(
            "LIVE_STATE_REQUIRES_CURRENT_STRONG_LIVENESS_EVIDENCE",
            result.stdout,
        )

    def test_admission_only_does_not_prove_liveness(self):
        record = base_record()
        record["artifact_class"] = (
            "PERSISTENT_EXTERNAL_OPERATIONAL_STATE"
        )
        record["liveness_expectation"] = "REQUIRED"
        record["liveness_state"] = "LIVE"
        record["liveness_evidence"] = {
            "path_present": True,
            "admission_metadata_present": True,
            "live_process_confirmed": False,
            "open_file_or_fifo_confirmed": False,
            "current_control_plane_evidence": False
        }

        result = self.assert_fail(record)

        self.assertIn(
            "LIVE_STATE_REQUIRES_CURRENT_STRONG_LIVENESS_EVIDENCE",
            result.stdout,
        )

    def test_live_process_can_prove_liveness(self):
        record = base_record()
        record["artifact_class"] = (
            "PERSISTENT_EXTERNAL_OPERATIONAL_STATE"
        )
        record["liveness_expectation"] = "REQUIRED"
        record["liveness_state"] = "LIVE"
        record["liveness_evidence"] = {
            "path_present": True,
            "admission_metadata_present": True,
            "live_process_confirmed": True,
            "open_file_or_fifo_confirmed": False,
            "current_control_plane_evidence": False,
            "process_id": 1234,
            "process_start_identity": "synthetic-start-id"
        }

        self.assert_pass(record)

    def test_historical_path_supported(self):
        record = base_record()
        record["artifact_class"] = (
            "LEGACY_OR_HISTORICAL_EXTERNAL_STATE"
        )
        record["existence_expectation"] = (
            "HISTORICAL_ONLY"
        )
        record["liveness_expectation"] = (
            "NOT_REQUIRED"
        )
        record["liveness_state"] = (
            "NOT_APPLICABLE"
        )
        record["retention_state"] = "LEGACY"
        record["disposition"] = "PRESERVE"
        record["original_historical_path"] = (
            "/home/khoshaba/old-evidence/run-001"
        )

        self.assert_pass(record)

    def test_retained_state_requires_identity(self):
        record = base_record()
        record["artifact_class"] = (
            "AUTHORITATIVE_RETAINED_EVIDENCE"
        )
        record["retention_state"] = "RETAINED"
        record["disposition"] = "RETAIN"

        self.assert_fail(record)

    def test_retained_state_with_object_sha_passes(self):
        record = base_record()
        record["artifact_class"] = (
            "AUTHORITATIVE_RETAINED_EVIDENCE"
        )
        record["retention_state"] = "RETAINED"
        record["disposition"] = "RETAIN"
        record["object_sha256"] = "a" * 64

        self.assert_pass(record)

    def test_stale_runtime_cannot_be_live(self):
        record = base_record()
        record["artifact_class"] = (
            "STALE_PRESERVED_RUNTIME_RESIDUE"
        )
        record["liveness_expectation"] = "NOT_REQUIRED"
        record["liveness_state"] = "LIVE"
        record["liveness_evidence"] = {
            "live_process_confirmed": True
        }

        result = self.assert_fail(record)

        self.assertIn(
            "STALE_CLASS_CANNOT_BE_LIVE",
            result.stdout,
        )

    def test_absent_reference_class_requires_absent_semantics(self):
        record = base_record()
        record["artifact_class"] = (
            "STALE_OR_HISTORICAL_REFERENCE_TARGET_ABSENT"
        )
        record["existence_expectation"] = "PRESENT"
        record["liveness_state"] = "NOT_LIVE"

        self.assert_fail(record)

    def test_expected_host_binding(self):
        record = base_record()

        result = self.run_record(
            record,
            expected_host="coll.vntu.org",
        )

        self.assertNotEqual(
            result.returncode,
            0,
        )

        self.assertIn(
            "HOST_BINDING_MISMATCH",
            result.stdout,
        )

    def test_validation_does_not_mutate_external_state(self):
        record = base_record()

        with tempfile.TemporaryDirectory() as tmp:
            sentinel = Path(tmp) / "sentinel"
            sentinel.write_text(
                "UNCHANGED\n",
                encoding="utf-8",
            )

            record["absolute_path"] = str(sentinel)

            before = sentinel.read_bytes()

            result = self.run_record(record)

            after = sentinel.read_bytes()

            self.assertEqual(
                result.returncode,
                0,
                msg=result.stdout + result.stderr,
            )

            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
