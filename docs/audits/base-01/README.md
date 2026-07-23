# BASE-01 — Audit of docker-compose_no_ric.yml

## Objective

Inspect the CONVERGE no-RIC reference deployment before its first build
and execution on the remote testbed VM.

## Upstream

- Repository: merimdzaferagic/CONVERGE-summer-school
- Branch: main
- Commit: b1d6d36334a44a0dfeaacd643b82948259355d7c

## Baseline architecture

- Open5GS 5G Core
- srsRAN gNB
- dummy radio unit
- synthetic test-mode UE
- metrics server
- InfluxDB
- Grafana

## Scope clarification

This configuration does not contain:

- a standalone software UE;
- a ZeroMQ radio path;
- a Near-RT RIC;
- an E2 Agent configuration;
- an xApp;
- USRP support in the current gNB image.

## Published ports

- TCP 9999: Open5GS WebUI
- TCP 3300: Grafana
- UDP 55555: metrics server

These ports must be reviewed before the first run because the reference
Compose file publishes them on the host.

## Docker networks

- 10.53.1.0/24: RAN and 5GC
- 172.19.1.0/24: metrics pipeline

## Persistent volumes

- gnb-storage
- influxdb-storage
- grafana-storage

## Security observations

- Reference credentials are present in the public example configuration.
- Grafana anonymous access is enabled.
- The 5GC and gNB containers use privileged mode.
- Published ports should be restricted for the remote VM.
- Reference credentials must never be reused for real SIM/USIM operation.

## Reproducibility observations

- Some external images use mutable version tags rather than immutable digests.
- The runtime image digests must be recorded after pull/build.
- The repository and srsRAN source commits must be recorded.
- Host and container timestamps must be normalised or documented.

## Current decision

Status: PENDING

The deployment may proceed to BASE-02 only after:

- Compose validation passes;
- required files exist;
- ports are free;
- Docker subnets do not conflict;
- the safe first-run port-binding plan is approved.

## Portability and evidence classification

`compose-model-unresolved.yml` is a raw BASE-01 audit snapshot produced
from the upstream Compose model on the reference VM.

It intentionally preserves absolute source-VM paths such as
`/home/ubuntu/upstream/CONVERGE-summer-school/...`. These paths are
historical evidence and are not intended to be portable or executable
from this repository.

The portable BASE-05 runtime is maintained separately under:

`deploy/phase-1-baseline/base-05-zmq/compose.runtime.yml`

Commit-readiness portability checks must apply to operational deployment
files. The raw BASE-01 snapshot is allowed only as explicitly classified
audit evidence and must not be used as a runtime Compose file.
