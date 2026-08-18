# Sci_O-RAN Unified Dataset Specification

## 1. Purpose and scope

This document defines the canonical dataset architecture for controlled
Sci_O-RAN experiments.

Its purpose is to establish a scientifically traceable representation of
measurements collected from heterogeneous observability sources while
preserving the semantics and provenance of the original evidence.

The unified dataset is intended to support:

- controlled traffic experiments;
- host, container, and network observability;
- native gNB telemetry;
- UE and 5GC observability;
- O-RAN KPM measurements;
- future actuator command and readback measurements;
- system-identification experiments;
- closed-loop control experiments;
- reproducible scientific analysis and archival dataset releases.

The specification follows the existing Sci_O-RAN data model:

    raw -> processed -> derived

Raw scientific evidence is immutable.

Processed and derived artifacts must remain traceable to the exact raw inputs
and deterministic procedures from which they were produced.

---

## 2. Identity model

### 2.1 Experiment identity

`experiment_id` is the primary scientific identifier of a controlled
experimental execution.

For the currently defined controlled downlink traffic experiments, the
canonical format remains:

    EXP-YYYYMMDD-DL-RRRRRK-RNN

Example:

    EXP-20260808-DL-03500K-R02

Its components have the established meanings:

- `YYYYMMDD` -- UTC experiment date;
- `DL` -- downlink traffic direction;
- `RRRRR` -- target offered traffic rate in kbit/s;
- `RNN` -- controlled repeat number.

The existing identifier convention shall not be replaced by a second
incompatible convention.

The same `experiment_id` shall be propagated across:

- experiment registry records;
- experiment manifests;
- acquisition runs;
- raw-data directories;
- processed datasets;
- derived datasets;
- analysis outputs;
- documentation;
- archival dataset releases.

Legacy exploratory evidence retains its already assigned identifier, for
example:

    EXP-20260808-DL-LEGACY-R00

No historical evidence shall be retrospectively assigned a more specific
experiment identity unless the mapping can be demonstrated from retained raw
evidence.

### 2.2 Run identity

`run_id` identifies one actual invocation of the experimental acquisition or
execution workflow.

The canonical format is:

    RUN-YYYYMMDDTHHMMSSZ-NNN

where:

- `YYYYMMDDTHHMMSSZ` is the UTC start time of the run at one-second
  resolution;
- `NNN` is a zero-padded sequence used to disambiguate multiple run
  invocations starting within the same second or repeated operational
  attempts.

Example:

    RUN-20260809T141530Z-001

`experiment_id` and `run_id` have different scientific functions.

`experiment_id` identifies the controlled scientific experiment and its
planned condition/repeat identity.

`run_id` identifies the concrete operational execution instance that produced,
or attempted to produce, evidence.

Normally, one accepted controlled experiment is expected to have one accepted
`run_id`.

If an execution is aborted, restarted, invalidated, or repeated because of an
operational failure, the previous run record shall be retained and a new
`run_id` shall be created. Failed or rejected runs shall not be silently
overwritten.

This separation allows the dataset provenance chain to distinguish the
scientific experiment definition from the operational history of its
execution.

### 2.3 Dataset identity

The existing dataset identifier convention remains:

    DS-YYYYMMDD-NNN-short-name

A dataset may contain evidence from one or more experiments, but every
experiment-scoped record must remain traceable to its `experiment_id` and,
where applicable, its `run_id`.

### 2.4 Record identity

Source-specific records that require stable row-level identity shall use a
source-specific `record_id`.

A `record_id` identifies a measurement record and must not be used as a
replacement for `experiment_id` or `run_id`.

The native gNB telemetry schema already uses this principle through its
`record_id` field.

---

## 3. Time model

### 3.1 General principle

Sci_O-RAN measurements originate from multiple clock domains.

Therefore, the unified dataset shall not assume that every source exposes one
interchangeable timestamp.

Source timestamps, receive timestamps, monotonic timestamps, and normalized
cross-source timestamps represent different measurement semantics and shall
not overwrite one another.

### 3.2 Raw timestamp preservation

Raw data shall preserve the timestamp representation emitted or captured by
the original source.

Examples include:

- native gNB JSON UNIX timestamp;
- receiver wall-clock timestamp;
- receiver monotonic timestamp;
- iperf timestamps;
- host-observability timestamps;
- container-observability timestamps;
- network-observability timestamps;
- future O-RAN KPM timestamps;
- future actuator command and readback timestamps.

Raw timestamp values shall not be rewritten merely to impose a common format.

Timestamp normalization is a processed-data operation.

### 3.3 Native gNB time domains

The already validated native gNB telemetry fields remain:

| Field | Unit | Clock domain | Scientific role |
|---|---:|---|---|
| `gnb_timestamp_s` | s since UNIX epoch | gNB wall clock | source-side JSON construction time |
| `rx_wall_ns` | ns since UNIX epoch | receiver host wall clock | host receive epoch time |
| `rx_mono_ns` | ns | receiver host monotonic clock | robust local receive ordering and inter-arrival timing |

These fields shall remain distinct.

For native telemetry:

    preferred local ordering = rx_mono_ns
    source wall-clock time   = gnb_timestamp_s

`gnb_timestamp_s` and `rx_wall_ns` are retained for epoch-based correlation.

`rx_mono_ns` shall not be interpreted as a UTC timestamp.

### 3.4 Canonical processed alignment timestamp

Processed time-series tables that participate in cross-source alignment shall
contain:

    timestamp_utc_ns

with the following semantics:

- type: signed 64-bit integer;
- unit: nanoseconds since UNIX epoch;
- time basis: UTC;
- purpose: canonical cross-source alignment coordinate;
- data level: processed or derived, never a replacement for raw source time.

`timestamp_utc_ns` shall be generated deterministically from the most
scientifically appropriate epoch-based timestamp available for the source.

The transformation used to generate it must be recorded in processing
provenance.

For a source that already emits an authoritative epoch timestamp, the
canonical timestamp is a normalized representation of that source time.

For a source for which only a receive-side epoch timestamp is scientifically
defensible, the receive-side epoch timestamp may be used, but its provenance
must identify that choice.

A synthetic timestamp derived only from an assumed nominal sampling interval
shall not be treated as observed measurement time.

### 3.5 Metadata timestamps

Experiment- and run-level metadata shall represent absolute wall-clock times
in UTC using RFC 3339 / ISO 8601 form with the `Z` UTC designator.

Examples:

    2026-08-09T14:15:30Z
    2026-08-09T14:15:30.305905619Z

The preserved precision shall reflect the precision supported by the source.

Canonical metadata fields will include, where applicable:

    start_time_utc
    end_time_utc

Human-readable local-time representations shall not be used as canonical
dataset time coordinates.

### 3.6 Ordering versus synchronization

Record ordering and cross-source synchronization are separate operations.

A monotonic timestamp may be the correct coordinate for ordering records
within one acquisition process while an epoch-based timestamp is required for
alignment with other observability streams.

The dataset architecture shall preserve both when both have scientific value.

No processing stage shall collapse distinct clock domains into one field
without retaining the source fields and documenting the transformation.

---

## 4. Normative principles established so far

The following rules are already normative for the unified dataset:

1. raw scientific data are immutable;
2. `experiment_id` is the primary experiment-level scientific identifier;
3. `run_id` identifies the actual workflow execution instance;
4. failed or superseded runs remain part of provenance;
5. source-specific timestamps are preserved;
6. monotonic and epoch-based timestamps are not interchangeable;
7. `timestamp_utc_ns` is a processed alignment coordinate, not raw evidence;
8. timestamp normalization must be deterministic and provenance-traceable;
9. synthetic timestamps based solely on nominal sampling periods are not
   accepted as observed timestamps;
10. processed and derived data shall never overwrite their raw inputs.

The remaining sections of this specification will define the physical dataset
layout, metadata schema, metric naming, units, missing-value rules,
provenance, checksums, validation, and machine-readable schema.

---

## 5. Physical data model

### 5.1 Dataset package hierarchy

A Sci_O-RAN dataset is represented as a versioned dataset package.

The canonical logical hierarchy is:

    <dataset_id>/
      README.md
      DATA_LICENSE
      metadata/
        dataset.yaml
        experiments/
        runs/
      schemas/
      raw/
        <experiment_id>/
          <run_id>/
            <source>/
      processed/
        <schema_version>/
          <experiment_id>/
            <run_id>/
              <source>/
      derived/
        <analysis_id>/
      checksums/
        SHA256SUMS

This hierarchy is a logical archival model. Large experimental payloads are
not required to reside in the Git repository.

Git shall contain the specifications, schemas, lightweight metadata,
processing software, manifests, checksum records where appropriate, and
archival references required to interpret the externally stored dataset.

### 5.2 Raw layer

The `raw` layer contains evidence captured directly from experimental tools,
runtime components, operating-system interfaces, telemetry receivers, or
measurement applications.

Examples include:

- traffic-generator output;
- iperf client and server output;
- native gNB telemetry datagrams or capture logs;
- host CPU and memory measurements;
- per-core CPU measurements;
- CPU-frequency measurements;
- load-average measurements;
- network-interface counters;
- RTT measurement output;
- container-resource measurements;
- UE and 5GC runtime measurements;
- future O-RAN KPM reports;
- future actuator command and readback capture records.

Raw artifacts shall preserve the original representation whenever practical.

The raw layer is immutable after acquisition closure.

An existing raw file shall not be edited to:

- normalize timestamps;
- rename fields internally;
- remove anomalous measurements;
- replace missing observations;
- convert units;
- redact publication-sensitive values;
- repair malformed records;
- reorder measurements;
- aggregate samples.

If correction, normalization, redaction, conversion, or repair is required,
a new processed or publication artifact shall be generated while the retained
scientific raw copy remains unchanged.

### 5.3 Acquisition closure

A raw acquisition becomes closed when the corresponding run has ended and the
artifacts intended as scientific evidence have been collected.

After acquisition closure:

- raw files shall be treated as read-only scientific evidence;
- their file inventory shall be recorded;
- cryptographic checksums shall be calculated before archival release;
- subsequent transformations shall reference the raw artifact rather than
  replacing it.

If additional raw evidence is discovered after closure, it shall be added as
a separately identified artifact with provenance explaining when and why it
was incorporated.

Previously archived raw bytes shall not be silently replaced.

### 5.4 Processed layer

The `processed` layer contains deterministic representations of raw evidence
that improve machine readability, temporal comparability, typing, or
structural consistency without introducing analytical conclusions.

Permitted processed operations include:

- parsing source records;
- normalizing field names;
- assigning canonical data types;
- converting explicitly documented units;
- creating `timestamp_utc_ns`;
- validating records against a schema;
- representing missing measurements according to the missing-value policy;
- separating nested source records into relational or tabular structures;
- attaching `experiment_id`, `run_id`, and provenance references;
- sorting records when the source ordering rule is explicitly defined.

Processed data shall retain source-specific time fields whenever they have
scientific value.

A processed table shall not overwrite its raw source.

For each processed artifact, the provenance record must identify at least:

- source raw artifact or artifacts;
- processing software or script;
- software version or Git commit;
- schema version;
- transformation time;
- transformation parameters where applicable.

### 5.5 Derived layer

The `derived` layer contains quantities or structures produced through
scientific computation, aggregation, synchronization, statistical analysis,
feature construction, or modelling.

Examples include:

- P50, P95, and P99 RTT;
- throughput summaries;
- loss and jitter summaries;
- CPU-utilization aggregates;
- per-experiment resource statistics;
- queueing indicators;
- synchronized cross-source analysis tables;
- resampled time series;
- rolling-window statistics;
- system-identification features;
- controller-performance metrics;
- model inputs and outputs;
- experiment-level statistical summaries.

Derived artifacts shall never be presented as direct measurements when they
are calculated quantities.

Each derived field must be traceable to:

    raw evidence
        -> processed representation
        -> transformation or analysis procedure
        -> derived result

### 5.6 Unified time-series architecture

The Sci_O-RAN unified dataset shall use a federated time-series model rather
than forcing heterogeneous measurements into one raw wide table.

Each measurement source may retain:

- its native sampling rate;
- its native event structure;
- its source-specific timestamps;
- source-specific identifiers;
- source-specific quality or status fields.

Processed time-series sources that support cross-source analysis shall expose
the common alignment coordinate:

    timestamp_utc_ns

and the common identity coordinates:

    experiment_id
    run_id

This creates a common analytical coordinate system without destroying the
semantics of the original measurement streams.

A single physical row is therefore not required to contain simultaneous
values for every Sci_O-RAN metric.

### 5.7 Cross-source synchronization

Cross-source synchronization is an explicit transformation.

A synchronized analytical table may be generated from multiple processed
sources by a documented procedure such as:

- exact timestamp matching;
- nearest-neighbour matching within a declared tolerance;
- fixed-window aggregation;
- resampling;
- interval overlap;
- source-specific event association.

The synchronization method and tolerance shall be recorded in provenance.

Interpolation shall never occur implicitly.

If interpolation is scientifically justified, the interpolated value shall be
identified as derived rather than observed.

### 5.8 Source namespaces

The unified dataset shall use stable logical source namespaces.

The initial namespace set is:

| Namespace | Scientific content |
|---|---|
| `traffic` | offered traffic configuration and traffic-generation evidence |
| `iperf` | measured throughput, loss, jitter, and iperf execution results |
| `netif` | network-interface throughput, packet, drop, and error counters |
| `rtt` | RTT samples and latency statistics |
| `host_cpu` | host CPU utilization and per-core CPU measurements |
| `cpu_freq` | processor frequency measurements |
| `load` | host load-average measurements |
| `memory` | host memory measurements |
| `container` | gNB, UE, 5GC, and supporting container resource metrics |
| `native_gnb` | native gNB scheduler and runtime telemetry |
| `oran_kpm` | O-RAN KPM measurements |
| `actuator` | future actuator commands, acknowledgements, and readback |

A namespace identifies measurement semantics, not necessarily one specific
collection tool.

Tool-specific provenance shall be stored separately so that replacement of a
measurement implementation does not require redefining the scientific meaning
of the namespace.

### 5.9 Separation of observation and configuration

Measured values and configured values shall remain distinguishable.

For example:

- offered traffic rate is a configured experimental input;
- measured iperf throughput is an observation;
- configured telemetry interval is a configuration value;
- observed telemetry inter-arrival time is a measurement;
- requested actuator value is a command;
- actuator readback is an observation.

The dataset shall not use one field interchangeably for requested,
configured, observed, and derived values.

### 5.10 No implicit data fabrication

Absence of an observation shall not be replaced automatically with zero.

Zero is a valid scientific value only when the measurement semantics establish
that zero was actually observed or calculated.

Missing, unavailable, invalid, and not-applicable values will be represented
explicitly according to the missing-value policy defined later in this
specification.

---

## 6. Metadata schema

### 6.1 Metadata design principle

Sci_O-RAN metadata shall contain only information that has a defined
scientific, reproducibility, integrity, or provenance function.

A metadata field shall not be introduced solely because it is common in a
generic archival template.

The metadata model is divided into four principal scopes:

    dataset
    experiment
    run
    artifact

These scopes represent different entities and shall not be collapsed into one
flat record.

The relationships are:

    dataset
      -> experiment
          -> run
              -> artifact

A dataset may contain multiple experiments.

An experiment may contain multiple operational runs when a run is aborted,
rejected, or repeated.

A run may produce multiple raw, processed, and derived artifacts.

### 6.2 Dataset-level metadata

Dataset-level metadata describes the released or internally versioned
scientific dataset as a whole.

| Field | Type | Requirement | Scientific function |
|---|---|---|---|
| `dataset_id` | string | required | stable identity of the dataset package |
| `dataset_title` | string | required | human-readable scientific title |
| `dataset_version` | string | required | identifies the exact dataset revision |
| `schema_version` | string | required | identifies the metadata/data schema used |
| `created_time_utc` | RFC 3339 string | required | records dataset package creation time |
| `experiment_ids` | list[string] | required | identifies experiments represented in the dataset |
| `data_levels` | list[string] | required | declares whether raw, processed, and/or derived data are present |
| `description` | string | required | states the scientific content and intended interpretation |
| `repository_commit` | string | required | links the dataset definition to the exact Git revision |
| `license` | string | required for release | identifies the dataset reuse terms |
| `known_limitations` | list[string] | required | records scientifically relevant limitations; empty list permitted |
| `validation_status` | string | required | records whether dataset validation has been completed |
| `archival_record` | object | conditional | records DOI and archival location after publication |

`experiment_ids` shall contain identifiers, not free-text experiment names.

`known_limitations` shall not be omitted merely because no limitation is
currently known. In that case it shall be represented as an empty list.

### 6.3 Experiment-level metadata

Experiment-level metadata describes the controlled scientific condition being
evaluated.

The minimum experiment record is:

| Field | Type | Requirement | Scientific function |
|---|---|---|---|
| `experiment_id` | string | required | primary scientific experiment identity |
| `experiment_status` | string | required | distinguishes planned, completed, rejected, legacy, or otherwise classified evidence |
| `experiment_date_utc` | date | required | UTC date encoded in or associated with the experiment identity |
| `traffic_direction` | enum | conditional | identifies DL, UL, bidirectional, or non-traffic experiment semantics |
| `transport_protocol` | string | conditional | records transport protocol used by the workload |
| `offered_rate_kbit_s` | integer | conditional | records configured offered traffic rate |
| `repeat_number` | integer | conditional | identifies controlled repetition |
| `configured_duration_s` | numeric | conditional | records intended workload duration |
| `packet_size_bytes` | integer | conditional | records configured packet size when experimentally relevant |
| `experiment_purpose` | string | required | states the scientific purpose of the experiment |
| `configuration_ref` | string | required | points to the configuration snapshot or manifest |
| `accepted_run_id` | string or null | required | identifies the run accepted as evidence for this experiment |
| `evidence_status` | string | required | classifies experiment evidence using the established Sci_O-RAN evidence discipline |
| `notes` | string or null | optional | records scientifically relevant exceptional information |

A field marked `conditional` is required when that parameter forms part of
the experimental condition.

For example, `offered_rate_kbit_s` is required for controlled traffic-rate
experiments but is not required for an experiment whose purpose is solely
idle-state telemetry characterization.

The metadata model shall therefore distinguish:

    field not applicable to experiment design

from:

    applicable field whose value is missing

### 6.4 Experiment evidence status

`evidence_status` shall reuse the evidence discipline already established for
Sci_O-RAN controlled traffic experiments.

The canonical vocabulary is:

| Value | Meaning |
|---|---|
| `FACT` | directly supported by preserved raw evidence and sufficient experiment metadata |
| `FACT_PARTIAL` | directly supported observations exist, but the experiment record is incomplete |
| `HYPOTHESIS` | interpretation is consistent with available evidence but requires additional controlled validation |
| `ASSUMPTION` | unverified condition that must not be treated as a scientific result |

This vocabulary shall not be replaced by a parallel experiment-evidence
classification.

Operational lifecycle and scientific evidence classification are separate
concepts.

For example:

    experiment_status = completed
    evidence_status   = FACT

is valid when a completed experiment has sufficient retained evidence.

Likewise:

    experiment_status = legacy
    evidence_status   = FACT_PARTIAL

is appropriate for previously documented exploratory traffic evidence whose
directly observed measurements are retained but whose experiment record is
incomplete.

`rejected` belongs to experiment or run lifecycle status where applicable; it
is not an experiment evidence class.

Experiment-level `evidence_status` is also distinct from field-level
`evidence_class`.

Field-level `evidence_class` answers:

    how is the meaning or unit of this metric established?

Experiment-level `evidence_status` answers:

    how strongly is this experimental claim supported by retained evidence?

### 6.5 Run-level metadata

Run-level metadata describes one concrete operational execution.

The minimum run record is:

| Field | Type | Requirement | Scientific function |
|---|---|---|---|
| `run_id` | string | required | unique identity of the operational execution |
| `experiment_id` | string | required | links the run to its scientific experiment |
| `run_status` | string | required | records accepted, completed, aborted, failed, or rejected execution state |
| `start_time_utc` | RFC 3339 string | required | exact observed or recorded run start time |
| `end_time_utc` | RFC 3339 string or null | required | exact run end time when available |
| `host_id` | string | required | identifies the acquisition/execution host without relying on implicit environment knowledge |
| `software_commit` | string | required | Git commit representing the executed project state |
| `configuration_ref` | string | required | links to the exact run configuration or manifest |
| `traffic_command` | string or null | conditional | preserves the complete traffic-generator command when traffic is generated |
| `collector_set` | list[string] | required | identifies measurement namespaces expected during the run |
| `clock_sync_status` | string | required | records known clock-synchronization state relevant to cross-source timing |
| `failure_reason` | string or null | conditional | explains failed or aborted execution |
| `operator_notes` | string or null | optional | records exceptional operational facts relevant to interpretation |

`run_status` shall describe the operational outcome.

It shall not be inferred solely from the presence of output files.

`accepted_run_id` at experiment level and `run_status` at run level allow a
failed acquisition attempt to remain in provenance without being used
silently as accepted scientific evidence.

### 6.6 Host identity

`host_id` shall be a stable project-local identifier for the system that
executed or captured the run.

It shall not depend exclusively on an IP address.

An IP address may change between sessions and may also be inappropriate for a
public archival release.

Examples of project-local identifiers may include:

    tb3-dell
    tb3-ue-host
    analysis-node-01

The mapping between a project-local identifier and environment-specific
network information may be retained separately when operationally necessary.

### 6.7 Configuration reference

`configuration_ref` identifies the exact configuration evidence associated
with an experiment or run.

It may reference:

- an experiment manifest;
- a version-controlled configuration file;
- a configuration snapshot;
- a container-compose file;
- an immutable archived configuration artifact.

The reference must resolve sufficiently to reconstruct the experimental
condition.

A prose statement such as "default configuration" is not a valid
`configuration_ref`.

### 6.8 Collector set

`collector_set` records which logical measurement namespaces were expected to
produce evidence during the run.

Example:

    traffic
    iperf
    netif
    rtt
    host_cpu
    cpu_freq
    load
    memory
    container
    native_gnb

The collector set describes expected acquisition coverage.

The existence of a namespace in `collector_set` does not by itself prove that
valid observations were actually obtained.

Actual artifact presence and validation status shall be determined from the
artifact inventory.

### 6.9 Clock synchronization status

Cross-source temporal analysis requires explicit knowledge of clock quality.

`clock_sync_status` shall therefore describe the synchronization state known
for the run.

The initial controlled vocabulary is:

| Value | Meaning |
|---|---|
| `synchronized` | clock synchronization was active and verified for the required host set |
| `partially_synchronized` | synchronization was available only for part of the measurement path |
| `unsynchronized` | relevant clocks were known not to be synchronized |
| `unknown` | synchronization state cannot be established from retained evidence |
| `not_applicable` | cross-host wall-clock synchronization is not relevant to the run |

The value `synchronized` shall not be assigned merely because a time
synchronization service was installed.

Verification evidence must exist for the experimental period or for a
scientifically justified interval covering it.

### 6.10 Artifact-level metadata

Every retained scientific artifact shall have an inventory record.

The minimum artifact metadata is:

| Field | Type | Requirement | Scientific function |
|---|---|---|---|
| `artifact_id` | string | required | stable identity inside the dataset package |
| `experiment_id` | string | required | experiment provenance |
| `run_id` | string or null | conditional | operational provenance where applicable |
| `data_level` | enum | required | identifies raw, processed, or derived status |
| `namespace` | string | required | identifies scientific measurement semantics |
| `relative_path` | string | required | resolves the artifact within the dataset package |
| `media_type` | string | required | records machine-readable content type |
| `byte_size` | integer | required | supports integrity and inventory validation |
| `sha256` | string | required after acquisition closure | cryptographic identity of the exact file bytes |
| `schema_version` | string or null | conditional | identifies the schema used for structured data |
| `source_artifact_ids` | list[string] | conditional | records direct parent artifacts for processed or derived data |
| `processing_provenance_id` | string or null | conditional | links transformations to reproducible provenance |
| `validation_status` | string | required | records artifact-level validation state |

For raw artifacts, `source_artifact_ids` is normally empty.

For processed and derived artifacts, the direct source relationship shall be
recorded whenever the artifact was generated from retained parent artifacts.

### 6.11 Artifact identity

`artifact_id` is a dataset-local stable identifier.

It must not be derived solely from the filename because filenames can change
during packaging while the scientific object remains conceptually the same.

The exact bytes are identified independently by `sha256`.

Therefore:

    artifact_id = logical dataset identity
    sha256       = exact byte-level identity

These concepts shall remain distinct.

### 6.12 Status fields

Status fields shall use controlled vocabularies rather than unrestricted
prose where programmatic validation is required.

At minimum, the final machine-readable schema shall define controlled values
for:

- `experiment_status`;
- `run_status`;
- `evidence_status`;
- `validation_status`;
- `clock_sync_status`;
- `data_level`.

Free-text explanation may supplement a status but shall not replace it.

### 6.13 Metadata relationships

The minimum provenance relationships are:

    dataset_id
        -> experiment_id
            -> run_id
                -> artifact_id

and for transformed artifacts:

    source artifact_id
        -> processing provenance
            -> output artifact_id

These relationships provide the minimum graph required to trace a scientific
result back to its operational execution and retained evidence.


---

## 7. Column naming, units, and missing-value policy

### 7.1 General field-naming convention

Canonical processed and derived field names shall use:

    lowercase_snake_case

Names shall be composed of ASCII letters, digits, and underscores.

Canonical names shall describe scientific meaning rather than the particular
tool that happened to produce the value.

For example:

    offered_rate_kbit_s
    throughput_kbit_s
    rtt_ms
    cpu_utilization_pct

are preferred over ambiguous or tool-dependent names such as:

    rate
    speed
    latency_value
    iperf_speed

Tool-specific names may be retained in raw data and source-specific schemas
when preservation of the original representation is scientifically required.

### 7.2 Common identity and time columns

Processed time-series tables shall use the following common columns where
applicable:

| Field | Meaning |
|---|---|
| `experiment_id` | scientific experiment identity |
| `run_id` | operational execution identity |
| `record_id` | source-specific row or event identity when required |
| `timestamp_utc_ns` | canonical processed UTC alignment coordinate |
| `artifact_id` | parent artifact identity when row-level provenance requires it |

A source-specific table may contain additional native timestamp fields.

These source timestamps shall not be removed merely because
`timestamp_utc_ns` is available.

### 7.3 Unit suffix convention

When a numeric field has a physical unit, the canonical field name should
encode that unit whenever this improves unambiguous interpretation.

The initial suffix vocabulary is:

| Suffix | Unit |
|---|---|
| `_ns` | nanoseconds |
| `_us` | microseconds |
| `_ms` | milliseconds |
| `_s` | seconds |
| `_hz` | hertz |
| `_khz` | kilohertz |
| `_mhz` | megahertz |
| `_bytes` | bytes |
| `_kbit_s` | kilobits per second |
| `_mbit_s` | megabits per second |
| `_pct` | percent |
| `_count` | count |

A field name shall not change unit between records.

For example, a column named `throughput_kbit_s` shall contain values expressed
in kbit/s for every valid record.

If a processing step converts units, the output field name and processing
provenance shall reflect that conversion.

### 7.4 Dimensionless values

Dimensionless metrics shall not receive an artificial physical-unit suffix.

Examples include:

    load_1m
    load_5m
    load_15m

Load average is dimensionless and shall not be described as CPU percent.

Counts and cumulative counters shall remain distinguishable from rates and
percentages.

### 7.5 Initial canonical metric names

The following names establish the initial cross-source vocabulary.

#### Traffic configuration

| Field | Unit | Semantic class |
|---|---:|---|
| `offered_rate_kbit_s` | kbit/s | configured input |
| `configured_duration_s` | s | configured input |
| `packet_size_bytes` | bytes | configured input |

#### iperf observations

| Field | Unit | Semantic class |
|---|---:|---|
| `throughput_kbit_s` | kbit/s | observed measurement |
| `loss_pct` | % | observed or tool-calculated measurement |
| `jitter_ms` | ms | observed or tool-calculated measurement |
| `bytes_transferred` | bytes | observed transfer quantity |

Tool output shall remain available as raw evidence so that normalized fields
can be traced to the original iperf representation.

#### Network-interface observations

| Field | Unit | Semantic class |
|---|---:|---|
| `rx_bytes_total` | bytes | cumulative counter |
| `tx_bytes_total` | bytes | cumulative counter |
| `rx_packets_total` | count | cumulative counter |
| `tx_packets_total` | count | cumulative counter |
| `rx_drops_total` | count | cumulative counter |
| `tx_drops_total` | count | cumulative counter |
| `rx_errors_total` | count | cumulative counter |
| `tx_errors_total` | count | cumulative counter |
| `rx_throughput_kbit_s` | kbit/s | derived rate |
| `tx_throughput_kbit_s` | kbit/s | derived rate |

A throughput rate calculated from interface counters is a derived value and
shall not be represented as a directly observed cumulative counter.

#### RTT observations and statistics

| Field | Unit | Semantic class |
|---|---:|---|
| `rtt_ms` | ms | observed RTT sample |
| `rtt_p50_ms` | ms | derived percentile |
| `rtt_p95_ms` | ms | derived percentile |
| `rtt_p99_ms` | ms | derived percentile |

Percentile fields shall record the aggregation window or experiment scope in
their provenance.

#### Host CPU observations

| Field | Unit | Semantic class |
|---|---:|---|
| `cpu_utilization_pct` | % | host CPU observation |
| `cpu_core_id` | - | processor-core identity |
| `cpu_core_utilization_pct` | % | per-core CPU observation |

A host-wide CPU value and a per-core CPU value shall not share one ambiguous
field name.

#### CPU frequency

| Field | Unit | Semantic class |
|---|---:|---|
| `cpu_core_id` | - | processor-core identity |
| `cpu_frequency_mhz` | MHz | observed processor frequency |

If the source exposes frequency in another unit, conversion to MHz is a
processed-data transformation and shall be provenance-traceable.

#### Load average

| Field | Unit | Semantic class |
|---|---:|---|
| `load_1m` | dimensionless | host observation |
| `load_5m` | dimensionless | host observation |
| `load_15m` | dimensionless | host observation |

#### Memory observations

| Field | Unit | Semantic class |
|---|---:|---|
| `memory_total_bytes` | bytes | host memory quantity |
| `memory_used_bytes` | bytes | host memory observation |
| `memory_available_bytes` | bytes | host memory observation |

Definitions of used and available memory shall follow the acquisition source
and shall be documented when the source semantics differ.

#### Container observations

| Field | Unit | Semantic class |
|---|---:|---|
| `container_id` | - | container identity |
| `container_role` | - | scientific role such as gNB, UE, or 5GC |
| `container_cpu_pct` | % | container resource observation |
| `container_memory_bytes` | bytes | container resource observation |
| `container_rx_bytes_total` | bytes | cumulative network counter where available |
| `container_tx_bytes_total` | bytes | cumulative network counter where available |

Container runtime-specific identifiers shall not substitute for
`container_role`.

### 7.6 Native gNB naming policy

The already validated native gNB dataset schema remains authoritative for
native gNB field semantics.

Existing validated fields such as:

    gnb_timestamp_s
    rx_wall_ns
    rx_mono_ns
    average_latency_us

shall not be renamed merely to make them visually resemble another namespace.

A future unified schema may add normalized aliases only when there is a
scientific need and the relationship to the source field is explicit.

Native gNB metrics whose semantics have already been documented shall retain
those documented units and evidence classes.

### 7.7 O-RAN KPM naming policy

O-RAN KPM metric names and units shall not be invented before the exact
E2SM-KPM measurement definition has been validated.

The future `oran_kpm` schema shall preserve:

- the measurement type or standardized measurement name;
- the measurement unit defined by the applicable specification or producer;
- measurement scope;
- granularity period where applicable;
- source and receive timing where available.

Any normalized alias introduced by Sci_O-RAN shall retain an explicit mapping
to the original KPM measurement identity.

### 7.8 Actuator naming policy

Future control experiments shall distinguish at least three concepts:

    requested command
    acknowledged command
    observed readback

A requested actuator value shall not be represented as though it were an
observed applied value.

Actuator-specific fields shall therefore distinguish command-side and
readback-side semantics.

The exact actuator metric names and units shall be defined only after the
runtime actuator surface has been experimentally validated.

### 7.9 Missing-value principle

Missingness is a scientific state and shall not be silently converted into a
numeric value.

In particular:

    missing != 0

and:

    missing != interpolated value

A value of zero is valid only when zero was actually observed, emitted by the
source, or produced by an explicitly documented calculation.

### 7.10 Raw-data missingness

Raw files preserve the source representation.

If a source omits a value, produces an empty field, emits an error, terminates
early, or does not produce a record, the raw artifact shall not be edited to
manufacture a replacement value.

Interpretation of that condition belongs to processed-data validation.

### 7.11 Processed-data null representation

For processed and derived structured data, an unavailable numeric or textual
value shall be represented using the native null mechanism of the storage
format whenever such a mechanism exists.

Examples include:

- Parquet null;
- JSON `null`;
- nullable typed fields in analytical storage.

If CSV is used, an empty field may represent null only when the accompanying
schema explicitly defines that convention.

The following sentinel values shall not be used as generic missing values:

    -1
    9999
    N/A
    NA
    unknown
    -

unless one of those literal values is part of an external source format that
is being preserved unchanged in raw evidence.

### 7.12 Missing-value reason

When the cause of missingness materially affects scientific interpretation,
the dataset shall record a controlled missing-value reason.

The initial vocabulary is:

| Value | Meaning |
|---|---|
| `not_observed` | the expected observation was not captured |
| `unavailable` | the source could not provide the measurement |
| `invalid` | a value was captured but failed validity requirements |
| `parse_error` | raw evidence exists but could not be parsed successfully |
| `not_applicable` | the metric does not apply to this record or experiment |
| `outside_window` | no source observation belongs to the synchronization window |

A missing-value reason is not required for every nullable field.

It is required when the distinction between causes is relevant to analysis,
validation, or reproducibility.

### 7.13 Invalid versus missing

An invalid observed value and an absent observation are different states.

Therefore:

- an absent observation may be represented as null with `not_observed`;
- a captured but rejected value may be represented as null in a cleaned
  processed table with `invalid`;
- the original invalid value shall remain available in raw evidence;
- the validation rule that rejected the value shall be provenance-traceable.

### 7.14 Synchronization-induced missingness

Cross-source synchronization may create rows for which one source has no
matching observation inside the declared synchronization tolerance.

Such a condition shall not be interpreted automatically as packet loss,
collector failure, or zero activity.

Where scientifically relevant, it shall be represented as null with:

    outside_window

or another explicitly justified quality state.

### 7.15 Interpolation policy

Interpolation is a derived-data operation.

Interpolated values shall:

- never replace raw observations;
- never be labelled as directly observed values;
- record the interpolation method;
- record the source observations used;
- record the interpolation parameters;
- remain distinguishable from observed samples.

A dataset processing pipeline shall not interpolate merely to eliminate null
values.

### 7.16 Data dictionary requirement

Every machine-readable table or record family shall have a data dictionary.

For each canonical field, the dictionary shall define at least:

| Property | Purpose |
|---|---|
| `name` | canonical field name |
| `description` | scientific meaning |
| `type` | machine-readable data type |
| `unit` | physical or logical unit |
| `nullable` | whether null is permitted |
| `semantic_class` | configuration, observation, counter, derived statistic, command, readback, or identity |
| `source` | originating measurement source or transformation |
| `data_level` | raw, processed, or derived |
| `evidence_class` | strength or basis of the field definition where applicable |

Additional properties shall be introduced only when they have a defined
scientific or validation purpose.


---

## 8. Provenance, integrity, and versioning

### 8.1 Provenance principle

Every processed or derived scientific artifact shall be reproducibly traceable
to the exact input artifacts and transformation that produced it.

The minimum transformation chain is:

    input artifact_id(s)
        -> processing_provenance_id
            -> output artifact_id(s)

Provenance shall describe an actual transformation, not merely the general
software project used to perform it.

### 8.2 Processing provenance record

Each deterministic processing or analysis operation that produces retained
scientific artifacts shall have a provenance record.

The minimum provenance fields are:

| Field | Type | Requirement | Scientific function |
|---|---|---|---|
| `processing_provenance_id` | string | required | unique identity of the transformation record |
| `process_name` | string | required | identifies the processing or analysis operation |
| `process_type` | enum | required | distinguishes processing, synchronization, aggregation, analysis, modelling, or validation |
| `created_time_utc` | RFC 3339 string | required | records when the transformation was executed |
| `input_artifact_ids` | list[string] | required | identifies exact scientific inputs |
| `output_artifact_ids` | list[string] | required | identifies exact generated outputs |
| `software_commit` | string | required | identifies the exact project Git revision |
| `entrypoint` | string | required | identifies the script, executable, notebook, or command entrypoint |
| `parameters` | object | required | records transformation parameters; empty object permitted |
| `input_schema_versions` | list[string] | conditional | records relevant input schema versions |
| `output_schema_version` | string or null | conditional | records schema of structured output |
| `environment_ref` | string or null | conditional | identifies a reproducible environment when execution environment affects results |
| `container_image_digest` | string or null | conditional | identifies immutable container image when containerized processing is used |
| `notes` | string or null | optional | records exceptional scientifically relevant information |

A processing record shall reference exact artifact identities rather than only
directory names.

### 8.3 Provenance identity

The canonical project-local format for a processing provenance identifier is:

    PROV-YYYYMMDDTHHMMSSZ-NNN

Example:

    PROV-20260809T151245Z-001

The identifier represents one retained transformation execution.

Re-running the same script with the same inputs still constitutes a separate
execution and therefore receives a separate provenance identifier if its
output is retained as scientific evidence.

### 8.4 Software provenance

A filename alone is insufficient software provenance.

Where Git is used, `software_commit` shall contain the full commit identifier
of the code used for the transformation or experiment execution.

If the relevant software is external to the Sci_O-RAN repository, provenance
shall retain a resolvable version, release, commit, or immutable image digest
as appropriate.

Mutable labels such as:

    latest

shall not be accepted as the sole reproducibility reference for a released
scientific artifact.

### 8.5 Processing parameters

Transformation parameters shall be recorded whenever changing them can change
the resulting scientific values.

Examples include:

- synchronization tolerance;
- resampling interval;
- aggregation-window width;
- percentile scope;
- filter threshold;
- selected columns;
- unit-conversion rule;
- interpolation method;
- model hyperparameters;
- controller parameters.

Default values used by software shall be recorded or resolvable from the exact
software version.

### 8.6 SHA-256 integrity model

SHA-256 is the canonical byte-level integrity algorithm for Sci_O-RAN dataset
artifacts.

After acquisition closure, each retained raw artifact shall have a SHA-256
digest.

Processed and derived artifacts intended for retention or release shall also
have SHA-256 digests.

The digest represents the exact bytes of the artifact.

If one byte changes, the resulting object is not the same byte-level artifact
and shall not silently retain the old checksum.

### 8.7 Checksum manifest

An archival dataset package shall contain:

    checksums/SHA256SUMS

The manifest shall contain one record per retained package file that is
included in integrity verification, using the conceptual form:

    <sha256-hex>  <dataset-relative-path>

Requirements are:

- SHA-256 values use lowercase hexadecimal representation;
- paths are relative to the dataset package root;
- paths uniquely identify package files;
- manifest entries are sorted lexicographically by path;
- the checksum manifest shall not include itself recursively;
- checksum verification shall be performed before archival release.

The exact manifest-generation command shall be retained in release or
processing provenance.

### 8.8 Raw checksum continuity

The checksum calculated for a raw artifact after acquisition closure establishes
the integrity identity of that retained raw evidence.

Processing, packaging, transfer, or archival preparation shall not change the
raw bytes while continuing to claim the original checksum.

If publication requires redaction or transformation, the publication artifact
shall receive:

- a new `artifact_id`;
- an appropriate non-raw `data_level` or release classification;
- a new SHA-256 digest;
- provenance linking it to the retained source artifact.

The original scientific raw artifact remains unchanged.

### 8.9 Dataset version

`dataset_version` identifies the exact logical revision of the dataset package.

The canonical version form is:

    vMAJOR.MINOR.PATCH

Example:

    v1.0.0

The version components have the following project semantics:

| Component | Increment when |
|---|---|
| `MAJOR` | dataset interpretation, compatibility, or schema relationship changes incompatibly |
| `MINOR` | scientifically meaningful content is added without invalidating the established compatible structure |
| `PATCH` | metadata, documentation, manifests, or other package information is corrected without changing the meaning of retained scientific measurements |

Dataset versioning does not authorize modification of immutable raw evidence.

If corrected scientific evidence is required, it shall be represented by new
artifacts and provenance rather than overwriting the previous raw bytes.

### 8.10 Released dataset immutability

A published archival dataset version is treated as immutable by Sci_O-RAN.

After release, any change to the archived package that is intended to become
part of the scientific record requires a new dataset version.

Previous released versions remain part of the provenance history and shall
not be treated as though they never existed.

This rule applies even when an archival platform technically permits editing
some record metadata after publication.

### 8.11 Schema version

`schema_version` is independent of `dataset_version`.

The canonical schema version form is:

    MAJOR.MINOR.PATCH

Example:

    1.0.0

The two identifiers answer different questions:

    dataset_version = which scientific dataset revision is this?
    schema_version  = which structural contract describes these records?

Multiple dataset versions may use the same schema version.

A schema version may also be reused by multiple datasets.

### 8.12 Schema compatibility

Schema changes shall be classified according to their effect on existing
machine-readable records.

Examples of compatible changes may include:

- adding an optional field;
- adding a new controlled-vocabulary value when consumers are designed to
  tolerate such extension;
- adding a new source-specific table without changing existing tables.

Examples of incompatible changes include:

- changing the scientific meaning of an existing field;
- changing an existing field unit without changing its identity;
- changing a required field type incompatibly;
- removing a required field;
- reusing an existing field name for different semantics.

An incompatible schema change requires a `MAJOR` schema-version increment.

### 8.13 Dataset and schema version relationship

Every structured artifact shall be resolvable to the schema version that
defines it.

The dataset metadata shall declare its package-level schema version, while an
artifact may declare a more specific schema version when necessary.

A dataset release shall not depend on an undocumented "current schema".

The referenced machine-readable schema must be retained with the dataset
release or be resolvable through an immutable software/archive reference.

### 8.14 Validation status

Validation status records whether an artifact or dataset has passed the
defined integrity and structural checks.

The initial controlled vocabulary is:

| Value | Meaning |
|---|---|
| `not_validated` | validation has not yet been executed |
| `valid` | all required checks passed |
| `valid_with_warnings` | required checks passed but documented non-fatal issues exist |
| `invalid` | one or more required validation checks failed |

`valid` shall not be assigned solely because a file can be opened.

Validation may include, as applicable:

- checksum verification;
- metadata-schema validation;
- required-field validation;
- identifier consistency;
- timestamp validity;
- controlled-vocabulary validation;
- artifact-path resolution;
- provenance-link resolution;
- source-specific data checks.

### 8.15 Reproducibility chain

For every retained processed or derived result, Sci_O-RAN should be able to
establish the chain:

    scientific result
        -> output artifact_id
        -> processing_provenance_id
        -> input artifact_id(s)
        -> run_id
        -> experiment_id
        -> configuration_ref
        -> software_commit
        -> raw evidence checksum

A dataset shall not be described as fully reproducible merely because these
fields exist.

The referenced artifacts, software, configuration, and transformation
information must also be available and internally consistent.


---

## 9. Archival release and Zenodo architecture

### 9.1 Scope of this section

This section defines the future archival structure of a Sci_O-RAN dataset
release.

It does not authorize or perform publication.

During the current dataset-design phase:

- no Zenodo record is created;
- no DOI is claimed;
- no archival upload is performed;
- `archival_record` may remain null;
- dataset licensing must not be represented as finalized unless the actual
  reuse terms have been reviewed and approved.

Platform-specific publication behaviour shall be revalidated against the
current Zenodo documentation immediately before an actual release.

### 9.2 Archival object separation

Scientifically significant datasets, software, and technical reports should
remain separately identifiable research objects.

The preferred Sci_O-RAN archival model is:

    dataset record
        <-> software archival record
        <-> technical report or publication record

The dataset record contains the scientific data package.

The software record contains the versioned code required to acquire, process,
validate, or analyse the dataset when that software constitutes a significant
research object.

The technical report record documents the experimental architecture,
methodology, limitations, validation, and interpretation.

These objects shall be linked rather than merged solely for convenience.

### 9.3 Canonical dataset release package

The logical package for a versioned Sci_O-RAN dataset release is:

    <dataset_id>-<dataset_version>/
      README.md
      DATA_LICENSE
      metadata/
        dataset.json
        experiments/
        runs/
        artifacts/
        provenance/
      schemas/
        sci-oran-metadata-<schema_version>.schema.json
        sci-oran-data-dictionary-<schema_version>.json
      raw/
        <experiment_id>/
          <run_id>/
            <namespace>/
      processed/
        <schema_version>/
          <experiment_id>/
            <run_id>/
              <namespace>/
      derived/
        <analysis_id>/
      checksums/
        SHA256SUMS
      RELEASE_MANIFEST.json

Not every release must contain every data level.

The actual contents shall be declared by dataset metadata through
`data_levels` and the artifact inventory.

An archival package shall not contain empty directories merely to imitate the
logical hierarchy.

### 9.4 Release README

Each archival dataset release shall contain a human-readable `README.md`.

At minimum, the README shall explain:

- dataset title and dataset ID;
- dataset version;
- schema version;
- scientific purpose;
- experiment coverage;
- represented experiment IDs;
- represented run IDs;
- included data levels;
- directory structure;
- principal measurement namespaces;
- timestamp model;
- raw-data immutability policy;
- processing and provenance model;
- checksum verification procedure;
- known limitations;
- data-license reference;
- software dependency or software archival reference;
- technical-report or publication reference;
- citation instructions after DOI assignment.

The README shall describe the dataset actually released.

It shall not advertise measurement streams that are absent from that release.

### 9.5 Data licensing

Dataset licensing and software licensing are separate concerns.

The archival dataset package shall use:

    DATA_LICENSE

as the canonical human-readable file describing reuse terms for the scientific
data.

A software `LICENSE` file from the Git repository shall not automatically be
treated as the license of the dataset.

Before public release, the selected dataset license must be:

- legally applicable to the released material;
- consistent with third-party rights and source-data constraints;
- represented consistently in `DATA_LICENSE`;
- represented consistently in dataset metadata;
- represented consistently in the archival repository record.

The current schema-design phase intentionally does not assign a final dataset
license.

A dataset release shall not use a placeholder license as though it were a
real reuse grant.

### 9.6 Third-party and sensitive material review

Before archival publication, raw and processed artifacts shall be reviewed for
material that may not be appropriate for public release.

Examples include:

- credentials;
- authentication tokens;
- private keys;
- operational secrets;
- unintended environment variables;
- sensitive network information;
- third-party data with incompatible reuse terms;
- identifiers that should not be publicly disclosed.

Scientific raw evidence retained internally shall not be silently edited
during this review.

If publication requires redaction or transformation, the publication artifact
shall be separately identified and provenance-linked to its retained source.

### 9.7 Release manifest

`RELEASE_MANIFEST.json` shall describe the exact logical contents of one
dataset release.

At minimum it shall contain or reference:

- `dataset_id`;
- `dataset_version`;
- `schema_version`;
- release creation time in UTC;
- experiment IDs;
- run IDs;
- included data levels;
- artifact inventory;
- checksum-manifest path;
- repository commit;
- software archival identifier when available;
- technical-report identifier when available;
- dataset DOI when assigned.

The release manifest is an inventory and linkage object.

It shall not duplicate complete measurement tables.

### 9.8 Checksum package

The archival package shall contain:

    checksums/SHA256SUMS

as defined by the integrity policy in Section 8.

Before publication, release validation shall confirm:

    every expected retained file
        -> exists
        -> has the recorded byte size
        -> matches the recorded SHA-256 digest

The checksum manifest itself shall be distributed as part of the release but
shall not recursively checksum itself.

### 9.9 Dataset DOI

A Zenodo dataset release shall have its own persistent identifier.

The dataset DOI represents the dataset object and shall not be replaced by:

- an article DOI;
- a technical-report DOI;
- a software DOI;
- a GitHub repository URL.

For reproducibility claims, Sci_O-RAN shall reference the persistent
identifier of the exact dataset version used in an analysis.

A higher-level version-family identifier may additionally be used for
discovery where supported by the archival platform, but it shall not replace
the exact-version identifier in reproducibility provenance.

### 9.10 DOI reservation

If a dataset DOI is required inside release files before publication, the
archival workflow may reserve a DOI during release preparation.

A reserved DOI shall not be represented as a published dataset until the
corresponding archival record has actually been published.

During the current Prompt 07 design stage, no DOI shall be reserved.

### 9.11 Dataset-to-software relationship

The Git repository and the archived software release represent different
levels of software reference.

For an executed experiment or transformation, the strongest local software
provenance remains:

    software_commit

When an immutable software archival release with a DOI exists, dataset
metadata should additionally reference that software DOI.

The preferred relationship from the dataset to software used to generate,
process, or analyse it is:

    dataset DOI
        -- references -->
    version-specific software DOI

The exact software version or archival release associated with the relevant
Git commit must remain resolvable.

A mutable repository branch name such as `main` shall not replace
`software_commit` in reproducibility provenance.

### 9.12 Dataset-to-technical-report relationship

When a technical report specifically documents the dataset, experimental
methodology, or release, the preferred semantic relationship is:

    dataset DOI
        -- isDocumentedBy -->
    technical report DOI

The corresponding report may expose the inverse semantic relation when
supported:

    technical report DOI
        -- documents -->
    dataset DOI

This relationship indicates documentation.

It does not imply that the report and the dataset are the same research
object.

### 9.13 Relationship qualification

Related-identifier relations shall be chosen according to the actual semantic
relationship between research objects.

For example, `references`, `isDocumentedBy`, or another supported relation
shall be used only when its meaning is true for the specific objects.

Relations shall not be added merely to increase metadata density.

The archival metadata used for an actual release shall be validated against
the controlled vocabulary supported by the archival platform at publication
time.

### 9.14 GitHub, software DOI, dataset DOI, and report DOI

The preferred reproducibility graph is:

    Git repository
        -> exact software_commit
        -> versioned software archival release
        -> software DOI

    experiment_id
        -> run_id
        -> raw / processed / derived artifacts
        -> dataset_version
        -> dataset DOI

    technical methodology and interpretation
        -> technical report
        -> technical report DOI

with explicit related identifiers linking the independently citable objects.

The DOI graph complements rather than replaces internal provenance based on
experiment IDs, run IDs, artifact IDs, Git commits, and SHA-256 digests.

### 9.15 FAIR interpretation

FAIR principles are applied in Sci_O-RAN as functional engineering and
scientific requirements rather than as a reason to add unused metadata.

#### Findable

Findability is supported through:

- stable `dataset_id`;
- stable `experiment_id`;
- stable `run_id`;
- structured metadata;
- machine-readable schema;
- data dictionary;
- persistent archival DOI after publication;
- related identifiers connecting research outputs.

#### Accessible

Accessibility is supported through:

- an archival repository record;
- documented access conditions;
- explicit data licensing;
- human-readable README documentation;
- package-level file inventory;
- preservation of metadata even when some files require restricted access.

FAIR accessibility does not require every artifact to be openly downloadable
when legitimate restrictions apply.

#### Interoperable

Interoperability is supported through:

- explicit data types;
- canonical units;
- stable field naming;
- documented namespaces;
- RFC 3339 UTC metadata timestamps;
- `timestamp_utc_ns` for processed cross-source alignment;
- machine-readable JSON Schema;
- machine-readable data dictionary;
- explicit source and derived semantics.

Interoperability shall not be achieved by destroying source-specific
measurement semantics.

#### Reusable

Reusability is supported through:

- immutable retained raw evidence;
- explicit raw, processed, and derived levels;
- exact software provenance;
- transformation provenance;
- SHA-256 integrity;
- dataset and schema versioning;
- known limitations;
- missing-value semantics;
- data licensing;
- source-specific timing preservation;
- experiment and run identities;
- reproducible relationships between data, software, and documentation.

### 9.16 FAIR metadata restraint

A field is justified only when it contributes to at least one of:

- scientific interpretation;
- experimental reconstruction;
- temporal alignment;
- integrity verification;
- provenance;
- validation;
- discoverability;
- reuse conditions.

FAIR compliance shall not be interpreted as maximizing the number of metadata
fields.

Undefined, unverifiable, or scientifically purposeless metadata creates
ambiguity rather than interoperability.

### 9.17 Pre-publication release gate

A Sci_O-RAN dataset shall not be described as publication-ready until at least
the following release checks have passed:

- metadata-schema validation;
- referential-integrity validation;
- artifact inventory validation;
- SHA-256 verification;
- dataset-version validation;
- schema-version validation;
- required README validation;
- `DATA_LICENSE` consistency validation;
- sensitive-information review;
- provenance-link validation;
- software-reference validation;
- known-limitations review;
- archival related-identifier review.

Publication to Zenodo is a separate future operation after this release gate.
