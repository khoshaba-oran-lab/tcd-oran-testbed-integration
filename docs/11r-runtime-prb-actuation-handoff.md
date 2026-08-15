# Sci_O-RAN Prompt 11R Runtime PRB Actuation Handoff

## Status

This document records the intermediate handoff point reached on
2026-08-14 during Prompt 11R-2.

The runtime PRB actuator discovery and build stages are complete.
The final runtime Actuation Gate has not yet been executed.

Current classification:

- PRE_ACTUATION_8MBIT_BASELINE_GATE=PASS
- Y_BEFORE_CAPTURE_GATE=PASS
- PRE_ACTUATION_RUNTIME_CONTINUITY_GATE=PASS
- ACTUATOR_BINARY_EXECUTED=NO
- E2_CONTROL_REQUEST_SENT=NO
- CONTROL_REQUEST_COUNT=0
- RUNTIME_ACTUATION_GATE=NOT_YET_EXECUTED

## Runtime PRB actuator

The selected actuator is an E2SM-RC slice-level PRB quota control.

Final payload contract:

- PLMN: 00101
- SST: 1
- SD: omitted
- MIN_PRB: 0
- MAX_PRB: 25
- dedicated PRB: omitted
- slice count: 1
- control request count: exactly 1

Patch:

`deploy/phase-2-flexric/tb3-runtime/actuator/patches/0001-xapp-oran-slice-ctrl-prb25.patch`

Patch SHA256:

`350b0b3f9dbdd50064d2f4a803da1eda1e8d90644c5901080a61d346b3a74448`

Canonical normalized actuator binary SHA256:

`a867c2944775bdfbe3af973ff22f11df08fcb736b5a45aa572d5d9a53516dd46`

The canonical binary identity passed reproducibility validation after
normalizing build-id/debug-path metadata.

Raw linked binaries were not byte-identical due to build metadata and
debug-path differences. This limitation must remain documented.

## Corrected traffic workload

The original reverse-mode fixed-volume workload was rejected after a
runaway experiment demonstrated that the expected 20M termination
contract was not satisfied in the tested UDP reverse-mode topology.

The validated replacement topology is:

```text
5GC/UPF iperf3 client
        |
        | UDP downlink
        v
UE network namespace iperf3 server
```

Frozen workload contract:

- protocol: UDP
- direction: downlink
- topology: 5GC client to UE namespace server
- reverse mode: no
- bitrate: 8 Mbit/s
- transfer size: 20M
- client safety timeout: 60 s

Frozen workload SHA256:

`5cd4deb7e4f4698cdf8929a854a9dc0b91f40528a16e1e7818d5cab39157fb08`

A bounded 1M validation completed successfully before the scientific
baseline run.

## Valid pre-actuation reference measurement

Experiment ID:

`EXP-20260814-A11R23-PRE-PRB25-8MBIT-R01`

Run ID:

`RUN-20260814T172548Z-001`

Measured Y_before:

- sender duration: 20.97 s
- sender bitrate: 8.00 Mbit/s
- receiver duration: 21.04 s
- receiver bitrate: 7.97 Mbit/s
- receiver jitter: 1.439 ms
- packet loss: 0/14484
- packet loss percentage: 0%
- UE tun_srsue RX byte delta: 21391528
- UE tun_srsue TX byte delta: 12839

The harness completed normally:

- SCI_ORAN_PREFLIGHT_READY_GATE=PASS
- HARNESS_EXIT_CODE=0
- FINAL_STATUS=COMPLETED
- RUNNER_COMPLETE=PASS

Persistent 5GC, RIC, gNB and UE container identities remained unchanged
during the measurement.

## Durable evidence

The end-of-day evidence was frozen outside /tmp at:

`/home/khoshaba/sci-oran-evidence/action11r/2026-08-14-y-before`

The evidence root contains:

- Y_before control evidence
- corrected workload
- raw iperf3 client/server output
- canonical experiment-harness run
- experiment manifest
- fresh user-plane smoke evidence
- actuator patch
- HANDOFF.env
- SHA256SUMS

The durable evidence SHA256 manifest was verified before this checkpoint.

## Required fresh-session continuation

After the next canonical day-start, do not treat the previous runtime
PIDs, start times, SCTP association identifiers, or readiness timestamp
as current.

The next session must execute the following sequence:

```text
canonical day-start
        ->
fresh sci-oran doctor
        ->
SCI_ORAN_READY_GATE=PASS
        ->
fresh user-plane smoke
        ->
fresh final paired Y_before
        ->
freeze pre-control runtime continuity
        ->
execute exactly one E2SM-RC PRB25 control request
        ->
capture u_cmd
        ->
capture u_ack
        ->
capture direct readback if available
        ->
verify runtime and association continuity
        ->
capture Y_after using the identical workload
        ->
capture native/KPM telemetry
        ->
offline paired analysis
        ->
final Actuation Gate classification
```

The control command must not restart gNB, UE, 5GC or RIC.

## Final Actuation Gate

The intended evidence chain is:

```text
u_cmd
  ->
u_ack
  ->
u_applied/readback
  ->
plant response
  ->
native/KPM telemetry
```

Required runtime gates include:

- RUNTIME_E2_COMMAND_GATE
- RUNTIME_E2_ACK_GATE
- RUNTIME_NO_RESTART_GATE
- ACTUATOR_READBACK_GATE
- RUNTIME_PLANT_RESPONSE_GATE
- RUNTIME_TELEMETRY_GATE
- GNB_PID_CONTINUITY_GATE
- UE_PID_CONTINUITY_GATE
- CORE_PID_CONTINUITY_GATE
- RIC_PID_CONTINUITY_GATE
- E2_ASSOCIATION_CONTINUITY_GATE
- N2_ASSOCIATION_CONTINUITY_GATE
- USER_PLANE_CONTINUITY_GATE

A CONTROL ACK must not be mislabeled as direct actuator readback.

If direct readback is unavailable, preserve the distinction:

```text
DIRECT_ACTUATOR_READBACK=UNAVAILABLE
INDIRECT_APPLIED_STATE_EVIDENCE=CONTROL_ACK_PLUS_PLANT_RESPONSE
```

In that case an operational runtime actuation result may be classified
separately from the strict original Actuation Gate.

## Next gate

`NEXT_GATE=FRESH_SESSION_PRE_CONTROL_AND_RUNTIME_E2SM_RC_PRB25_CONTROL`

Do not start PID control or system identification before the Actuation
Gate has been classified.
