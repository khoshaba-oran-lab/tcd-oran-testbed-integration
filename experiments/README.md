# Sci_O-RAN Experiments

This directory contains lightweight metadata required to reproduce and trace Sci_O-RAN experiments.

Large raw datasets and runtime artifacts are not stored directly in Git.

## Experiment workflow

Each significant experiment follows the project workflow:

> experiment -> validation -> raw data -> metadata -> documentation -> Git commit -> next experiment

An experiment must not be treated as complete until its raw data and metadata have been preserved.

## Experiment identity

Every reproducible experiment must have a unique `experiment_id`.

The recommended identifier format is:

    EXP-YYYYMMDD-NNN-short-name

Example:

    EXP-20260808-001-dl-load

The identifier must remain unchanged across:

- experiment metadata;
- raw-data directories;
- derived datasets;
- analysis outputs;
- documentation;
- dataset releases.

## Directory roles

- `manifests/` - metadata for individual experiment runs.
- `schemas/` - machine-readable experiment and dataset schemas.
- `examples/` - documented example manifests and reference experiment layouts.

## Minimum experiment metadata

A reproducible experiment manifest should record at least:

- `experiment_id`;
- experiment purpose;
- experiment status;
- UTC start timestamp;
- UTC end timestamp;
- Tb3 host/environment reference;
- Git commit or working-tree state;
- software/version references;
- Docker image tags and digests where applicable;
- configuration references and checksums;
- traffic-generator parameters;
- actuator/input parameters where applicable;
- telemetry sources;
- raw-data locations;
- validation result;
- known failures or exclusions;
- notes required to reproduce the run.

## Evidence status

Experiment conclusions should distinguish:

- `FACT` - directly supported by collected evidence;
- `HYPOTHESIS` - interpretation consistent with the evidence but requiring further validation;
- `ASSUMPTION` - unverified condition that must not be treated as a scientific result.

## Raw and derived data

Raw measurements should be preserved without modification.

Processing should produce separate derived artifacts rather than replacing raw data.

The expected conceptual separation is:

    raw -> processed -> derived

Each derived artifact must be traceable to its source experiment and processing procedure.

## Git and archival storage

Git stores lightweight experiment metadata, schemas, documentation, scripts, configuration references, and checksums.

Large experimental datasets should remain outside Git and, when scientifically relevant, be packaged as versioned archival releases such as Zenodo datasets.

A dataset release should retain references to the experiment IDs from which it was produced.

## Current status

The experiment metadata architecture is being established during Phase 2 of the Sci_O-RAN project.

The presence of an experiment manifest or dataset reference does not by itself imply that the experiment has been scientifically validated.
