# Prompt 12R experiment transaction state machine

## 1. Purpose

Prompt 12R replaces ad-hoc scientific shell sequences with an explicit,
fail-closed experiment transaction.

The transaction exists to preserve the distinction between:

1. experimental-platform health;
2. plant initial state;
3. scientific workload readiness;
4. exactly-once scientific actuation;
5. post-trigger plant observation;
6. scientific adjudication.

The central scientific rule remains:

`MODEL_VALID = PLATFORM_HEALTHY`

No state transition defined here authorises a live scientific PRB control.

This document is prospective and does not rewrite frozen T1 or T2 evidence.

## 2. Existing implementation semantics to preserve

Repository inspection established several existing mechanisms that must be
reused rather than replaced.

### 2.1 Canonical identity validation

Shared Prompt 12 identity rules already require canonical experiment and run
identities.

Identity validation must occur before creation of scientific side effects.

The historical R01V3 five-digit run-ID defect demonstrated why this ordering
is mandatory.

### 2.2 Doctor readiness

`scripts/sci-oran-doctor.sh`

already provides the authoritative platform readiness result:

`SCI_ORAN_READY_GATE`

and:

`FAILURE_REASON`

Prompt 12R platform qualification must consume that result and strengthen it
only where the Prompt 12 scientific contract requires additional admission
rules.

### 2.3 Generic experiment harness

`scripts/experiment-harness/run-experiment.sh`

already provides generic precheck, metadata, logger, traffic, postcheck,
finalisation and terminal-status handling.

It is useful infrastructure but is not by itself a sufficient Prompt 12R
scientific transaction state machine.

### 2.4 Six-transition orchestrator

`scripts/experiment-harness/prompt12-six-transition-orchestrator.py`

already encodes:

- frozen T1-T6 transition order;
- admission dependencies;
- initial stationarity admission;
- previous-post-step stationarity admission;
- applied-readback time origin;
- continuity requirements;
- live control disabled in dry-run orchestration.

It represents useful orchestration semantics but currently does not provide
the full runtime transaction states defined in this document.

### 2.5 Atomic prestart

`scripts/experiment-harness/prompt12-atomic-prestart.py`

already provides:

- final precontrol revalidation;
- freshness checks;
- a live/simulate separation;
- at-most-one Docker start invocation;
- fail-closed handling after a start invocation;
- `NEVER_REPEAT_AFTER_START_INVOCATION` semantics.

The prospective transaction must preserve those exactly-once boundaries.

### 2.6 Atomic control executor

`scripts/experiment-harness/prompt12-precontrol-trigger-executor.py`

already provides:

- `EXECUTOR_GATE`;
- explicit fail-closed reasons;
- trigger write attempt count;
- trigger write success count;
- scientific-trigger-consumed status;
- `NEVER_REPEAT` after successful scientific trigger delivery;
- `NEVER_AUTOMATICALLY_REPLAY` after an attempted write whose final outcome
  cannot safely be repeated automatically.

These semantics are authoritative for the scientific-trigger boundary.

## 3. Transaction identity

Every prospective scientific transaction must have a unique immutable
transaction identity.

The transaction identity must bind at least:

- experiment ID;
- run ID;
- repository HEAD;
- scientific protocol version;
- platform qualification evidence;
- runtime incarnation;
- initial-state evidence;
- workload evidence;
- actuator identity;
- trigger identity;
- scientific evidence namespace.

A new transaction must never silently inherit mutable state from a previous
transaction.

## 4. Two-dimensional state model

Prompt 12R distinguishes:

1. `TRANSACTION_STATE`;
2. `FAILURE_CLASS`.

This prevents platform/tooling cause from being confused with the scientific
point at which failure occurred.

### 4.1 Transaction state

Canonical success-path states are:

`NEW`
`DEPLOYED`
`PLATFORM_QUALIFIED`
`INITIAL_STATE_VERIFIED`
`ACTUATOR_ARMED`
`WORKLOAD_READY`
`PRESTEP_ADMITTED`
`TRIGGERED_EXACTLY_ONCE`
`APPLIED_VERIFIED`
`POSTSTEP_COMPLETE`
`SCIENTIFICALLY_ADJUDICATED`
`CLOSED`
`DESTROYED`

Failure-path transaction states are:

`ABORTED_PRETRIGGER`

and:

`INVALID_POSTTRIGGER`

### 4.2 Failure class

Canonical failure classes are:

`NONE`
`PLATFORM_FAILURE`
`TOOLING_FAILURE`

Once the irreversible trigger-attempt boundary has been crossed, an
invalid or ambiguous acquisition is represented by the
`INVALID_POSTTRIGGER` transaction state, with the causal failure class
preserved separately.

This includes both a confirmed consumed trigger followed by failure and an
ambiguous trigger-write attempt whose consumption status is `UNKNOWN`.

This avoids ambiguous values such as treating `PLATFORM_FAILURE` sometimes as
a state and sometimes as a cause.

## 5. Trigger boundary

The most important transaction boundary is the first scientific trigger write
attempt.

This is an irreversible replay-risk boundary.

Before any trigger write attempt:

`SCIENTIFIC_TRIGGER_CONSUMED=NO`

After successful trigger delivery:

`SCIENTIFIC_TRIGGER_CONSUMED=YES`

and:

`SCIENTIFIC_TRIGGER_REPLAY_DECISION=NEVER_REPEAT`

If a write attempt occurs but software cannot prove whether delivery
completed, the transaction must preserve:

`SCIENTIFIC_TRIGGER_CONSUMED=UNKNOWN`

and:

`SCIENTIFIC_TRIGGER_REPLAY_DECISION=NEVER_AUTOMATICALLY_REPLAY`

Such an ambiguous write-attempt outcome must not be classified as
`ABORTED_PRETRIGGER` and must not pass through
`TRIGGERED_EXACTLY_ONCE`, because successful exactly-once delivery was not
proved.

It moves directly from `PRESTEP_ADMITTED` to `INVALID_POSTTRIGGER`.

Human or automated logic must never infer replay safety merely because later
processing failed.

## 6. State: NEW

`NEW` means:

- canonical experiment identity has been validated;
- canonical run identity has been validated;
- a unique transaction namespace has been allocated logically;
- no experiment side effect has yet occurred.

Required invariant:

`SCIENTIFIC_TRIGGER_CONSUMED=NO`

Forbidden in `NEW`:

- workload launch;
- actuator start;
- PRB control;
- scientific trigger;
- mutation of an earlier experiment namespace.

Failure before leaving `NEW` is:

`ABORTED_PRETRIGGER`

with failure class:

`TOOLING_FAILURE`

unless the cause is explicitly platform-related.

## 7. Transition NEW -> DEPLOYED

`DEPLOYED` means that the required experimental platform incarnation exists.

Deployment itself belongs to lifecycle tooling and is not performed by the
scientific qualification probe.

Required evidence must identify the runtime incarnation.

The transaction must not advance merely because a previous day-start once
succeeded.

## 8. State: DEPLOYED

Required invariant:

- expected runtime incarnation exists;
- scientific trigger not consumed;
- no scientific workload has been started by this transaction.

`DEPLOYED` does not imply healthy.

A deployed but unhealthy runtime must fail before scientific preparation.

## 9. Transition DEPLOYED -> PLATFORM_QUALIFIED

This transition requires the contract defined in:

`docs/12r-platform-health-contract.md`

At minimum:

`PLATFORM_QUALIFIED=PASS`

must be bound to the same runtime incarnation as the transaction.

Failure results in:

`TRANSACTION_STATE=ABORTED_PRETRIGGER`

and:

`FAILURE_CLASS=PLATFORM_FAILURE`

No scientific trigger may be issued.

## 10. State: PLATFORM_QUALIFIED

The infrastructure is fit to host the experiment.

This state does not prove the current PRB operating point.

Therefore:

`PLATFORM_QUALIFIED != INITIAL_STATE_VERIFIED`

The separation is mandatory.

## 11. Transition PLATFORM_QUALIFIED -> INITIAL_STATE_VERIFIED

This transition requires fresh evidence of the actual plant starting state.

For a transition such as T2 26 -> 39 PRB, the transaction must prove that the
plant currently has the required 26-PRB initial state.

Historical final state from an earlier run is insufficient.

An old `PRB_ACTUATOR_APPLIED` line is insufficient unless it is demonstrably
bound to the current runtime incarnation and current state.

The exact prospective read-only verification mechanism remains to be
implemented and qualified.

No new PRB control is authorised solely to satisfy this state.

## 12. State: INITIAL_STATE_VERIFIED

Required invariant:

- platform qualification still belongs to the current runtime incarnation;
- actual initial PRB state equals the protocol-required value;
- no scientific trigger has been consumed.

If the initial state is wrong, the transaction must not advance.

Any required recovery/reset is a separate authorised operation, not an
implicit transaction transition.

After recovery, platform and initial-state qualification must be repeated.

## 13. Transition INITIAL_STATE_VERIFIED -> ACTUATOR_ARMED

The actuator may be prepared only after initial-state verification.

Arming is not scientific triggering.

Required conditions include:

- exact actuator identity;
- exact command target;
- no unexpected actuator restart;
- no prior trigger consumed for this transaction;
- control channel/FIFO identity belongs uniquely to this transaction;
- trigger token belongs uniquely to this transaction.

A reused FIFO or trigger token is prohibited.

## 14. State: ACTUATOR_ARMED

Required invariant:

`SCIENTIFIC_TRIGGER_CONSUMED=NO`

The actuator is capable of accepting the future exactly-once trigger, but no
scientific PRB transition has yet occurred.

Failure at this state remains pretrigger failure.

## 15. Transition ACTUATOR_ARMED -> WORKLOAD_READY

The scientific receiver and workload path are prepared.

The existing receiver readiness repair must be reused.

Receiver readiness requires the timestamped observation:

`Server listening on 5201`

and a consistent live receiver-container state.

Docker `Running=true` by itself is insufficient.

The prospective stale-iperf cleanliness gate must also pass before new
workload ownership is accepted.

## 16. State: WORKLOAD_READY

Required invariants include:

- unique receiver belongs to the current transaction;
- receiver application readiness = PASS;
- stale iperf contamination = absent;
- workload source/destination/rate match the scientific protocol;
- receiver acquisition timestamps are active;
- trigger not consumed.

This state does not yet mean that the output is stationary.

## 17. Transition WORKLOAD_READY -> PRESTEP_ADMITTED

The existing frozen precontrol chain is reused:

`receiver acquisition`
`-> parser`
`-> canonicalizer`
`-> latest-50 complete contiguous selection`
`-> output stationarity`
`-> freshness`
`-> precontrol admission`

The final admission must satisfy the frozen timing requirements.

For the existing Prompt 12 contract this includes:

- minimum pre-step duration;
- stationarity threshold;
- latest complete contiguous samples;
- bounded freshness;
- causal timestamp ordering.

## 18. State: PRESTEP_ADMITTED

This is the final state from which a scientific trigger may be considered.

Required invariants:

- platform still valid;
- runtime incarnation unchanged;
- initial PRB state not invalidated;
- actuator armed;
- workload/receiver continuous;
- final output stationarity = PASS;
- final freshness = PASS;
- no trigger yet consumed.

There must be no human round-trip between a final freshness decision and a
live exactly-once trigger if that round-trip can violate the freshness bound.

## 19. Transition PRESTEP_ADMITTED -> TRIGGERED_EXACTLY_ONCE

This transition is the irreversible scientific boundary.

It is performed only through the qualified atomic executor.

Required precondition:

`EXECUTOR_GATE=PASS`

Successful transition requires:

- exactly one write attempt;
- exactly one successful write;
- control executed;
- scientific trigger consumed.

Expected evidence:

`TRIGGER_WRITE_ATTEMPT_COUNT=1`

`TRIGGER_WRITE_SUCCESS_COUNT=1`

`CONTROL_EXECUTED=YES`

`SCIENTIFIC_TRIGGER_CONSUMED=YES`

`SCIENTIFIC_TRIGGER_REPLAY_DECISION=NEVER_REPEAT`

Once these conditions occur, the transaction must never return to a
pretrigger state.

## 20. State: TRIGGERED_EXACTLY_ONCE

The scientific trigger is consumed.

This state is irreversible.

Any subsequent tooling or platform failure cannot convert the transaction
back into an unconsumed attempt.

No automatic retry of the same scientific trigger is allowed.

## 21. Transition TRIGGERED_EXACTLY_ONCE -> APPLIED_VERIFIED

The plant step is scientifically established only by authoritative applied
readback.

The time origin remains:

`U_APPLIED_READBACK`

Required causal ordering follows the frozen Prompt 12 contract.

A command submission without applied readback is not sufficient.

If the trigger was consumed but applied state cannot be verified, the
transaction cannot be treated as an ordinary pretrigger abort.

It proceeds to post-trigger invalidation.

## 22. State: APPLIED_VERIFIED

Required evidence includes the authoritative applied state.

For PRB control this includes:

- applied minimum PRB;
- applied maximum PRB;
- applied-readback timestamp.

Scientific plant time zero is bound to applied readback, not command-send
time and not acknowledgement time.

## 23. Transition APPLIED_VERIFIED -> POSTSTEP_COMPLETE

Post-step acquisition continues until the prospective bounded completion
policy is satisfied.

The current redesign does not freeze that duration policy yet.

The future policy must use evidence-based settling/stationarity criteria and
a bounded timeout rather than arbitrary long fixed-duration acquisition.

Throughout this state:

- receiver continuity must remain valid;
- platform continuity must remain valid;
- timestamp ordering must remain valid;
- no additional scientific trigger is allowed.

## 24. State: POSTSTEP_COMPLETE

Required evidence must establish that the post-step acquisition is complete
according to the prospective bounded-duration policy.

Completion does not yet mean that the run is scientifically valid.

Scientific adjudication remains mandatory.

## 25. Transition POSTSTEP_COMPLETE -> SCIENTIFICALLY_ADJUDICATED

Scientific adjudication must separate:

- valid plant response;
- platform failure;
- tooling failure;
- timing violation;
- continuity violation;
- stationarity failure;
- malformed evidence;
- other protocol violations.

A platform or tooling anomaly must not be fitted into the plant model.

## 26. State: SCIENTIFICALLY_ADJUDICATED

The run has an explicit scientific disposition.

Possible successful disposition includes a valid estimation/validation
repetition.

Possible unsuccessful disposition includes a post-trigger invalid scientific
acquisition.

The exact model-selection implications belong to the prospective protocol
amendment, not to this state-machine document.

## 27. Transition SCIENTIFICALLY_ADJUDICATED -> CLOSED

`CLOSED` means:

- scientific disposition is frozen;
- trigger replay decision is frozen;
- evidence manifest is frozen;
- required checksums are frozen;
- transaction outcome is immutable.

Closing a scientifically invalid run does not make it valid.

`CLOSED` means administratively and evidentially complete.

## 28. State: CLOSED

No scientific activity is permitted.

The transaction may proceed only to destruction of disposable runtime
resources or archival operations that do not rewrite scientific evidence.

## 29. Transition CLOSED -> DESTROYED

`DESTROYED` means disposable transaction-specific runtime objects have been
removed through authorised lifecycle/cleanup mechanisms.

Destruction must not remove frozen scientific evidence.

A new scientific attempt requires a new transaction identity.

## 30. Pretrigger failure path

Any failure before the first scientific trigger write attempt must produce:

`TRANSACTION_STATE=ABORTED_PRETRIGGER`

and:

`SCIENTIFIC_TRIGGER_CONSUMED=NO`

The causal class must be recorded separately.

Examples:

### Platform cause

`FAILURE_CLASS=PLATFORM_FAILURE`

Examples include:

- Doctor readiness failure;
- base-container restart count non-zero;
- runtime incarnation changed;
- network path failure;
- E2/N2 failure;
- UE session failure;
- disk/resource admission failure;
- stale iperf contamination.

### Tooling cause

`FAILURE_CLASS=TOOLING_FAILURE`

Examples include:

- malformed identity;
- parser failure;
- canonicalizer invocation failure;
- missing required file;
- freshness executor defect;
- invalid transaction namespace.

Pretrigger abort permits creation of a future fresh transaction, but does not
permit mutation/reuse of the failed transaction identity.

## 31. Confirmed post-trigger failure path

Any failure after the scientific trigger is confirmed consumed must never be
represented as `ABORTED_PRETRIGGER`.

The transaction must enter:

`TRANSACTION_STATE=INVALID_POSTTRIGGER`

with:

`SCIENTIFIC_TRIGGER_CONSUMED=YES`

and the causal class retained.

Examples:

`FAILURE_CLASS=PLATFORM_FAILURE`

or:

`FAILURE_CLASS=TOOLING_FAILURE`

The consumed trigger remains:

`SCIENTIFIC_TRIGGER_REPLAY_DECISION=NEVER_REPEAT`

The invalid acquisition must remain as diagnostic/evidence material but must
not silently enter the model estimation set.

## 32. Ambiguous write-attempt outcome

If a trigger write was attempted but software cannot prove whether delivery
completed, successful exactly-once triggering has not been established.

The transaction must fail closed directly as:

`PRESTEP_ADMITTED -> INVALID_POSTTRIGGER`

with:

`TRIGGER_WRITE_ATTEMPT_COUNT=1`

`TRIGGER_WRITE_SUCCESS_COUNT=0`

`SCIENTIFIC_TRIGGER_CONSUMED=UNKNOWN`

`SCIENTIFIC_TRIGGER_REPLAY_DECISION=NEVER_AUTOMATICALLY_REPLAY`

The transaction must not enter `ABORTED_PRETRIGGER`, because a plant-side
effect may already have occurred.

It must also not enter `TRIGGERED_EXACTLY_ONCE`, because successful delivery
was not proved.

This conservative rule prevents duplicate scientific input steps when the
write outcome is uncertain.

## 33. Recovery separation

The scientific transaction must not perform hidden recovery.

It must not silently:

- restart containers;
- rebuild Docker networks;
- restart Docker;
- kill stale workloads;
- reset PRB;
- redeploy RIC;
- relaunch gNB/UE/5GC;
- replay trigger.

Recovery is an explicit lifecycle operation.

After recovery, the previous platform qualification is invalid.

A fresh scientific transaction must re-establish:

`DEPLOYED`
`-> PLATFORM_QUALIFIED`
`-> INITIAL_STATE_VERIFIED`

before any scientific preparation continues.

## 34. State monotonicity

Transaction states are monotonic.

Forbidden backward transitions include:

`PRESTEP_ADMITTED -> WORKLOAD_READY`

`TRIGGERED_EXACTLY_ONCE -> PRESTEP_ADMITTED`

`APPLIED_VERIFIED -> ACTUATOR_ARMED`

`CLOSED -> SCIENTIFICALLY_ADJUDICATED`

`DESTROYED -> CLOSED`

If a prerequisite becomes invalid before the trigger, the transaction aborts.

If a prerequisite becomes invalid after the trigger, the transaction is
post-trigger invalid.

It does not move backwards.

## 35. Evidence-before-transition rule

Every state transition must be evidence-driven.

The durable transaction record must identify:

- previous state;
- requested next state;
- transition decision timestamp;
- gate values;
- evidence paths;
- evidence SHA256 values;
- repository HEAD;
- runtime-incarnation binding;
- trigger-consumption status;
- failure class if applicable.

A state must never be advanced based only on conversational context or operator
memory.

## 36. Side-effect ordering

The general ordering rule is:

`validate -> observe -> decide -> side effect`

not:

`side effect -> inspect whether prerequisites were valid`

Examples:

- identity validation before namespace/workload creation;
- platform qualification before initial-state verification;
- receiver readiness before client launch;
- final freshness before trigger;
- exactly-once trigger before applied-state verification.

This ordering directly addresses the failure modes discovered in Prompt 12.

## 37. Idempotence classes

Operations are divided into three classes.

### 37.1 Read-only/idempotent

Examples:

- repository inspection;
- Doctor evidence parsing;
- checksum verification;
- offline parser/canonicalizer replay;
- stationarity evaluation;
- platform-health evidence evaluation.

These may be repeated when their input identity is unchanged.

### 37.2 Replaceable pretrigger setup

Examples may include transaction-local preparation that has not consumed a
scientific trigger.

If replacement is required, it must occur under an explicit new transaction
or authorised cleanup boundary.

### 37.3 Irreversible scientific side effects

Examples:

- scientific trigger write;
- applied plant step.

These are not replayable.

## 38. Historical-class mapping

Historical Prompt 12 records are not renamed.

Examples such as:

`ABANDONED_PRETRIGGER_ZERO_SCIENTIFIC_CONTROL`

`ABANDONED_PRETRIGGER_DIAGNOSTIC_ATTEMPT`

`INVALID_DIAGNOSTIC_REPETITION_NEVER_REPEAT`

`CLOSED_VALIDATED`

remain frozen exactly as recorded.

For prospective Prompt 12R transactions they map conceptually to the new
state/failure model, but historical files must not be rewritten merely to
match new terminology.

## 39. Minimum prospective transaction record

A future machine-readable transaction record should contain at least:

- schema version;
- transaction ID;
- experiment ID;
- run ID;
- transition label;
- repository HEAD;
- protocol identity;
- transaction state;
- previous transaction state;
- failure class;
- failure reason;
- platform qualification identity;
- runtime incarnation identity;
- initial PRB required;
- initial PRB observed;
- receiver/workload identity;
- actuator identity;
- precontrol admission result;
- trigger write attempt count;
- trigger write success count;
- scientific trigger consumed;
- replay decision;
- applied-readback identity;
- post-step completion result;
- scientific adjudication result;
- closeout checksum identity.

## 40. Required state-transition legality

The normal legal path is exactly:

`NEW`
`-> DEPLOYED`
`-> PLATFORM_QUALIFIED`
`-> INITIAL_STATE_VERIFIED`
`-> ACTUATOR_ARMED`
`-> WORKLOAD_READY`
`-> PRESTEP_ADMITTED`
`-> TRIGGERED_EXACTLY_ONCE`
`-> APPLIED_VERIFIED`
`-> POSTSTEP_COMPLETE`
`-> SCIENTIFICALLY_ADJUDICATED`
`-> CLOSED`
`-> DESTROYED`

Pretrigger failure path:

`NEW|DEPLOYED|PLATFORM_QUALIFIED|INITIAL_STATE_VERIFIED|`
`ACTUATOR_ARMED|WORKLOAD_READY|PRESTEP_ADMITTED`
`-> ABORTED_PRETRIGGER`
`-> CLOSED`
`-> DESTROYED`

Confirmed post-trigger invalid path:

`TRIGGERED_EXACTLY_ONCE|APPLIED_VERIFIED|POSTSTEP_COMPLETE`
`-> INVALID_POSTTRIGGER`
`-> SCIENTIFICALLY_ADJUDICATED`
`-> CLOSED`
`-> DESTROYED`

Ambiguous trigger-write path:

`PRESTEP_ADMITTED`
`-> INVALID_POSTTRIGGER`
`-> SCIENTIFICALLY_ADJUDICATED`
`-> CLOSED`
`-> DESTROYED`

The ambiguous path is legal only after exactly one trigger write attempt whose
successful delivery cannot be proved. Its required consumption status is
`UNKNOWN` and its replay decision is `NEVER_AUTOMATICALLY_REPLAY`.

No other state transition is implicitly legal.

## 41. Implementation consequence

The next implementation should not immediately create a live executor.

The safe sequence is:

1. define a machine-readable transaction schema;
2. implement an offline state-transition validator;
3. create positive and negative regression fixtures;
4. prove illegal backward transitions fail closed;
5. prove pretrigger and post-trigger failure classification;
6. prove consumed-trigger replay protection;
7. only then integrate observational platform-health evidence;
8. only after all offline gates pass consider a live transaction driver.

## 42. Current boundary

Prompt 12R now has:

- offline precontrol-toolchain qualification;
- a platform-health architecture contract;
- a prospective experiment transaction state machine.

Still unresolved before live science:

- machine-readable transaction schema and validator;
- stale-iperf cleanliness implementation;
- zero-restart Prompt 12 admission implementation;
- platform-qualification binding/freshness implementation;
- trustworthy `INITIAL_STATE_VERIFIED` current-PRB mechanism;
- bounded-duration/settling-time policy;
- prospective Prompt 12 protocol-v2 amendment.

No R01V4 or other new scientific PRB trigger is authorised by this document.
