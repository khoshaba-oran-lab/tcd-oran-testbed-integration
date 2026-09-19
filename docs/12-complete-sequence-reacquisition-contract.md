# Prompt 12 complete-sequence reacquisition contract

CONTRACT_ID=PROMPT12-COMPLETE-SEQUENCE-REACQUISITION-V1-DRAFT
CONTRACT_STATUS=APPROVED_CONTENT_PENDING_REPOSITORY_CHECKPOINT
SOURCE_COMMIT=bf77e078203fae30043e15d306b916648894e386

## 1. Purpose

This contract defines the reacquisition needed to identify and validate a
SISO model across all six Prompt-12 PRB transitions. It preserves the frozen
design in `docs/12-siso-system-identification-design.md`.

## 2. Required repetitions

Each repetition shall execute one continuous sequence:

    13 -> 26 -> 39 -> 52 -> 39 -> 26 -> 13 PRB
     T1    T2    T3    T4    T5    T6

The required model-use classes are:

| Repetition | Model-use class |
|---|---|
| R01 | estimation |
| R02 | estimation |
| R03 | estimation |
| R04 | holdout validation |

The frozen totals are:

    COMPLETE_SEQUENCE_COUNT=4
    TRANSITIONS_PER_SEQUENCE=6
    TOTAL_VALID_TRANSITIONS=24

## 3. Continuity

Within each repetition, the offered workload, receiver measurement, gNB,
UE, 5GC, and RIC shall remain continuous. A workload restart is permitted
only between complete repetitions. Partial runs shall not be concatenated.

## 4. Admission and transition gates

R01-R04 shall start at a verified 13-PRB applied readback. The initial
operating point requires at least 11 seconds of valid pre-step observation
and a passing output-stationarity gate.

For every transition:

- the trigger is attempted exactly once;
- command and acknowledgement evidence is retained;
- exactly one expected applied readback is observed;
- applied readback defines scientific time zero;
- intervals straddling time zero are excluded;
- at least 10 seconds of valid post-step observation is retained;
- post-step stationarity passes;
- workload, receiver, and process continuity pass;
- no gNB, UE, or 5GC restart occurs.

The stationary post-state of one transition may serve as the pre-state of
the next transition in the same continuous repetition.

## 5. Fail-closed rule

If any trigger, readback, stationarity, continuity, timeout, or evidence
gate fails, no later transition in that repetition may be triggered. The
partial evidence shall be preserved, but the repetition shall not count as
valid. A replacement requires fresh repetition and operation identities.
Consumed identities and scientific triggers shall never be replayed.

## 6. Required evidence

Each repetition shall retain raw receiver output, control events, applied
readback, stationarity results, continuity and restart checks, orchestration
reports, excluded time-zero-straddling intervals, provenance, and a verified
SHA256 manifest.

A repetition is valid only when all six transitions occur in the frozen
order and the final sequence gate passes.

## 7. Dataset isolation

R01-R03 may be used for model-family comparison, order selection, parameter
estimation, residual analysis, and estimation-only cross-validation.

R04 shall remain inaccessible until the model family, order, parameters,
and acceptance thresholds have been frozen. R04 shall not be used for
fitting, selection, threshold adjustment, or controller tuning. Failure on
R04 shall be reported as validation failure rather than repaired by refit.

## 8. Existing evidence

The current separate T1-T6 dataset remains immutable qualification and
exploratory evidence. It does not replace R01-R04 and shall not be silently
relabelled as estimation or holdout data.

The accepted historical T1 ARX1 result remains a prior local T1 result. It
shall not be automatically generalised to T2-T6 or pooled with the new
complete sequences.

## 9. Implementation reuse

The existing six-transition orchestrator, bounded supervisor, atomic
prestart, trigger executor, stationarity evaluator, receiver pipeline, and
their tests form the reuse baseline. A replacement orchestrator is not
authorised. Any required change shall be limited to demonstrated interface
or parameterisation gaps and authorised separately.

## 10. Boundaries and next gate

This contract does not select a model family or order and does not authorise
model fitting, controller tuning, R01, or any new PRB actuation.

Before R01 can be considered, the repository contract must be checked,
exact invocations must be resolved, relevant tests must pass, and a dry-run
without scientific actuation must pass.

R01_AUTHORISED=NO
SCIENTIFIC_TRIGGER_AUTHORISED=NO
MODEL_FITTING_AUTHORISED=NO
NEXT_REQUIRED_GATE=CONTRACT_REPOSITORY_CHECKPOINT
