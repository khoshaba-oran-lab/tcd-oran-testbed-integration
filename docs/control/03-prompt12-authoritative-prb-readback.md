# Prompt-12 authoritative PRB applied readback

## Canonical source

The authoritative native applied-PRB readback source for Prompt-12 is:

`CONTAINER:/tmp/gnb.log`

The backing `/tmp` path is part of the gNB runtime state. Docker stdout/stderr obtained through `docker logs` is not an authoritative Prompt-12 PRB readback source.

## Native marker

A successful applied readback requires exactly one native marker inside the operation-specific observation window:

`PRB_ACTUATOR_APPLIED`

with both fields:

- `applied_min_prbs`
- `applied_max_prbs`

The expected values must match the intended initial state or scientific transition.

## Runtime identity

The collector fails closed unless the running gNB matches both the expected image ID and expected container incarnation (`StartedAt`).

The collector is:

`scripts/experiment-harness/prompt12-authoritative-prb-readback.py`

Its machine-readable contract is:

`experiments/manifests/prompt12-authoritative-prb-readback-contract-v1.json`

## R6 Stage05 correction

The consumed recovery-only operation

`prompt12-r6-stage05-initial26-20261004T091825Z-7fd698a7`

was retrospectively adjudicated against the authoritative `/tmp/gnb.log`.

The native marker was observed at:

`2026-10-04T09:18:27.644785`

with:

`applied_min_prbs=0`

`applied_max_prbs=26`

Therefore R6 Stage05 is PASS.

This correction does not authorise Stage06, T2 26-to-39, scientific traffic, FIFO triggering, lifecycle mutation, or any replay of the consumed Stage05 operation.
