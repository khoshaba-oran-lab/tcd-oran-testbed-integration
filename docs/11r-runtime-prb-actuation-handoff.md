# Sci_O-RAN Prompt 11R Runtime PRB Actuation Handoff

## Status

Prompt 11R runtime PRB actuator validation was completed experimentally
through R03 on 2026-08-17.

The historical Prompt 11R.42 / R02 negative result remains preserved below.
R03 is the subsequent repaired experiment that resolved the missing
applied-state and plant-response evidence.

Current classification:

- AO27=CLOSED
- AO28=CLOSED
- ACTUATION_GATE=PASS
- R03_CONTROL=EXECUTED_EXACTLY_ONCE_NEVER_REPEAT
- PRIMARY_TELEMETRY_PATH=NATIVE_GNB_TELEMETRY
- E2SM_KPM_VALIDATION=NOT_PERFORMED_IN_R03
- AO29=OPEN_PENDING_GITHUB_CHECKPOINT
- SYSTEM_IDENTIFICATION=ALLOWED_AFTER_AO29

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

## Historical pre-experiment gate

Before the 2026-08-16 live-control experiment, the planned next gate was
NEXT_GATE=FRESH_SESSION_PRE_CONTROL_AND_RUNTIME_E2SM_RC_PRB25_CONTROL.

That gate has now been executed and is superseded by the final
Prompt 11R.42 classification below.

## Prompt 11R.42 final experimental classification

A fresh-session live experiment was completed on 2026-08-16 with the
corrected E2SM-RC PRB25 actuator.

The corrected actuator binary used in the experiment had SHA256
0fb175a8cdfc376033717245746bd1e257101c3a18baccf9e5e7891d1ec4a689.

The experiment established the following facts:

- exactly one live actuator execution was performed;
- exactly one E2SM-RC PRB25 Control Request was emitted;
- U_CMD=PROVEN;
- U_ACK=PROVEN;
- CONTROL_REQUEST_COUNT=1;
- ADDITIONAL_CONTROL_REQUEST_SENT=NO;
- no restart of gNB, UE, 5GC, or Near-RT RIC occurred;
- the E2 SCTP association remained present after control;
- DIRECT_ACTUATOR_READBACK=UNAVAILABLE.

The paired frozen 8 Mbit/s UDP downlink observations were:

- Y_BEFORE_RX_MBIT_S=7.97;
- Y_AFTER_RX_MBIT_S=7.98;
- Y_BEFORE_JITTER_MS=1.564;
- Y_AFTER_JITTER_MS=1.593;
- Y_BEFORE_LOSS=0/14482;
- Y_AFTER_LOSS=0/14484.

Therefore PLANT_RESPONSE_AT_8MBIT=INCONCLUSIVE. The absence of an
observable throughput degradation at this operating point must not be
interpreted as proof that the PRB25 command was not applied.

Post-control telemetry classification was:

- NATIVE_TELEMETRY=UNAVAILABLE_IN_CURRENT_RUNTIME;
- KPM_RUNTIME_CAPTURE=UNAVAILABLE_IN_CURRENT_SESSION.

The resulting final classification is:

- EXACTLY_ONE_LIVE_CONTROL_EXPERIMENT=PASS;
- INDIRECT_APPLIED_STATE_EVIDENCE=INSUFFICIENT_FOR_PASS;
- OPERATIONAL_RUNTIME_ACTUATION_GATE=NOT_PASSED;
- STRICT_ORIGINAL_ACTUATION_GATE=NOT_PASSED;
- FINAL_ACTUATION_GATE_CLASSIFICATION=CLOSED_NOT_PASSED;
- PROMPT11_SYSTEM_IDENTIFICATION_ALLOWED=NO;
- PROMPT11_PID_ALLOWED=NO;
- PROMPT11_MPC_ALLOWED=NO.

The authoritative durable classification artifact is stored outside Git at:

/home/khoshaba/sci-oran-evidence/action11r/2026-08-16-live-control-prb25/actuation-gate-classification.env

Its SHA256 is:

e15b4a1ec3776d3c4a4ccf6756402838c325a290981508d4374427567250d40e

The one-shot actuator container used for this experiment must not be
re-executed.

HISTORICAL_NEXT_GATE=PROMPT_11R42_DOCUMENTATION_AND_GITHUB_CHECKPOINT

## Prompt 11R R03 final status

Experiment:

- EXP_ID=EXP-20260817-A11R50-PRB25-18MBIT-R03
- evidence root=/home/khoshaba/sci-oran-evidence/action11r/2026-08-17-prb25-18mbit-r03
- target RNTI=0x4601
- physical cell bandwidth=52 PRB
- requested maximum ratio=25 percent
- applied maximum=13 PRB

Exactly-one Control evidence:

- R03_CONTROL_EXECUTED=YES
- CONTROL_REQUEST_COUNT=1
- U_CMD=PASS
- U_ACK=PASS
- U_APPLIED_READBACK=PASS
- applied_min_prbs=0
- applied_max_prbs=13
- R03_CONTROL_REPEAT_ALLOWED=NO

Pre-control R03:

- receiver throughput approximately 17.8 Mbit/s
- packet loss=0 percent
- maximum DL NewTx grant=48 PRB
- mean dl_bo=45396.31
- maximum dl_bo=109416

Post-control R03:

- receiver throughput=7.01 Mbit/s
- packet loss=32 percent
- DL NewTx samples=13671
- maximum DL NewTx grant=13 PRB
- NewTx violations above 13 PRB=0
- mean dl_bo=3978307.50
- maximum dl_bo=6066373
- post/pre mean dl_bo ratio=87.6350

Final experimental classification:

- POST_NEW_TX_PRB_CAP=PASS
- THROUGHPUT_RESPONSE=PASS
- QUEUE_RESPONSE=PASS
- PLANT_RESPONSE=OBSERVED
- NATIVE_TELEMETRY=PASS
- NO_RESTART=PASS
- ACTUATION_GATE=PASS

The demonstrated chain is:

u_cmd -> u_ack -> u_applied/readback -> plant response -> native gNB telemetry

The reproducible R03 configuration had E2SM-RC enabled and E2SM-KPM
disabled. E2SM-KPM validation was therefore not performed in R03 and
remains a separate O-RAN observability validation task.

R03 dataset freeze:

- DATASET_FREEZE_UTC=2026-08-17T11:44:24Z
- FROZEN_FILE_COUNT=57
- files.tsv SHA256=00d034b6e3f22672034273fe9da83197c92129a8bfaf1d585a513146f87af9d7
- freeze.env SHA256=f1c20b45faeec290979e62a4fbea65f17d054e9e14e64246e19773c41363638b

The historical Prompt 11R.42 negative result remains preserved for its
original experiment. R03 supersedes it only as the current project state.

Current state:

- AO27=CLOSED
- AO28=CLOSED
- ACTUATION_GATE=PASS
- AO29=OPEN_PENDING_GITHUB_CHECKPOINT
- SYSTEM_IDENTIFICATION=ALLOWED_AFTER_AO29
