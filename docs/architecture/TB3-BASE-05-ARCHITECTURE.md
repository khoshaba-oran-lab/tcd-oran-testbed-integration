# Tb3 BASE-05 ZeroMQ Baseline Architecture

## 1. Purpose and Scope

This document describes the architecture of the validated Sci_O-RAN
BASE-05 software-only 5G SA baseline as deployed on the `tb3-dell`
experimental host.

The baseline consists of:

- Open5GS 5G Core;
- srsRAN Project gNB;
- srsUE from srsRAN_4G;
- a ZeroMQ-based virtual RF path between the gNB and UE;
- an IPv4 PDU session through the Open5GS UPF.

The validated baseline does not include:

- Near-RT RIC;
- active E2 agent or E2SM-KPM processing;
- xApps;
- USRP hardware;
- over-the-air RF operation;
- Grafana, InfluxDB, or an external metrics platform.

The canonical baseline identifier is:

`BASE-05-ZMQ-001`

The original baseline and the Tb3 Sandy Bridge portability layer are
documented separately in this file. Post-baseline observability changes,
including the current native gNB JSON metrics configuration, are not treated
as part of the original BASE-05 baseline.

## 2. Logical Architecture

BASE-05 implements a software-only end-to-end 5G SA path on a single
experimental host. The 5G Core, gNB, and UE execute as separate Docker
services connected through a dedicated Docker bridge network.

The logical data and control path is:

    +-------------------------+
    | Open5GS 5GC             |
    | Docker IP: 10.53.1.2    |
    | AMF / UPF functions     |
    +-----------+-------------+
                |
                | N2 / NGAP
                | AMF port 38412
                |
    +-----------v-------------+
    | srsRAN Project gNB      |
    | Docker IP: 10.53.1.3    |
    | NR Band 3, 10 MHz       |
    +-----------+-------------+
                |
                | ZeroMQ virtual RF
                | gNB TX :2000
                | UE TX  :2001
                |
    +-----------v-------------+
    | srsUE                   |
    | Docker IP: 10.53.1.4    |
    +-----------+-------------+
                |
                | IPv4 PDU session
                |
    +-----------v-------------+
    | tun_srsue               |
    | UE: 10.45.1.2/24        |
    +-----------+-------------+
                |
                | User plane
                |
    +-----------v-------------+
    | Open5GS UPF gateway     |
    | 10.45.1.1               |
    +-------------------------+

### 2.1 Docker transport network

The Compose project uses the Docker bridge network:

- logical network name: `ran`;
- resolved Docker network name: `tcd-base05-zmq_ran`;
- subnet: `10.53.1.0/24`.

Static service addresses are:

| Service | Container name | Docker IPv4 address |
|---|---|---|
| Open5GS 5GC | `base05_open5gs_5gc` | `10.53.1.2` |
| srsRAN gNB | `base05_srsran_gnb` | `10.53.1.3` |
| srsUE | `base05_srsran_srsue` | `10.53.1.4` |

The Docker transport network and the UE PDU-session network are distinct.
The `10.53.1.0/24` network provides container-to-container transport,
whereas the validated UE PDU address is `10.45.1.2/24` with UPF gateway
`10.45.1.1`.

### 2.2 ZeroMQ virtual RF path

The radio interface is implemented entirely in software using ZeroMQ.

The gNB configuration defines:

- transmit endpoint: `tcp://*:2000`;
- receive endpoint: `tcp://srsue:2001`;
- base sample rate: `11.52e6` samples/s.

The srsUE configuration defines the complementary endpoints:

- transmit endpoint: `tcp://*:2001`;
- receive endpoint: `tcp://gnb:2000`;
- base sample rate: `11.52e6` samples/s.

Therefore, the virtual RF flow is:

    gNB TX :2000        -------------------->  srsUE RX gnb:2000
    gNB RX srsue:2001   <--------------------  srsUE TX :2001

No USRP device or physical RF interface participates in this baseline.

## 3. Runtime Composition and Tb3 Portability Layer

### 3.1 Original BASE-05 runtime

The canonical BASE-05 runtime is identified as `BASE-05-ZMQ-001` and is
defined by `compose.runtime.yml`.

The original runtime contains three services:

| Service | Function | Original image |
|---|---|---|
| `5gc` | Open5GS 5G Core | `tcd-oran/base05-open5gs:v2.7.0-e584550e` |
| `gnb` | srsRAN Project gNB | `srsran/gnb-zmq:24.10.0-eca587d0597a-v2` |
| `srsue` | srsUE | `srsran/srsue-zmq:23.11-eea87b1d893a` |

The original runtime lock records `RUNTIME_PULL_POLICY=never`.
Consequently, the canonical reference runtime expects the validated images
to be available locally.

The original gNB build was produced with `GNB_BUILD_MARCH=native`.
The baseline lock also records that the original build is not claimed to be
bit-reproducible and that base-image digests and APT package versions were
not fully pinned.

### 3.2 Tb3 Sandy Bridge portability layer

The `tb3-dell` host uses an additional Compose override:

`compose.sandybridge.yml`

The effective Tb3 runtime is therefore produced from:

    compose.runtime.yml
            +
    compose.sandybridge.yml
            |
            v
    Tb3 Sandy Bridge runtime

The Tb3 CPU profile records:

- target architecture: `amd64`;
- CPU microarchitecture: `sandybridge`;
- required CPU flags: `sse4_1`, `sse4_2`, `avx`;
- unavailable CPU flags: `avx2`, `fma`, `avx512f`;
- compiler architecture target: `sandybridge`;
- compiler tuning target: `sandybridge`.

The Sandy Bridge adaptation avoids relying on the reference build's
`-march=native` assumption and provides host-compatible runtime artifacts.

### 3.3 Immutable Tb3 image references

The Tb3 override replaces the original local image references with
registry references pinned by SHA-256 digest.

| Service | Tb3 immutable image reference |
|---|---|
| `5gc` | `khoshaba/tb3-base05-artifacts@sha256:e584550ebb654abcce8801c479d977f97b0397319e5dd92c1e06b7091d92160d` |
| `gnb` | `khoshaba/tb3-base05-artifacts:gnb-zmq-24.10.0-9d5dd742-sandybridge-v1@sha256:7e3a3c4d9e4a46d1e2bf566420e714f8f69f27fa0239a066330c59f0384d6319` |
| `srsue` | `khoshaba/tb3-base05-artifacts:srsue-zmq-23.11-eea87b1d893a-sandybridge-v2@sha256:ea98a2ab87f98037bc172f8422dc1f5fc65ebad21f847bc10b5765b9ecf02410` |

For the Tb3 profile, the effective pull policy is `missing`. An existing
local image may therefore be reused, while a missing image can be retrieved
using its pinned immutable registry reference.

The Docker Hub repository used for these artifacts is private and requires
authentication.

### 3.4 Host environment

The recorded Tb3 host environment is:

| Property | Recorded value |
|---|---|
| Hostname | `tb3-dell` |
| Operating system | `Ubuntu 24.04.4 LTS` |
| Kernel | `6.8.0-137-generic` |
| Architecture | `x86_64` |
| Docker client | `29.7.2` |
| Docker server | `29.7.2` |
| Docker Compose | `5.4.0` |

The authoritative host-environment record is maintained in
`manifests/hosts/tb3-dell.yaml`.

At the recorded provenance point, the Git working tree was not clean.
Therefore, the Git commit identifier alone is insufficient to reconstruct
the exact observed runtime state.

## 4. Runtime Lifecycle and Readiness Gates

### 4.1 Operator entry points

For `tb3-dell`, the repository-level operator entry points are:

- `scripts/tb3-sandybridge-up.sh`;
- `scripts/tb3-sandybridge-down.sh`.

These files are lightweight wrappers. The actual deployment-specific
implementations are maintained under:

`deploy/phase-1-baseline/base-05-zmq/scripts/`

The Tb3 startup and shutdown procedures use both:

- `compose.runtime.yml`;
- `compose.sandybridge.yml`.

Therefore, the Sandy Bridge scripts, rather than the generic
`scripts/compose.sh` helper, define the effective operational lifecycle for
the validated Tb3 deployment.

### 4.2 Startup sequence

The controlled startup order is:

    5gc
      |
      v
     gNB
      |
      v
    srsUE

The startup procedure is intentionally staged.

First, the `5gc` service is started. The procedure waits until the Open5GS
container reports a healthy state.

The configured 5GC health check tests whether TCP port `7777` is reachable
at `127.0.0.20` inside the container.

After the 5GC readiness gate passes, the gNB is started and must reach the
Docker `running` state.

The srsUE is then started and must also reach the Docker `running` state.

The startup script uses `--no-build` and `--no-deps` for the individual
service-start operations. Image construction is therefore outside the
runtime startup procedure.

### 4.3 UE registration and PDU-session readiness

Container state alone is not treated as sufficient evidence that the
end-to-end baseline is ready.

After srsUE startup, the procedure waits for the interface:

`tun_srsue`

inside the UE container.

The presence of an IPv4 address on this interface is used as the operational
UE registration/PDU-session readiness gate.

The validated BASE-05 runtime records:

- UE tunnel: `tun_srsue`;
- UE PDU address: `10.45.1.2/24`;
- UPF gateway: `10.45.1.1`.

Previously validated functional evidence also records successful:

- ZeroMQ IQ flow;
- UE registration;
- PDU-session establishment;
- user-plane connectivity to the UPF gateway;
- overall functional runtime gate.

These validation results describe the established Tb3 baseline and do not
replace future experiment-specific validation.

### 4.4 Shutdown sequence

The controlled shutdown sequence is the reverse of startup:

    srsUE
      |
      v
     gNB
      |
      v
     5gc

After the services are stopped, Docker Compose `down --remove-orphans` is
executed.

Consequently, a normal successful shutdown removes:

- the `5gc`, `gnb`, and `srsue` containers;
- the Compose network.

It does not intentionally remove:

- Docker images;
- Docker volumes.

Therefore, observing no containers in either `docker ps` or `docker ps -a`
is an expected post-shutdown state for this deployment.

### 4.5 Persistent gNB volume

The gNB service uses the named volume:

`tcd-base05-zmq_gnb-storage`

mounted at:

`/tmp`

inside the gNB container.

The normal shutdown procedure does not use `docker compose down --volumes`.
The named volume can therefore persist across normal container lifecycle
operations.

Configuration files for the gNB and srsUE are mounted read-only from the
repository and are not stored in this volume.

## 5. RAN and Protocol Configuration

### 5.1 5G control-plane parameters

The gNB connects to the Open5GS AMF using the following configured
parameters:

| Parameter | Value |
|---|---|
| AMF address | `10.53.1.2` |
| AMF port | `38412` |
| gNB bind address | `10.53.1.3` |
| PLMN | `00101` |
| TAC | `7` |
| SST | `1` |

The gNB-to-AMF control-plane relationship uses NGAP over SCTP.

### 5.2 NR radio configuration

The validated gNB configuration uses:

| Parameter | Value |
|---|---|
| NR band | `3` |
| DL ARFCN | `368500` |
| Channel bandwidth | `10 MHz` |
| Common SCS | `15 kHz` |
| PDSCH MCS table | `qam64` |
| PUSCH MCS table | `qam64` |
| PRACH configuration index | `1` |
| gNB TX gain | `75` |
| gNB RX gain | `75` |
| ZeroMQ sample rate | `11.52 Msps` |

These parameters define the software radio configuration used by the
BASE-05 ZeroMQ link. They do not imply operation of a physical RF front end.

### 5.3 UE radio and protocol configuration

The srsUE side is configured with:

| Parameter | Value |
|---|---|
| RF implementation | `zmq` |
| NR band | `3` |
| NR carriers | `1` |
| E-UTRA carriers | `0` |
| Number of RF antennas | `1` |
| Sample rate | `11.52 Msps` |
| UE TX gain | `50` |
| UE RX gain | `40` |
| RRC release | `15` |
| APN | `srsapn` |
| APN protocol | `ipv4` |
| UE tunnel device | `tun_srsue` |

The UE uses a software USIM configuration for laboratory operation.

Subscriber identifiers and authentication material are intentionally not
reproduced in this architecture document.

### 5.4 Container privileges and host interfaces

The runtime requires elevated container capabilities for selected services.

The `5gc` service runs in privileged mode.

The gNB service:

- runs in privileged mode;
- receives `SYS_NICE`;
- receives `CAP_SYS_PTRACE`.

The srsUE service receives:

- `NET_ADMIN`;
- `SYS_NICE`.

The host device:

`/dev/net/tun`

is exposed to the srsUE container so that the UE-side `tun_srsue`
interface can be created.

These permissions are part of the validated software-only runtime and
should be treated as deployment requirements when reproducing BASE-05.

## 6. Observability and O-RAN Boundary

### 6.1 Original BASE-05 scope

The canonical `BASE-05-ZMQ-001` baseline is a functional software-only
5G SA deployment. Its purpose is to provide a stable end-to-end reference
path before additional observability, O-RAN, system-identification, or
control functionality is introduced.

The original baseline runtime lock explicitly records:

`METRICS_PROFILE_INCLUDED=false`

The original tracked gNB configuration also records:

`e2ap_enable: false`

The validated BASE-05 architecture therefore does not depend on:

- a Near-RT RIC;
- an active E2 agent;
- E2SM-KPM telemetry;
- xApps;
- an external metrics server;
- InfluxDB;
- Grafana.

These components must be treated as later extensions rather than implicit
parts of the baseline.

### 6.2 Native gNB metrics extension

The current working tree contains a post-baseline modification to
`configs/gnb_zmq_base05.yaml` that enables native JSON metrics output.

The locally added configuration is conceptually:

    metrics:
      addr: 10.53.1.1
      port: 55555
      enable_json_metrics: true
      sched_report_period: 1000

This modification is not part of the configuration checksum recorded for
the canonical `BASE-05-ZMQ-001` baseline.

Accordingly, scientific documentation and experiment manifests must
distinguish between:

1. the canonical BASE-05 configuration; and
2. BASE-05 with the native-metrics extension enabled.

Native JSON metrics may be used in later Sci_O-RAN observability work, but
their presence must not retroactively redefine the original baseline.

### 6.3 E2/KPM separation

Native srsRAN JSON metrics and O-RAN E2SM-KPM telemetry are separate
measurement paths.

The availability or validation of native gNB metrics must not be treated as
evidence that:

- an E2 connection exists;
- E2AP procedures are active;
- a Near-RT RIC is connected;
- E2SM-KPM measurements have been validated.

O-RAN E2SM-KPM validation is therefore maintained as a separate Sci_O-RAN
work package.

### 6.4 Baseline preservation principle

Later experimental phases may add telemetry collectors, host observability,
container observability, network measurements, E2/KPM components, runtime
actuators, or closed-loop controllers.

Such extensions should preserve a traceable relationship to
`BASE-05-ZMQ-001` and explicitly record every configuration or runtime
difference that can affect experimental results.

This separation allows the software-only baseline to serve as the stable
reference configuration for comparative experiments.

## 7. Evidence and Provenance

The architecture described in this document is derived from tracked
deployment files, runtime lock files, host manifests, and validated
operational procedures rather than from an assumed reference architecture.

### 7.1 Primary architecture sources

The principal sources for the BASE-05 architecture are:

- `deploy/phase-1-baseline/base-05-zmq/compose.runtime.yml`;
- `deploy/phase-1-baseline/base-05-zmq/configs/gnb_zmq_base05.yaml`;
- `deploy/phase-1-baseline/base-05-zmq/configs/ue_zmq_base05.conf`;
- `deploy/phase-1-baseline/base-05-zmq/locks/base-05-zmq.lock`;
- `deploy/phase-1-baseline/base-05-zmq/locks/base-05-zmq-runtime.lock`.

The Tb3 portability and runtime-specific sources are:

- `deploy/phase-1-baseline/base-05-zmq/compose.sandybridge.yml`;
- `deploy/phase-1-baseline/base-05-zmq/profiles/tb3-dell-sandybridge.env`;
- `deploy/phase-1-baseline/base-05-zmq/scripts/tb3-sandybridge-up.sh`;
- `deploy/phase-1-baseline/base-05-zmq/scripts/tb3-sandybridge-down.sh`;
- `manifests/hosts/tb3-dell.yaml`.

### 7.2 Operational documentation

The existing operational reference is:

`docs/runbooks/BASE-05-ZMQ-RUNBOOK.md`

The runbook documents the original BASE-05 workflow. For the current
`tb3-dell` deployment, the Sandy Bridge startup and shutdown scripts are
the authoritative operator entry points because they combine both the base
Compose model and the host-specific override.

The generic `scripts/compose.sh` helper loads only `compose.runtime.yml`
and therefore does not by itself represent the complete effective Tb3
runtime.

### 7.3 Runtime configuration resolution

The effective Tb3 Compose model is obtained by resolving:

    compose.runtime.yml
            +
    compose.sandybridge.yml

The resolved model is generated evidence and may expose locally supplied
environment values. It must therefore be reviewed and redacted before
publication or archival release.

In particular, subscriber authentication material must not be copied into
public GitHub documentation, datasets, reports, or Zenodo releases.

### 7.4 Evidence classification

Statements in this document are treated according to the Sci_O-RAN
evidence discipline.

Experimental or configuration facts are statements directly supported by:

- tracked configuration;
- lock files;
- host manifests;
- script logic;
- resolved Compose output;
- previously validated functional evidence.

Working hypotheses must be identified separately and must not be presented
as validated system behaviour.

Assumptions requiring verification must not be used as scientific
conclusions until supported by controlled experimental evidence.

### 7.5 Current working-tree qualification

At the time of this architecture review, the repository working tree
contains a local modification that adds native gNB JSON metrics to the
BASE-05 gNB configuration.

Therefore, the current working tree is not identical to the canonical
configuration checksum recorded for `BASE-05-ZMQ-001`.

Any experiment performed from the modified working tree must record this
difference explicitly in its experiment metadata.

## 8. Baseline Invariants and Reproducibility Constraints

The following properties define the architectural identity of the Tb3
BASE-05 software-only baseline.

### 8.1 Runtime topology invariants

The reference topology contains exactly three principal runtime services:

- `5gc`;
- `gnb`;
- `srsue`.

They communicate through the dedicated Docker bridge network associated
with the `tcd-base05-zmq` Compose project.

Adding a Near-RT RIC, xApp, external radio hardware, additional UE, or
alternative 5GC implementation constitutes an architectural extension and
must be recorded explicitly.

### 8.2 Radio-path invariant

The BASE-05 radio path is software-only and uses the complementary ZeroMQ
endpoints on TCP ports `2000` and `2001`.

Replacing ZeroMQ with USRP, another SDR transport, or an OTA RF path changes
the experimental architecture and must not be reported as the unchanged
BASE-05 configuration.

### 8.3 Addressing invariants

The validated Docker service addressing is:

- 5GC: `10.53.1.2`;
- gNB: `10.53.1.3`;
- srsUE: `10.53.1.4`;
- Docker subnet: `10.53.1.0/24`.

The validated UE-side user-plane addressing is:

- UE PDU address: `10.45.1.2/24`;
- UPF gateway: `10.45.1.1`.

Changes to these values may be technically valid, but they must be recorded
as deviations from the validated BASE-05 instance.

### 8.4 Tb3 execution invariant

On `tb3-dell`, the effective runtime is defined by the combination of:

- `compose.runtime.yml`;
- `compose.sandybridge.yml`.

The repository-level `tb3-sandybridge-up.sh` and
`tb3-sandybridge-down.sh` wrappers are the normal Tb3 operator entry points.

Using only the generic base Compose model does not reproduce the complete
Tb3 Sandy Bridge runtime profile.

### 8.5 Image provenance invariant

For reproducible Tb3 execution, the Sandy Bridge image artifacts are
identified by immutable SHA-256 registry references.

A mutable tag alone must not be treated as sufficient provenance when an
immutable digest is available.

If an image is rebuilt, replaced, or resolved to a different digest, that
runtime must be treated as a distinct software provenance state.

### 8.6 Configuration provenance invariant

The canonical BASE-05 gNB and srsUE configurations are tied to checksums in
the baseline lock files.

A modified configuration may still be experimentally useful, but it must be
identified as a baseline extension or experimental variant.

In particular, the current native JSON metrics block is a post-baseline
observability extension and must be recorded explicitly when enabled.

### 8.7 Experiment reproducibility requirement

A future Sci_O-RAN experiment derived from BASE-05 should record at least:

- experiment identifier;
- UTC execution timestamps;
- Git commit and working-tree qualification;
- host/environment manifest reference;
- effective Docker image digests;
- configuration provenance;
- traffic-generation parameters;
- enabled observability extensions;
- validation-gate results;
- references to raw and processed datasets.

This information is required to distinguish a reproducible BASE-05-derived
experiment from an undocumented runtime variation.
