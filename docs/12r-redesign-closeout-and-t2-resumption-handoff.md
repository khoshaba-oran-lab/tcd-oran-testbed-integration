# Prompt 12R Redesign Closeout and T2 Resumption Handoff

## 1. Purpose

This record closes the architectural redesign phase introduced after the
Prompt 12 T2 execution path demonstrated unacceptable operational fragility.

Prompt 12R is not a replacement for Prompt 12 scientific identification.

Its purpose was to make the scientific execution boundary substantially more
fail-closed, observable and replay-safe before additional live PRB experiments
are attempted.

The governing scientific rule remains:

`MODEL_VALID = PLATFORM_HEALTHY`

Platform failure, tooling failure and scientific plant response must remain
separate causal categories.

## 2. Redesign status

The Prompt 12R redesign phase is now considered logically complete.

No further open-ended architectural redesign is authorised merely because an
additional improvement could be imagined.

Any work after this closeout must be justified directly by the minimum
requirements for returning to live Prompt 12 T2 experimental acquisition.

This is an explicit scope-creep stop.

## 3. Runtime boundary at redesign closeout

The experimental runtime remains intentionally stopped.

The last clean day-stop established:

`DAY_STOP_OPERATION_ID=lifecycle-day-stop-20260827T183759Z-4bd62d3f`

`DAY_STOP_TEARDOWN_OPERATION_ID=lifecycle-teardown-20260827T183759Z-4bd62d3f`

Current intended runtime state:

`STOPPED_CLEAN`

Prompt 12R redesign work did not require day-start.

No new scientific PRB control was executed during redesign.

## 4. T2 scientific status at redesign closeout

Prompt 12 T2 remains:

`T2 = 26 -> 39 PRB`

T2 is not scientifically closed yet.

The currently frozen valid scientific estimation count remains:

`1 / 3`

The valid repetition is T2 R03.

Its scientific trigger was consumed and must never be repeated.

The existing valid R03 evidence remains authoritative.

T2 R01V3 remains:

`ABANDONED_PRETRIGGER_ZERO_SCIENTIFIC_CONTROL`

R01V3 does not count as a scientific estimation repetition.

Its historical run identity remains:

`RUN-20260827T180525Z-54020`

That invalid historical run identity must not be rewritten.

R01V3 did not consume a scientific trigger.

No R01V4 has been executed.

R04 remains unauthorised until the estimation-set requirements applicable at
the time of resumption are satisfied.

## 5. Principal root causes preserved by Prompt 12R

Prompt 12R established several important causal findings.

### 5.1 Ad-hoc identity construction was unsafe

R01V3 used an invalid run identity that bypassed sufficiently early canonical
identity validation.

The repository-wide Prompt 12 run ID contract remains:

`^RUN-[0-9]{8}T[0-9]{6}Z-[0-9]{3}$`

Identity validation must occur before experiment side effects.

### 5.2 Offline replay required a deterministic executor clock

The original executor used the current wall clock even during historical
no-control replay.

Prompt 12R introduced a deterministic injected executor timestamp for
`mode=no-control` only.

The live FIFO path explicitly forbids that override.

### 5.3 Trigger delivery has an irreversible ambiguity boundary

A successful trigger establishes:

`SCIENTIFIC_TRIGGER_CONSUMED=YES`

and:

`SCIENTIFIC_TRIGGER_REPLAY_DECISION=NEVER_REPEAT`

If a trigger write is attempted but delivery cannot be proved, the
transaction must preserve:

`SCIENTIFIC_TRIGGER_CONSUMED=UNKNOWN`

and:

`SCIENTIFIC_TRIGGER_REPLAY_DECISION=NEVER_AUTOMATICALLY_REPLAY`

The ambiguous path is:

`PRESTEP_ADMITTED -> INVALID_POSTTRIGGER`

It is not a pretrigger abort and it is not a proven exactly-once trigger.

### 5.4 Platform health must not be absorbed into the plant model

Existing Doctor/readiness tooling already covers substantial platform health,
including:

- host resource readiness;
- disk headroom;
- base-container readiness;
- network readiness;
- ZMQ readiness;
- N2 readiness;
- E2 readiness;
- E2SM-RC readiness;
- UE session readiness;
- user-plane readiness;
- traffic-harness readiness;
- process-incarnation continuity.

Prompt 12R therefore did not create a competing replacement health framework.

## 6. Durable Prompt 12R deliverables

The following redesign deliverables are now repository records.

### 6.1 Offline precontrol qualification

`docs/12r-offline-toolchain-qualification.md`

This records offline replay qualification of:

`raw receiver evidence`
`-> parser`
`-> canonicalizer`
`-> latest-50 selection`
`-> output stationarity`
`-> freshness`
`-> precontrol admission`
`-> deterministic no-control executor`

### 6.2 Qualified executor repair

`scripts/experiment-harness/prompt12-precontrol-trigger-executor.py`

The repair supports deterministic offline replay without weakening live FIFO
timing semantics.

Dedicated executor regression tests exist at:

`scripts/experiment-harness/tests/test_prompt12_precontrol_trigger_executor.py`

### 6.3 Platform-health contract

`docs/12r-platform-health-contract.md`

This separates:

`PLATFORM_QUALIFIED`

from:

`INITIAL_STATE_VERIFIED`

and preserves the rule:

`MODEL_VALID = PLATFORM_HEALTHY`

### 6.4 Experiment transaction state machine

`docs/12r-experiment-transaction-state-machine.md`

The normal prospective transaction path is:

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

Failure transaction states are:

- `ABORTED_PRETRIGGER`;
- `INVALID_POSTTRIGGER`.

Causal failure classes are:

- `PLATFORM_FAILURE`;
- `TOOLING_FAILURE`.

### 6.5 Machine-readable transaction schema

`datasets/schemas/sci-oran-prompt12r-experiment-transaction-v1.0.0.schema.json`

It uses JSON Schema Draft 2020-12.

Trigger-consumption values are:

- `NO`;
- `YES`;
- `UNKNOWN`.

### 6.6 Offline transaction-transition validator

`scripts/experiment-harness/prompt12r-validate-transaction-transition.py`

The qualified validator enforces, among other properties:

- legal state transitions;
- no illegal backward transition;
- immutable transaction identity;
- monotonic transition time;
- write-once evidence identities;
- previous-record semantic validity;
- exactly-once trigger semantics;
- ambiguous trigger semantics;
- replay protection;
- initial-state invariants;
- failure-class continuity;
- invalid post-trigger adjudication protection.

A temporary offline regression matrix exercised 20 cases.

Observed result:

`REGRESSION_CASE_COUNT=20`

`REGRESSION_FAILURE_COUNT=0`

`TRANSACTION_VALIDATOR_QUALIFICATION_GATE=PASS`

No live runtime or scientific control was used by that qualification.

## 7. Prompt 12R checkpoint chain

Important redesign checkpoints include:

`9b2b1d2fc751fae5bd21fc6fe5096ca9069a9a65`
`prompt12r: qualify offline precontrol toolchain`

`73ab60296862ac82fb9d9693f9c9a52b3e701d82`
`prompt12r: define platform health contract`

`67231c55fabbbf026b0219edfe99b19d48af07c1`
`prompt12r: define experiment transaction state machine`

`4bceba64cfb4ce64d2d14bab43b2345544890a86`
`prompt12r: define experiment transaction schema`

`b63f776843744630dd3a28861a74e20ec3e75e34`
`prompt12r: fix ambiguous trigger write semantics`

`6bf1d1a810806d56d52dc0a39386e3e6947cbd68`
`prompt12r: qualify experiment transaction validator`

No push is asserted by this closeout record.

## 8. Scope-stop decision

Prompt 12R must not continue as an indefinite architecture-improvement
project.

The following are explicitly not sufficient reasons to reopen broad redesign:

- a possible cleaner abstraction;
- another schema refactor;
- another generic orchestration framework;
- an optional logging enhancement;
- a desirable but non-blocking telemetry extension;
- additional architectural documentation with no direct live-science gate.

Future changes must be tied to a concrete T2 resumption blocker.

## 9. Minimum remaining live-science gates

Several items identified during redesign remain relevant, but from this point
they are classified as **T2 resumption gates**, not open-ended Prompt 12R
deliverables.

They are:

1. zero-restart admission for the four base runtime containers;
2. explicit stale-iperf process cleanliness before workload admission;
3. transaction binding and bounded freshness of platform qualification;
4. trustworthy read-only verification of the current initial PRB state;
5. bounded-duration / settling / stationarity execution policy derived from
   existing evidence rather than an arbitrary long-duration run;
6. a narrow prospective protocol amendment that binds these gates into the
   resumed T2 execution.

These items should be implemented only to the minimum degree required for
safe T2 acquisition.

They must not become another general redesign programme.

## 10. Highest-priority unresolved scientific-operational issue

The most important unresolved gate is:

`INITIAL_STATE_VERIFIED`

For T2, the experiment must prove the current initial state is 26 PRB before a
new 26 -> 39 scientific trigger.

Historical evidence of a previous applied control must not be treated as proof
of the current state.

No new PRB control is authorised merely to manufacture this proof.

A trustworthy current-state mechanism must therefore be resolved before a new
scientific T2 trigger.

## 11. Bounded-duration direction

The resumed experiment should not default to another arbitrary 3600-second
observation.

Existing T1 and T2 evidence should be used to define:

- minimum pre-step observation;
- stationarity admission;
- minimum post-step observation;
- settling/stationarity completion;
- maximum timeout.

The experiment should terminate when the scientific evidence requirement is
satisfied or when a bounded timeout invalidates the acquisition.

This is a scientific execution requirement, not an invitation for additional
generic framework redesign.

## 12. Return-to-science decision

The next project phase is:

`PROMPT 12 — RESUME T2 EXPERIMENTAL ACQUISITION`

It is not:

`CONTINUE PROMPT 12R ARCHITECTURE REDESIGN`

The resumed phase must first clear the minimum T2 resumption gates listed
above.

After those gates pass, a new scientific T2 estimation repetition may be
considered explicitly.

No scientific trigger is authorised by this closeout record itself.

## 13. One-action-at-a-time execution policy for the resumed phase

The resumed experimental phase must retain the strict operational protocol:

1. classify the immediately completed Action only as PASS, FAIL, BLOCKED or
   NOT_EXECUTED;
2. provide exactly one next Action;
3. wait for complete stdout/stderr before another Action;
4. repository/source/runtime/scientific/evidence work runs directly on
   `tb3-dell`;
5. lifecycle day-start/day-stop/deploy/teardown/recovery runs directly on
   `coll.vntu.org`;
6. never bundle sequential Actions;
7. prefer read-only inspection before writes;
8. never replay a consumed scientific trigger;
9. no new scientific PRB control without explicit authorisation;
10. after a partially changing failure, perform read-only forensics before a
    retry;
11. preserve important root causes and scientific boundaries in repository
    records/evidence.

## 14. New-chat handoff objective

The next chat should begin from repository records rather than reconstructing
Prompt 12R from conversation history.

Its objective is:

1. verify repository/checkpoint/runtime identity;
2. confirm Prompt 12R redesign is closed;
3. convert only the six minimum live-science gates into executable admission
   checks;
4. derive the bounded T2 duration/stationarity policy from frozen historical
   T1/T2 evidence;
5. produce the narrow T2 protocol amendment;
6. perform lifecycle start only when required;
7. qualify the platform observationally before scientific preparation;
8. establish trustworthy current 26-PRB initial state;
9. prepare a fresh T2 repetition transaction;
10. execute a new 26 -> 39 trigger only after every required pretrigger gate
    passes and explicit authorisation is reached;
11. adjudicate and close the resulting scientific repetition;
12. continue toward completing T2 rather than reopening broad redesign.

## 15. Final Prompt 12R boundary

At this closeout boundary:

- Prompt 12R architectural redesign is logically complete;
- offline precontrol qualification is PASS;
- platform-health contract is defined;
- transaction state machine is defined;
- machine-readable transaction schema is defined;
- ambiguous trigger semantics are resolved;
- offline transaction validator qualification is PASS with 20/20 cases;
- runtime remains intentionally stopped;
- no new scientific trigger has been executed;
- T2 remains scientifically incomplete at 1 valid estimation repetition;
- broad redesign scope is closed;
- the next phase is controlled return to T2 experimental acquisition.
