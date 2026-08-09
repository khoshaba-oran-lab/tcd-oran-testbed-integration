# Sci_O-RAN - Resource and Network Observability

## 1. Purpose

Prompt 08 introduces lightweight host, container, and network observability for
the Sci_O-RAN Tb3 environment.

The instrumentation is designed to operate without changing the established Tb3
baseline and without installing additional packages.

The main objective is to collect resource-state information that can later be
time-aligned with native gNB telemetry, traffic-generator measurements, and
derived radio metrics such as `dl_bs`, throughput, latency, and error counters.

An important research objective is to test whether the observed queueing
boundary depends only on radio-resource conditions or is also influenced by
host CPU load, per-core saturation, scheduler contention, ZMQ processing, or
network softirq activity.

## 2. Baseline runtime

The observed Tb3 runtime contains three active containers:

| Role | Container | Docker address |
|---|---|---|
| gNB | `base05_srsran_gnb` | `10.53.1.3/24` |
| srsUE | `base05_srsran_srsue` | `10.53.1.4/24` |
| 5GC | `base05_open5gs_5gc` | `10.53.1.2/24` |

All containers use Docker network `tcd-base05-zmq_ran`.

The corresponding host bridge is `br-bc86fd9f902b` with address
`10.53.1.1/24`.

No new observability packages were installed.

## 3. Available Linux instrumentation

The existing Tb3 system already provides the main required tools and kernel
interfaces:

- `mpstat`, `pidstat`, `sar`, `iostat`, and `vmstat`;
- `docker`;
- `ss`, `ip`, `tc`, and `ethtool`;
- `/proc`;
- `/sys`;
- cgroup v2.

Docker reports:

- cgroup driver: `systemd`;
- cgroup version: `2`.

The final collector therefore relies primarily on `/proc`, `/sys`, cgroup v2,
and a limited number of lightweight system commands.

## 4. Host observability

### 4.1 CPU

The collector records:

- total CPU utilization;
- per-logical-CPU utilization;
- user CPU time;
- system CPU time;
- idle time;
- iowait;
- IRQ;
- softirq;
- steal time.

The Tb3 VM exposes eight logical CPUs: `CPU0` through `CPU7`.

Short baseline measurements demonstrated that individual logical CPUs can
approach saturation even when total host CPU utilization remains substantially
below 100 percent.

Consequently, per-core utilization is a mandatory observable variable.

### 4.2 Load and scheduler state

The host telemetry includes:

- load average for 1, 5, and 15 minutes;
- running-process count;
- blocked-process count;
- cumulative context-switch count;
- cumulative interrupt count;
- process creation count.

Cumulative counters must be converted to interval deltas during dataset
processing.

### 4.3 Memory

Relevant memory values include:

- total memory;
- free memory;
- available memory;
- buffers;
- cache;
- swap;
- dirty memory.

Swap was not configured in the investigated Tb3 baseline.

## 5. CPU frequency and thermal limitations

Tb3 is running as a fully virtualized VM.

The guest reports an Intel Xeon E5-2690 0 nominal frequency close to 2.9 GHz.
However, runtime frequency scaling information is not exposed through the
guest `cpufreq` sysfs interface.

Although `/dev/cpu/*/msr` devices exist, `turbostat` cannot read the required
MSR inside the current VM and returns an I/O error.

Therefore, guest-reported MHz values must not be interpreted as reliable
runtime CPU-frequency measurements.

The collector records these values only as contextual information and explicitly
marks runtime frequency as unreliable.

No usable `thermal_zone*` sensors were exposed to the VM during inventory.
Runtime CPU temperature is therefore currently unavailable from the guest.

The VM configuration was not modified to work around these limitations.

## 6. Container observability

Container resource telemetry is collected primarily through cgroup v2.

For each of gNB, srsUE, and 5GC, the collector records:

- cumulative CPU usage;
- CPU user time;
- CPU system time;
- CPU throttling counters;
- current memory consumption;
- peak memory consumption;
- memory limit;
- memory events;
- current PID count;
- block I/O;
- runtime state;
- restart count;
- OOM-killed state;
- current container PID.

Container PIDs are resolved dynamically because they change after a restart.

At the investigated baseline, all three containers reported:

- `cpu.max = max 100000`;
- no CPU quota;
- `nr_throttled = 0`;
- `throttled_usec = 0`.

Therefore, cgroup CPU quota throttling was not observed during the baseline
measurements.

## 7. Docker network topology

Direct network-namespace verification established the following mapping:

| Component | Container interface | Host interface |
|---|---|---|
| 5GC | `eth0@if71` | `veth4ff68b4` |
| gNB | `eth0@if72` | `veth4a66d06` |
| srsUE | `eth0@if73` | `veth049d2af` |

All three host veth interfaces are attached to `br-bc86fd9f902b`.

The external VM interface is `enp1s0`.

The standard Docker interface `docker0` is not part of the active Tb3
experiment path.

## 8. 5G user-plane interfaces

The srsUE container exposes:

`tun_srsue = 10.45.1.2/24`

The Open5GS container exposes:

`ogstun`

For the currently observed UE, the relevant user-plane subnet is
`10.45.1.0/24`.

The effective tunnel endpoints are:

`10.45.1.2 <-> 10.45.1.1`

Container network counters are readable without repeated `docker exec`,
`sudo`, or `nsenter` operations by using:

`/proc/<container-pid>/net/dev`

The collected interface counters include:

- RX bytes;
- RX packets;
- RX errors;
- RX drops;
- TX bytes;
- TX packets;
- TX errors;
- TX drops.

## 9. Separation of ZMQ and 5G user-plane traffic

A critical result of Prompt 08 is that Docker network I/O must not be
interpreted directly as 5G user-plane throughput.

The gNB and srsUE `eth0` interfaces carry very large cumulative traffic volumes
associated with the internal ZMQ-based radio transport.

During the same observations, `tun_srsue` and `ogstun` showed only minimal
user-plane traffic.

The following traffic classes must therefore remain separate in the Sci_O-RAN
dataset:

1. Docker and ZMQ transport: gNB `eth0`, srsUE `eth0`, host veth interfaces,
   and Docker bridge.
2. 5G user-plane traffic: `tun_srsue` and `ogstun`.
3. External VM traffic: `enp1s0`.

`docker stats` network I/O must not be used as a substitute for 5G user-plane
throughput.

## 10. qdisc observations

The external interface `enp1s0` uses `fq_codel`.

Relevant qdisc information includes:

- transmitted bytes;
- transmitted packets;
- drops;
- overlimits;
- requeues;
- backlog;
- ECN marks.

The Docker bridge and host-side veth interfaces currently use `noqueue`.

The `tun_srsue` and `ogstun` interfaces use `fq_codel` inside their respective
network namespaces.

Because access to their namespace-level qdisc state requires privileged
`nsenter` in the current VM, these qdiscs were validated by read-only spot
checks rather than included in every one-second collector cycle.

This avoids introducing repeated privileged operations into the lightweight
baseline collector.

An existing cumulative `ogstun` TX-drop counter was observed. Two consecutive
snapshots showed no increase, while the corresponding qdisc reported zero
drops and zero backlog.

The value is therefore treated as historical cumulative state rather than
evidence of an active packet-loss condition during the observation interval.

## 11. Softirq and network-processing state

The external interface `enp1s0` uses the `virtio_net` driver.

Substantial cumulative `NET_RX` softirq activity was observed across all eight
logical CPUs.

The collector retains the following softirq categories:

- `NET_RX`;
- `NET_TX`;
- `SCHED`;
- `TIMER`;
- `BLOCK`;
- `RCU`.

These values are cumulative counters. Analysis should use their interval
differences rather than raw absolute values.

## 12. Thread-level findings

Thread-level inventory identified several computationally significant gNB
threads.

Representative short measurements showed approximately:

- gNB `radio`: about 97 percent of one logical CPU;
- gNB `phy_worker`: about 24 percent;
- gNB `ZMQbg/IO/0`: about 40 percent;
- gNB `du_cell#0`: about 15 percent.

These values are representative snapshots and must not be interpreted as fixed
resource requirements.

The srsUE also demonstrated substantial ZMQ processing, with
`srsUE ZMQbg/IO/0` reaching approximately 30 to 35 percent CPU in representative
samples.

The investigated gNB threads use `SCHED_OTHER` and are allowed to execute on
CPUs `0-7`.

Several srsUE threads use real-time `SCHED_FIFO` scheduling:

| Thread | Scheduling policy | Priority |
|---|---|---:|
| `SYNC` | `SCHED_FIFO` | 98 |
| `WORKER0` | `SCHED_FIFO` | 96 |
| `WORKER1` | `SCHED_FIFO` | 96 |
| `WORKER2` | `SCHED_FIFO` | 96 |
| `STACK` | `SCHED_FIFO` | 94 |

These threads are also allowed on CPUs `0-7`.

Short placement snapshots demonstrated CPU migration of gNB `radio`,
`du_cell#0`, and `ZMQbg/IO/0`.

This observation does not establish causal interference between srsUE and gNB.
It demonstrates only that scheduling placement, real-time UE threads, gNB
compute demand, ZMQ processing, and per-core saturation are plausible
confounding factors that must be considered in controlled experiments.

## 13. Queueing-boundary research hypothesis

Prompt 08 establishes the following working hypothesis.

Observed queueing behavior may depend on a combination of:

- radio-resource demand;
- gNB radio and PHY compute demand;
- srsUE compute demand;
- ZMQ transport processing;
- network softirq processing;
- scheduler contention;
- transient per-core saturation.

These relations remain hypotheses. Causal conclusions require controlled,
repeatable experiments in which resource and radio telemetry are aligned on a
common time axis.

## 14. Sampling interval

The selected default sampling interval is:

`1 second`

The first implementation used a relative loop in which collection time was
added to every requested sleep interval.

A ten-sample test showed:

- requested interval: `1.000 s`;
- mean actual interval: approximately `1.035396 s`;
- maximum actual interval: approximately `1.046177 s`.

The collector was therefore changed to monotonic-clock absolute deadlines.

Final cadence validation over six samples produced:

- requested interval: `1.000000 s`;
- steady-state mean interval: `0.999980 s`;
- steady-state minimum: `0.999963 s`;
- steady-state maximum: `0.999992 s`;
- mean absolute cadence error: `0.020 ms`;
- maximum absolute cadence error: `0.037 ms`.

The one-second interval is therefore accepted as the default baseline sampling
period.

## 15. Collector overhead

The final overhead test used ten samples at a requested one-second interval.

Measured process cost was:

- real time: `10.45 s`;
- user CPU time: `0.21 s`;
- system CPU time: `0.22 s`;
- CPU usage reported by `/usr/bin/time`: approximately 4 percent of one logical
  CPU;
- maximum resident memory: approximately `30 MB`.

Tb3 exposes eight logical CPUs. Therefore the observed collector CPU cost
corresponds to a small fraction of total VM compute capacity.

No cgroup CPU throttling was observed for gNB, srsUE, or 5GC during the test.

The instrumentation overhead is considered acceptable for baseline
experiments.

## 16. Implemented collector

The resource and network collector is:

`scripts/tb3-resource-network-observer.py`

Default execution:

`./scripts/tb3-resource-network-observer.py`

Example finite one-minute run:

`./scripts/tb3-resource-network-observer.py --interval 1 --count 60`

Example JSONL capture:

`./scripts/tb3-resource-network-observer.py --interval 1 --count 60 > resource-network.jsonl`

The schema identifier is:

`sci_oran_resource_network_observability_v1`

Each JSONL record contains:

- UTC timestamp;
- Unix timestamp in nanoseconds;
- sample number;
- requested sampling interval;
- actual sampling interval;
- host CPU and per-core CPU state;
- load and scheduler counters;
- memory state;
- softirq counters;
- guest frequency context and reliability flag;
- thermal availability state;
- host network-interface counters;
- periodically sampled `enp1s0` qdisc data;
- container runtime state;
- container cgroup CPU, memory, PID, and block-I/O metrics;
- network counters from each container namespace.

## 17. Integration with native gNB telemetry

The existing native gNB telemetry implementation remains unchanged:

`scripts/tb3-native-metrics-compact.sh`

Resource/network observability is intentionally maintained as an independent
collector.

This separation preserves the current Tb3 baseline and avoids coupling native
gNB metric reception with host instrumentation.

Future experiment processing should time-align:

- native gNB telemetry;
- resource/network observability;
- traffic-generator measurements;
- experiment metadata.

The resulting common timeline will support correlation of radio behavior with
host and network resource state.

## 18. Operational constraints

The following constraints must be preserved in later experiments:

1. Do not interpret container `NetIO` as 5G user-plane throughput.
2. Do not interpret guest-reported CPU MHz as reliable dynamic frequency.
3. Convert cumulative counters to interval deltas before rate analysis.
4. Resolve container PIDs dynamically after container restart.
5. Preserve UTC timestamps for every sample.
6. Preserve per-core CPU metrics.
7. Keep the resource collector independent of native gNB telemetry collection.
8. Avoid introducing privileged continuous instrumentation unless required by a
   later controlled experiment.
9. Treat thread-placement observations as descriptive evidence, not proof of
   causal interference.
10. Treat the queueing-boundary resource hypothesis as unconfirmed until tested
    under controlled and reproducible traffic conditions.

## 19. Prompt 08 outcome

Prompt 08 establishes a lightweight and reproducible observability layer for
the Sci_O-RAN Tb3 platform.

The implemented collector provides the principal computational, container, and
network variables required to investigate whether changes in `dl_bs`,
throughput, latency, or queueing behavior correlate with resource pressure in
addition to radio-resource conditions.

The selected baseline sampling interval is one second, with UTC timestamps and
nanosecond Unix timestamps available for later integration with native gNB
telemetry and the Sci_O-RAN experiment dataset.
