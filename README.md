# TCD O-RAN Testbed Integration

Private integration workspace for reproducing the CONVERGE software-only
srsRAN baseline, validating RIC/E2/KPM workflows, developing a read-only
E2/KPM telemetry collector xApp, and preparing a future USRP-based OTA
validation stage.

## Project phases

### Phase I-A — CONVERGE Software-Only Baseline

- Open5GS 5G Core
- srsRAN gNB
- srsRAN test mode
- metrics server
- InfluxDB
- Grafana

### Phase I-B — Full Software UE Connectivity

Validated software-only end-to-end 5G SA connectivity using:

- Open5GS 5G Core;
- srsRAN Project gNB;
- ZeroMQ virtual RF transport;
- pinned srsUE from srsRAN_4G;
- operational PDU session and user-plane connectivity.

Deployment files are maintained under:

`deploy/phase-1-baseline/base-05-zmq`

### Phase II-A — FlexRIC E2/KPM Smoke Test

Validate E2 Setup, E2-node registration and reference KPM indications.

### Phase II-B — O-RAN SC Reference xApp

Validate the reference O-RAN SC Near-RT RIC and Python KPM monitoring xApp.

### Phase II-C — Read-Only E2/KPM Telemetry Collector xApp

Develop the custom collector, structured data output and experiment manifest.

### Phase II-D — Optional AI-Native Telemetry Integration

Evaluate the ai_nn_controller InfluxDB/ZeroMQ/REST/MCP data path separately
from the standard E2/KPM xApp path.

### Phase III — USRP-Based OTA Validation

Connect the validated software workflow to an approved USRP and physical UE.

## Repository policy

- No credentials, SSH keys or SIM/USIM secrets.
- No private testbed addressing in committed files.
- No raw subscriber payloads.
- No unapproved RF configuration.
- No large datasets or packet captures in Git.
- Testbed-specific artifacts must be reviewed before publication.
