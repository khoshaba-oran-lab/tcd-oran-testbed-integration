# Prompt 12 T2 26->39 PRB resumption protocol v2 amendment

## 1. Scope

This document is a narrow prospective amendment for resuming Prompt 12 T2,
the SISO transition:

    26 PRB -> 39 PRB

It does not reopen the Prompt 12R architecture redesign.

It does not modify historical T2 evidence.

It does not authorise a scientific PRB trigger by itself.

The frozen Prompt 12 scientific design and the existing T2 protocol remain in
force except where this amendment adds explicit pretrigger platform-safety and
bounded-duration requirements.

## 2. Model-validity boundary

Scientific interpretation is permitted only when:

    MODEL_VALID = PLATFORM_HEALTHY

Failures of the following must not be absorbed into identified plant dynamics:

- gNB;
- UE;
- 5GC;
- RIC;
- E2;
- Docker runtime;
- lifecycle network;
- measurement transport;
- workload process;
- storage capacity;
- timestamp integrity;
- telemetry freshness.

A platform failure invalidates the acquisition as platform evidence rather than
as a plant-response sample.

## 3. Runtime-incarnation qualification

Before a fresh T2 transaction may advance to scientific admission, platform
qualification shall be bound to the exact live runtime incarnation used by that
transaction.

At minimum:

- expected 5GC container is present and healthy;
- expected gNB container is present and healthy;
- expected UE container is present and healthy;
- expected RIC container is present and healthy;
- the lifecycle network identity is correct;
- the expected frozen gNB image/configuration identity is present;
- qualification evidence is fresh relative to the transaction;
- later restart or runtime replacement invalidates the qualification.

Platform qualification from an earlier runtime incarnation is not sufficient.

## 4. Zero-restart gate

Immediately before scientific admission:

    5GC RestartCount = 0
    gNB RestartCount = 0
    UE RestartCount = 0
    RIC RestartCount = 0

If any required container has restarted, the current platform qualification is
invalid and the transaction shall not advance to PRESTEP_ADMITTED.

## 5. Stale workload cleanliness

Before starting the receiver/workload pair for a fresh transaction, stale iperf
state shall be explicitly excluded.

The pre-workload gate shall prove that no stale iperf client or server process
from an earlier attempt can contaminate the new receiver stream.

A failed stale-workload cleanliness gate is a pretrigger failure.

No scientific trigger may be issued after that failure.

## 6. Initial-state verification

T2 requires:

    INITIAL_STATE_VERIFIED = 26 PRB

This shall refer to the actual current plant state of the exact qualified
runtime incarnation.

The following are insufficient on their own:

- a historical final state;
- an old PRB_ACTUATOR_APPLIED record;
- a previous experiment's applied readback;
- an assumed state inherited from an earlier runtime.

No new scientific 26->39 PRB control may be issued merely to discover whether
the starting state is 26 PRB.

If the current 26-PRB state cannot be established prospectively and
trustworthily, the scientific transaction remains blocked.

A separately authorised reset-to-26 operation remains distinct from a T2
scientific repetition. Any such reset trigger is itself exactly-once and must
never be replayed after consumption. Following reset/recovery, platform and
initial-state qualification shall be repeated and bound to the resulting live
runtime incarnation.

This amendment does not yet claim that a trustworthy prospective
INITIAL_STATE_VERIFIED mechanism has been qualified.

## 7. Frozen pre-step admission

The frozen Prompt 12 rules remain:

    STARTUP_GUARD_S = 1
    PRE_STEP_MINIMUM_DURATION_S = 11
    STATIONARITY_WINDOW_S = 5
    SAMPLES_PER_WINDOW = 25
    CV_MAX_PCT = 5
    MEAN_SHIFT_MAX_PCT = 5

The scientific trigger is permitted only after:

    elapsed pre-step >= 11 s
    AND OUTPUT_STATIONARITY_GATE = PASS
    AND platform qualification remains valid
    AND INITIAL_STATE_VERIFIED = 26 PRB
    AND stale-workload cleanliness = PASS
    AND zero-restart gate = PASS

## 8. Frozen post-step stationarity cadence

The existing Prompt 12 adaptive completion rule remains unchanged.

The first post-step decision occurs after two complete non-overlapping 5 s
windows.

Therefore:

    POST_STEP_MINIMUM_DURATION_S = 10

If stationarity fails, exactly one additional non-overlapping 5 s window is
collected and the two most recent windows are reevaluated.

Thus decision checkpoints are:

    10 s
    15 s
    20 s
    25 s
    30 s

subject to receiver/timestamp alignment around the applied-readback origin.

The stationarity criterion remains:

    CV_y(W1) <= 5 percent
    CV_y(W2) <= 5 percent
    relative mean shift <= 5 percent

## 9. Evidence-derived maximum post-step timeout

Historical first frozen-cadence stationarity PASS observations used for this
prospective bound are:

| Evidence | First PASS after applied readback |
|---|---:|
| T1 R01 | 20.063178 s |
| T1 R02 | 20.059179 s |
| T1 R03V2 | 15.143840 s |
| T1 R04 holdout | 19.959443 s |
| T2 R03 retrospective frozen-cadence evaluation | 10.016375 s |

The maximum observed first-pass time is:

    20.063178 s

A prospective maximum post-step timeout is therefore frozen for resumed T2 as:

    POST_STEP_MAX_TIMEOUT_S = 30

This value:

- lies on the frozen 5 s reevaluation cadence;
- exceeds every observed first-pass duration above;
- provides approximately 9.94 s margin above the observed maximum;
- provides two complete additional 5 s reevaluation opportunities beyond the
  approximately 20 s historical maximum;
- replaces the earlier arbitrary 3600 s workload-duration practice for this
  resumed T2 acquisition.

The experiment shall terminate at the first permitted frozen-cadence
stationarity PASS.

If no PASS has occurred by the 30 s bound, the acquisition shall not continue
indefinitely. It shall be closed as a bounded posttrigger scientific failure
according to the transaction-state contract.

## 10. Scientific trigger boundary

A fresh 26->39 PRB scientific trigger is authorised only when all required
pretrigger gates are simultaneously PASS.

In particular:

    PLATFORM_QUALIFIED = PASS
    ZERO_RESTART_GATE = PASS
    STALE_WORKLOAD_CLEANLINESS_GATE = PASS
    INITIAL_STATE_VERIFIED = 26 PRB
    PRESTEP_ADMITTED = PASS

The trigger remains exactly-once.

After trigger consumption:

    SCIENTIFIC_TRIGGER_CONSUMED = YES
    REPLAY_DECISION = NEVER_REPEAT

An ambiguous trigger outcome is never automatically replayed.

## 11. Current resumption status

This amendment resolves the bounded-duration requirement prospectively.

It does not resolve the remaining current-state proof requirement.

Therefore the next live T2 scientific repetition remains:

    NOT_YET_AUTHORISED

until the prospective 26-PRB INITIAL_STATE_VERIFIED mechanism is resolved and
all live platform gates pass on the exact runtime incarnation.
