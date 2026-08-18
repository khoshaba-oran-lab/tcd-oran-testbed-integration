# Sci_O-RAN Datasets

This directory defines the dataset architecture and archival references for Sci_O-RAN experiments.

Large experimental datasets are not stored directly in Git.

## Dataset principles

Every scientific dataset must remain traceable to the experiment or experiments that produced it.

The project distinguishes three data levels:

    raw -> processed -> derived

### Raw data

Raw data are measurements captured directly from experimental tools or system components.

Raw data must be preserved without modification whenever they are retained as scientific evidence.

Examples may include:

- gNB telemetry;
- UE and gNB runtime logs;
- host resource measurements;
- container measurements;
- network measurements;
- latency measurements;
- traffic-generator outputs;
- packet captures where required.

### Processed data

Processed data are produced by deterministic transformations of raw data.

Examples may include:

- normalized timestamps;
- parsed telemetry records;
- synchronized measurement streams;
- filtered records;
- converted file formats.

Processing must not overwrite the original raw data.

### Derived data

Derived data contain quantities calculated from raw or processed measurements.

Examples may include:

- P50, P95, and P99 latency;
- throughput summaries;
- resource-utilization statistics;
- model-identification inputs;
- controller-performance metrics;
- aggregated experiment statistics.

Every derived artifact must be traceable to its source data and processing procedure.

## Dataset identity

A released or archived dataset must have a stable dataset identifier.

The recommended identifier format is:

    DS-YYYYMMDD-NNN-short-name

A dataset may reference one or more experiment IDs.

Experiment IDs remain the primary link between experimental execution and stored research data.

## Minimum dataset metadata

Each dataset record should eventually include at least:

- dataset ID;
- title;
- dataset version;
- creation timestamp in UTC;
- related experiment IDs;
- data level: raw, processed, or derived;
- schema version;
- file inventory;
- checksums;
- processing provenance where applicable;
- software or script references used for transformation;
- validation status;
- known limitations;
- archival location;
- DOI when released through Zenodo or another archival repository.

## Storage model

GitHub stores:

- dataset specifications;
- schemas;
- lightweight metadata;
- dataset registry records;
- checksums;
- processing scripts;
- archival references.

Large research files remain outside Git.

The repository `.gitignore` intentionally excludes common runtime and dataset formats such as CSV, JSONL, Parquet, PCAP, and log files.

## Archival releases

Scientifically relevant datasets should be packaged as immutable versioned releases.

Zenodo is the intended archival platform unless another repository is justified for a specific dataset.

A release should contain enough information to establish:

    dataset -> experiment -> configuration -> software -> raw evidence

where applicable.

## Integrity

Released files should have cryptographic checksums, preferably SHA-256.

Checksums must refer to the exact files included in the archival release.

## Sensitive information

Raw artifacts must be reviewed before publication.

Potentially sensitive material may include:

- credentials or authentication material;
- environment-specific configuration;
- internal network information;
- identifiers not intended for public release;
- container environment variables;
- operational logs containing unintended sensitive values.

Publication review must not alter the retained scientific raw copy. If redaction is required, the redacted publication artifact must be treated as a separate derived or release artifact.

## Current status

The unified dataset architecture is being established during Phase 2 of Sci_O-RAN.

No dataset should be described as reproducible or publication-ready solely because files have been collected.

## Version-controlled dataset records

Lightweight dataset registry records are stored under:

    datasets/records/<dataset_id>/

Each dataset directory represents one stable dataset identity and may contain
versioned metadata, artifact inventories, checksum references, processing
provenance, validation records, and archival references.

For example:

    datasets/records/DS-20260817-001-r03-prb-actuation/

Large raw, processed, or derived scientific payloads are not copied into this
directory merely to place them under Git version control. Their immutable
archival payload remains outside Git and is linked through artifact identity,
byte size, SHA-256 checksum, provenance metadata, and, after publication, the
archival record and DOI.

The detailed metadata record under `datasets/records/<dataset_id>/` serves as
the GitHub dataset registry record. A separate `datasets/registry.csv` is not
required by the current Sci_O-RAN dataset specification.
