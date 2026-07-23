# BASE-05 ZeroMQ Software-Only Baseline

This directory contains the portable runtime and pinned source artifacts
for the validated BASE-05 software-only end-to-end 5G SA deployment.

## Architecture

- Open5GS 5G Core
- srsRAN Project gNB with the ZeroMQ RF driver
- srsUE from pinned srsRAN_4G source
- Docker network transport between the gNB and UE
- No Near-RT RIC
- No active E2 agent
- No USRP or over-the-air RF path

## Imported artifacts

- `docker/Dockerfile.gnb-zmq`
- `docker/Dockerfile.srsue-zmq`
- `configs/gnb_zmq_base05.yaml`
- `configs/ue_zmq_base05.conf`
- `locks/srsue-zmq.source.lock`
- `locks/base-05-zmq.lock`
- `locks/import-manifest.tsv`

The imported artifacts were admitted only after the BASE-06A integrity
and sensitive-field equivalence gates passed.

## Security note

The UE configuration contains laboratory subscriber identifiers and
authentication parameters inherited unchanged from the tracked upstream
example. They must not be reused as production or OTA subscriber
credentials.

## Runtime status

The portable runtime is implemented in `compose.runtime.yml` and managed
through `scripts/compose.sh`.

The validated deployment contains:

- Open5GS 5GC at `10.53.1.2`;
- srsRAN gNB at `10.53.1.3`;
- srsUE at `10.53.1.4`;
- UE PDU address `10.45.1.2/24`;
- UPF gateway `10.45.1.1`.

The resolved Compose model is generated evidence and must not be committed.
