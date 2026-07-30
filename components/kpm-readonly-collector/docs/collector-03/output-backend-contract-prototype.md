# COLLECTOR-03 software prototype output backend contract

> **Status:** Software prototype only. The canonical record is derived from emulator evidence, is not frozen, and is not an accepted schema v1. REAL-GATE-01 and REAL-GATE-02 remain pending.

## 1. Scope

This contract defines output behaviour for the read-only KPM collector after
COLLECTOR-02A-SW defensive validation baseline. It does not alter subscription semantics,
E2 control behaviour, or the callback's validation policy.

The canonical row schema is `tcd.kpm.record.emulator-draft-0.1`. Every record is classified as
either:

- `measurement`: a validated metadata/value pair; or
- `diagnostic`: one rejected structural row represented once without partial
  metadata/value pairing.

## 2. Architectural invariant

The FlexRIC callback MUST NOT perform file, network, compression, Parquet, or
Prometheus exposition I/O.

The callback may only validate, normalise, and enqueue or retain a bounded
canonical record. Serialization and output occur outside the callback execution
path.

## 3. Selected backend architecture

### 3.1 CSV native streaming sink

- Implemented in C without a third-party runtime dependency.
- UTF-8, RFC 4180 escaping, one header row, LF line endings.
- Field order is exactly the ordinal order in `canonical-record-emulator-draft-0.1.tsv`.
- Null values are encoded as empty fields.
- Integers use decimal notation.
- Real values use the C locale, finite decimal notation, and no NaN or infinity.
- The sink writes complete rows only.
- Flush and close errors are observable through output counters and exit status.

### 3.2 JSONL native streaming sink

- Implemented in C without a third-party JSON library.
- UTF-8, one complete JSON object per LF-terminated line.
- Every canonical field is present.
- Nullable values are encoded as JSON `null`.
- Strings are escaped according to JSON rules.
- NaN and infinity are forbidden.
- Object key order follows `canonical-record-emulator-draft-0.1.tsv` for deterministic tests,
  although consumers MUST treat JSON object order as non-semantic.

### 3.3 Prometheus atomic textfile sink

- Implemented in C as Prometheus text exposition, not as an embedded HTTP
  server.
- A complete snapshot is written to a temporary file and atomically renamed to
  the configured `.prom` path.
- Metric names and bounded labels are defined in
  `prometheus-metrics-v1.tsv`.
- UE identifiers, node identifiers, measurement names, measurement IDs, and
  free-form diagnostic text MUST NOT be Prometheus labels.
- The textfile contains aggregate collector health and output counters only.
- An HTTP exporter or node-exporter textfile collector may publish the file
  outside the collector process.

### 3.4 Parquet pinned offline converter

- The collector executable does not link Arrow or Parquet libraries.
- Canonical JSONL is the source stream for Parquet conversion.
- Conversion runs as a separate bounded batch step in a pinned tool image.
- The converter MUST apply the logical types in `canonical-record-emulator-draft-0.1.tsv`.
- It MUST reject unknown fields, missing fields, NaN, infinity, schema-version
  mismatch, and rows that violate canonical invariants.
- Output is written to a temporary file and atomically renamed.
- Parquet acceptance is semantic: schema, row count, nullability, and field
  values MUST match the source JSONL. Byte-for-byte identity is not required.
- The tool image and PyArrow version MUST be pinned and recorded in evidence.

## 4. Canonical semantic invariants

1. `schema_version` is exactly `tcd.kpm.record.emulator-draft-0.1`.
2. A `diagnostic` record has `meas_info_index` and `meas_record_index` null.
3. A `length_mismatch` diagnostic has unequal
   `meas_info_lst_len` and `meas_record_len`.
4. Diagnostic records have `descriptor_type=unknown`,
   `value_type=unknown`, and all measurement value fields null.
5. A `measurement` record has non-null matching metadata and record indexes.
6. `descriptor_type=name` requires `measurement_name` and null
   `measurement_id`.
7. `descriptor_type=id` requires `measurement_id` and null
   `measurement_name`.
8. `value_type=integer` requires `integer_value` and null `real_value`.
9. `value_type=real` requires finite `real_value` and null `integer_value`.
10. `value_type=no_value` requires both value fields null.
11. `incomplete_flag_present=false` requires `incomplete_flag=null`.
12. No backend may silently truncate, partially pair, or drop a canonical field.

## 5. Failure policy

- Default policy: report the backend error, increment a bounded error counter,
  stop accepting new output for that failed sink, and permit lifecycle cleanup.
- A failed sink MUST NOT mutate or reinterpret canonical records for another
  sink.
- Backend failure MUST NOT cause E2 control operations.
- The process exit status MUST be non-zero when a configured durable sink could
  not be opened, completed, flushed, or closed.
- Prometheus snapshot failure is observable but does not rewrite CSV, JSONL, or
  Parquet content.

## 6. Determinism and provenance

Every output run records:

- collector Git commit;
- canonical schema version;
- enabled backends;
- output paths;
- row count per backend;
- rejected-row count;
- backend error count;
- source JSONL SHA-256 for Parquet conversion;
- Parquet converter image and PyArrow version.

## 7. Explicit exclusions

The COLLECTOR-03 software prototype does not provide:

- database insertion;
- remote object-store upload;
- embedded HTTP serving;
- per-UE or per-measurement Prometheus labels;
- callback-thread file or network I/O;
- schema inference from data values;
- automatic dependency installation on the host.
