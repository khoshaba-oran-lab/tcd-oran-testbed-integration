#!/usr/bin/env python3
"""Strict tcd.kpm.record.emulator-draft-0.1 JSONL to typed Parquet converter."""

from __future__ import annotations

import argparse
import csv
import errno
import hashlib
import json
import math
import os
from pathlib import Path
import sys
from typing import Any, Iterable

import pyarrow as pa
import pyarrow.parquet as pq

SCHEMA_VERSION = "tcd.kpm.record.emulator-draft-0.1"
CONVERTER_VERSION = "collector03-sw-prototype-emulator-draft-0.1"
DEFAULT_CATALOGUE = Path("/opt/tcd-kpm/schema/canonical-record-emulator-draft-0.1.tsv")
DEFAULT_MAX_ROWS = 1_000_000
DEFAULT_BATCH_ROWS = 4096

UINT32_MAX = (1 << 32) - 1
UINT64_MAX = (1 << 64) - 1
INT64_MIN = -(1 << 63)
INT64_MAX = (1 << 63) - 1

ARROW_TYPES = {
    "string": pa.string(),
    "enum": pa.string(),
    "uint64": pa.uint64(),
    "uint32": pa.uint32(),
    "boolean": pa.bool_(),
    "int64": pa.int64(),
    "float64": pa.float64(),
}

STRUCTURAL_STATUSES = {
    "ok",
    "no_value",
    "length_mismatch",
    "invalid_input",
    "unsupported_ue_id",
    "unsupported_descriptor",
    "unsupported_value_type",
}
DESCRIPTOR_TYPES = {"name", "id", "unknown"}
VALUE_TYPES = {"integer", "real", "no_value", "unknown"}
RECORD_KINDS = {"measurement", "diagnostic"}


class ConversionError(ValueError):
    """Raised for deterministic input or conversion contract violations."""


def fail(message: str) -> None:
    raise ConversionError(message)


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            fail(f"duplicate field: {key}")
        result[key] = value
    return result


def reject_constant(token: str) -> None:
    fail(f"non-finite JSON number: {token}")


def load_catalogue(path: Path) -> list[dict[str, Any]]:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
    except OSError as exc:
        fail(f"cannot read catalogue {path}: {exc}")

    if len(rows) != 28:
        fail(f"catalogue field count must be 28, found {len(rows)}")

    fields: list[dict[str, Any]] = []
    seen: set[str] = set()
    for expected_ordinal, row in enumerate(rows, start=1):
        try:
            ordinal = int(row["ordinal"])
            name = row["field_name"]
            logical_type = row["logical_type"]
            nullable_token = row["nullable"]
        except (KeyError, TypeError, ValueError) as exc:
            fail(f"invalid catalogue row {expected_ordinal}: {exc}")

        if ordinal != expected_ordinal:
            fail("catalogue ordinals are not contiguous")
        if not name or name in seen:
            fail(f"invalid or duplicate catalogue field: {name!r}")
        if logical_type not in ARROW_TYPES:
            fail(f"unsupported logical type for {name}: {logical_type}")
        if nullable_token not in {"yes", "no"}:
            fail(f"invalid nullable token for {name}: {nullable_token}")

        seen.add(name)
        fields.append(
            {
                "name": name,
                "logical_type": logical_type,
                "nullable": nullable_token == "yes",
            }
        )

    if fields[0]["name"] != "schema_version":
        fail("schema_version must be the first canonical field")
    return fields


def validate_scalar(name: str, logical_type: str, nullable: bool, value: Any) -> Any:
    if value is None:
        if not nullable:
            fail(f"field {name} is not nullable")
        return None

    if logical_type in {"string", "enum"}:
        if not isinstance(value, str):
            fail(f"field {name} must be a string")
        return value

    if logical_type == "boolean":
        if not isinstance(value, bool):
            fail(f"field {name} must be a boolean")
        return value

    if logical_type in {"uint32", "uint64", "int64"}:
        if isinstance(value, bool) or not isinstance(value, int):
            fail(f"field {name} must be an integer")
        if logical_type == "uint32" and not 0 <= value <= UINT32_MAX:
            fail(f"field {name} is outside uint32 range")
        if logical_type == "uint64" and not 0 <= value <= UINT64_MAX:
            fail(f"field {name} is outside uint64 range")
        if logical_type == "int64" and not INT64_MIN <= value <= INT64_MAX:
            fail(f"field {name} is outside int64 range")
        return value

    if logical_type == "float64":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            fail(f"field {name} must be numeric")
        converted = float(value)
        if not math.isfinite(converted):
            fail(f"field {name} must be finite")
        return converted

    fail(f"field {name} has unsupported logical type {logical_type}")


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def validate_semantics(row: dict[str, Any]) -> None:
    require(row["schema_version"] == SCHEMA_VERSION, "schema_version mismatch")
    require(row["record_kind"] in RECORD_KINDS, "invalid record_kind")
    require(row["structural_status"] in STRUCTURAL_STATUSES, "invalid structural_status")
    require(row["descriptor_type"] in DESCRIPTOR_TYPES, "invalid descriptor_type")
    require(row["value_type"] in VALUE_TYPES, "invalid value_type")
    require(bool(row["ue_id_type"]), "ue_id_type must not be empty")

    if not row["incomplete_flag_present"]:
        require(row["incomplete_flag"] is None, "absent incomplete flag must be null")
    else:
        require(row["incomplete_flag"] is not None, "present incomplete flag must have a value")

    if row["record_kind"] == "diagnostic":
        require(row["meas_info_index"] is None, "diagnostic meas_info_index must be null")
        require(row["meas_record_index"] is None, "diagnostic meas_record_index must be null")
        require(row["descriptor_type"] == "unknown", "diagnostic descriptor_type must be unknown")
        require(row["value_type"] == "unknown", "diagnostic value_type must be unknown")
        require(row["measurement_name"] is None, "diagnostic measurement_name must be null")
        require(row["measurement_id"] is None, "diagnostic measurement_id must be null")
        require(row["integer_value"] is None, "diagnostic integer_value must be null")
        require(row["real_value"] is None, "diagnostic real_value must be null")
        require(row["diagnostic_code"] is not None, "diagnostic_code must be present")
        require(row["diagnostic_message"] is not None, "diagnostic_message must be present")
        if row["structural_status"] == "length_mismatch":
            require(
                row["meas_info_lst_len"] != row["meas_record_len"],
                "length_mismatch diagnostic requires unequal lengths",
            )
        return

    require(row["meas_info_index"] is not None, "measurement meas_info_index must be present")
    require(row["meas_record_index"] is not None, "measurement meas_record_index must be present")
    require(
        row["meas_info_index"] == row["meas_record_index"],
        "measurement metadata and record indexes must match",
    )
    require(row["diagnostic_code"] is None, "measurement diagnostic_code must be null")
    require(row["diagnostic_message"] is None, "measurement diagnostic_message must be null")

    if row["descriptor_type"] == "name":
        require(row["measurement_name"] is not None, "name descriptor requires measurement_name")
        require(row["measurement_id"] is None, "name descriptor requires null measurement_id")
    elif row["descriptor_type"] == "id":
        require(row["measurement_id"] is not None, "id descriptor requires measurement_id")
        require(row["measurement_name"] is None, "id descriptor requires null measurement_name")
    else:
        fail("measurement descriptor_type must be name or id")

    if row["value_type"] == "integer":
        require(row["integer_value"] is not None, "integer value requires integer_value")
        require(row["real_value"] is None, "integer value requires null real_value")
    elif row["value_type"] == "real":
        require(row["real_value"] is not None, "real value requires real_value")
        require(row["integer_value"] is None, "real value requires null integer_value")
    elif row["value_type"] == "no_value":
        require(row["integer_value"] is None, "no_value requires null integer_value")
        require(row["real_value"] is None, "no_value requires null real_value")
    else:
        fail("measurement value_type must be integer, real, or no_value")


def parse_row(line: str, line_number: int, fields: list[dict[str, Any]]) -> dict[str, Any]:
    try:
        raw = json.loads(
            line,
            object_pairs_hook=strict_object,
            parse_constant=reject_constant,
        )
    except (json.JSONDecodeError, ConversionError) as exc:
        fail(f"line {line_number}: invalid JSON: {exc}")

    if not isinstance(raw, dict):
        fail(f"line {line_number}: record must be a JSON object")

    expected_names = [field["name"] for field in fields]
    expected_set = set(expected_names)
    actual_set = set(raw)
    missing = sorted(expected_set - actual_set)
    unknown = sorted(actual_set - expected_set)
    if missing:
        fail(f"line {line_number}: missing fields: {','.join(missing)}")
    if unknown:
        fail(f"line {line_number}: unknown fields: {','.join(unknown)}")

    row: dict[str, Any] = {}
    for field in fields:
        name = field["name"]
        row[name] = validate_scalar(
            name,
            field["logical_type"],
            field["nullable"],
            raw[name],
        )

    try:
        validate_semantics(row)
    except ConversionError as exc:
        fail(f"line {line_number}: {exc}")
    return row


def inspect_source(
    input_path: Path,
    fields: list[dict[str, Any]],
    max_rows: int,
) -> tuple[str, int]:
    digest = hashlib.sha256()
    row_count = 0

    try:
        with input_path.open("rb") as handle:
            for line_number, raw_line in enumerate(handle, start=1):
                digest.update(raw_line)
                try:
                    line = raw_line.decode("utf-8")
                except UnicodeDecodeError as exc:
                    fail(f"line {line_number}: input is not UTF-8: {exc}")
                if not line.strip():
                    fail(f"line {line_number}: blank lines are not allowed")
                parse_row(line, line_number, fields)
                row_count += 1
                if row_count > max_rows:
                    fail(f"row count exceeds configured maximum {max_rows}")
    except OSError as exc:
        fail(f"cannot read input {input_path}: {exc}")

    if row_count == 0:
        fail("input contains no canonical records")
    return digest.hexdigest(), row_count


def iter_rows(input_path: Path, fields: list[dict[str, Any]]) -> Iterable[dict[str, Any]]:
    with input_path.open("r", encoding="utf-8", newline="") as handle:
        for line_number, line in enumerate(handle, start=1):
            yield parse_row(line, line_number, fields)


def build_schema(
    fields: list[dict[str, Any]],
    source_sha256: str,
    row_count: int,
) -> pa.Schema:
    arrow_fields = [
        pa.field(
            field["name"],
            ARROW_TYPES[field["logical_type"]],
            nullable=field["nullable"],
        )
        for field in fields
    ]
    metadata = {
        b"tcd.schema_version": SCHEMA_VERSION.encode("ascii"),
        b"tcd.converter_version": CONVERTER_VERSION.encode("ascii"),
        b"tcd.source_sha256": source_sha256.encode("ascii"),
        b"tcd.row_count": str(row_count).encode("ascii"),
        b"tcd.pyarrow_version": pa.__version__.encode("ascii"),
    }
    return pa.schema(arrow_fields, metadata=metadata)


def write_batch(
    writer: pq.ParquetWriter,
    schema: pa.Schema,
    field_names: list[str],
    rows: list[dict[str, Any]],
) -> None:
    columns = {name: [row[name] for row in rows] for name in field_names}
    table = pa.Table.from_pydict(columns, schema=schema)
    writer.write_table(table, row_group_size=len(rows))


def fsync_file(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        try:
            os.fsync(descriptor)
        except OSError as exc:
            if exc.errno not in {errno.EINVAL, errno.EROFS}:
                raise
    finally:
        os.close(descriptor)


def convert(
    input_path: Path,
    output_path: Path,
    catalogue_path: Path,
    max_rows: int,
    batch_rows: int,
    compression: str | None,
) -> tuple[str, int]:
    if max_rows < 1:
        fail("max_rows must be positive")
    if batch_rows < 1:
        fail("batch_rows must be positive")
    if input_path.resolve() == output_path.resolve():
        fail("input and output paths must differ")
    if not output_path.parent.is_dir():
        fail(f"output parent directory does not exist: {output_path.parent}")

    fields = load_catalogue(catalogue_path)
    source_sha256, row_count = inspect_source(input_path, fields, max_rows)
    schema = build_schema(fields, source_sha256, row_count)
    field_names = [field["name"] for field in fields]

    temporary_path = output_path.with_name(f"{output_path.name}.tmp.{os.getpid()}")
    if temporary_path.exists():
        fail(f"temporary path already exists: {temporary_path}")

    writer: pq.ParquetWriter | None = None
    try:
        writer = pq.ParquetWriter(
            temporary_path,
            schema,
            compression=compression,
            use_dictionary=False,
            write_statistics=True,
            version="2.6",
            data_page_version="1.0",
        )
        batch: list[dict[str, Any]] = []
        for row in iter_rows(input_path, fields):
            batch.append(row)
            if len(batch) == batch_rows:
                write_batch(writer, schema, field_names, batch)
                batch.clear()
        if batch:
            write_batch(writer, schema, field_names, batch)
        writer.close()
        writer = None

        fsync_file(temporary_path)
        os.replace(temporary_path, output_path)
        fsync_directory(output_path.parent)
    except Exception:
        if writer is not None:
            try:
                writer.close()
            except Exception:
                pass
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass
        raise

    return source_sha256, row_count


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert strict tcd.kpm.record.emulator-draft-0.1 JSONL to typed Parquet",
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--catalogue", type=Path, default=DEFAULT_CATALOGUE)
    parser.add_argument("--max-rows", type=int, default=DEFAULT_MAX_ROWS)
    parser.add_argument("--batch-rows", type=int, default=DEFAULT_BATCH_ROWS)
    parser.add_argument(
        "--compression",
        choices=("none", "snappy", "gzip", "brotli", "lz4", "zstd"),
        default="zstd",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    compression = None if args.compression == "none" else args.compression
    try:
        source_sha256, row_count = convert(
            args.input,
            args.output,
            args.catalogue,
            args.max_rows,
            args.batch_rows,
            compression,
        )
    except Exception as exc:
        print(f"PARQUET_CONVERTER=FAIL\nERROR={exc}", file=sys.stderr)
        return 1

    print("PARQUET_CONVERTER=PASS")
    print(f"SCHEMA_VERSION={SCHEMA_VERSION}")
    print(f"SOURCE_SHA256={source_sha256}")
    print(f"ROW_COUNT={row_count}")
    print(f"PYARROW_VERSION={pa.__version__}")
    print(f"OUTPUT={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
