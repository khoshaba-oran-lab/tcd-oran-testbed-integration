# Prompt 12R platform-health qualification contract

## 1. Purpose

Prompt 12R separates experimental-platform validity from O-RAN plant
dynamics.

The governing rule is:

`MODEL_VALID = PLATFORM_HEALTHY`

A PRB-response dataset is scientifically admissible only when infrastructure
health is independently established. Platform failures must not be fitted as
ARX, FOPDT, gain, delay, settling-time, or controller dynamics.

This document is prospective. It does not modify frozen Prompt 12 T1 or T2
evidence and does not authorise a new scientific PRB transition.

## 2. Transaction boundary

The redesigned transaction separates platform health from plant initial
state:

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

The important separation is:

- `PLATFORM_QUALIFIED` means the infrastructure is fit to host an experiment;
- `INITIAL_STATE_VERIFIED` means the plant is proven to be at the required
  starting PRB operating point.

An assumed or historical PRB value must not be used as a substitute for
fresh initial-state verification.

## 3. Existing reusable readiness authority

The existing primary infrastructure readiness implementation is:

`scripts/sci-oran-doctor.sh`

Its final readiness decision is:

`SCI_ORAN_READY_GATE`

with a fail-closed:

`FAILURE_REASON`

The current Doctor aggregates at least:

- `HOST_READINESS_GATE`;
- `HOST_RESOURCE_READINESS_GATE`;
- `CONTAINER_READINESS_GATE`;
- `NETWORK_READINESS_GATE`;
- `ZMQ_READINESS_GATE`;
- `N2_READINESS_GATE`;
- `E2_READINESS_GATE`;
- `E2SM_RC_READINESS_GATE`;
- `UE_SESSION_READINESS_GATE`;
- `USER_PLANE_READINESS_GATE`;
- `TRAFFIC_HARNESS_READINESS_GATE`.

Prompt 12R must reuse these gates rather than create an independent,
incompatible implementation of the same checks.

## 4. Host resource qualification

The existing Doctor already provides explicit pre-experiment host-capacity
qualification through:

`deploy/phase-2-flexric/tb3-runtime/locks/host-resource-readiness.policy`

The current policy requires:

- minimum CPU count: 8;
- maximum 1-minute load per CPU: 1.00;
- maximum 5-minute load per CPU: 1.00;
- minimum available memory: 20 percent;
- minimum available memory: 2097152 KiB;
- minimum available HOME filesystem space: 10485760 KiB;
- maximum HOME filesystem utilisation: 90 percent;
- minimum available Docker filesystem space: 10485760 KiB;
- maximum Docker filesystem utilisation: 90 percent;
- maximum HOME inode utilisation: 90 percent;
- CPU, memory and I/O PSI limits;
- no mandatory swap requirement.

Therefore disk-space headroom is not a missing capability. It is already part
of the authoritative Doctor readiness path and must be inherited by
`PLATFORM_QUALIFIED`.

This is particularly important because a previous scientific acquisition was
lost because of disk exhaustion.

## 5. Base runtime qualification

The existing Doctor already resolves and checks the required base runtime:

- 5GC;
- gNB;
- UE;
- RIC.

For each role it captures runtime identity information including:

- container name;
- container ID;
- PID;
- start time;
- restart count;
- image ID;
- running state;
- status;
- Docker health status where defined.

`CONTAINER_READINESS_GATE` already requires the expected containers to be
running with the expected image identity.

## 6. Restart-count policy gap

The Doctor currently records restart counts and requires restart-count
stability across its own readiness observation interval.

It explicitly states:

`PROCESS_CONTINUITY_RESTART_COUNT_ZERO_REQUIRED=NO`

and:

`PROCESS_CONTINUITY_RESTART_COUNT_STABILITY_REQUIRED=YES`

For system identification this is insufficient as an admission criterion.

A container that restarted before Doctor began could be stable during Doctor
while still representing a disturbed or partially recovered experimental
incarnation.

Prompt 12R therefore strengthens the prospective experiment admission rule:

`PLATFORM_BASE_RESTART_COUNT_ZERO_GATE=PASS`

must require:

- 5GC restart count = 0;
- gNB restart count = 0;
- UE restart count = 0;
- RIC restart count = 0.

This zero-restart rule is an experiment-incarnation admission requirement.
It does not rewrite the general-purpose Doctor semantics.

If any required base container has a non-zero restart count, the scientific
transaction must not continue to `INITIAL_STATE_VERIFIED`.

The appropriate failure class is:

`PLATFORM_FAILURE`

and the incarnation must be replaced or explicitly recovered before a new
scientific transaction is created.

## 7. Process continuity

The existing Doctor already captures start and end runtime fingerprints for
the four base roles and checks stability of:

- name;
- container ID;
- PID;
- start time;
- restart count;
- image ID.

This capability must be reused.

For Prompt 12R:

`PLATFORM_PROCESS_CONTINUITY_GATE=PASS`

requires the Doctor process-continuity result to pass.

A change in PID, start time, restart count, container ID, or image identity
during platform qualification invalidates platform admission.

## 8. Network and protocol-path qualification

The existing Doctor provides reusable qualification for:

### Docker network

- expected network exists;
- expected subnet exists;
- 5GC membership;
- gNB membership;
- UE membership;
- RIC membership;
- expected fixed IP identities where specified.

### ZMQ radio path

The Doctor verifies configuration coherence and observes socket state across
multiple snapshots.

### N2

The Doctor checks the gNB-to-5GC SCTP association and association stability.

### E2

The Doctor checks the gNB-to-RIC SCTP association and association stability.

### E2SM-RC

The Doctor verifies the required E2SM-RC runtime/service-model state and
process continuity.

### UE session

The Doctor verifies the UE runtime session, TUN link and PDU address and
checks UE/5GC continuity.

### User plane

The Doctor verifies the required user-plane readiness evidence.

Therefore a new Prompt 12R checker must consume these existing authoritative
results rather than independently infer network health.

## 9. Platform readiness freshness

A previously passing Doctor result must not be treated as indefinitely valid.

`PLATFORM_QUALIFIED` must bind to one specific runtime incarnation and one
specific readiness artifact.

At minimum the qualification record must preserve:

- Doctor readiness ID;
- readiness timestamp;
- readiness artifact SHA256;
- runtime identities/fingerprints;
- repository HEAD;
- required policy/configuration identities.

A platform qualification belonging to another container incarnation must be
rejected.

The future transaction executor must define a bounded allowed age between
platform qualification and advancement into experiment preparation.

The exact age bound is not frozen by this document and must be justified
during implementation/offline qualification.

## 10. Receiver readiness already available

The Prompt 12 traffic adapter already provides a strengthened receiver
readiness gate.

A receiver is not considered ready merely because Docker says that its
container is running.

The gate requires a timestamped receiver-capture record containing:

`Server listening on 5201`

and validates that the receiver is still running when the marker is accepted.

The existing repair also established that a stale marker from an already
stopped receiver must fail closed.

This gate is reusable for the later:

`WORKLOAD_READY`

transaction state.

It must not be weakened back to:

`Docker container running == application ready`

because that exact assumption previously caused a workload-start tooling
race.

## 11. Receiver continuity

Prompt 12 already requires continuous workload and receiver measurement
across the controlled step.

The precontrol chain also proves a contiguous recent measurement segment by
requiring:

`latest_50_complete_contiguous_samples`

with exactly 50 complete samples before the final freshness/admission
decision.

These mechanisms belong primarily to:

- `WORKLOAD_READY`;
- `PRESTEP_ADMITTED`;
- post-step scientific adjudication.

They are not substitutes for base platform health.

## 12. Stale iperf process-cleanliness gap

Repository inspection did not identify an explicit pre-experiment gate that
proves there is no stale iperf server/client process capable of contaminating
a new Prompt 12 workload.

Unique receiver naming and timestamped receiver readiness are useful but do
not prove namespace-wide process cleanliness.

Prompt 12R therefore requires a new read-only admission gate:

`IPERF_PROCESS_CLEANLINESS_GATE`

Before a new receiver/workload is created, the gate must establish that the
relevant UE/shared network namespace contains no pre-existing iperf listener
or client belonging to an earlier transaction.

The implementation must be observational only.

It must not use `pkill`, `killall`, automatic container removal, or another
cleanup action as part of the qualification decision.

If stale workload state is observed:

`PLATFORM_QUALIFIED` must fail closed.

Cleanup/recovery, if authorised, is a separate lifecycle operation followed
by a completely fresh qualification.

## 13. Timestamp sanity

Receiver acquisition already records both:

- `rx_wall_ns`;
- `rx_mono_ns`.

Existing parser, canonicalizer and stationarity code reject invalid or
non-monotonic timestamp sequences.

The precontrol freshness path additionally binds:

- newest complete sample timestamp;
- precontrol decision timestamp;
- executor start timestamp.

Prompt 12R therefore reuses these timestamp-ordering checks at measurement
admission.

A prospective transaction-level timestamp-sanity gate must also ensure that
the experiment does not combine evidence from different runtime
incarnations or impossible causal ordering.

At minimum:

`sample <= gate decision <= executor/trigger preparation`

must hold for the relevant pretrigger chain.

No synthetic timestamp may replace an observed live timestamp in scientific
execution.

Synthetic clocks remain offline-test-only.

## 14. Initial PRB state is not a platform-health gate

Repository inspection found no authoritative read-only current-state query
that can prove the presently applied PRB cap without relying on historical
control evidence.

The existing:

`PRB_ACTUATOR_APPLIED`

record is authoritative for a specific applied control event, but an older
line in `/tmp/gnb.log` is not a safe current-state query.

The existing actuator-timeline parser also expects a complete:

`Control Request -> PRB_ACTUATOR_APPLIED -> acknowledgement`

triplet and therefore is not a general read-only current-state probe.

Consequently Prompt 12R must not pretend that Doctor success proves the
initial PRB state.

Initial PRB belongs to the separate transaction state:

`INITIAL_STATE_VERIFIED`

and must have fresh, incarnation-bound evidence.

Historical values such as 13, 26, 39 or 52 PRB must never be inferred as
current merely because they were the final state of an earlier run.

The exact safe mechanism for prospective initial-state verification remains
an implementation item and must be qualified before live scientific
execution.

No new PRB control is authorised merely to resolve this design question.

## 15. PLATFORM_QUALIFIED prospective decision

The prospective decision is:

`PLATFORM_QUALIFIED=PASS`

only if all required platform-health components pass for the same runtime
incarnation.

Required components are:

1. authoritative Doctor:
   `SCI_ORAN_READY_GATE=PASS`;

2. host-resource readiness:
   `HOST_RESOURCE_READINESS_GATE=PASS`;

3. required runtime containers:
   `CONTAINER_READINESS_GATE=PASS`;

4. zero restart count for 5GC/gNB/UE/RIC:
   `PLATFORM_BASE_RESTART_COUNT_ZERO_GATE=PASS`;

5. runtime process continuity:
   `PLATFORM_PROCESS_CONTINUITY_GATE=PASS`;

6. network path:
   `NETWORK_READINESS_GATE=PASS`;

7. ZMQ:
   `ZMQ_READINESS_GATE=PASS`;

8. N2:
   `N2_READINESS_GATE=PASS`;

9. E2:
   `E2_READINESS_GATE=PASS`;

10. E2SM-RC:
    `E2SM_RC_READINESS_GATE=PASS`;

11. UE session:
    `UE_SESSION_READINESS_GATE=PASS`;

12. user plane:
    `USER_PLANE_READINESS_GATE=PASS`;

13. traffic-harness integrity:
    `TRAFFIC_HARNESS_READINESS_GATE=PASS`;

14. stale iperf absence:
    `IPERF_PROCESS_CLEANLINESS_GATE=PASS`;

15. readiness artifact/runtime-incarnation binding:
    `PLATFORM_QUALIFICATION_BINDING_GATE=PASS`;

16. bounded qualification freshness:
    `PLATFORM_QUALIFICATION_FRESHNESS_GATE=PASS`.

Initial PRB is intentionally not included in this list because it belongs to
the subsequent:

`INITIAL_STATE_VERIFIED`

state.

## 16. Failure semantics

Before any scientific trigger:

- platform-health failure -> `PLATFORM_FAILURE`;
- experiment-tool failure -> `TOOLING_FAILURE`;
- experiment transaction terminates without scientific trigger;
- no consumed trigger may be replayed;
- recovery is separate from qualification.

After a scientific trigger, platform failure cannot be silently treated as
plant response.

The resulting scientific acquisition must be adjudicated under an explicit
post-trigger invalidation class rather than fitted into the plant model.

## 17. No automatic recovery inside scientific qualification

Platform qualification must be observational and fail closed.

It must not silently:

- restart base containers;
- recreate the network;
- restart Docker;
- kill stale iperf;
- reset PRB state;
- relaunch the RIC;
- perform E2 Control;
- launch scientific workload.

Automatic repair inside a qualification probe would destroy the distinction
between observing platform health and changing the platform.

Recovery belongs to lifecycle tooling on the lifecycle host and must be
followed by a new platform qualification.

## 18. Current redesign status

The existing Doctor already covers substantially more of the required
platform-health contract than initially assumed, including host resource and
disk headroom, network paths, E2/N2, UE session and process continuity.

The principal prospective gaps established by Prompt 12R inspection are:

1. zero-restart admission for all four base runtime containers;
2. explicit stale-iperf process cleanliness;
3. transaction binding/freshness of platform qualification;
4. a separate trustworthy `INITIAL_STATE_VERIFIED` mechanism for current PRB
   state.

Therefore the next implementation work should extend/reuse existing
readiness evidence rather than replace Doctor with another parallel health
system.

No day-start or new live scientific PRB control is authorised by this
contract.
