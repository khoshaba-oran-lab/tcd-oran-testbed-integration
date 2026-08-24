# Prompt 12 T2 day-end handoff — 2026-08-24

## Scope

This checkpoint closes the 2026-08-24 runtime session before the
first scientific T2 estimation replication.

T2 remains the open-loop SISO transition:

- initial input: 26 PRB;
- target input: 39 PRB;
- delta-u: +13 PRB;
- workload: UDP DL 18000 kbit/s;
- primary output: receiver throughput;
- plant step origin: U_APPLIED_READBACK.

No PI/PID synthesis has started.

## T2 reset-to-26

Reset operation:

`prompt12-t2-reset-to26-20260824T170410Z-30c31515`

Status:

- exactly one reset trigger was consumed;
- reset trigger is NEVER_REPEAT;
- replay is forbidden;
- exactly one E2SM-RC Control Request was sent;
- Control ACK was received;
- authoritative native gNB readback proved
  `applied_min_prbs=0` and `applied_max_prbs=26`;
- trigger-to-applied latency was 27.601479 ms;
- authoritative native gNB log is `/tmp/gnb.log`.

The reset must never be replayed.

## Observability finding

The current gNB incarnation produced a startup event:

`PRB_ACTUATOR_APPLIED ... applied_max_prbs=275`

before the first E2 Control Request.

Therefore incarnation-wide PRB_ACTUATOR_APPLIED count is not a valid
proxy for E2 Control count.

Control association must be time ordered:

`Control Request -> PRB_ACTUATOR_APPLIED -> Control ACK`.

## T2 R01 identity created but not consumed

Operation:

`prompt12-t2-r01-26to39-20260824T174345Z-064e8bc9`

Experiment:

`EXP-20260824-T2-26TO39-DL-18000K-R01`

Run:

`RUN-20260824T174345Z-016`

Evidence root:

`/home/khoshaba/sci-oran-evidence/prompt12/t2-26to39/prompt12-t2-r01-26to39-20260824T174345Z-064e8bc9-v1`

At day-end:

- actuator was never created or started;
- workload was never started;
- no pre-stationarity measurement was performed;
- trigger write attempt count is zero;
- scientific trigger count is zero;
- no T2 scientific Control was executed.

This run is therefore classified:

`ABANDONED_PRETRIGGER_PLANNED_DAY_STOP`

It is not a consumed scientific R01 replication.

Because its frozen initial-state provenance references the current
runtime incarnation, this operation ID, experiment ID, and run ID must
not be reused after day-stop/day-start.

The next runtime session must create a fresh R01 identity after fresh
runtime admission and authoritative proof of the required 26 PRB
initial state.

## Evidence integrity

Day-end handoff:

`/home/khoshaba/sci-oran-evidence/prompt12/t2-26to39/prompt12-t2-r01-26to39-20260824T174345Z-064e8bc9-v1/DAY-END-HANDOFF.env`

SHA256:

`339fa94e23b446c6d77f4ae8b14172a93aa7f30b88337a550059a00d11230a01`

Day-end checksum manifest:

`/home/khoshaba/sci-oran-evidence/prompt12/t2-26to39/prompt12-t2-r01-26to39-20260824T174345Z-064e8bc9-v1/DAY-END-SHA256SUMS`

SHA256:

`a20ea3957b950fd3af0049935351eacbf61859650be3c701d3cedba82ba39411`

## Next-session boundary

After the planned lifecycle day-stop, the next session must:

1. perform lifecycle day-start on coll.vntu.org;
2. verify the new runtime incarnation on tb3-dell;
3. not infer 26 PRB from this expired runtime session;
4. authoritatively establish or prove 26 PRB;
5. create fresh T2 R01 operation/experiment/run identities;
6. prearm actuator V2 for 75 percent / expected 39 PRB;
7. start the frozen UDP DL 18000 kbit/s workload;
8. satisfy the frozen pre-step stationarity gate;
9. execute exactly one T2 R01 scientific trigger;
10. use U_APPLIED_READBACK as t0.

The consumed T2 reset trigger and all consumed T1 triggers remain
NEVER_REPEAT.
