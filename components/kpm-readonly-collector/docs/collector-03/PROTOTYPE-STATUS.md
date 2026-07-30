# COLLECTOR-03 software prototype status

~~text
COLLECTOR-03-SW-PROTOTYPE=IN_PROGRESS
COLLECTOR-03-SW=NOT_ACCEPTED
NORMALISED-SCHEMA-V1=NOT_FROZEN
REAL-GATE-01=PENDING
REAL-GATE-02=PENDING
~~

## Current schema classification

~~text
SCHEMA_IDENTIFIER=tcd.kpm.record.emulator-draft-0.1
SCHEMA_STATUS=EMULATOR_DERIVED_DRAFT
SCHEMA_FREEZE_STATE=NOT_FROZEN
SCHEMA_ACCEPTANCE_STATE=NOT_ACCEPTED
SOURCE_BASIS=SOFTWARE_EMULATOR_ONLY
~~

The current record definition exists to support implementation experiments,
serialization tests, replay preparation, and output-backend prototyping.

It does not provide an external compatibility guarantee and may change after
real-node telemetry is obtained and characterised.

## Permitted work before schema freeze

- correction of implementation defects;
- non-schema-binding refactoring;
- prototype output-backend experiments;
- preparation of raw-output and normalised-output interfaces;
- preparation of software-manifest and experiment-manifest interfaces;
- preservation of reproducible software-only tests.

## Not permitted before schema freeze

- declaring the current schema to be normalised schema v1;
- accepting `COLLECTOR-03-SW`;
- claiming compatibility with a real E2 node;
- treating emulator-derived measurement semantics as final;
- publishing stable field or compatibility guarantees.

## Missing acceptance requirements

- `HW-INFO-01`;
- `HW-CONTRACT-01`;
- `REAL-GATE-01`;
- completion of full `COLLECTOR-02-SW`;
- `REAL-GATE-02`;
- formal normalised schema v1 freeze;
- complete raw/normalised output separation;
- experiment manifest;
- software manifest;
- `TEST-01`;
- `REAL-GATE-03`.
