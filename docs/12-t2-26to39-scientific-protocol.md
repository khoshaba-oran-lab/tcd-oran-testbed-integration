# Prompt 12 T2: 26→39 PRB Scientific Protocol

Protocol ID: `PROMPT12-T2-26TO39-V1.0.0`

Status: **FROZEN_OFFLINE_PENDING_GIT_CHECKPOINT**

Frozen UTC: `2026-08-24T16:06:46Z`

Repository parent: `e4c244e0e707c806aef32b5fa5172ce8b90e9cf9`
Branch: `feat/prompt12-siso-identification`

## 1. Scientific boundary

T1 = 13→26 PRB is already CLOSED, VALIDATED and NEVER_REPEAT.

T2 = 26→39 PRB has not started.

This protocol freeze does **not** authorize day-start, workload, reset,
E2SM-RC Control, or PI/PID synthesis.

`T2_EXECUTION_AUTHORIZED=NO`

The next authorization boundary is a separate Git checkpoint plus verified
remote synchronization of this protocol.

## 2. T2 transition identity

- Transition: T2
- Direction: upward
- Initial allocation: 50% = 26 PRB
- Target allocation: 75% = 39 PRB
- Delta u: +13 PRB
- Synthetic workload w(t): UDP DL 18 Mbit/s
- Control input u(t): DL PRB allocation
- Primary output y(t): receiver throughput_kbit_s
- Sampling interval: 0.2 s
- Plant time origin: U_APPLIED_READBACK

No T1 model parameter is automatically transferred to T2.

No T1 numerical validation threshold is automatically transferred to T2.

## 3. Sampling and stationarity

The frozen Prompt-12 rules remain in force:

- startup guard >= 1 s;
- pre-step observation >= 11 s;
- two consecutive, non-overlapping 5 s stationary windows;
- 25 samples per window;
- CV <= 5% in each window;
- mean shift <= 5%;
- post-step observation >= 10 s;
- extend post-step observation in 5 s increments until the latest two
  windows pass stationarity.

Transition-crossing samples are preserved as evidence but are not steady-state
samples.

KPM is not required for Prompt-12 validity.

## 4. Timing gates

- PRECONTROL_FRESHNESS_MAX_MS = 800
- TRIGGER_TO_APPLIED_MAX_MS = 2800
- FINAL_SAMPLE_TO_APPLIED_MAX_MS = 3600

Timing fields retained:

- rx_mono_ns
- rx_wall_ns
- gnb_timestamp_s

Actuator events remain separate:

- u_cmd
- u_ack
- u_applied/readback

## 5. Prearmed V2 actuator identity

Mandatory actuator architecture: persistent/prearmed V2.

Source SHA-256:

`ca12da2df05989e38d38c4a374091745f1550f87837bc88484963178776e1185`

Binary SHA-256:

`652001a0893b2f65d6ccdd77aac3794bea998d0beaa54781882006d64c47a0c6`

Build evidence:

`/home/khoshaba/sci-oran-evidence/prompt12/prearmed-actuator-v2-build-r1`

Before trigger:

- E2 is fully initialized;
- exactly one E2 node is discovered;
- RC message is prebuilt;
- local FIFO is waiting;
- SCI_ORAN_ACTUATOR_ARMED=YES;
- CONTROL_REQUEST_COUNT=0.

Exactly one `TRIGGER` token is accepted and exactly one
`control_sm_xapp_api(...)` call is permitted.

After successful delivery of `TRIGGER`, that operation immediately becomes
NEVER_REPEAT.

## 6. Initial state and reset policy

Every T2 replication must begin from an **authoritatively proven 26 PRB**.

The state may not be inferred merely from:

- the previous experiment;
- the previous chat;
- T1 having ended at 26 PRB;
- day-start behaviour.

If 26 PRB cannot be proven, a separate reset-to-26 operation is required.

A reset:

- targets 50% = 26 PRB;
- uses prearmed V2;
- has its own operation ID, run ID, evidence and trigger;
- is not a T2 estimation sample;
- must produce applied readback = 26 PRB;
- becomes NEVER_REPEAT when its trigger is consumed.

A tooling failure after a reset trigger does not permit replaying that trigger.
An uncertain reset outcome blocks further scientific execution until current
plant state is independently established.

Because a successful T2 replication finishes at 39 PRB, a subsequent T2
replication again requires authoritative proof of 26 PRB, normally through a
separately evidenced return-to-26 operation.

## 7. Replication plan

T2 uses:

- 3 estimation replications: R01, R02, R03;
- 1 true unseen validation replication: R04.

R04 is acquired only after:

1. all three estimation replications are frozen;
2. model family selection is complete;
3. selected model parameters are frozen;
4. T2-specific steady-gain acceptance limit is frozen;
5. T2-specific dynamic NRMSE acceptance limit is frozen.

Each replication has a unique run ID and unique exactly-once trigger.

No automatic outlier rejection is planned.

## 8. Static gain

For each estimation replication:

`K_i = (post_mean - pre_mean) / 13`

in kbit/s/PRB.

The frozen T2 aggregate static gain is the arithmetic mean of the three valid
estimation gains.

No replication may be removed after observing its result merely to improve the
aggregate model.

## 9. Candidate model families

The candidate set is frozen before T2 data:

1. ARX1
2. FOPDT
3. DISCRETE_FIRST_ORDER
4. STATIC_QUASISTATIC

T1 parameters are not T2 parameters.

Model selection uses three-fold leave-one-replication-out validation.

Primary metric:

`NRMSE = 100 * RMSE / abs(observed held-out delta_y)`

The family with the smallest mean LOO NRMSE wins.

After family selection, its parameters are fitted from all three T2 estimation
replications and frozen **before R04**.

## 10. T2 validation thresholds

The numerical T1 limits are not copied.

Instead, the threshold-generation **method** is frozen now.

### Steady gain limit

For each estimation fold, hold out gain K_i and predict it using the arithmetic
mean of the other two estimation gains.

Compute:

`APE_i = 100 * abs(K_i - K_pred_i) / abs(K_i)`

The T2 R04 steady-gain APE limit is:

`max(APE_1, APE_2, APE_3)`

This numerical limit must be frozen before R04 exists.

### Dynamic limit

For the selected model family, retain the three LOO NRMSE values.

The T2 R04 dynamic NRMSE limit is:

`max(LOO_NRMSE_1, LOO_NRMSE_2, LOO_NRMSE_3)`

This numerical limit must also be frozen before R04 exists.

### R04 acceptance

R04 passes only if both are true:

- steady-gain APE <= frozen T2 steady-gain limit;
- dynamic NRMSE <= frozen T2 dynamic limit.

R04 cannot be used to tune either limit.

## 11. T2 versus T1

Frozen T1 reference:

- mean static gain = 189.235897 kbit/s/PRB;
- selected family = ARX1;
- a = 0.5235206985110815;
- b = 0.4826205807797367;
- normalized steady = 1.0128888689847129;
- equivalent discrete-pole tau ≈ 0.309055535 s.

T2 comparison must report:

- mean gain difference from T1;
- relative gain difference;
- selected model-family agreement/disagreement;
- dynamic prediction accuracy;
- if T2 also selects ARX1: a, b and equivalent discrete-pole tau differences.

Similar static gain alone is not proof of global linearity.

## 12. Global versus local/piecewise interpretation

T2 cannot establish a global model over 13..52 PRB.

The strongest possible result after T2 is only a
**regional shared-model compatibility candidate over 13..39 PRB**.

That candidate requires all of the following:

1. T1 remains valid on its frozen R04;
2. T2 passes its true unseen R04;
3. T1 and T2 select the same model family;
4. the frozen T1 model predicts T2 R04 without refitting and remains within
   T2 frozen validation limits;
5. the frozen T2 model predicts T1 R04 without refitting and remains within
   T1 frozen validation limits.

If any condition fails, the scientific interpretation over 13..39 PRB is
local/piecewise.

T3 = 39→52 PRB is still required before any claim of a single model over
13..52 PRB.

T2 does not prove reverse-direction equivalence or absence of hysteresis.

## 13. Forbidden post-hoc retuning

After the first T2 scientific trigger, protocol V1 may not be silently changed.

After R04 is observed, it is forbidden to:

- change model family;
- change model parameters;
- change validation limits;
- relabel R04 as estimation data;
- repeat R04 because it failed;
- exclude an inconvenient estimation replication post hoc.

A failed R04 is a legitimate scientific result.

Any subsequent alternative model requires a separately versioned protocol and
cannot restore unseen status to already observed R04 data.

## 14. Evidence and repository layout

Raw evidence base:

`/home/khoshaba/sci-oran-evidence/prompt12/t2-26to39/`

Each acquisition/reset operation receives its own evidence root and provenance.

Raw evidence is not copied wholesale into Git.

At T2 closeout, Git should mirror the proven T1 pattern with:

- dataset-metadata-v1.0.0.json
- t2-scientific-result-v1.0.0.json
- frozen-evidence-roots-v1.0.0.tsv
- evidence-file-inventory-v1.0.0.tsv
- release-checksums-v1.0.0.sha256

plus:

- docs/12-t2-26to39-identification-closeout.md
- experiments/manifests/prompt12-t2-26to39-closeout-v1.0.0.json
- experiments/registry.csv update

## 15. T2 closeout definition

A negative validation outcome may still be scientifically CLOSED.

Possible final scientific outcomes:

- VALIDATED_ON_TRUE_R04_HOLDOUT
- CLOSED_NOT_VALIDATED_ON_TRUE_R04_HOLDOUT

Repository-level T2 CLOSED additionally requires complete frozen evidence,
provenance, checksums, registry/manifest records, local Git checkpoint and
verified remote checkpoint.

## 16. NEVER_REPEAT boundary

Already consumed T1 controls remain NEVER_REPEAT:

- R01
- R02
- R03V2
- R04
- R04 reset 26→13

For T2, every scientific or reset trigger becomes NEVER_REPEAT immediately
after successful `TRIGGER` delivery, regardless of later tooling success.

## 17. Current authorization boundary

After this offline content freeze:

`T2_26_TO_39_SCIENTIFIC_PROTOCOL_FROZEN=YES`

but:

`T2_PROTOCOL_GIT_CHECKPOINTED=NO`

`T2_EXECUTION_AUTHORIZED=NO`

No day-start, workload, reset or E2SM-RC Control is authorized until the
protocol receives a separate Git checkpoint and remote-sync verification.
