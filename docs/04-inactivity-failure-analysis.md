# Sci_O-RAN Tb3 Inactivity Failure Analysis and Recovery

## 1. Purpose

This document records the forensic analysis of the long-idle failure observed
on the Sci_O-RAN Tb3 BASE-05 ZeroMQ deployment.

The observed operational symptoms were:

- the `5gc`, `gnb`, and `srsue` containers remained running;
- native gNB telemetry no longer reported an active UE;
- the user plane was unavailable;
- later UE-side traffic triggered NAS Service Request attempts but did not
  restore end-to-end service;
- `tun_srsue` was observed by the operator during the failed state, although
  this particular interface-state observation was not independently preserved
  in the forensic bundle.

The analysis explicitly distinguishes between:

1. directly proven events;
2. probable causal interpretation;
3. hypotheses that remain unconfirmed.

Individual restart of only the gNB or only the UE is not treated as the
canonical recovery method. Recovery is based on the validated full Tb3
lifecycle.

## 2. Forensic evidence set

The preserved forensic bundle is:

    artifacts/forensics/tb3-failure-20260808T084259Z/

The forensic snapshot time was:

    2026-08-08T08:45:59.145088116 UTC

The preserved artifacts are:

| Artifact | Size | SHA-256 |
|---|---:|---|
| `gnb.log` | 137981952 B | `2f01f4c1a2acb7d614a1e0ea2be09d1a2378df6174ab8f9bd9e35a3ee7ddb4c3` |
| `ue.log` | 362045440 B | `569364c6fbedb439c5e1799d9f144f096f67dedfb8a14db84b782d1d08d65dcb` |
| `native-metrics-compact.log` | 14347 B | `e206a5c28fe45748273c7d0489757a809a5381f008a2845f02b89801f28cf85f` |
| `docker-inspect.json` | 29202 B | `b56c6ece2e59888315e4d1331269b7063aabd02ed37c126b08825b599db3fc95` |
| `docker-ps.txt` | 873 B | `cee8989eb5845f769f57480c10c75496d0226604860c1635839aa65685e8febf` |
| `snapshot-time.txt` | 34 B | `9f1b7d11742837aa6b4b951408ba034233f20ca53f3ac9f12d70564be23b7503` |

These hashes define the evidence set used by this analysis.

## 3. Configuration relevant to the failure

The gNB configuration contains:

    inactivity_timer: 7200

Thus the configured inactivity interval is 7200 seconds, or two hours.

The parameter is directly relevant to the observed inactivity-associated
release sequence. However, the preserved forensic evidence does not contain
the internal CU-UP inactivity-counter state and therefore cannot establish
the exact timestamp from which that counter was evaluated.

## 4. Forensic timeline

### 4.1 Initial UE establishment

The UE context was created shortly after baseline startup.

The gNB log records:

    2026-08-07T15:06:34.129269  F1 UE context created
    2026-08-07T15:06:34.130952  CU-CP added UE context
    2026-08-07T15:06:34.483726  PDUSessionResourceSetupRequest
    2026-08-07T15:06:34.509083  PDUSessionResourceSetupResponse

These records establish that the initial UE context and PDU session were
successfully created.

### 4.2 Last observed user-plane activity

The last observable gNB-side user-plane activity occurred at approximately:

    2026-08-07T15:43:10.249 UTC

The final records include DRB1, PDCP, RLC, and GTP-U activity in both uplink
and downlink directions.

An independent UE-side audit gives an essentially identical boundary:

    2026-08-07T15:43:10.257 UTC

The UE log contains final `GW`, `RLC-NR DRB1`, and associated user-plane
records at this time.

Therefore, both independently preserved endpoints place the final observable
user-plane exchange at approximately `15:43:10 UTC`.

### 4.3 Inactivity-associated release

At:

    2026-08-07T17:50:37.242431 UTC

the gNB recorded:

    BearerContextInactivityNotification

The subsequent control-plane sequence was:

    BearerContextInactivityNotification
      -> UEContextReleaseRequest
      -> UEContextReleaseCommand
      -> RRC rrcRelease
      -> BearerContextReleaseCommand
      -> PDU session psi=1 disconnect
      -> F1 UE context removal
      -> UEContextReleaseComplete

The principal timestamps are:

    17:50:37.242431  BearerContextInactivityNotification
    17:50:37.242605  UEContextReleaseRequest
    17:50:37.246905  UEContextReleaseCommand
    17:50:37.247183  DCCH DL rrcRelease
    17:50:37.247460  Disconnecting PDU session with psi=1
    17:50:37.374863  F1 UE context removed
    17:50:37.411722  UEContextReleaseComplete

The gNB additionally reported that the RRC container was not acknowledged
within a 120 ms window. This warning is retained as evidence, but it must not
be interpreted as proof that the UE failed to receive the RRC Release.

### 4.4 UE reception of RRC Release

The UE log independently proves successful reception of the RRC Release:

    2026-08-07T17:50:37.258526  SRB1 - Rx rrcRelease
    2026-08-07T17:50:37.258560  Received RRC Release

The UE received the release approximately 11 ms after the corresponding
gNB-side transmission.

Immediately afterwards, the UE reset local protocol state:

    Resetting MAC-NR
    Bearers: Reset EPS bearer manager

Residual or late downlink traffic was subsequently observed against bearer
state that had already been removed. The UE reported, for example:

    LCID 1 doesn't exist. Dropping PDU.

Therefore, the hypothesis that the failure was caused by loss of the
RRC Release on the radio interface is contradicted by the preserved UE log.

### 4.5 Absence of post-release RRC recovery

A complete audit of the remaining UE log found only two `RRC-NR` records
starting at the release boundary:

    POST_RELEASE_RRC_LINES=2

Those two records are the two RRC Release reception messages listed above.

No subsequent UE-side `RRC-NR` records were found for:

- RRC Setup;
- RRC Re-establishment;
- a new RRC connection procedure;
- another RRC state transition.

The corresponding gNB-side post-release audit found no later:

- RACH or Random Access procedure;
- RRC Setup;
- RRC Re-establishment;
- Initial UE message;
- UE context creation;
- PDU Session Resource Setup request.

The gNB log remained active until approximately:

    2026-08-08T08:45:50 UTC

Therefore, the absence of these events is not explained by premature
termination of the gNB log.

### 4.6 Failed NAS Service Request attempts

On the following day, new UE-side traffic triggered:

    2026-08-08T08:39:04.755962  GW TX PDU
    2026-08-08T08:39:04.755980  UE does not have service
    2026-08-08T08:39:04.756011  NAS5G Service Request

Further attempts occurred at approximately four-second intervals:

    2026-08-08T08:39:08.758059  NAS5G Service Request
    2026-08-08T08:39:12.758733  NAS5G Service Request

The UE also reported:

    Can't deliver SDU for EPS bearer 1. Dropping it.

During the same period, the gNB continued to produce scheduler metrics but
recorded no new RACH, RRC Setup, RRC Re-establishment, Initial UE signalling,
or new UE context.

The preserved evidence therefore shows that the NAS layer attempted Service
Request processing, but no corresponding new radio-access procedure became
visible at the gNB.

### 4.7 Native telemetry before forensic capture

The compact native telemetry capture covers approximately:

    2026-08-08T08:42:42.902 UTC
    to
    2026-08-08T08:45:58.422 UTC

Throughout the complete preserved interval, all approximately 184 samples
reported:

    ue=NONE

At the same time, cell scheduler telemetry continued to be produced and
reported:

    cell_errors=0

This proves that the native gNB telemetry path and scheduler remained active
while no UE was visible in the scheduler UE metrics.

The compact capture starts after the UE had already disappeared from the gNB
UE metrics. It therefore does not contain the transition from UE-visible to
UE-absent state.

## 5. Inactivity-timer timing assessment

The configured inactivity timer is:

    7200 s

Independent UE-side and gNB-side forensic evidence places the final observable
user-plane activity at approximately:

    2026-08-07T15:43:10.25 UTC

The inactivity notification occurred at:

    2026-08-07T17:50:37.242431 UTC

The observed interval is therefore approximately:

    7647 s
    = 2 h 07 min 27 s

This is approximately:

    447 s
    = 7 min 27 s

longer than the configured 7200-second value.

Consequently, the available forensic evidence does not support the simplified
model:

    final visible user-plane packet + exactly 7200 s = inactivity notification

The approximately 447-second discrepancy is retained as an unresolved
forensic limitation.

Possible explanations include:

- internal CU-UP activity accounting not represented by the preserved
  user-plane log records;
- inactivity-counter semantics that differ from simple last-packet timing;
- delayed inactivity evaluation or notification;
- another internal event affecting the inactivity state.

None of these explanations is proven by the available forensic evidence.

The exact origin and internal state of the CU-UP inactivity counter therefore
remain unresolved and must not be inferred from the visible packet timestamps
alone.

## 6. Root-cause assessment

### 6.1 Proven events

The following events are directly supported by the preserved forensic
evidence:

1. The gNB was configured with:

       inactivity_timer: 7200

2. The UE initially registered and established a PDU session successfully.

3. User-plane traffic was observed on both the UE and gNB sides until
   approximately:

       2026-08-07T15:43:10.25 UTC

4. The gNB subsequently generated:

       BearerContextInactivityNotification

5. The inactivity notification was followed by a complete UE-context release
   sequence, including:

       UEContextReleaseRequest
       UEContextReleaseCommand
       RRC rrcRelease
       BearerContextReleaseCommand
       PDU session psi=1 disconnect
       F1 UE context removal
       UEContextReleaseComplete

6. The UE successfully received and decoded the RRC Release.

7. The UE then reset MAC-NR and its EPS bearer manager.

8. No further `RRC-NR` events were recorded by the UE after reception of the
   RRC Release.

9. No subsequent RACH, RRC Setup, RRC Re-establishment, new UE context, or
   new PDU-session setup was recorded by the gNB.

10. Later UE-side traffic caused repeated NAS5G Service Request attempts, but
    no corresponding radio-access procedure became visible at the gNB.

11. User-plane SDUs were subsequently dropped because the expected bearer
    service was no longer available.

12. Native gNB telemetry remained operational but reported:

        ue=NONE

13. All three principal containers remained continuously running with no
    Docker restart, OOM kill, dead state, or process exit.

### 6.2 Probable failure mechanism

The most probable failure mechanism is a post-release state inconsistency on
the srsUE side.

The evidence supporting this assessment is the combination of:

- successful reception of RRC Release;
- local MAC and bearer reset;
- complete absence of later `RRC-NR` procedures;
- absence of a new radio-access procedure at the gNB;
- later NAS5G Service Request attempts that do not result in RRC access;
- continued inability to deliver user-plane SDUs;
- UE PHY activity continuing with the previous `C-RNTI 0x4601` after the gNB
  had already removed the corresponding UE context.

This behaviour is consistent with failure of the UE to transition from the
released state into a functioning new RRC-access procedure when service was
later required.

### 6.3 Unconfirmed hypotheses

The available forensic evidence does not prove:

- a specific software defect in srsUE;
- a specific erroneous source-code function or state-machine transition;
- that the 120 ms RRC-container acknowledgement warning caused the failure;
- that RRC Release was lost on the radio interface;
- that Docker or container runtime state caused the failure;
- that the gNB scheduler stopped operating;
- that Open5GS crashed;
- that the inactivity counter started at the timestamp of the final visible
  user-plane packet;
- that the proposed future keepalive mechanism necessarily resets the
  inactivity counter.

These possibilities must therefore not be presented as established root
causes without additional experimental or source-level evidence.

### 6.4 Root-cause classification

For the current evidence set, the failure is classified as:

    Initiating mechanism:
        inactivity-associated UE/bearer context release

    Confirmed release outcome:
        UE context and PDU-session state removed by the network

    Abnormal subsequent behaviour:
        no functioning UE RRC recovery/access procedure

    Probable failure locus:
        UE-side post-release state/recovery handling

    Specific software defect:
        NOT PROVEN

## 7. Recovery procedure

### 7.1 Recovery principle

The canonical recovery method for this failure class is the validated full
Tb3 Sandy Bridge lifecycle.

An individual restart of only the gNB or only the srsUE is not the default
recovery method because the incident involves state distributed across the
UE, gNB, and 5GC.

The repository-level operator entry points are:

    scripts/tb3-sandybridge-down.sh
    scripts/tb3-sandybridge-up.sh

### 7.2 Controlled shutdown

Execute:

    scripts/tb3-sandybridge-down.sh

The implemented shutdown order is:

    srsUE
      -> gNB
      -> 5GC
      -> docker compose down --remove-orphans

The shutdown script verifies that the service containers are removed.

The normal shutdown procedure intentionally retains:

- Docker images;
- Docker volumes.

The `--volumes` option must not be added unless persistent-volume destruction
is explicitly intended.

### 7.3 Controlled startup

Execute:

    scripts/tb3-sandybridge-up.sh

The implemented startup sequence is:

    5GC
      -> 5GC healthy gate
      -> gNB running gate
      -> srsUE running gate
      -> tun_srsue IPv4 gate

The expected UE tunnel state is:

    interface: tun_srsue
    IPv4 CIDR: 10.45.1.2/24

A successful startup reports:

    TB3_SANDYBRIDGE_UP=PASS
    UE_REGISTRATION_GATE=PASS

### 7.4 Mandatory functional user-plane gate

Container state and the presence of `tun_srsue` are necessary but are not
sufficient to declare recovery complete.

The user plane must be verified explicitly with:

    docker exec base05_srsran_srsue \
      ping -I tun_srsue -c 5 10.45.1.1

The required acceptance criterion is:

    5 packets transmitted
    5 packets received
    0% packet loss

During this analysis, the post-start verification produced:

    UE_CIDR=10.45.1.2/24
    5 packets transmitted
    5 packets received
    0% packet loss

with an observed RTT summary of:

    min/avg/max/mdev = 21.656/31.574/39.346/7.560 ms

This confirms successful end-to-end user-plane operation after recovery.

### 7.5 Recovery acceptance criteria

Recovery is accepted only when all of the following conditions hold:

1. Open5GS is running and healthy.
2. The gNB container is running.
3. The srsUE container is running.
4. `tun_srsue` exists with the expected IPv4 address.
5. UE registration/PDU-session readiness has passed.
6. The functional user-plane probe to `10.45.1.1` succeeds with zero packet
   loss.

A Docker `running` state alone must never be used as the recovery criterion
for this failure class.

## 8. Monitoring criteria

The observed incident demonstrates that Tb3 health cannot be represented by
a single process-level signal. Failure detection must correlate container,
radio-access, native-telemetry, and user-plane observations.

### 8.1 Container and process health

The monitoring layer should record:

- 5GC container state and health status;
- gNB container state;
- srsUE container state;
- Docker restart count;
- OOM-killed state;
- exited or dead state.

These signals are necessary for detecting process failures but are
insufficient for detecting the failure analyzed in this document.

During the observed incident, all three principal containers remained
running while end-to-end UE service was unavailable.

### 8.2 UE tunnel readiness

The UE-side monitoring layer should verify:

    interface: tun_srsue
    expected IPv4 CIDR: 10.45.1.2/24

Tunnel presence is a registration/PDU-session readiness signal.

However, `tun_srsue` must not be used as an independent proof of continuing
user-plane connectivity because the failed state may persist after the
initial tunnel establishment.

### 8.3 Native gNB UE visibility

The native compact telemetry provides an independent gNB-side observation of
UE scheduler visibility.

For experiments requiring a continuously active UE, the monitoring system
should distinguish between:

    ue=<UE metrics>

and:

    ue=NONE

A persistent transition to `ue=NONE` after a previously visible UE should be
treated as a degradation signal when continuous service is expected.

The signal must remain experiment-aware: `ue=NONE` is not necessarily an
error in experiments where intentional UE release or idle operation is part
of the test procedure.

### 8.4 Functional user-plane probe

End-to-end user-plane availability should be tested independently of
container and tunnel state.

The validated probe is:

    ping -I tun_srsue 10.45.1.1

For a controlled health check, the probe result should record:

    UTC timestamp
    experiment ID
    transmitted packets
    received packets
    packet loss
    RTT

A failed probe while containers remain running is a direct indication that
process health and service health have diverged.

### 8.5 Control-plane release events

The following events should be preserved with UTC timestamps when present:

    BearerContextInactivityNotification
    UEContextReleaseRequest
    UEContextReleaseCommand
    RRC rrcRelease
    BearerContextReleaseCommand
    PDU session disconnect
    UEContextReleaseComplete

These events provide the causal context needed to distinguish an intentional
or inactivity-associated release from a process failure.

### 8.6 Cross-layer failure signature

For experiments that require persistent UE service, the following combination
should be treated as a high-confidence stuck-state signature:

    containers running
    AND
    gNB scheduler telemetry active
    AND
    native telemetry persistently reports ue=NONE
    AND
    functional user-plane probe fails

An additional strong inconsistency is:

    tun_srsue exists
    AND
    user-plane probe fails
    AND
    gNB reports no active UE

This combination must not be classified as a healthy Tb3 runtime merely
because Docker reports all containers as running.

### 8.7 Monitoring response

When the cross-layer failure signature is detected, the operational sequence
should be:

    preserve forensic state
      -> record UTC timestamp and experiment ID
      -> preserve relevant UE/gNB/native telemetry
      -> avoid isolated component restart
      -> execute full Tb3 lifecycle if recovery is required
      -> repeat registration and user-plane acceptance gates

This preserves evidence before recovery and prevents process-level health
signals from masking a radio-access or UE-state failure.

## 9. Proposed keepalive policy

The keepalive mechanism described in this section is a proposed operational
safeguard. It has not yet been experimentally validated as a guaranteed method
for resetting the configured gNB inactivity timer.

### 9.1 Intended scope

Keepalive should be used only in experiments where continuous UE attachment
and uninterrupted user-plane availability are explicit experimental
requirements.

Keepalive must be disabled for experiments intended to study:

- inactivity behaviour;
- inactivity-triggered UE release;
- idle-state transitions;
- Service Request behaviour;
- RRC recovery or re-establishment.

Otherwise, keepalive traffic would modify the behaviour that the experiment
is intended to observe.

### 9.2 Proposed mechanism

The proposed mechanism is a minimal user-plane probe transmitted explicitly
through:

    tun_srsue

toward the validated UPF-side gateway:

    10.45.1.1

A candidate probe is:

    ping -I tun_srsue -c 1 -W 2 10.45.1.1

The initial proposed interval is:

    300 s

This interval is substantially shorter than the configured:

    inactivity_timer = 7200 s

while introducing negligible traffic relative to normal Sci_O-RAN throughput
experiments.

### 9.3 Observability requirements

Every keepalive execution should record at least:

- experiment ID;
- UTC transmission timestamp;
- source interface;
- destination address;
- success or failure;
- RTT;
- packet-loss result.

Keepalive packets must be identifiable as control traffic and must not be
mixed with workload traffic when calculating experimental throughput or
latency metrics.

### 9.4 Validation requirement

The proposed keepalive policy must not be considered proven until it is
validated experimentally.

A controlled comparison should include at least:

    Run A: long idle interval without keepalive
    Run B: long idle interval with keepalive

Both runs should extend beyond the configured inactivity interval.

The experiment should determine whether keepalive:

- prevents `BearerContextInactivityNotification`;
- preserves the gNB UE context;
- preserves native UE visibility;
- preserves the PDU session;
- maintains functional user-plane connectivity;
- materially changes workload measurements.

### 9.5 Current status

The current status of this policy is:

    keepalive mechanism: PROPOSED
    interval: 300 s
    operational effectiveness: NOT YET VALIDATED
    effect on inactivity counter: NOT PROVEN

The keepalive mechanism therefore must not be represented as a confirmed fix
for the failure documented here.

Increasing `inactivity_timer` alone is also not considered a canonical fix,
because doing so could mask the post-release recovery problem rather than
demonstrate that recovery operates correctly.

## 10. Limitations

The present analysis has the following limitations.

1. The compact native telemetry capture begins only approximately three
   minutes before the forensic snapshot. It therefore does not preserve the
   transition from an active UE to `ue=NONE`.

2. The forensic evidence does not contain an internal CU-UP inactivity-counter
   trace. The approximately 447-second difference between the configured
   inactivity timer and the observed last-user-plane-to-release interval
   therefore remains unresolved.

3. The forensic bundle does not contain a complete preserved Open5GS
   application-level control-plane log covering the incident.

4. Persistence of `tun_srsue` during the failed state was observed by the
   operator but was not independently preserved in the forensic snapshot as
   an interface-state record.

5. The UE log proves successful reception of RRC Release, but the exact
   internal meaning of the later 120 ms RRC-container acknowledgement warning
   has not been established.

6. The evidence is consistent with a post-release srsUE state/recovery
   inconsistency, but it does not identify a specific source-code defect.

7. A controlled reproduction across multiple inactivity/recovery cycles has
   not yet been performed.

8. The proposed keepalive policy has not yet been validated experimentally
   against the configured inactivity mechanism.

These limitations define the boundary between forensic evidence and
interpretation and must be retained in future publications or technical
reports derived from this incident.

## 11. Final assessment

The observed incident was not caused by a container exit, Docker restart,
OOM termination, or complete gNB scheduler failure.

The preserved evidence establishes the following sequence:

    successful UE registration and PDU-session establishment
      -> user-plane activity
      -> inactivity-associated bearer notification
      -> UE context release
      -> RRC Release
      -> PDU-session removal
      -> gNB UE context removal

The UE successfully received the RRC Release.

The abnormal behaviour occurred afterwards.

No subsequent UE-side RRC procedure was recorded, and the gNB observed no new
RACH, RRC Setup, RRC Re-establishment, or UE-context creation procedure.

When later user-plane traffic triggered NAS5G Service Request attempts, those
attempts did not result in restoration of radio access or the PDU-session user
plane.

The most probable failure interpretation supported by the available evidence
is therefore:

    post-release UE-side recovery/state inconsistency

This interpretation must remain narrower than claiming a confirmed srsUE
software defect.

The validated operational recovery procedure is:

    scripts/tb3-sandybridge-down.sh
      -> scripts/tb3-sandybridge-up.sh
      -> UE registration/tunnel readiness gate
      -> functional user-plane probe to 10.45.1.1
      -> 0% packet loss acceptance criterion

Future Sci_O-RAN observability for long-running Tb3 experiments should combine:

- container and process health;
- UE tunnel readiness;
- native gNB UE visibility;
- control-plane inactivity/release events;
- functional user-plane reachability.

This cross-layer approach is required because the analyzed failure remained
invisible to Docker process-state monitoring alone.
