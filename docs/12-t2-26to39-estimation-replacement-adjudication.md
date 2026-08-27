# Prompt 12 T2 26-to-39 PRB estimation replacement adjudication

## Status

This record adjudicates how the frozen Prompt 12 T2 protocol is to proceed after
the observed R01, R02 and R03 acquisition outcomes.

This record does **not** modify the frozen T2 scientific protocol, candidate
model families, model-selection metric, validation rules, stationarity
thresholds, timing thresholds, or holdout contract.

No scientific control is authorised by this record alone.

## Frozen source rules

The frozen base SISO design states that a failed or incomplete attempt:

- is retained as diagnostic evidence;
- does not increment the valid repetition count;
- shall be replaced by another attempt of the same directed step in an
  explicitly recorded replacement run if necessary.

The frozen T2 protocol requires:

- three valid estimation replications;
- logical estimation roles R01, R02 and R03;
- one true unseen holdout R04;
- R04 acquisition only after the three valid estimation replications,
  model-family selection, model refit/freeze, and T2-specific validation
  thresholds are frozen.

Every successful scientific or reset trigger is NEVER_REPEAT.

## R01 adjudication

Historical T2 R01 executed a scientific 26-to-39 PRB trigger.

Its final evidence records:

- scientific trigger consumed = YES;
- trigger replay allowed = NO;
- trigger-to-applied timing gate = PASS;
- final-sample-to-applied timing gate = FAIL;
- T2 repetition timing gate = FAIL.

Therefore historical R01 is:

`INVALID_DIAGNOSTIC_REPETITION_NEVER_REPEAT`

It does not count toward the three valid T2 estimation replications.

Logical estimation slot `ESTIMATION_R01` therefore remains scientifically
unfilled.

A future replacement for this slot must:

- be an explicitly recorded replacement acquisition;
- preserve canonical logical slot R01;
- use canonical T2 R01 experiment identity semantics;
- use a new unique RUN_ID;
- use a new unique trigger;
- never reuse or replay the historical consumed R01 trigger;
- satisfy every frozen T2 admission, timing, stationarity and evidence gate.

For human-readable provenance the replacement may be described as an R01
replacement / R01V2-style scientific label, analogous to the frozen T1 R03V2
precedent, while its canonical logical T2 repeat slot remains R01.

## R02 adjudication

Historical T2 R02 was closed before scientific trigger consumption.

Its final evidence records:

- scientific result = NOT_VALID_SCIENTIFIC_REPETITION;
- scientific trigger consumed = NO;
- closed namespace must not be replayed/reused.

Therefore historical R02 is:

`ABANDONED_PRETRIGGER_DIAGNOSTIC_ATTEMPT`

It does not count toward the three valid T2 estimation replications.

Logical estimation slot `ESTIMATION_R02` remains scientifically unfilled.

The frozen failed-pretrigger policy permits a fresh R02 run only as a distinct
acquisition with:

- a new unique RUN_ID;
- a new unique trigger/token;
- a new evidence root;
- no reuse of the abandoned R02 run/token;
- proof of the required zero-control pretrigger state for the newly prepared
  actuator context before any scientific trigger is delivered.

The logical scientific role remains `ESTIMATION_R02`.

## R03 adjudication

Historical T2 R03 is already:

`CLOSED_VALIDATED`

Its final scientific gate is PASS.

It occupies logical estimation slot:

`ESTIMATION_R03`

Its consumed trigger is NEVER_REPEAT.

No replacement R03 is required or authorised.

## Current valid estimation count

At this adjudication boundary:

- R01 valid estimation contribution: 0;
- R02 valid estimation contribution: 0;
- R03 valid estimation contribution: 1.

Therefore:

`T2_VALID_ESTIMATION_REPETITION_COUNT=1`

and:

`T2_REQUIRED_VALID_ESTIMATION_REPETITION_COUNT=3`

Two valid logical estimation slots remain to be filled:

1. R01 replacement;
2. fresh R02 acquisition.

## R04 firewall

R04 remains:

`TRUE_UNSEEN_VALIDATION`

R04 is **NOT_AUTHORIZED** at this boundary.

Before R04 can exist, the frozen protocol still requires:

1. valid R01-slot replacement;
2. valid R02-slot fresh acquisition;
3. preserved valid R03;
4. frozen three-replication estimation set;
5. per-replication steady gains;
6. leave-one-replication-out model-family selection;
7. selected-family refit using all three estimation replications;
8. frozen model parameters;
9. frozen T2 steady-gain APE validation limit;
10. frozen T2 dynamic NRMSE validation limit.

## Never-repeat boundary

The following historical controls are not to be replayed:

- consumed invalid T2 R01 scientific trigger;
- consumed valid T2 R03 scientific trigger;
- all previously consumed T2 reset triggers.

No new PRB control is executed by this adjudication.

## Current next scientific requirement

The next acquisition-level scientific requirement is to fill the unresolved
R01 logical estimation slot with a separately evidenced replacement run.

Before that run is executed, the testbed must separately pass the normal
lifecycle, initial-state, workload, prearm, freshness and pre-step stationarity
admission sequence required by the frozen T2 protocol.
