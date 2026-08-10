# Sci_O-RAN Reproducible Experiment Harness

## 1. Purpose

The Sci_O-RAN experiment harness provides a deterministic orchestration layer
for controlled and reproducible experiments on Tb3.

The harness shall coordinate existing acquisition components rather than
duplicate their telemetry or observability functionality.

The initial workflow is:

~~~text
pre-run health check
        |
        v
experiment_id resolution
        |
        v
run_id generation
        |
        v
metadata/configuration snapshot
        |
        v
logger startup
        |
        v
logger readiness validation
        |
        v
exact UTC experiment start
        |
        v
controlled traffic input
        |
        v
exact UTC experiment end
        |
        v
cooldown
        |
        v
post-run health check
        |
        v
graceful logger shutdown
        |
        v
artifact validation
        |
        v
SHA-256 checksums
        |
        v
run manifest generation
~~~

## 2. Architectural principles

The harness shall satisfy the following principles:

1. deterministic experiment and run identity;
2. UTC-based wall-clock timestamps;
3. explicit process identifiers and exit codes;
4. no hidden service or container restarts;
5. graceful process cleanup;
6. immutable preservation of raw measurements;
7. separation of raw, processed, and derived data;
8. explicit software, configuration, and Git provenance;
9. explicit failure recording;
10. modular traffic and actuator interfaces;
11. optional O-RAN KPM acquisition;
12. machine-readable run manifests;
13. reproducibility from retained configuration and provenance.

## 3. Identity model

The canonical controlled-traffic experiment identifier follows:

~~~text
EXP-YYYYMMDD-DL-RRRRRK-RNN
~~~

Example:

~~~text
EXP-20260809-DL-04000K-R01
~~~

A concrete operational execution uses:

~~~text
RUN-YYYYMMDDTHHMMSSZ-NNN
~~~

Example:

~~~text
RUN-20260809T183547Z-001
~~~

`experiment_id` identifies the scientific experiment.

`run_id` identifies one actual execution of that experiment.

Failed, interrupted, or rejected executions shall retain their own `run_id`
and shall not be silently overwritten by subsequent attempts.

## 4. Orchestration boundary

The harness is an orchestrator.

It shall not contain duplicated implementations of:

- native gNB metric collection;
- host and container resource measurement;
- network observability;
- O-RAN KPM decoding;
- traffic generation logic beyond adapter invocation.

Existing project components shall be invoked through explicit interfaces.

## 5. Initial component model

The initial harness consists conceptually of:

~~~text
Experiment Runner
 |
 +-- Health Check Interface
 |
 +-- Metadata Snapshot Interface
 |
 +-- Resource Logger Adapter
 |
 +-- Native Telemetry Adapter
 |
 +-- Optional KPM Logger Adapter
 |
 +-- Traffic Input Adapter
 |
 +-- Future Runtime Actuator Adapter
 |
 +-- Process Supervisor
 |
 +-- Artifact Validator
 |
 +-- Checksum Generator
 |
 +-- Manifest Generator
~~~

The traffic input and future runtime actuator shall remain separate adapters so
that controlled traffic can later be complemented or replaced by runtime
control actions without redesigning the experiment lifecycle.

## 6. Process supervision policy

Every background acquisition process shall have:

- an explicit command;
- captured PID;
- dedicated stdout file;
- dedicated stderr file;
- recorded start time;
- recorded stop time;
- recorded exit status.

The normal shutdown sequence shall be:

~~~text
SIGINT -> wait -> validate exit -> fallback only if required
~~~

The harness shall not use unconditional `SIGKILL` as a normal stop mechanism.

The harness shall not restart failed services, containers, collectors, or
telemetry sources unless a future experiment specification explicitly defines
such behaviour.

## 7. Native telemetry policy

Only one process shall bind to the canonical native gNB UDP endpoint at a time.

For raw acquisition, the native UDP receiver is the preferred canonical source
because preservation of raw measurements has priority over compact formatting.

Compact or parsed telemetry shall be treated as processed or derived output
unless a later validated collector architecture provides both forms without
competing for the same UDP socket.

## 8. Resource observability policy

`scripts/tb3-resource-network-observer.py` shall initially be treated as an
external logger adapter.

Its JSON-lines stdout shall be redirected to an experiment-scoped raw artifact.

The logger shall be started by the runner, its PID retained, and its termination
status recorded.

## 9. KPM policy

O-RAN KPM acquisition is optional in the initial harness.

KPM collection shall be represented by an adapter with the same lifecycle
semantics as other loggers:

~~~text
start -> readiness -> acquire -> stop -> exit status -> artifact validation
~~~

Absence of KPM acquisition shall be represented explicitly in run metadata and
shall not be interpreted as collector failure.

## 10. Raw-data preservation

Raw files shall never be modified in place after acquisition.

Any normalization, filtering, parsing, aggregation, synchronization, or feature
extraction shall produce separate processed or derived artifacts.

The provenance chain shall remain:

~~~text
raw -> processed -> derived
~~~

## 11. Failure semantics

A run may finish as:

- successful;
- failed;
- interrupted;
- rejected during validation.

Failure shall not cause deletion of already acquired raw evidence.

The run manifest shall record the failure stage, relevant exit codes, and known
reason where available.


## 12. Experiment lifecycle state contract

The runner shall execute every run as an explicit state transition sequence.

The canonical states are:

PRECHECK
-> IDENTITY
-> SNAPSHOT
-> LOGGER_START
-> LOGGER_READY
-> RUNNING
-> COOLDOWN
-> POSTCHECK
-> LOGGER_STOP
-> VALIDATION
-> FINALIZATION
-> terminal state

The normal terminal state is:

COMPLETED

Abnormal terminal states are:

FAILED
INTERRUPTED
REJECTED

### 12.1 PRECHECK

PRECHECK verifies that the environment is suitable for experiment execution.

This state shall be read-only with respect to infrastructure state.

The runner shall not automatically restart containers, services, collectors,
network functions, or experiment components in order to make PRECHECK pass.

A failed mandatory health check shall prevent traffic execution.

### 12.2 IDENTITY

IDENTITY resolves the canonical experiment_id and creates a unique run_id.

The run_id shall identify exactly one operational execution attempt.

Once created, the run_id shall not be reused by another attempt.

### 12.3 SNAPSHOT

SNAPSHOT captures reproducibility metadata before acquisition begins.

At minimum this state shall preserve references to:

- Git commit and working-tree state;
- host/environment manifest;
- software manifest;
- Docker image manifest where applicable;
- relevant configuration files and their checksums;
- experiment input parameters.

### 12.4 LOGGER_START

LOGGER_START launches all enabled acquisition adapters.

Each started background process shall immediately have its PID, command,
stdout path, stderr path, and start timestamp retained by the process
supervisor.

A logger startup failure shall be recorded explicitly.

### 12.5 LOGGER_READY

LOGGER_READY verifies that every mandatory logger is ready before controlled
traffic begins.

Optional adapters, including KPM when disabled by experiment configuration,
shall be represented explicitly as disabled or not_applicable rather than
failed.

Controlled traffic shall not start before mandatory logger readiness has been
validated.

### 12.6 RUNNING

Immediately before controlled traffic invocation, the runner shall record the
canonical UTC experiment start timestamp.

The traffic adapter shall then execute the configured controlled input.

The runner shall retain the traffic command, parameters, PID where applicable,
stdout, stderr, and exit code.

Immediately after the controlled traffic interval terminates, the runner shall
record the canonical UTC experiment end timestamp.

### 12.7 COOLDOWN

Enabled acquisition processes shall continue operating during the configured
cooldown interval.

The cooldown duration shall be explicit experiment metadata and shall not be a
hidden constant.

### 12.8 POSTCHECK

POSTCHECK evaluates experiment infrastructure after controlled traffic and
cooldown have completed.

The post-run health state shall be retained even if it differs from PRECHECK.

The runner shall not hide degradation by automatically restarting components.

### 12.9 LOGGER_STOP

Background acquisition processes shall be stopped through the process
supervisor.

SIGINT is the preferred graceful termination signal for the initial native and
resource observers.

The runner shall wait for each process and retain its exit status.

Escalation to another signal shall occur only after an explicit timeout and
shall be recorded in the run metadata.

### 12.10 VALIDATION

VALIDATION checks the retained run evidence.

Validation shall include, where applicable:

- required artifact existence;
- non-empty mandatory raw artifacts;
- identifier consistency;
- timestamp availability;
- logger exit information;
- traffic exit information;
- basic manifest completeness.

Validation failure shall not delete collected evidence.

### 12.11 FINALIZATION

FINALIZATION generates retained checksums and the machine-readable run manifest.

Checksums shall be generated only after acquisition files have been closed.

The manifest shall describe both successful and unsuccessful execution paths.

### 12.12 Terminal-state semantics

COMPLETED means that the configured workflow executed and mandatory validation
passed.

FAILED means that an operational error prevented successful execution.

INTERRUPTED means that execution was terminated externally or by an explicit
user interruption.

REJECTED means that acquisition completed sufficiently to retain evidence, but
the run was not accepted as valid scientific evidence.

No terminal state shall cause automatic deletion of the run directory or its
raw artifacts.

## 13. Logger adapter interface contract

All acquisition loggers shall be integrated through a common logical adapter
contract.

The runner shall not depend on logger-specific implementation details beyond
this contract.

### 13.1 Adapter operations

Each logger adapter shall conceptually provide the following operations:

- configure;
- start;
- ready;
- stop;
- validate;
- describe.

`configure` resolves the command, parameters, output paths, and adapter policy
without starting acquisition.

`start` launches the acquisition process and returns control to the runner
after the process identifier has been captured.

`ready` determines whether the logger is ready for experiment traffic.

`stop` performs graceful termination and waits for the acquisition process.

`validate` evaluates the logger artifacts after acquisition has stopped.

`describe` exposes retained provenance and runtime information for manifest
generation.

### 13.2 Adapter context

Every enabled logger adapter shall receive a run-scoped context containing at
least:

- experiment_id;
- run_id;
- run directory;
- raw artifact directory;
- runtime log directory;
- repository root;
- experiment configuration reference;
- adapter-specific configuration.

The adapter shall not invent a second experiment or run identity.

### 13.3 Process metadata

For every started logger, the process supervisor shall retain at least:

- adapter name;
- enabled state;
- mandatory or optional role;
- exact command and arguments;
- PID;
- stdout path;
- stderr path;
- process start time in UTC;
- readiness time in UTC where applicable;
- process stop time in UTC;
- requested stop signal;
- actual exit code;
- whether signal escalation was required;
- produced artifact paths.

This metadata shall remain available even when the logger fails.

### 13.4 Readiness semantics

Readiness shall be adapter-specific but bounded by an explicit timeout.

A readiness check shall never wait indefinitely.

Examples of acceptable readiness evidence include:

- an explicit READY marker emitted by the collector;
- successful creation of the expected output stream;
- receipt of the first structurally valid sample;
- another deterministic adapter-specific health condition.

A process merely existing is not sufficient readiness evidence when stronger
evidence is available.

Mandatory logger readiness failure shall block transition to RUNNING.

Optional logger readiness failure shall be recorded and handled according to
the experiment configuration.

### 13.5 Stop semantics

The runner shall request graceful termination through the adapter.

For the initial resource and native telemetry collectors, SIGINT is the
preferred stop signal.

After sending the configured graceful signal, the process supervisor shall
wait for a bounded timeout.

If the process has already exited, the original exit state shall be retained
rather than replaced with an artificial success state.

Any escalation beyond the preferred signal shall be explicit and recorded.

### 13.6 Validation semantics

Logger validation shall occur only after the acquisition process has stopped
and its output files have been closed.

Validation may include:

- expected artifact existence;
- non-empty mandatory artifact checks;
- structural validation where applicable;
- readiness evidence;
- process exit information;
- timestamp presence;
- adapter-specific consistency checks.

Validation shall not modify raw artifacts.

### 13.7 Initial adapter mapping

The initial harness shall map existing project components as follows:

Resource logger:
`scripts/tb3-resource-network-observer.py`

Native telemetry logger:
`scripts/tb3-native-metrics-receiver.sh`

Optional KPM logger:
`components/kpm-readonly-collector`

The compact native metrics collector is not the canonical raw acquisition
adapter because it transforms the received telemetry into a reduced textual
representation.

### 13.8 Adapter isolation

A logger adapter shall own only the process or processes that it explicitly
started.

It shall not terminate unrelated processes that happen to match a command
name.

Cleanup shall therefore use captured process identifiers rather than broad
commands such as process-name based kill operations.

The runner shall never use logger cleanup as an implicit infrastructure restart
mechanism.

## 14. Traffic and actuator adapter contract

Experiment input shall be separated from acquisition logging.

The runner shall invoke experiment inputs through explicit adapters rather than
embedding traffic-generator or actuator-specific commands directly into the
main orchestration logic.

### 14.1 Traffic adapter role

The initial traffic adapter represents the controlled traffic input used by the
current Sci_O-RAN experiments.

The traffic adapter shall expose sufficient information to reproduce the input,
including at least:

- traffic adapter name and version where applicable;
- exact command and arguments;
- traffic direction;
- source and destination endpoints;
- configured rate or load;
- configured duration;
- protocol and port where applicable;
- stdout path;
- stderr path;
- PID where applicable;
- exit code;
- start and stop information.

The runner shall retain the exact invoked command rather than reconstructing it
later from descriptive metadata.

### 14.2 Traffic execution semantics

Traffic execution shall begin only after all mandatory acquisition adapters
have passed readiness validation.

The runner owns the canonical experiment start and end timestamps.

The canonical experiment start timestamp shall be recorded immediately before
traffic invocation.

The canonical experiment end timestamp shall be recorded immediately after the
controlled traffic execution interval has terminated.

Traffic adapter failure shall be retained as run evidence and shall not trigger
an implicit retry using the same run_id.

A retry shall create a new run_id.

### 14.3 Traffic process supervision

If traffic execution creates a process, that process shall be supervised using
the same principles as acquisition processes:

- exact command retention;
- PID capture;
- dedicated stdout and stderr artifacts;
- bounded execution;
- explicit exit-code capture;
- controlled cleanup.

Traffic cleanup shall affect only processes explicitly created by the adapter.

### 14.4 Runtime actuator adapter role

A future runtime actuator adapter may supplement or replace static traffic
input.

The actuator interface shall therefore remain logically independent from the
traffic adapter.

The actuator adapter may represent commands such as runtime parameter changes,
resource-control actions, scheduling changes, or other validated control
operations.

The main experiment lifecycle shall not need redesign when an actuator is
introduced.

### 14.5 Actuation event record

Every runtime actuation command shall generate a timestamped event record.

At minimum, an actuation event shall retain:

- experiment_id;
- run_id;
- actuator name;
- action sequence number;
- command or requested control value;
- UTC request timestamp;
- UTC completion timestamp where applicable;
- resulting status;
- exit code or equivalent result;
- error information where applicable.

Actuation events shall be preserved as experiment evidence.

### 14.6 Determinism and hidden behaviour

Traffic and actuator adapters shall not silently change experiment parameters.

Defaults that affect scientific interpretation shall be explicit in experiment
configuration or retained adapter metadata.

Neither adapter shall restart infrastructure components unless the experiment
configuration explicitly defines such an action as part of the scientific
procedure.

### 14.7 Input validation

Before RUNNING begins, the configured input adapter shall validate its required
parameters.

Examples include:

- syntactically valid traffic rate;
- positive duration;
- valid endpoint information;
- required executable availability;
- valid actuator parameter range where known.

Invalid mandatory input configuration shall prevent transition to RUNNING.

### 14.8 Input provenance

The run manifest shall distinguish between:

- configured input;
- exact executed input;
- observed execution result.

This distinction prevents intended parameters from being confused with what
was actually executed.

The adapter shall expose sufficient retained metadata for all three views.

## 15. Canonical status mapping and acceptance policy

The runner may use internal lifecycle states for orchestration, but retained
metadata shall use the canonical vocabulary defined by the Sci_O-RAN dataset
schema.

### 15.1 Internal-to-schema run status mapping

The canonical mapping is:

- internal COMPLETED maps to run_status `completed`;
- internal FAILED maps to run_status `failed`;
- internal INTERRUPTED maps to run_status `aborted`;
- internal REJECTED maps to run_status `rejected`.

The internal lifecycle vocabulary shall not be written directly into schema
fields when the schema defines a different canonical value.

### 15.2 Completed versus accepted

A technically completed run is not automatically accepted scientific evidence.

`run_status = completed` means that the configured operational workflow
finished and mandatory technical validation completed successfully.

`run_status = accepted` means that the run has additionally been designated as
the accepted evidence-producing execution for its experiment.

These meanings shall remain distinct.

### 15.3 Acceptance gate

Acceptance shall occur only after retained evidence is available for review.

At minimum, acceptance requires:

- successful mandatory artifact validation;
- required metadata availability;
- identifier consistency;
- required checksum availability;
- no unresolved mandatory logger failure;
- no unresolved traffic execution failure;
- no known condition that invalidates the scientific run.

The harness shall not infer acceptance solely from file existence or process
exit code zero.

### 15.4 accepted_run_id semantics

When a run is accepted, the corresponding experiment record may set:

`accepted_run_id = <run_id>`

A failed, aborted, rejected, or merely completed but not yet accepted run shall
not silently replace an existing accepted_run_id.

If no run has yet been accepted, accepted_run_id shall remain null.

### 15.5 Failed and aborted evidence

Failed and aborted runs remain part of provenance.

Their retained artifacts, timestamps, commands, exit information, and failure
reason shall remain available for diagnosis and reproducibility analysis.

A retry after failed, aborted, or rejected execution shall receive a new
run_id.

### 15.6 Rejection semantics

A run may be operationally complete yet scientifically rejected.

Such a run shall retain:

`run_status = rejected`

and its evidence shall remain preserved.

Rejection shall not delete raw data or rewrite the historical execution record.

### 15.7 Experiment-level status

Experiment-level status and run-level status shall remain separate.

An experiment may contain several operational runs while only one run is
ultimately accepted as evidence.

The experiment record shall therefore describe the scientific condition,
whereas run records describe individual execution attempts.

## 16. Storage and artifact layout contract

The experiment harness shall use the canonical Sci_O-RAN dataset hierarchy
rather than introduce a parallel experiment-storage model.

### 16.1 Canonical raw run path

The canonical run-scoped raw-data path is:

    raw/<experiment_id>/<run_id>/<namespace>/

Every raw scientific artifact produced by an enabled acquisition or input
adapter shall be retained below this hierarchy.

Examples include:

    raw/<experiment_id>/<run_id>/native_gnb/
    raw/<experiment_id>/<run_id>/host_cpu/
    raw/<experiment_id>/<run_id>/container/
    raw/<experiment_id>/<run_id>/netif/
    raw/<experiment_id>/<run_id>/traffic/
    raw/<experiment_id>/<run_id>/iperf/
    raw/<experiment_id>/<run_id>/oran_kpm/

Only namespaces defined by the canonical dataset schema shall be used for
schema-governed artifact records.

### 16.2 Experiment and run isolation

Every operational execution shall have its own unique run_id directory below
its experiment_id.

A second execution attempt shall never reuse or overwrite the raw directory of
a previous run.

The invariant is:

    experiment_id
        -> one scientific experiment
        -> one or more run_id values
        -> isolated raw artifacts for every run

A failed, aborted, or rejected run therefore remains physically distinguishable
from a later retry.

### 16.3 Metadata separation

Experiment, run, and artifact metadata shall remain logically separate from raw
measurement bytes.

The canonical dataset hierarchy places metadata below:

    metadata/experiments/
    metadata/runs/
    metadata/artifacts/

The harness shall retain references from metadata records to raw artifacts
using dataset-relative paths.

Raw data files shall not be modified to embed metadata that can instead be
represented in the canonical metadata model.

### 16.4 Runtime diagnostic output

Adapter stdout that constitutes the actual measurement stream shall be
preserved as a raw artifact in the corresponding scientific namespace.

Adapter stderr and runner diagnostic information shall also be preserved when
required to explain execution outcome, but diagnostic retention shall not
change the scientific namespace of measurement artifacts.

The manifest shall distinguish measurement artifacts from diagnostic process
information.

### 16.5 Artifact closure

An artifact becomes checksum-eligible only after the producing process has
terminated or otherwise closed the file.

The harness shall not calculate the final retained SHA-256 value while the file
is still being written.

After closure, the runner shall determine at least:

- dataset-relative path;
- byte size;
- SHA-256 digest;
- data level;
- namespace;
- validation status.

These values provide the basis for the canonical artifact inventory.

### 16.6 Run finalization checksums

During run finalization, the harness shall calculate SHA-256 digests for
retained run artifacts after acquisition closure.

The calculated digests shall be retained in run and artifact metadata used for
provenance and integrity checking.

The harness shall not create a competing checksum convention with different
digest semantics.

### 16.7 Dataset-level checksum manifest

The canonical archival checksum manifest remains:

    checksums/SHA256SUMS

It is a dataset-package-level object.

Its entries shall use:

    <sha256-hex>  <dataset-relative-path>

and shall be sorted lexicographically by path.

The checksum manifest shall not include itself recursively.

Run finalization therefore computes the exact per-artifact digests required for
later dataset packaging, while archival packaging constructs the canonical
dataset-level SHA256SUMS inventory.

### 16.8 Processed and derived separation

The harness shall not place normalized, parsed, synchronized, aggregated, or
analysed output back into the raw run directory.

Processed data shall use the canonical hierarchy:

    processed/<schema_version>/<experiment_id>/<run_id>/<namespace>/

Derived analytical results shall use:

    derived/<analysis_id>/

Every processed or derived artifact shall remain traceable to its retained raw
source through artifact and processing-provenance metadata.

### 16.9 No destructive overwrite

Existing experiment, run, or raw-artifact paths shall not be silently
overwritten.

Before acquisition begins, the runner shall verify that the target run_id does
not already identify an existing retained run directory.

A path collision shall cause pre-run failure rather than destructive reuse.

## 17. Run manifest contract

Every operational execution shall produce a machine-readable harness run
manifest.

The harness manifest records orchestration evidence that is more detailed than
the canonical dataset run record, while remaining linked to canonical
experiment, run, and artifact metadata.

### 17.1 Separation from dataset metadata

The harness run manifest shall not replace the canonical dataset metadata
schema.

The canonical dataset model remains responsible for:

- experiment records;
- run records;
- artifact records;
- processing provenance records.

The harness manifest records execution-specific orchestration details and
references the corresponding canonical identifiers.

No field in the harness manifest shall redefine the scientific meaning of
experiment_id, run_id, artifact_id, namespace, data_level, or validation
status.

### 17.2 Manifest identity and location

The recommended repository-side logical location is:

    manifests/runs/<experiment_id>/<run_id>.json

The manifest filename shall be derived from run_id and shall not be reused by
another execution.

The manifest shall contain both experiment_id and run_id internally so that
identity does not depend solely on its path.

### 17.3 Minimum manifest sections

The operational run manifest shall contain at least the following logical
sections:

- identity;
- lifecycle;
- timestamps;
- repository_state;
- environment;
- configuration;
- collectors;
- traffic;
- actuator;
- processes;
- artifacts;
- validation;
- checksums;
- failure;
- final_status.

Fields that are not applicable shall be represented explicitly where the
manifest contract requires presence rather than being silently omitted.

### 17.4 Identity section

The identity section shall retain at least:

- experiment_id;
- run_id;
- harness manifest version;
- creation time in UTC.

The harness shall never generate a second scientific identity for the same run.

### 17.5 Lifecycle and timestamp section

The manifest shall retain lifecycle progress sufficiently to identify the last
successfully entered or completed stage.

Relevant UTC timestamps shall include, where available:

- manifest creation;
- precheck;
- logger startup;
- logger readiness;
- canonical experiment start;
- canonical experiment end;
- cooldown completion;
- postcheck;
- logger stop;
- validation;
- finalization.

Missing timestamps caused by failure shall not be replaced with fabricated
values.

### 17.6 Repository state

The repository_state section shall retain at least:

- Git branch;
- full 40-character HEAD commit;
- whether the working tree was clean;
- relevant uncommitted-state information when the tree was not clean.

The manifest shall not claim that a run corresponds to a clean committed state
when uncommitted changes affected execution.

### 17.7 Software and environment references

The environment section shall retain references to the applicable project
manifests, including where relevant:

- host manifest;
- software manifest;
- Docker image manifest;
- deployment configuration;
- clock synchronization evidence.

Referenced lightweight configuration files shall be identified by stable
repository-relative paths where possible.

### 17.8 Configuration integrity

Configuration inputs that affect experimental interpretation shall be
checksum-addressable.

For each retained configuration file used by the run, the manifest shall record
at least:

- repository-relative or dataset-relative path;
- SHA-256 digest;
- role in the experiment.

The recorded digest shall correspond to the exact bytes used by the run.

### 17.9 Collector records

Every configured collector shall have an explicit manifest record.

The record shall distinguish at least:

- enabled;
- disabled;
- not_applicable;
- startup_failed;
- readiness_failed;
- stopped;
- validation_failed.

For a started collector, the record shall retain:

- adapter name;
- namespace or namespaces;
- mandatory or optional role;
- exact command;
- PID;
- stdout path;
- stderr path;
- start timestamp;
- readiness result;
- stop signal;
- stop timestamp;
- exit code;
- escalation information where applicable.

### 17.10 Traffic record

The traffic section shall distinguish:

- configured traffic input;
- exact executed traffic command;
- observed execution result.

It shall retain applicable traffic parameters, command, timestamps, process
information, stdout, stderr, and exit code.

A failed traffic execution shall remain represented in the manifest.

### 17.11 Actuator record

When no runtime actuator is enabled, the actuator section shall state that
explicitly.

When runtime actuation is enabled, the manifest shall reference or contain the
ordered timestamped actuation event records defined by the actuator contract.

### 17.12 Artifact inventory

Every retained run artifact shall be represented in the manifest or referenced
through its canonical artifact metadata record.

For finalized files, the retained information shall include at least:

- logical role;
- namespace;
- data level;
- dataset-relative path;
- byte size;
- SHA-256 digest;
- validation status.

The artifact inventory shall distinguish measurement data from diagnostic
process output.

### 17.13 Process exit information

Exit information shall be retained even when execution is unsuccessful.

The runner shall not normalize every process outcome to success merely because
cleanup completed.

Where a process terminates because of the runner's requested graceful signal,
the manifest shall preserve enough information to distinguish expected
termination from an unexpected collector failure.

### 17.14 Failure record

The failure section shall identify, where available:

- lifecycle stage;
- component or adapter;
- UTC failure time;
- error category;
- exit code or signal;
- retained error message;
- whether cleanup completed;
- whether evidence remains usable for diagnosis.

A failure record shall never cause automatic deletion of already closed raw
artifacts.

### 17.15 Manifest update policy

The harness manifest shall be created early in the run lifecycle after run_id
allocation rather than only after successful completion.

Lifecycle progress shall be persisted as execution proceeds so that an aborted
or failed run retains useful orchestration evidence.

Manifest updates shall use an atomic replacement strategy where practical so
that interruption does not intentionally leave a partially written JSON file.

### 17.16 Finalization semantics

During FINALIZATION, the runner shall:

- stop all owned background processes;
- ensure retained artifact files are closed;
- calculate final byte sizes and SHA-256 digests;
- complete artifact validation results;
- record final process outcomes;
- record the canonical terminal status;
- write the finalized harness manifest.

Finalization shall not silently convert FAILED, INTERRUPTED, or REJECTED
execution into successful execution.

### 17.17 Deterministic serialization

The finalized JSON manifest shall use deterministic serialization rules.

At minimum:

- UTF-8 encoding;
- stable key ordering;
- no non-deterministic generated field ordering;
- RFC 3339 UTC timestamp representation;
- explicit manifest version.

Deterministic serialization supports reproducible hashing, review, and
comparison between execution records.

### 17.18 Sensitive and environment-specific information

The manifest shall retain enough information for reproducibility without
unnecessarily exposing secrets.

Authentication tokens, passwords, private keys, session credentials, and other
secret material shall never be copied into the manifest.

Where a command contains a secret-bearing argument, retained command metadata
shall use an explicit redacted representation while preserving the
non-sensitive reproducibility context.

## 18. Implementation module layout

The initial implementation shall remain modular and shall not place the entire
experiment lifecycle into one monolithic shell script.

### 18.1 Harness implementation root

The implementation shall reside below:

    scripts/experiment-harness/

The initial logical structure is:

    scripts/experiment-harness/
      run-experiment.sh
      lib/
        common.sh
        identity.sh
        process-supervisor.sh
        manifest.sh
        validation.sh
      adapters/
        resource-observer.sh
        native-telemetry.sh
        traffic.sh
        kpm.sh

The exact set of files may evolve, but the separation of runner, reusable
lifecycle functions, process supervision, manifest handling, validation, and
adapter-specific logic shall be preserved.

### 18.2 Main runner responsibility

`run-experiment.sh` shall provide the top-level orchestration lifecycle.

Its responsibilities shall include:

- parsing validated experiment configuration;
- invoking PRECHECK;
- resolving experiment_id;
- generating run_id;
- creating run-scoped paths;
- coordinating metadata snapshot;
- invoking enabled adapters;
- recording canonical experiment timestamps;
- coordinating cooldown and postcheck;
- requesting logger shutdown;
- invoking validation;
- invoking finalization;
- returning a meaningful process exit code.

The main runner shall not directly implement collector-specific acquisition
logic.

### 18.3 Common library

`lib/common.sh` shall contain only generic harness utilities.

Examples include:

- UTC timestamp generation;
- logging helpers;
- repository-root resolution;
- path validation;
- deterministic file writing helpers;
- generic error reporting.

It shall not contain native gNB, KPM, or traffic-specific behaviour.

### 18.4 Identity library

`lib/identity.sh` shall be responsible for deterministic identity handling.

It shall validate experiment_id against the canonical project convention and
generate a unique run_id.

Identity generation shall detect path and manifest collisions before
acquisition begins.

A collision shall cause failure rather than automatic overwrite.

### 18.5 Process supervisor library

`lib/process-supervisor.sh` shall own generic background-process lifecycle
operations.

Its responsibilities shall include:

- process startup;
- PID capture;
- stdout and stderr redirection;
- readiness-support metadata;
- bounded graceful termination;
- exit-code capture;
- signal-escalation recording;
- owned-process cleanup.

The supervisor shall operate only on PIDs explicitly created by the harness.

### 18.6 Manifest library

`lib/manifest.sh` shall own operational harness manifest persistence.

It shall support:

- early manifest creation after run_id allocation;
- atomic manifest replacement where practical;
- lifecycle-state updates;
- process metadata updates;
- artifact inventory updates;
- failure recording;
- deterministic final serialization.

It shall not replace the canonical Sci_O-RAN dataset schema.

### 18.7 Validation library

`lib/validation.sh` shall contain generic run validation operations.

Examples include:

- required artifact existence;
- non-empty mandatory artifact checks;
- identifier consistency;
- timestamp presence;
- checksum availability;
- manifest completeness;
- mandatory adapter outcome checks.

Adapter-specific structural validation shall remain inside the corresponding
adapter or an adapter-specific validator.

### 18.8 Adapter implementation boundary

Each file below `adapters/` shall translate one concrete experiment component
into the common logical adapter lifecycle.

The initial mapping is:

    resource-observer.sh
        -> scripts/tb3-resource-network-observer.py

    native-telemetry.sh
        -> scripts/tb3-native-metrics-receiver.sh

    traffic.sh
        -> controlled traffic generator invocation

    kpm.sh
        -> optional components/kpm-readonly-collector integration

An adapter shall not redefine the global experiment lifecycle.

### 18.9 Configuration boundary

Scientific experiment parameters shall not be hard-coded throughout multiple
implementation files.

The runner shall receive or resolve one explicit experiment configuration
source whose retained values determine enabled adapters and experiment input.

Implementation defaults that affect scientific interpretation shall be
documented and persisted.

### 18.10 Exit-code boundary

The top-level runner shall return a meaningful non-zero exit code when the run
does not complete its required operational workflow.

Internal helper failures shall propagate to the runner through explicit return
codes rather than being silently ignored.

Cleanup operations shall preserve the original primary failure reason when
possible.

### 18.11 Incremental implementation rule

Implementation shall proceed in small validated increments.

The initial code shall establish only the minimum runner framework required to
exercise lifecycle and failure handling.

Adapters shall then be integrated one at a time.

A large all-in-one harness implementation shall not be introduced in a single
change.

## 19. Multi-namespace source capture policy

Some acquisition tools may emit one original stream containing measurements
belonging to several canonical Sci_O-RAN namespaces.

The current resource and network observer is such a source.

### 19.1 Resource observer semantics

`scripts/tb3-resource-network-observer.py` emits one JSONL stream containing,
within the same records:

- host CPU measurements;
- CPU-frequency measurements;
- load measurements;
- memory measurements;
- host network-interface and qdisc measurements;
- container resource and network measurements.

These measurements correspond to the canonical semantic namespaces:

- host_cpu;
- cpu_freq;
- load;
- memory;
- netif;
- container.

The acquisition tool itself is not a scientific namespace.

### 19.2 No false namespace assignment

The harness shall not assign the complete combined resource-observer stream to
one arbitrary canonical namespace merely to satisfy a singular namespace field.

In particular, the complete stream shall not be labelled solely as host_cpu,
container, netif, or another individual namespace when its retained contents
span several measurement semantics.

The harness shall also not introduce a tool-specific namespace such as
resource_observer without an explicit future dataset-schema decision.

### 19.3 Original source preservation

The original combined JSONL emitted by the resource observer shall be preserved
byte-for-byte as an acquisition source capture.

After acquisition closure it shall be treated as immutable retained evidence.

The harness shall record at least:

- source tool identity;
- experiment_id;
- run_id;
- exact command;
- capture path;
- byte size;
- SHA-256 digest;
- validation result;
- the set of canonical measurement namespaces represented by the source.

### 19.4 Harness versus canonical artifact metadata

Until the canonical dataset schema explicitly defines representation of one
physical raw artifact spanning several namespaces, the harness shall not
fabricate a schema-governed artifact record with scientifically incorrect
namespace metadata.

The combined source capture may therefore be represented first in the
operational harness manifest as source-level acquisition evidence.

This is a compatibility safeguard, not permission to omit provenance.

### 19.5 Deterministic namespace extraction

Canonical namespace-specific representations may subsequently be generated by
a deterministic processing step.

Conceptually:

    combined resource-observer source capture
        -> host_cpu
        -> cpu_freq
        -> load
        -> memory
        -> netif
        -> container

Such namespace-specific outputs are transformations of the retained source and
shall therefore not silently replace the original capture.

Their data level and processing provenance shall be assigned according to the
canonical dataset specification.

### 19.6 No acquisition-time destructive split

The initial resource adapter shall not destructively split, filter, normalize,
or rewrite the collector stdout before retaining the original source capture.

A tee or additional processing operation may be introduced later only if the
original byte stream remains independently preserved.

### 19.7 Schema evolution boundary

If later dataset packaging requires a first-class canonical representation of
multi-namespace raw source artifacts, that requirement shall be addressed as an
explicit dataset-schema evolution decision.

The experiment harness shall not silently change the Prompt 08 namespace
semantics or metadata schema as an implementation shortcut.
