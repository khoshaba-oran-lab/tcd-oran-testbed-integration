# Sci_O-RAN Documentation

This directory contains the research documentation for the Sci_O-RAN experimental platform.

Sci_O-RAN is used for reproducible investigation of 5GS/O-RAN telemetry, resource observability, system identification, and closed-loop control using SISO/MIMO models, PID, and MPC.

## Research workflow

The project follows the reproducibility workflow:

> experiment -> validation -> raw data -> metadata -> documentation -> Git commit -> next experiment

Experimental facts, working hypotheses, and assumptions requiring verification must be documented separately.

## Current documentation

- `architecture/` - system and testbed architecture.
- `audits/` - repository, deployment, and reproducibility audits.
- `decisions/` - architectural and research decision records.
- `runbooks/` - reproducible operational procedures.
- `vm/` - VM and host-related documentation.

## Planned documentation areas

The documentation architecture will progressively cover:

- project roadmap and research status;
- deployment and environment reproducibility;
- native gNB telemetry and telemetry semantics;
- user-plane validation;
- failure and recovery analysis;
- traffic characterization;
- host, container, and network observability;
- experiment methodology and dataset specification;
- runtime actuator discovery and the Actuation Gate;
- system identification;
- SISO and MIMO modelling;
- PID and MPC control;
- O-RAN E2SM-KPM validation;
- comparative experiments;
- reproducibility audit;
- limitations and known constraints.

## Data and experiment provenance

Large runtime artifacts and raw datasets are not stored directly in Git.

The repository stores code, configuration, documentation, schemas, manifests, checksums, and dataset references. Raw and processed research datasets intended for publication will be released through an archival repository such as Zenodo.

Each reproducible experiment should eventually be associated with:

- a unique experiment ID;
- UTC timestamps;
- software and configuration versions;
- Docker image tags and digests where applicable;
- input and traffic parameters;
- raw-data references;
- validation status;
- derived-data provenance.

## Repository status

Documentation is being expanded incrementally as part of the Sci_O-RAN research workflow. A directory or placeholder does not imply that the corresponding research work package has been completed.

## Project coordination

The current research roadmap and work-package status are maintained in:

- [`roadmap/project-roadmap.md`](roadmap/project-roadmap.md) - gate-driven research roadmap and phase dependencies.
- [`roadmap/project-status.md`](roadmap/project-status.md) - current work-package states, confirmed repository findings, and immediate priorities.

The roadmap defines the intended research sequence. The status document records the evidence-based state of the project at a particular point in time.
