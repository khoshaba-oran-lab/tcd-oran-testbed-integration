# BASE-05 ZeroMQ Baseline Runbook

## Purpose

This runbook describes the validated software-only end-to-end 5G SA
baseline maintained in:

`deploy/phase-1-baseline/base-05-zmq`

## Architecture

    Open5GS 5GC
        |
        | NGAP over SCTP
        v
    srsRAN Project gNB
        |
        | ZeroMQ virtual RF path
        v
    srsUE
        |
        | PDU session
        v
    tun_srsue -> Open5GS UPF

## Validated addresses

- Open5GS: `10.53.1.2`
- gNB: `10.53.1.3`
- srsUE: `10.53.1.4`
- UE PDU address: `10.45.1.2/24`
- UPF gateway: `10.45.1.1`

## Prerequisites

The following Docker images must exist locally:

- `tcd-oran/base05-open5gs:v2.7.0-e584550e`
- `srsran/gnb-zmq:24.10.0-eca587d0597a-v2`
- `srsran/srsue-zmq:23.11-eea87b1d893a`

Create the ignored local Open5GS environment file:

    cd deploy/phase-1-baseline/base-05-zmq
    cp configs/open5gs.env.example configs/open5gs.env
    chmod 600 configs/open5gs.env

## Validate the runtime model

    scripts/compose.sh config --quiet
    scripts/compose.sh config --services
    scripts/compose.sh config --images

Expected services:

- `5gc`
- `gnb`
- `srsue`

## Start the baseline

Normal startup:

    scripts/compose.sh up -d

Controlled staged startup:

    scripts/compose.sh up -d --no-deps 5gc
    scripts/compose.sh up -d --no-deps gnb
    scripts/compose.sh up -d --no-deps srsue

Inspect the project:

    scripts/compose.sh ps --all

## Verify the control plane

The Open5GS container must be healthy:

    docker inspect base05_open5gs_5gc       --format '{{if .State.Health}}{{.State.Health.Status}}{{end}}'

The gNB and Open5GS containers must have an SCTP association on AMF
port `38412`.

## Verify the user plane

Check the UE tunnel address:

    docker exec base05_srsran_srsue       ip -o -4 addr show dev tun_srsue

Expected address:

    10.45.1.2/24

Check connectivity to the UPF gateway:

    docker exec base05_srsran_srsue       ping -I tun_srsue -c 5 10.45.1.1

The validated result is `0% packet loss`.

## Stop the baseline

    scripts/compose.sh down

Do not add `--volumes` unless removal of persistent volumes is explicitly
intended.

## Security

The configuration contains public laboratory subscriber parameters inherited
from the upstream example. They must not be reused for production, physical
SIM or USIM provisioning, or OTA experiments.

The local file `configs/open5gs.env` and generated resolved Compose models
must not be committed.

## Scope

This baseline excludes:

- metrics server;
- InfluxDB;
- Grafana;
- Near-RT RIC;
- E2/KPM processing;
- xApps;
- USRP hardware;
- over-the-air operation.
