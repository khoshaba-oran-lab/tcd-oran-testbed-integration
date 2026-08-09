# Sci_O-RAN Controlled Traffic Experiments

## 1. Purpose

This document defines the traffic-experiment methodology and Experiment Registry conventions for the Sci_O-RAN project.

It also records the status of the preliminary exploratory downlink traffic characterization performed before the unified observability and experiment-acquisition framework was established.

The primary experiment registry is:

`experiments/registry.csv`

The objective is not to infer a falsely precise system-capacity threshold from incomplete exploratory data. The preliminary result is treated as evidence of a transition or queueing-onset region that requires subsequent controlled experimentation.

---

## 2. Evidence discipline

Experimental information is classified using the following evidence states:

- `FACT` — directly supported by preserved raw evidence and sufficient experiment metadata.
- `FACT_PARTIAL` — directly supported observations exist, but the experiment record is incomplete.
- `HYPOTHESIS` — an interpretation consistent with available evidence but requiring additional controlled validation.
- `ASSUMPTION` — an unverified condition that must not be treated as a scientific result.

A traffic rate, UTC window, protocol parameter, packet size, loss value, jitter value, or system-capacity statement must not be reconstructed as a fact unless it can be traced to retained evidence.

---

## 3. Legacy exploratory traffic characterization

### 3.1 Status

Preliminary downlink traffic characterization was performed before the current Sci_O-RAN experiment metadata and unified observability conventions were established.

The exploratory work included tests approximately in the region of:

- 0.5 Mbit/s;
- 1 Mbit/s;
- 2 Mbit/s;
- 3 Mbit/s;
- 3.5 Mbit/s;
- 4 Mbit/s;

including repeated measurements near the upper part of the explored range.

These nominal rates describe the historical experimental intent. They are not assigned to individual legacy telemetry episodes unless a direct evidence link exists.

### 3.2 Preserved raw evidence

A historical native gNB telemetry capture was recovered from temporary storage and preserved locally as:

`datasets/legacy-exploratory-20260808/raw/tb3-native-metrics-experiment.log`

SHA-256:

`9f4d206758377bc76cde9dd60c834f617076a04e2987ea6fa5c743d8199c470b`

The original capture contains the explicit session marker:

`EXPERIMENT_SESSION_START_UTC=2026-08-08T09:02:52.305905619`

The preserved file contains 5463 telemetry samples.

### 3.3 Recoverable observations

Analysis of the preserved telemetry capture established the following directly observable facts:

- 69 telemetry samples contain non-zero downlink bitrate;
- 21 telemetry samples contain `dl_bs > 0`;
- the maximum observed `dl_bs` value is 1234 bytes;
- no sample with `dl_nok > 0` was identified in this capture;
- seven separated downlink activity episodes can be identified using a gap-based segmentation heuristic.

The seven episodes are evidence of separated downlink activity periods. They are not treated as seven fully reconstructed experiments.

### 3.4 Legacy evidence gap

The legacy material does not provide a complete reproducible mapping between each downlink activity episode and:

- the intended traffic rate;
- exact `iperf3` command;
- protocol configuration;
- packet size;
- exact traffic-generator start and end timestamps;
- complete `iperf3` throughput result;
- packet loss;
- jitter;
- synchronized host-resource measurements;
- synchronized container-resource measurements;
- synchronized network measurements.

Therefore the historical series is classified as `FACT_PARTIAL`.

No individual historical episode is assigned a structured rate-specific experiment ID such as:

`EXP-20260808-DL-03500K-R02`

unless such mapping can be demonstrated from preserved raw evidence.

The legacy session is represented in the registry by:

`EXP-20260808-DL-LEGACY-R00`

### 3.5 Interpretation

The legacy experiments are retained as exploratory evidence only.

They must not be used to claim an exact saturation threshold or exact system capacity.

The scientifically appropriate preliminary interpretation is that the exploratory tests identified a transition or queueing-onset region in the upper part of the tested downlink-load range.

Subsequent experiments must characterize that region using controlled, repeatable measurements and the unified Sci_O-RAN observability framework.

---

## 4. Experiment identifier convention

Controlled downlink traffic experiments use the format:

`EXP-YYYYMMDD-DL-RRRRRK-RNN`

where:

- `YYYYMMDD` is the UTC experiment date;
- `DL` identifies downlink traffic;
- `RRRRR` is the target traffic rate in kbit/s, zero-padded where useful;
- `RNN` is the repeat number.

Example:

`EXP-20260808-DL-03500K-R02`

The same `experiment_id` must be used consistently across:

- Experiment Registry records;
- experiment manifests;
- raw-data directories;
- processed datasets;
- derived datasets;
- analysis outputs;
- documentation;
- archival dataset releases.

---

## 5. Minimum controlled-experiment record

Each new controlled traffic experiment must record at least:

- experiment ID;
- experiment status;
- UTC date;
- traffic direction;
- transport protocol;
- target traffic rate;
- repeat number;
- exact UTC start timestamp;
- exact UTC end timestamp;
- configured duration;
- packet size;
- complete traffic-generator command;
- measured throughput;
- packet loss;
- jitter where applicable;
- native gNB telemetry interval;
- relevant native gNB metrics;
- `dl_bs` behaviour;
- `dl_nok` behaviour;
- raw traffic-generator output location;
- raw native gNB telemetry location;
- raw host-observability location;
- raw container-observability location;
- raw network-observability location;
- evidence status;
- experimental conclusion;
- relevant limitations or anomalies.

---

## 6. Unified observability requirement

The next controlled experiment series must not reproduce the legacy limitation of collecting only partial telemetry.

For each experiment, the acquisition window should collect synchronized or timestamp-alignable evidence from the following sources.

### 6.1 Traffic generator

The exact traffic-generator configuration and output must be retained, including:

- direction;
- protocol;
- target rate;
- packet size;
- duration;
- achieved throughput;
- packet loss;
- jitter where available.

### 6.2 Native gNB telemetry

Relevant native gNB observations include, where applicable:

- downlink bitrate;
- `dl_bs`;
- `dl_nof_ok`;
- `dl_nof_nok`;
- MCS;
- CQI;
- relevant uplink measurements required for context;
- telemetry timestamps;
- telemetry receive timing.

### 6.3 Host observability

The controlled acquisition framework should include:

- total CPU utilization;
- per-core CPU utilization;
- load average;
- CPU frequency;
- memory utilization.

### 6.4 Container observability

Relevant containers should be monitored for:

- CPU utilization;
- memory utilization;
- network receive/transmit statistics;
- relevant runtime state.

### 6.5 Network observability

Relevant network measurements should include, where applicable:

- interface throughput;
- packet drops;
- interface errors;
- RTT;
- latency statistics;
- P50/P95/P99 values where scientifically appropriate.

---

## 7. Raw-data traceability

Raw measurements must be retained without modification.

The conceptual data flow is:

`raw -> processed -> derived`

Every processed or derived result must retain a traceable relationship to:

`experiment_id -> raw files -> processing procedure -> result`

Large raw files are intentionally excluded from Git.

Git stores lightweight metadata, documentation, schemas, checksums, scripts, and archival references.

Scientifically relevant datasets should subsequently be packaged as immutable versioned archival releases, with Zenodo as the intended archival platform unless another repository is justified.

---

## 8. Transition-region methodology

The current exploratory evidence does not justify publication of a precise capacity value.

The next experimental series should instead determine whether repeated controlled observations support a transition from:

1. low-load operation with no persistent downlink queue;

to:

2. an intermediate region with intermittent queue formation;

to:

3. sustained queue formation under higher offered load.

The transition should be assessed using repeated experiments and synchronized observability rather than a single traffic-generator result.

Any later capacity or saturation estimate must state:

- the experimental definition used;
- the observation interval;
- the repeatability criterion;
- the relevant queueing criterion;
- loss behaviour;
- system-resource state;
- software and configuration provenance.

---

## 9. Current conclusion

The preliminary traffic-characterization phase is retained as scientifically useful exploratory evidence, but it is not considered a complete reproducible controlled experiment series.

The historical native telemetry capture has been preserved and registered as partial evidence.

No false precision is introduced for missing historical parameters.

The next traffic experiments will use structured experiment IDs, exact UTC windows, preserved traffic-generator outputs, native gNB telemetry, and synchronized host, container, and network observability.
