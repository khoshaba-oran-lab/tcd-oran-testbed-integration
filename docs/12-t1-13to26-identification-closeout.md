# Sci_O-RAN Prompt 12 - T1 13-to-26 PRB Identification Closeout

## Status

T1 is closed with scientific status:

`VALIDATED_ON_TRUE_R04_HOLDOUT`

This closeout applies to the open-loop SISO plant identification transition
from 13 PRB to 26 PRB under UDP downlink workload at 18 Mbit/s.

No PI/PID controller synthesis is authorized from T1 alone.

## Estimation set

The frozen estimation set contains exactly three replications:

- R01: `RUN-20260822T142755Z-009`
- R02: `RUN-20260822T143648Z-010`
- R03V2: `RUN-20260822T161918Z-014`

R02 remains included.

No outlier rejection was performed.

The mean static gain is `189.235897 kbit/s/PRB`.

The median static gain is `171.723077 kbit/s/PRB`.

The gain population coefficient of variation is `13.312655%`.

## Canonical experiment identities

The original frozen acquisition evidence establishes the following
experiment/run identities:

- R01: `EXP-20260822-DL-18000K-R01` / `RUN-20260822T142755Z-009`
- R02: `EXP-20260822-DL-18000K-R02` / `RUN-20260822T143648Z-010`
- R03V2: `EXP-20260822-DL-18000K-R03` / `RUN-20260822T161918Z-014`
- R04: `EXP-20260822-DL-18000K-R04` / `RUN-20260822T164537Z-015`

`R03V2` is the scientific replication label. Its historical canonical
experiment identity remains `EXP-20260822-DL-18000K-R03`; it must not be
retrospectively renamed.

The original R01, R02, and R03V2 acquisition roots are included in the
dataset evidence inventory and their SHA256SUMS manifests pass verification.

## Frozen dynamic model

The selected model family is `ARX1`.

Frozen parameters:

- `a = 0.5235206985110815`
- `b = 0.4826205807797367`
- `normalized_steady = 1.0128888689847129`

The equivalent discrete-pole time constant is approximately
`0.309055535 s`.

This value is an ARX discrete-pole equivalent and must not be described as a
separately identified FOPDT time constant.

The model was selected using leave-one-replication-out validation.

Mean leave-one-out normalized RMSE:

- ARX1: `27.268449%`
- FOPDT: `27.340213%`
- discrete first order: `29.350637%`
- static/quasi-static: `31.447423%`

## True unseen R04 validation

R04:

`RUN-20260822T164537Z-015`

was reserved as `TRUE_UNSEEN_VALIDATION`.

It was not used for model selection, model parameter estimation, or threshold
tuning.

Observed R04 values:

- pre steady throughput: `7285.200000 kbit/s`
- post steady throughput: `9614.800000 kbit/s`
- delta throughput: `2329.600000 kbit/s`
- observed static gain: `179.200000 kbit/s/PRB`

Steady gain APE:

`5.600389% <= 23.765052%`

Result:

`STEADY_GAIN_VALIDATION_GATE=PASS`

Dynamic validation:

- RMSE: `581.234498 kbit/s`
- NRMSE: `24.949970%`
- frozen acceptance limit: `35.626969%`

Result:

`DYNAMIC_MODEL_VALIDATION_GATE=PASS`

Overall:

`R04_MODEL_VALIDATION_GATE=PASS`

After R04, the model family, model parameters, and acceptance thresholds
remained unchanged.

## Exactly-once boundaries

The reset actuator used for `26-to-13 PRB` before R04 is permanently
`NEVER_REPEAT`.

The R04 `13-to-26 PRB` trigger is permanently `NEVER_REPEAT`.

A consumed scientific trigger must never be replayed to repair later
post-processing or repository tooling.

## Evidence provenance

Five evidence roots are frozen for the T1 closeout:

1. T1 estimation freeze.
2. T1 model selection.
3. R04 reset and prearm.
4. R04 holdout acquisition.
5. R04 final closure.

The R04 acquisition root does not contain its own top-level SHA256SUMS file.
For closeout, a repository-side portable per-file SHA-256 inventory is
generated.

In addition, the final closure was verified byte-for-byte against the R04
acquisition for:

- model validation;
- timing gates;
- pre-step stationarity;
- post-step stationarity.

All four copy-identity gates passed.

## Scientific scope

T1 validates a local plant model only for:

- 13-to-26 PRB;
- UDP downlink at 18 Mbit/s;
- the current Tb3 configuration;
- the current receiver throughput measurement architecture.

T1 does not establish:

- global linearity over 13..52 PRB;
- unchanged gain for 26-to-39 or 39-to-52 PRB;
- reverse-direction equivalence;
- absence of hysteresis;
- workload invariance;
- saturation behaviour over the full PRB range.

The preferred next candidate is T2 = 26-to-39 PRB, but T2 is not authorized
by this closeout record itself. A separate frozen scientific protocol and a
successful lifecycle/runtime admission are required before execution.
