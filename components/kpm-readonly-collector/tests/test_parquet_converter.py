#!/usr/bin/env python3
"""Container-level tests for the pinned canonical Parquet converter."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

CONVERTER = Path("/opt/tcd-kpm/bin/jsonl_to_parquet.py")
CATALOGUE = Path("/opt/tcd-kpm/schema/canonical-record-emulator-draft-0.1.tsv")
SCHEMA_VERSION = "tcd.kpm.record.emulator-draft-0.1"

TEST_COUNT = 9
PASSED = 0


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def base_record() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": "measurement",
        "indication_sequence": 1,
        "receive_timestamp_us": 1000001,
        "kpm_header_timestamp_us": None,
        "message_format": 3,
        "node_type": "gnb",
        "node_id": "001-01-000001",
        "ue_report_index": 0,
        "ue_id_type": "gnb_ue_id",
        "ue_id_value": "42",
        "meas_data_index": 0,
        "meas_info_index": 0,
        "meas_record_index": 0,
        "meas_data_lst_len": 1,
        "meas_info_lst_len": 2,
        "meas_record_len": 2,
        "incomplete_flag_present": False,
        "incomplete_flag": None,
        "structural_status": "ok",
        "descriptor_type": "name",
        "measurement_name": "DRB.UEThpDl",
        "measurement_id": None,
        "value_type": "integer",
        "integer_value": 125,
        "real_value": None,
        "diagnostic_code": None,
        "diagnostic_message": None,
    }


def valid_records() -> list[dict[str, Any]]:
    integer_record = base_record()

    real_record = base_record()
    real_record.update(
        {
            "indication_sequence": 2,
            "receive_timestamp_us": 1000002,
            "kpm_header_timestamp_us": 999999,
            "meas_info_index": 1,
            "meas_record_index": 1,
            "descriptor_type": "id",
            "measurement_name": None,
            "measurement_id": 7,
            "value_type": "real",
            "integer_value": None,
            "real_value": 12.5,
        }
    )

    diagnostic = base_record()
    diagnostic.update(
        {
            "record_kind": "diagnostic",
            "indication_sequence": 3,
            "receive_timestamp_us": 1000003,
            "ue_report_index": None,
            "ue_id_type": "unknown",
            "ue_id_value": None,
            "meas_info_index": None,
            "meas_record_index": None,
            "meas_info_lst_len": 2,
            "meas_record_len": 4,
            "structural_status": "length_mismatch",
            "descriptor_type": "unknown",
            "measurement_name": None,
            "measurement_id": None,
            "value_type": "unknown",
            "integer_value": None,
            "real_value": None,
            "diagnostic_code": "length_mismatch",
            "diagnostic_message": "metadata_len=2 record_len=4",
        }
    )
    return [integer_record, real_record, diagnostic]


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> bytes:
    data = b"".join(
        (json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        for record in records
    )
    path.write_bytes(data)
    return data


def run_converter(input_path: Path, output_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(CONVERTER),
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--catalogue",
            str(CATALOGUE),
            "--batch-rows",
            "2",
        ],
        text=True,
        capture_output=True,
        check=False,
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_no_temporary_files(directory: Path) -> None:
    leftovers = list(directory.glob("*.tmp.*"))
    check(not leftovers, f"temporary files remain: {leftovers}")


def test_valid_conversion() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        input_path = root / "input.jsonl"
        output_path = root / "output.parquet"
        records = valid_records()
        write_jsonl(input_path, records)

        result = run_converter(input_path, output_path)
        check(result.returncode == 0, result.stderr)
        check("PARQUET_CONVERTER=PASS" in result.stdout, result.stdout)

        table = pq.read_table(output_path)
        check(table.num_rows == 3, "unexpected row count")
        check(table.column_names == list(records[0]), "field order mismatch")
        check(table.column("integer_value").to_pylist() == [125, None, None], "integer values mismatch")
        check(table.column("real_value").to_pylist() == [None, 12.5, None], "real values mismatch")
        check(table.column("record_kind").to_pylist() == ["measurement", "measurement", "diagnostic"], "record kinds mismatch")
        assert_no_temporary_files(root)


def test_schema_and_metadata_provenance() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        input_path = root / "input.jsonl"
        output_path = root / "output.parquet"
        data = write_jsonl(input_path, valid_records())
        result = run_converter(input_path, output_path)
        check(result.returncode == 0, result.stderr)

        schema = pq.read_schema(output_path)
        expected_types = {
            "schema_version": pa.string(),
            "indication_sequence": pa.uint64(),
            "message_format": pa.uint32(),
            "incomplete_flag_present": pa.bool_(),
            "integer_value": pa.int64(),
            "real_value": pa.float64(),
        }
        for name, expected_type in expected_types.items():
            check(schema.field(name).type == expected_type, f"type mismatch for {name}")

        metadata = schema.metadata or {}
        check(metadata[b"tcd.schema_version"] == SCHEMA_VERSION.encode(), "schema metadata mismatch")
        check(metadata[b"tcd.row_count"] == b"3", "row count metadata mismatch")
        check(metadata[b"tcd.source_sha256"] == hashlib.sha256(data).hexdigest().encode(), "source hash metadata mismatch")
        check(metadata[b"tcd.pyarrow_version"] == pa.__version__.encode(), "PyArrow metadata mismatch")


def test_deterministic_semantics() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        input_path = root / "input.jsonl"
        first = root / "first.parquet"
        second = root / "second.parquet"
        write_jsonl(input_path, valid_records())

        first_result = run_converter(input_path, first)
        second_result = run_converter(input_path, second)
        check(first_result.returncode == 0, first_result.stderr)
        check(second_result.returncode == 0, second_result.stderr)
        check(pq.read_table(first).equals(pq.read_table(second)), "semantic Parquet outputs differ")
        check(pq.read_schema(first).metadata == pq.read_schema(second).metadata, "metadata differs")


def test_atomic_failure_preserves_target() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        input_path = root / "input.jsonl"
        output_path = root / "output.parquet"
        write_jsonl(input_path, valid_records())
        result = run_converter(input_path, output_path)
        check(result.returncode == 0, result.stderr)
        before = sha256(output_path)

        invalid = valid_records()
        invalid[0]["record_kind"] = "invalid"
        write_jsonl(input_path, invalid)
        failed = run_converter(input_path, output_path)
        check(failed.returncode != 0, "invalid conversion unexpectedly succeeded")
        check(sha256(output_path) == before, "existing target changed after failure")
        assert_no_temporary_files(root)


def test_unknown_and_missing_fields_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        output_path = root / "output.parquet"

        unknown = valid_records()
        unknown[0]["unknown_field"] = 1
        unknown_input = root / "unknown.jsonl"
        write_jsonl(unknown_input, unknown)
        result = run_converter(unknown_input, output_path)
        check(result.returncode != 0 and "unknown fields" in result.stderr, result.stderr)
        check(not output_path.exists(), "output created for unknown field")

        missing = valid_records()
        del missing[0]["node_id"]
        missing_input = root / "missing.jsonl"
        write_jsonl(missing_input, missing)
        result = run_converter(missing_input, output_path)
        check(result.returncode != 0 and "missing fields" in result.stderr, result.stderr)
        check(not output_path.exists(), "output created for missing field")


def test_schema_version_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        records = valid_records()
        records[0]["schema_version"] = "tcd.kpm.record.emulator-draft-0.2"
        input_path = root / "input.jsonl"
        output_path = root / "output.parquet"
        write_jsonl(input_path, records)
        result = run_converter(input_path, output_path)
        check(result.returncode != 0 and "schema_version mismatch" in result.stderr, result.stderr)
        check(not output_path.exists(), "output created for schema mismatch")


def test_semantic_invariant_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        records = valid_records()
        records[2]["meas_record_len"] = 2
        input_path = root / "input.jsonl"
        output_path = root / "output.parquet"
        write_jsonl(input_path, records)
        result = run_converter(input_path, output_path)
        check(result.returncode != 0 and "unequal lengths" in result.stderr, result.stderr)
        check(not output_path.exists(), "output created for invalid diagnostic")


def test_nonfinite_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        input_path = root / "input.jsonl"
        output_path = root / "output.parquet"
        record = valid_records()[1]
        line = json.dumps(record, separators=(",", ":")).replace("12.5", "NaN") + "\n"
        input_path.write_text(line, encoding="utf-8")
        result = run_converter(input_path, output_path)
        check(result.returncode != 0 and "non-finite JSON number" in result.stderr, result.stderr)
        check(not output_path.exists(), "output created for non-finite value")


def test_duplicate_key_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        input_path = root / "input.jsonl"
        output_path = root / "output.parquet"
        record = base_record()
        text = json.dumps(record, separators=(",", ":"))
        duplicate = text[:-1] + ',"node_id":"duplicate"}\n'
        input_path.write_text(duplicate, encoding="utf-8")
        result = run_converter(input_path, output_path)
        check(result.returncode != 0 and "duplicate field" in result.stderr, result.stderr)
        check(not output_path.exists(), "output created for duplicate field")


def run_test(name: str, function: Any) -> None:
    global PASSED
    function()
    PASSED += 1
    print(f"TEST {name} PASS")


def main() -> int:
    tests = [
        ("valid_conversion", test_valid_conversion),
        ("schema_and_metadata_provenance", test_schema_and_metadata_provenance),
        ("deterministic_semantics", test_deterministic_semantics),
        ("atomic_failure_preserves_target", test_atomic_failure_preserves_target),
        ("unknown_and_missing_fields_rejected", test_unknown_and_missing_fields_rejected),
        ("schema_version_rejected", test_schema_version_rejected),
        ("semantic_invariant_rejected", test_semantic_invariant_rejected),
        ("nonfinite_rejected", test_nonfinite_rejected),
        ("duplicate_key_rejected", test_duplicate_key_rejected),
    ]
    for name, function in tests:
        run_test(name, function)

    check(PASSED == TEST_COUNT, "test count mismatch")
    print(f"PARQUET_CONVERTER_TEST_COUNT={TEST_COUNT}")
    print(f"PARQUET_CONVERTER_TEST_PASS_COUNT={PASSED}")
    print("EXPLICIT_ARROW_SCHEMA=PASS")
    print("JSONL_FIELD_VALIDATION=PASS")
    print("CANONICAL_SEMANTIC_VALIDATION=PASS")
    print("PARQUET_SCHEMA_AND_NULLABILITY=PASS")
    print("SOURCE_PROVENANCE_METADATA=PASS")
    print("ATOMIC_OUTPUT_REPLACEMENT=PASS")
    print("TARGET_PRESERVED_ON_FAILURE=PASS")
    print("NONFINITE_NUMBER_REJECTION=PASS")
    print("PARQUET_CONVERTER_TEST_RESULT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
