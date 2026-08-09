# Sci_O-RAN Research Roadmap

This document defines the high-level research sequence for the Sci_O-RAN experimental platform.

The roadmap is intentionally gate-driven. Later control-oriented phases must not begin until the required experimental evidence from earlier phases exists.

## Research principles

The project follows these principles:

1. Experimental results must be reproducible.
2. Experimental facts, working hypotheses, and assumptions requiring verification must be distinguished explicitly.
3. Raw data must be preserved before derived processing.
4. Every significant experiment must have sufficient metadata to reconstruct its conditions.
5. Documentation and data management are continuous parts of the experimental workflow.
6. Additional experiments should be performed only when they answer a new scientific question or reduce a material uncertainty.
7. PID and MPC work must not begin before runtime actuation and system identification have been demonstrated.

The standard workflow is:

> experiment -> validation -> raw data -> metadata -> documentation -> Git commit -> next experiment

---

## Phase 1 — Baseline and Initial Validation

### WP1 — Tb3 baseline

Establish a stable and reproducible experimental baseline on Tb3.

**Status:** DONE

### WP2 — User-plane validation

Demonstrate working user-plane traffic through the experimental 5GS path.

**Status:** DONE

### WP3 — Native gNB telemetry

Acquire native gNB metrics without assuming metric semantics from names alone.

**Status:** PARTIAL

### WP4 — Telemetry semantics

Determine the meaning, units, update behaviour, and limitations of relevant telemetry fields using implementation evidence, documentation, and controlled experiments.

**Status:** PARTIAL

### WP5 — Failure and recovery analysis

Characterize relevant failure and recovery behaviour and preserve forensic evidence.

**Status:** PARTIAL

### WP6 — Preliminary traffic characterization

Identify useful operating regions and observable load effects without unnecessarily over-refining thresholds during the exploratory stage.

**Status:** DONE

---

## Phase 2 — Documentation, Data and Resource Observability

### WP7 — GitHub documentation

Transform the repository into a documented research repository with explicit architecture, methodology, provenance, status, and decision records.

**Status:** IN PROGRESS

### WP8 — Software and environment manifest

Record the software, host, configuration, source, and runtime environment needed to reproduce experiments.

**Status:** NOT STARTED

### WP9 — Docker reproducibility

Record Docker image provenance using appropriate tags, source locks, build information, and immutable digests where applicable.

**Status:** NOT STARTED

### WP10 — Unified dataset architecture

Define common dataset conventions, schemas, metadata, raw/processed/derived separation, checksums, and archival references.

**Status:** NOT STARTED

### WP11 — Host observability

Collect host-level measurements including CPU, per-core CPU, load average, CPU frequency, and memory utilization.

**Status:** NOT STARTED

### WP12 — Container observability

Collect container-level CPU, memory, and network resource measurements.

**Status:** NOT STARTED

### WP13 — Network observability

Collect network throughput, packet drops, errors, RTT, and relevant latency statistics.

**Status:** NOT STARTED

### WP14 — Reproducible experiment harness

Develop a repeatable experiment execution workflow that coordinates traffic generation, telemetry collection, timestamps, metadata, and artifact storage.

**Status:** NOT STARTED

---

## Phase 3 — Controlled Dataset Acquisition

### WP15 — Dataset acquisition

Acquire synchronized experimental datasets using the reproducible experiment harness.

**Status:** NOT STARTED

### WP16 — Repeatability and statistics

Repeat controlled experiments and quantify variability, dispersion, and confidence in observed effects.

**Status:** NOT STARTED

### WP17 — End-to-end latency

Establish an E2E latency methodology including appropriate percentile statistics such as P50, P95, and P99.

**Status:** NOT STARTED

---

## Phase 4 — Runtime Actuation Gate

### WP18 — Runtime actuator discovery

Identify a parameter that can be changed during runtime and can influence a measurable system output.

**Status:** NOT STARTED

### WP19 — Actuation Gate

The project may proceed to control-system identification only if runtime actuation is experimentally demonstrated.

The gate requires evidence that:

1. the actuator can be changed reproducibly during operation;
2. the applied input value is known and logged;
3. a measurable output responds to the actuator;
4. the response is sufficiently repeatable for identification;
5. relevant constraints and safe operating limits are known.

**Status:** BLOCKED

---

## Phase 5 — SISO System Identification and Control

### WP20-WP23 — SISO identification and PID

The SISO phase includes:

- selection of an actuator-output pair;
- excitation experiment design;
- dynamic model identification;
- model validation;
- PID design;
- closed-loop evaluation.

This phase must compare model predictions with independent experimental data.

**Status:** BLOCKED

---

## Phase 6 — MIMO and Predictive Control

### WP24-WP27 — MIMO, multivariable PID, and MPC

Extend the validated control problem to multiple interacting inputs and outputs where experimentally justified.

The phase may include:

- interaction analysis;
- MIMO system identification;
- multivariable control;
- constrained MPC;
- comparative controller evaluation.

MIMO complexity must not be introduced unless experimental evidence demonstrates meaningful coupling between variables.

**Status:** BLOCKED

---

## Phase 7 — O-RAN Validation

### WP28 — O-RAN E2SM-KPM validation

Validate relevant O-RAN telemetry paths and E2SM-KPM measurements against independently observable system behaviour where possible.

The existence of a reported KPM metric must not by itself be treated as proof of semantic correctness.

**Status:** NOT STARTED

---

## Phase 8 — Comparative Evaluation and Research Release

### WP29-WP34

The final research phase includes:

- comparative experiments;
- controller and baseline comparison;
- dataset release preparation;
- software archival release;
- Zenodo dataset and technical-report releases where appropriate;
- reproducibility audit;
- limitations analysis;
- scientific publication.

**Status:** NOT STARTED

---

## Cross-cutting reproducibility requirements

The following requirements apply throughout all phases:

- unique experiment IDs;
- UTC timestamps;
- source and software version provenance;
- configuration provenance;
- Docker image tags and digests where applicable;
- input-condition records;
- raw-data preservation;
- metadata validation;
- checksums for released artifacts;
- explicit derived-data provenance;
- documented failures and exclusions;
- Git commits corresponding to reproducible research states.

GitHub is the primary repository for code, configurations, lightweight metadata, manifests, and documentation.

Large experimental datasets and archival research artifacts should be published separately through an archival service such as Zenodo and referenced from the repository.

---

## Current transition

The project has completed the exploratory baseline and traffic-characterization stage sufficiently to proceed.

The current priority is:

**Phase 2 — Documentation, Data and Resource Observability**

The project must not advance to controller development merely because telemetry is available. The next scientific prerequisite for control work is a reproducible observability and experiment-acquisition environment, followed by demonstrated runtime actuation and system identification.
