# COLLECTOR-02 KPM length-mismatch contract

## Status

- Contract version: 1
- Stage: `COLLECTOR-02`
- Scope: defensive validation before KPM measurement normalisation
- Baseline: closed `COLLECTOR-01`; its tracked files and behaviour are not modified by this contract

## Purpose

This contract defines how the collector validates the positional relationship between KPM measurement metadata and the measurement values in each decoded measurement-data row before producing normalised telemetry.

The observed motivating case had:

- `meas_info_lst_len = 2`
- `meas_record_len = 4`

The collector must not index the two-element metadata list with indices derived from the four-element measurement-record list.

## Terminology

For one decoded KPM indication and one measurement-data row:

- `metadata_len`: the number of authoritative measurement descriptors available for positional pairing;
- `record_len`: the row's `meas_record_len`;
- `normalised_value_count`: the number of labelled values emitted from that row.

An authoritative metadata list is either:

1. the measurement-info list carried by the indication; or
2. a separately retained, validated mapping from the applicable subscription/action definition.

Absence of an authoritative metadata list is not silently converted into an empty or synthetic list.

## Classification

### `ok`

Conditions:

- authoritative metadata is available;
- `metadata_len > 0`;
- `record_len > 0`;
- `metadata_len == record_len`;
- required pointers and elements are valid.

Result: all values in the row may proceed to type validation and normalisation.

### `length_mismatch`

Conditions:

- authoritative metadata is available;
- `metadata_len > 0`;
- `record_len > 0`;
- `metadata_len != record_len`.

Result: reject the current measurement-data row before positional pairing.

### `metadata_unavailable`

Conditions:

- `record_len > 0`; and
- no authoritative metadata list can be resolved.

Result: reject the current measurement-data row because values cannot be labelled safely. This state is distinct from `length_mismatch`.

### `invalid_record_length`

Conditions:

- `record_len == 0`; or
- `record_len` violates the decoded structure's supported bounds.

Result: reject the current measurement-data row before normalisation.

## Mandatory defensive behaviour

For every rejected row, the collector shall:

1. perform no read from either list at an index outside that list;
2. emit no normalised measurement values from the rejected row;
3. avoid partial positional pairing;
4. avoid silent truncation to `min(metadata_len, record_len)`;
5. avoid padding or inventing labels or values;
6. emit one deterministic structured diagnostic for the rejected row;
7. increment the corresponding rejection counter;
8. continue processing later rows and later indications;
9. avoid process termination, assertion failure, memory corruption, or undefined behaviour.

A malformed row must not prevent a subsequent valid indication from being processed.

## Required diagnostic fields

When available, a rejection diagnostic shall include:

- validation status;
- KPM indication format;
- node identity;
- subscription/request identity;
- indication sequence identity;
- measurement-data row index;
- `metadata_len`;
- `record_len`;
- collector timestamp.

Missing optional identity fields shall not prevent the validation result from being emitted.

## Required counters

At minimum, COLLECTOR-02 shall make these cumulative counters observable:

- accepted measurement-data rows;
- rejected measurement-data rows;
- `length_mismatch` rows;
- `metadata_unavailable` rows;
- `invalid_record_length` rows.

## Normalisation boundary

Length validation precedes value normalisation. Type conversion, unit handling, missing-value representation, and output serialisation are permitted only after the row has status `ok`.

## Rejection granularity

The unit of rejection is one measurement-data row. Other independently valid rows in the same indication may be processed, provided their validation does not depend on corrupted or untrusted shared state.

## Out of scope for this contract

- modifying FlexRIC decoder behaviour;
- modifying the closed COLLECTOR-01 baseline;
- silently repairing malformed producer data;
- hardware-specific KPM semantics;
- deciding final CSV, JSON, Parquet, or Prometheus schemas.

## Acceptance obligations

Implementation is acceptable only when automated tests demonstrate:

1. equal non-zero lengths produce all expected labelled values;
2. `2` metadata entries and `4` record entries produce `length_mismatch`, zero output values, and no crash;
3. `4` metadata entries and `2` record entries produce `length_mismatch`, zero output values, and no crash;
4. unavailable metadata produces `metadata_unavailable`, not `length_mismatch`;
5. zero record length produces `invalid_record_length`;
6. a valid indication following a rejected indication is processed successfully;
7. sanitiser-enabled execution reports no out-of-bounds access attributable to these cases.
