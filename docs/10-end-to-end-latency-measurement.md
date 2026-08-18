# Sci_O-RAN End-to-End Latency Measurement

## 1. Purpose and scope

This document defines the reproducible user-plane latency measurement
method adopted for the Sci_O-RAN testbed.

The measurement subsystem provides a network-level output for:

- QoS characterization;
- controlled traffic experiments;
- system identification;
- future SISO and MIMO models;
- PID-based control;
- MPC-based control;
- correlation with native gNB telemetry;
- correlation with host, container, and network observability;
- future correlation with O-RAN KPM telemetry.

The canonical latency signal is ICMP round-trip time measured through
the active UE user-plane path.

The native gNB metric `cell_avg_latency` MUST NOT be interpreted as
end-to-end network latency or user-plane RTT. It remains a
source-specific internal gNB metric.

## 2. Validated user-plane measurement path

The canonical RTT path is:

    srsUE
      tun_srsue
      10.45.1.2
          |
          | ICMP Echo Request / Reply
          v
        gNB
          |
          v
    5GC / UPF
      ogstun
      10.45.1.1

Canonical probe configuration:

    source container : base05_srsran_srsue
    source interface : tun_srsue
    source IP        : 10.45.1.2
    destination IP   : 10.45.1.1
    metric           : ICMP RTT

The path was experimentally validated using UE and 5GC interface
counters.

For a 64-byte ICMP payload, the observed IPv4 packet size was
92 bytes.

For 30 request/reply exchanges:

    30 * 92 = 2760 bytes

were observed on the corresponding user-plane interfaces in each
direction.

The reverse UPF-to-UE path was also validated independently.

Therefore this RTT measurement represents the demonstrated
UE-to-UPF user-plane path. It is not an external Internet latency
measurement.

## 3. Measurement tool selection

The existing testbed was inspected before installing any additional
software.

Relevant available tools included:

    ping
    iperf3
    tcpdump
    ss
    tc
    ethtool
    timedatectl
    python3
    nsenter

The adopted RTT mechanism uses the existing `iputils ping`
implementation.

No additional RTT measurement package was required.

The RTT adapter executes the equivalent of:

    ping -n -D \
        -I tun_srsue \
        -i 0.2 \
        -s 64 \
        -W 2 \
        10.45.1.1

The collector operates continuously during the experiment logger
lifecycle.

## 4. Canonical RTT probe profile

The validated Sci_O-RAN profile is:

| Parameter | Value |
|---|---|
| Source container | `base05_srsran_srsue` |
| Source interface | `tun_srsue` |
| Source address | `10.45.1.2` |
| Destination | `10.45.1.1` |
| Protocol | ICMP |
| Sampling interval | 0.2 s |
| Nominal sampling rate | 5 Hz |
| ICMP payload | 64 bytes |
| Observed IPv4 packet size | 92 bytes |
| Reply timeout | 2 s |
| Timestamp mode | `ping -D` |
| Timestamp type | software epoch timestamp |
| RTT clock | source-local elapsed-time measurement |

A 300-sample 5 Hz unloaded validation produced:

    samples : 300
    loss    : 0 %
    mean    : 31.146 ms
    P50     : 31.0 ms
    P95     : 40.4 ms
    P99     : 41.4 ms

## 5. Probe overhead

For a 64-byte ICMP payload at 5 Hz:

    payload rate per direction
    = 64 * 5 * 8
    = 2560 bit/s

At the observed IPv4 packet size of 92 bytes:

    IP rate per direction
    = 92 * 5 * 8
    = 3680 bit/s

For request plus reply:

    bidirectional IP-layer probe rate
    = 7360 bit/s

These values exclude radio, GTP, Ethernet, and other lower-layer
encapsulation overhead.

A B0/B1 functional validation was performed using a 500 kbit/s UDP
downlink workload.

Without the RTT probe:

    throughput   : 500 kbit/s
    iperf jitter : 0.856 ms
    packet loss  : 0/3386

With the 5 Hz RTT probe:

    throughput   : 500 kbit/s
    iperf jitter : 0.892 ms
    packet loss  : 0/3386

The difference in iperf jitter was 0.036 ms.

This is a functional overhead validation. It is not a statistically
exhaustive proof that active probing can never alter runtime state.

The RTT probe creates periodic user-plane traffic and is therefore
part of the experimental condition.

## 6. Workload-dependent RTT behavior

An A-B-A validation demonstrated a reproducible workload-dependent
change in the RTT distribution.

A1, unloaded with active RTT probing:

    mean : 30.635 ms
    P50  : 30.8 ms
    P95  : 40.0 ms
    P99  : 41.0 ms

B, 500 kbit/s controlled UDP downlink:

    mean : 23.891 ms
    P50  : 22.9 ms
    P95  : 38.1 ms
    P99  : 42.1 ms

A2, unloaded with active RTT probing:

    mean : 30.703 ms
    P50  : 30.3 ms
    P95  : 40.0 ms
    P99  : 41.2 ms

The difference between the A1 and A2 mean RTT values was
approximately 0.068 ms.

The loaded-state mean differed by approximately -6.778 ms from the
mean of the two unloaded states.

This demonstrates a reversible workload-dependent runtime-state
effect.

It does NOT establish that additional network traffic intrinsically
improves latency.

It also does NOT identify the responsible mechanism.

Possible contributing mechanisms may include scheduling state,
radio/runtime state, buffering, CPU scheduling, and other system
interactions.

Causal interpretation requires synchronized native gNB, system,
container, network, and future KPM telemetry.

Mean RTT alone is therefore insufficient. P50, P95, and P99 must
remain part of QoS characterization.

## 7. Timestamp semantics

A raw RTT reply has the form:

    [1786365963.658369] 72 bytes from 10.45.1.1:
    icmp_seq=1 ttl=64 time=29.3 ms

The bracketed `ping -D` timestamp is preserved in raw evidence.

Processed samples contain:

    timestamp_utc_ns

expressed as nanoseconds since the Unix epoch.

The processor uses exact decimal conversion.

For example:

    1786365963.658369 s
    ->
    1786365963658369000 ns

Action10.32 validated:

    TIMESTAMP_ERROR_NS=0
    EXACT_TIMESTAMP_CONVERSION=PASS
    ALL_RTT_TIMESTAMPS_EXACT=PASS

No intermediate binary floating-point representation is used for
epoch-to-nanosecond conversion.

RTT itself is calculated locally by the source-side probe.
Consequently inter-node wall-clock synchronization is not necessary
for the RTT value itself.

Clock synchronization remains necessary for cross-source temporal
correlation.

The common processed time coordinate is:

    timestamp_utc_ns

Raw source timestamps MUST remain preserved.

Synthetic timestamps reconstructed only from nominal sample periods
are not permitted.

## 8. Dynamic output y(t)

Processed RTT samples use schema:

    sci_oran_rtt_sample_v1

Each row contains:

    schema
    timestamp_source
    timestamp_utc_ns
    icmp_seq
    rtt_ms

The canonical measured dynamic output is:

    y(t_k) = RTT(t_k)

where:

- `t_k` is represented by `timestamp_utc_ns`;
- `RTT(t_k)` is the observed round-trip delay in milliseconds.

This raw time series is suitable for later system identification.

Experiment-level percentiles are statistical QoS summaries and are
not identical to the instantaneous dynamic output.

Any future moving-window estimator, EWMA, low-pass filter, or other
control-oriented transformation must be explicitly defined as a
separate processing stage.

The raw RTT series MUST NOT be overwritten.

## 9. Reproducible RTT processor

The processor is:

    scripts/experiment-harness/process-rtt.py

Its logical transformation is:

    raw/rtt/ping.log
        ->
    processed/rtt/rtt-samples.jsonl
        ->
    derived/rtt/rtt-summary.json

The processor produces the following sample-level variables:

    timestamp_utc_ns
    icmp_seq
    rtt_ms

The derived QoS summary contains:

- minimum RTT;
- mean RTT;
- population standard deviation;
- P50 RTT;
- P95 RTT;
- P99 RTT;
- maximum RTT;
- RTT mean absolute successive difference;
- closed-sequence packet loss;
- raw ping termination information.

Percentiles use the nearest-rank estimator.

Action10.31 validated:

    RTT_PROCESSOR_RUNTIME=PASS
    PROCESSED_RTT_SAMPLE_COUNT=PASS
    RTT_Y_T_CONTRACT=PASS
    SYNTHETIC_LOSS_AND_CENSORING=PASS

## 10. RTT variation

The adopted RTT variation statistic is the mean absolute successive
difference:

    J_RTT =
        (1 / (N - 1))
        * sum |RTT_i - RTT_(i-1)|

The processor stores it as:

    mean_absolute_successive_difference

This statistic describes variation between consecutive RTT samples.

It MUST NOT be silently interpreted as one-way packet-delay
variation.

It is also distinct from the UDP jitter statistic reported by
iperf3.

Accordingly:

    RTT_MASD_MS

and:

    iperf UDP jitter

are separate measurements.

## 11. Packet-loss accounting

A continuously running ping collector can be interrupted while its
last request is still unresolved.

During lifecycle validation the raw ping summary reported:

    18 packets transmitted
    17 received
    5.55556% packet loss

However, the received sequence identifiers were:

    1 2 3 ... 17

There was no internal sequence gap.

The final outstanding request was terminated with the collector and
is therefore a right-censored boundary probe.

The raw ping summary is preserved as evidence but is not directly
used as the canonical continuous-collector loss estimate.

The canonical closed-sequence method is:

    N_expected = seq_max - seq_min + 1

    N_lost = N_expected - N_unique_replies

    Loss_percent =
        100 * N_lost / N_expected

Requests beyond the maximum successfully received sequence at
collector termination are recorded separately as terminal unresolved
probes.

They are not automatically classified as network loss.

A synthetic sequence:

    1, 2, 4, 5

correctly produced:

    internal missing replies : 1
    closed-sequence loss     : 20 %

Therefore the processor distinguishes true internal missing sequence
numbers from termination right-censoring.

## 12. RTT collector process lifecycle

The RTT adapter is:

    scripts/experiment-harness/adapters/rtt.sh

The first implementation used a direct host-side `docker exec ping`.

Runtime validation demonstrated that stopping the host-side
`docker exec` process could leave the actual `ping` process alive
inside the UE container.

That implementation was rejected.

The corrected implementation uses a container-side PID file:

    /tmp/sci-oran-rtt-collector.pid

The lifecycle is logically:

    harness
        |
        +-- docker exec
                |
                +-- container PID file
                        |
                        +-- exec ping

Shutdown explicitly addresses the process running inside the
container.

Validated lifecycle properties include:

    RTT_CONTAINER_PROCESS_IDENTITY=PASS
    RTT_STOP=PASS
    RTT_HOST_PROCESS_STOPPED=PASS
    RTT_PIDFILE_REMOVED=PASS
    RTT_CONTAINER_PID_STOPPED=PASS
    RTT_ORPHAN_PROCESS_CHECK=PASS

## 13. Logger-stack integration

RTT is now a mandatory collector in the experiment logger stack.

The logger set is:

    resource
    native_gnb
    rtt

Lifecycle:

    LOGGER_START
        |
        +-- resource observer
        +-- native gNB telemetry
        +-- RTT collector
        |
    LOGGER_READY

Runtime validation demonstrated:

    RESOURCE_PROCESS_RUNNING=PASS
    NATIVE_PROCESS_RUNNING=PASS
    RTT_PROCESS_RUNNING=PASS
    LOGGER_STACK_READY=PASS
    RESOURCE_EVIDENCE=PASS
    NATIVE_MEASUREMENT_EVIDENCE=PASS
    RTT_EVIDENCE=PASS
    RTT_TIMESTAMP_EVIDENCE=PASS

After shutdown:

    RESOURCE_PROCESS_STOPPED=PASS
    NATIVE_PROCESS_STOPPED=PASS
    RTT_PROCESS_STOPPED=PASS
    RTT_PIDFILE_REMOVED=PASS
    RTT_ORPHAN_PROCESS_CHECK=PASS

## 14. POSTCHECK contract

The harness POSTCHECK now requires all three logger processes to
remain alive:

    resource
    native_gnb
    rtt

It additionally requires RTT evidence to exist and contain at least
one valid reply sample.

Runtime validation demonstrated:

    POSTCHECK_POSITIVE_CASE=PASS
    POSTCHECK_MISSING_RTT_EVIDENCE_RC=65
    POSTCHECK_MISSING_RTT_EVIDENCE_CASE=PASS
    POSTCHECK_STOPPED_RTT_RC=70
    POSTCHECK_STOPPED_RTT_CASE=PASS

Therefore an experiment cannot successfully pass POSTCHECK if the
RTT logger has died or if its evidence artifact has disappeared.

## 15. Final evidence contract

Final validation requires:

    raw/rtt/ping.log
    raw/rtt/ping.stderr.log

The RTT log must contain at least one syntactically valid RTT reply.

The recursive checksum mechanism includes these artifacts in:

    checksums/SHA256SUMS

Consequently an experiment cannot obtain final state `COMPLETED`
without RTT evidence.

## 16. Full end-to-end harness validation

A complete harness test was executed as:

    EXPERIMENT_ID=EXP-20260810-DL-R00500K-R01
    RUN_ID=RUN-20260810T124603Z-001

The functional traffic profile was:

    direction : downlink
    protocol  : UDP
    rate      : 500 kbit/s
    payload   : 1200 bytes
    duration  : 10 s

The 500 kbit/s workload is a functional validation workload only.

It MUST NOT be interpreted as:

- system capacity;
- saturation threshold;
- optimal operating point;
- system-identification excitation level.

Observed traffic result:

    receiver throughput : 499 kbit/s
    iperf jitter        : 0.766 ms
    packet loss         : 0/521

The full lifecycle reached:

    PRECHECK
    LOGGER_START
    LOGGER_READY
    RUNNING
    COOLDOWN
    POSTCHECK
    LOGGER_STOP
    VALIDATION
    FINALIZATION
    COMPLETED

Final runner state:

    TRAFFIC_EXIT_CODE=0
    FINAL_STATUS=COMPLETED
    RUNNER_COMPLETE=PASS

RTT evidence was included in the checksum set and complete checksum
verification passed.

No RTT orphan process remained after experiment completion.

## 17. RTT results from full harness validation

The complete RTT artifact contained:

    RTT samples : 65

Derived statistics were:

| Metric | Result |
|---|---:|
| Minimum RTT | 12.500 ms |
| Mean RTT | 24.834 ms |
| P50 RTT | 24.700 ms |
| P95 RTT | 39.000 ms |
| P99 RTT | 40.800 ms |
| Maximum RTT | 40.800 ms |
| RTT MASD | 7.781 ms |
| Internal missing replies | 0 |
| Closed-sequence loss | 0.000000% |

These statistics describe the entire RTT artifact generated during
the logger lifecycle.

They are NOT automatically workload-window-only statistics.

The RTT collector starts before traffic begins and remains active
through POSTCHECK.

Workload-specific analysis must therefore select RTT samples using
the recorded experiment boundaries:

    traffic_start_utc
    traffic_end_utc

This distinction is mandatory for future scientific evaluation.

## 18. Reproducibility artifacts

The Prompt 10 implementation consists of:

    scripts/experiment-harness/adapters/rtt.sh
    scripts/experiment-harness/process-rtt.py
    scripts/experiment-harness/lib/logger-stack.sh
    scripts/experiment-harness/lib/preflight.sh
    scripts/experiment-harness/lib/finalization.sh
    scripts/experiment-harness/run-experiment.sh
    docs/10-end-to-end-latency-measurement.md

Canonical RTT raw artifacts are:

    raw/rtt/ping.log
    raw/rtt/ping.stderr.log

Canonical future processed and derived locations are:

    processed/rtt/
    derived/rtt/

## 19. Scientific interpretation rules

The following rules are mandatory for later Sci_O-RAN experiments.

1. `cell_avg_latency` is not user-plane RTT.

2. Mean RTT alone is insufficient for QoS evaluation.

3. P50, P95, and P99 must be retained.

4. RTT MASD and iperf UDP jitter are different metrics.

5. Continuous ping termination summaries must be interpreted with
   right-censoring awareness.

6. Workload-dependent RTT changes must not be causally attributed
   without synchronized supporting telemetry.

7. The 500 kbit/s validation workload is not a capacity estimate.

8. Probe traffic is part of the experimental condition.

9. Raw source timestamps must be retained.

10. Workload-window statistics must use explicit traffic start/end
    boundaries.

11. Future control-oriented filtering must be documented separately.

12. Raw RTT samples must remain immutable evidence.

## 20. Prompt 10 technical acceptance state

The following capabilities have been experimentally demonstrated:

    USER_PLANE_PATH_VALIDATED=PASS
    RTT_5HZ_COLLECTION=PASS
    RTT_TIMESTAMP_ALIGNMENT_CONTRACT=PASS
    RTT_PROBE_OVERHEAD_FUNCTIONAL_VALIDATION=PASS
    RTT_CONTAINER_PROCESS_LIFECYCLE=PASS
    RTT_ORPHAN_PROCESS_CHECK=PASS
    RTT_CLOSED_SEQUENCE_LOSS_METHOD=PASS
    LOGGER_STACK_RTT_INTEGRATION=PASS
    RTT_POSTCHECK_CONTRACT=PASS
    RTT_FINAL_EVIDENCE_CONTRACT=PASS
    FULL_E2E_HARNESS_RTT_VALIDATION=PASS
    RTT_PROCESSOR_RUNTIME=PASS
    RTT_Y_T_CONTRACT=PASS
    EXACT_TIMESTAMP_CONVERSION=PASS

Prompt 10 is technically implemented.

It is not considered fully closed until repository validation and
the GitHub checkpoint have also completed successfully.
