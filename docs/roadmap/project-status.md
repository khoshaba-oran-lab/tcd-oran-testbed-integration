# Sci_O-RAN Project Status

**Status date:** 2026-08-14
**Repository:** `tcd-oran-testbed-integration`

## Status convention

The following states are used throughout the project:

- `NOT STARTED`
- `IN PROGRESS`
- `PARTIAL`
- `DONE`
- `BLOCKED`
- `DEFERRED`

A `DONE` state refers only to the explicitly defined scope of a work package and must not be interpreted as evidence that all related research questions have been resolved.

## Current work-package status

| WP | Work package | Status | Current interpretation |
|---|---|---|---|
| 1 | Tb3 baseline | DONE | Stable experimental baseline available for subsequent work |
| 2 | User-plane validation | DONE | User-plane operation has been validated for the current baseline |
| 3 | Native gNB telemetry | DONE | Native JSON telemetry path, transport, timestamps, receiver behaviour, metric semantics, and native dataset schema are documented |
| 4 | Telemetry semantics | DONE | Native gNB metric meanings, units, timing, and persistence semantics were validated against the exact runtime srsRAN source revision |
| 5 | Failure/recovery analysis | PARTIAL | Forensic artifacts exist; systematic analysis and documentation are incomplete |
| 6 | Preliminary traffic characterization | DONE | Exploratory traffic characterization completed; exact saturation threshold intentionally not over-refined |
| 7 | GitHub documentation | IN PROGRESS | Repository inventory completed sufficiently to begin documentation architecture |
| 8 | Software/environment manifest | DONE | Minimal Tb3 host and container-runtime provenance manifest established |
| 9 | Docker reproducibility | DONE | BASE-05 Sandy Bridge effective Compose images are recorded with immutable digests |
| 10 | Unified dataset | PARTIAL | Native gNB schema is defined; cross-source schema, synchronization, and remaining observability sources are not yet complete |
| 11 | Host observability | NOT STARTED | CPU, per-core CPU, load, frequency, and memory measurements remain to be integrated |
| 12 | Container observability | NOT STARTED | Container CPU, memory, and network measurements remain to be integrated |
| 13 | Network observability | NOT STARTED | Throughput, drops, errors, RTT, and percentile metrics remain to be integrated |
| 14 | Experiment harness | NOT STARTED | Reproducible experiment execution framework remains to be implemented |
| 15 | Dataset acquisition | NOT STARTED | Depends on experiment and dataset conventions |
| 16 | Repeatability and statistics | NOT STARTED | Requires stable acquisition procedures and repeated experiments |
| 17 | End-to-end latency | NOT STARTED | Unified latency methodology and percentile reporting remain to be established |
| 18 | Runtime actuator | NOT STARTED | A controllable runtime parameter with measurable system effect must be demonstrated |
| 19 | Actuation Gate | BLOCKED | Cannot be passed before runtime actuator validation |
| 20-23 | SISO identification and PID | BLOCKED | Requires validated actuation and system identification data |
| 24-27 | MIMO, PID, and MPC | BLOCKED | Requires preceding identification and control stages |
| 28 | O-RAN E2SM-KPM validation | NOT STARTED | Planned as a separate validation work package |
| 29-34 | Comparative experiments, releases, audit, publication | NOT STARTED | Final research and dissemination stages |

## Current research phase

The project is currently in:

**Phase 2 — Documentation, Data and Resource Observability**

The immediate priority is to establish reproducible documentation, experiment metadata conventions, environment provenance, and observability before beginning system-identification and controller-design experiments.

## Prompt 11B status

Prompt 11B — Comprehensive Read-Only Testbed Doctor has completed its
implementation and validation scope.

Confirmed results include:

- `DOCTOR_READ_ONLY_GATE=PASS`;
- all principal infrastructure and runtime readiness gates passed;
- `USER_PLANE_READINESS_GATE=PASS`;
- `TRAFFIC_HARNESS_READINESS_GATE=PASS`;
- `PROCESS_CONTINUITY_GATE=PASS`;
- `READINESS_ARTIFACT_GATE=PASS`;
- `READINESS_FRESHNESS_GATE=PASS`;
- `READINESS_ARTIFACT_FINALIZATION_GATE=PASS`;
- final `SCI_ORAN_READY_GATE=PASS`;
- final `FAILURE_REASON=NONE`;
- experiment preflight integration propagates the doctor result;
- negative-path validation demonstrates fail-closed behaviour.

Canonical Prompt 11B documentation is maintained in
`docs/11b-sci-oran-readiness-doctor.md`.

Prompt 11B does not by itself constitute runtime actuator validation and
must not be inferred from `SCI_ORAN_READY_GATE=PASS`. The subsequent
Prompt 11R.42 runtime-control experiment is summarized in the final-status
section below.

## Confirmed repository findings

The repository inventory established the following facts:

- Docker and Docker Compose deployment materials are already present.
- gNB and UE configurations are tracked for the BASE-05 ZMQ baseline.
- deployment-specific source and runtime lock files already exist.
- `kpm-readonly-collector` is a substantive software component rather than a placeholder.
- `experiments/manifests/`, `experiments/schemas/`, and `experiments/examples/` currently contain only placeholder structure in Git.
- large runtime artifacts and common dataset formats are intentionally excluded from Git.
- forensic runtime artifacts exist locally under `artifacts/`.
- repository-level Sandy Bridge scripts are wrappers for deployment-specific implementations and are not duplicate copies.
- Tb3 BASE-05 architecture and native gNB telemetry are preserved in remote checkpoint `0616298b149a0a4b13f6651aa67e7ac18628bf61` on branch `feat/tb3-dell-reproducibility`.
- the validated BASE-05 gNB configuration excludes the native metrics server; native gNB telemetry is treated as a separate observability configuration and must not modify the BASE-05 runtime baseline.
- on 2026-08-11, a controlled A/B recovery test showed that the HEAD-only `metrics:` block was the gNB configuration delta associated with failed initial access; restoring the `f04a55b` gNB configuration restored RACH, RRC, PDU session establishment, `tun_srsue = 10.45.1.2/24`, and `0% packet loss` to `10.45.1.1`.
- the native-metrics receiver and compact-parser helper scripts are tracked and preserved in the remote Git branch.

## Evidence discipline

Project documentation must explicitly distinguish:

### Experimental facts

Statements directly supported by observed outputs, stored artifacts, source code, configuration files, or controlled experiments.

### Working hypotheses

Interpretations consistent with available evidence but not yet independently demonstrated.

### Assumptions requiring verification

Statements that must not be used as scientific conclusions until verified.

Metric names, configuration parameter names, or script status labels must not by themselves be treated as proof of physical or protocol semantics.

## Control-system gate

PID or MPC implementation must not begin until:

1. a runtime actuator has been identified;
2. the actuator can be changed reproducibly during operation;
3. its effect on measurable outputs has been demonstrated;
4. sufficient input-output data exist for system identification;
5. the resulting model has been validated.

## Immediate priorities

1. Complete the current repository documentation and provenance checkpoint.
2. Add host, container, and network observability with a unified time base.
3. Complete experiment IDs, manifests, and cross-source dataset conventions.
4. Build a reproducible experiment harness.
5. Acquire repeatable synchronized datasets.
6. Proceed to runtime actuator discovery and system identification only after the observability/data gates are satisfied.

## Documentation rule

Documentation and data management are continuous parts of the experimental workflow:

> experiment -> validation -> raw data -> metadata -> documentation -> Git commit -> next experiment

## Prompt 11R.42 final status

Prompt 11R.42 completed an exactly-one corrected E2SM-RC PRB25 runtime
control experiment on 2026-08-16.

Proven experimental results:

- RUNTIME_CONTROL_EXECUTION=PROVEN;
- U_CMD=PROVEN;
- U_ACK=PROVEN;
- POST_CONTROL_NO_RESTART=PROVEN;
- POST_CONTROL_E2_ASSOCIATION_CONTINUITY=PROVEN;
- EXACTLY_ONE_LIVE_CONTROL_EXPERIMENT=PASS.

Remaining evidence limitations:

- DIRECT_ACTUATOR_READBACK=UNAVAILABLE;
- PLANT_RESPONSE_AT_8MBIT=INCONCLUSIVE;
- NATIVE_TELEMETRY=UNAVAILABLE_IN_CURRENT_RUNTIME;
- KPM_RUNTIME_CAPTURE=UNAVAILABLE_IN_CURRENT_SESSION.

Final gate classification:

- OPERATIONAL_RUNTIME_ACTUATION_GATE=NOT_PASSED;
- STRICT_ORIGINAL_ACTUATION_GATE=NOT_PASSED;
- FINAL_ACTUATION_GATE_CLASSIFICATION=CLOSED_NOT_PASSED.

System identification, PID, and MPC remain prohibited until the missing
applied-state, plant-response, and telemetry evidence is resolved.

Authoritative evidence:

/home/khoshaba/sci-oran-evidence/action11r/2026-08-16-live-control-prb25/actuation-gate-classification.env

SHA256:
e15b4a1ec3776d3c4a4ccf6756402838c325a290981508d4374427567250d40e
