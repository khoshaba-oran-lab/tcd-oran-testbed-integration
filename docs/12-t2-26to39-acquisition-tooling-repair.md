# Prompt 12 T2 26->39 acquisition-tooling compatibility repair

## Status

This record freezes the acquisition-tooling compatibility repair made before
the first T2 scientific trigger.

The frozen scientific protocol remains:

- `docs/12-t2-26to39-scientific-protocol.md`
- transition: T2 = 26 -> 39 PRB;
- workload: UDP DL 18000 kbit/s;
- primary output: receiver `throughput_kbit_s`;
- sampling period: 0.2 s;
- scientific time origin: `U_APPLIED_READBACK`;
- T2 estimation replications: R01, R02, R03;
- true unseen holdout: R04.

The scientific protocol itself was not modified by this repair.

## Root cause

The receiver acquisition implementation inherited T1-specific experiment-ID
validation:

`EXP-YYYYMMDD-DL-18000K-R0[1-4]`

T2 uses an explicit transition-qualified namespace:

`EXP-YYYYMMDD-T2-26TO39-DL-18000K-R0[1-4]`

Consequently, the legacy Prompt-12 SISO canonicalizer/schema rejected a valid
T2 identity before any T2 scientific trigger had occurred.

A second architectural incompatibility was identified in
`prompt12-atomic-prestart.py`: that tool assumes an actuator container in
Docker `created` state and atomically invokes `docker start`.

T2 instead uses the frozen persistent Prearmed Actuator V2 architecture:

1. actuator starts before scientific workload admission;
2. E2 initialization completes;
3. exactly one E2 node is connected;
4. `SCI_ORAN_ACTUATOR_ARMED=YES` is observed;
5. zero scientific Control is sent before the trigger;
6. the actuator waits on a local FIFO;
7. exactly one `TRIGGER` token is delivered;
8. one E2SM-RC Control Request is issued;
9. `U_APPLIED_READBACK` defines scientific t0.

Therefore the legacy `prompt12-atomic-prestart.py` live-start path MUST NOT be
used for T2 persistent/prearmed execution.

## Repair scope

The legacy T1 artifacts remain immutable.

Three T2-specific acquisition artifacts were introduced:

- `datasets/schemas/sci-oran-prompt12-t2-26to39-v1.0.0.schema.json`
- `scripts/experiment-harness/canonicalize-iperf-receiver-t2.py`
- `scripts/experiment-harness/prompt12-t2-receiver-pipeline.sh`

The T2 receiver pipeline is bound explicitly to both the T2 canonicalizer and
the T2 schema.

No workload, sampling, output, stationarity, actuator, timing, model-family,
model-selection, or holdout policy was changed.

## Frozen scientific-trigger procedure

No permanent FIFO-aware atomic trigger helper existed in the repository at
the time of this checkpoint.

For T2, the scientific trigger procedure is therefore frozen as an explicit
fail-closed execution boundary:

1. keep Prearmed Actuator V2 running with restart count zero;
2. start the frozen UDP DL 18000 kbit/s acquisition;
3. obtain at least the required pre-step observation;
4. canonicalize receiver intervals with the T2 pipeline/schema;
5. evaluate `OUTPUT_STATIONARITY_GATE`;
6. evaluate the final pre-control freshness gate using
   `prompt12-precontrol-freshness.py`;
7. require:
   - two consecutive non-overlapping 5 s windows;
   - 25 complete samples per window;
   - CV <= 5% in both windows;
   - mean shift <= 5%;
   - `PRECONTROL_OUTPUT_STATIONARITY_GATE=PASS`;
   - `PRECONTROL_FRESHNESS_GATE=PASS`;
   - `PRECONTROL_ADMISSION_GATE=PASS`;
8. immediately revalidate:
   - actuator still running;
   - restart count zero;
   - one E2 node;
   - armed marker present exactly once;
   - no trigger accepted;
   - no scientific Control Request;
   - FIFO still exists;
   - authoritative current state remains 26 PRB;
9. deliver exactly one `TRIGGER` token through the mounted FIFO using the
   prearmed container;
10. after successful trigger delivery, mark that scientific trigger
    `NEVER_REPEAT` immediately, irrespective of subsequent processing;
11. derive t0 only from native `PRB_ACTUATOR_APPLIED`;
12. require exactly one native sequence:
    `Control Request -> PRB_ACTUATOR_APPLIED -> Control Acknowledge`;
13. require applied maximum PRBs = 39;
14. require the frozen timing gates;
15. continue post-step receiver observation until the frozen post-step
    stationarity requirement passes.

No `docker start` invocation is part of the T2 scientific trigger boundary.

## Scientific boundary at this repair

This repair was performed before the first T2 scientific trigger.

At the repair boundary:

- T2 scientific trigger count = 0;
- R01 actuator = prearmed;
- workload = not started;
- pre-step stationarity = not executed;
- scientific Control = not executed;
- plant = authoritative 26 PRB;
- PI/PID synthesis = not started.

The already consumed T1 controls and T2 reset controls remain NEVER_REPEAT.
